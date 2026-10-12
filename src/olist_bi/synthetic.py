"""Synthetic Olist-shaped dataset generator for development, tests and CI.

NOT real data. It reproduces the 9-file schema, the Olist quirks that break naive pipelines
(multi-payment and multi-review orders, canceled orders, missing delivery dates, categories
without translation, repeat customers) and PLANTS one known business problem so the agent
can later be validated against a known ground truth:

    Planted scenario: in 2018-Q2 the `health_beauty` category loses volume and its delivery
    performance collapses, driven by two specific sellers (SELLER_BAD_1 / SELLER_BAD_2).
    Late deliveries from those sellers push review scores down.

Real Olist files dropped into data/raw/ replace this entirely.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from .etl.files import TABLE_FILES

CATEGORIES = {  # pt name -> (english, weight, base price)
    "cama_mesa_banho": ("bed_bath_table", 11, 90),
    "beleza_saude": ("health_beauty", 10, 130),
    "esporte_lazer": ("sports_leisure", 9, 110),
    "informatica_acessorios": ("computers_accessories", 8, 120),
    "moveis_decoracao": ("furniture_decor", 8, 85),
    "utilidades_domesticas": ("housewares", 7, 70),
    "relogios_presentes": ("watches_gifts", 6, 200),
    "telefonia": ("telephony", 5, 60),
    "automotivo": ("auto", 4, 100),
    "brinquedos": ("toys", 4, 95),
    "cool_stuff": ("cool_stuff", 4, 140),
    "perfumaria": ("perfumery", 4, 80),
    "bebes": ("baby", 3, 100),
    "eletronicos": ("electronics", 3, 75),
    "ferramentas_jardim": ("garden_tools", 3, 90),
    "papelaria": ("stationery", 3, 40),
    "livros_tecnicos": ("books_technical", 1, 55),
    "pet_shop": ("pet_shop", 2, 70),
    "pc_gamer": (None, 1, 400),  # deliberately missing from the translation table
}
PLANTED_CATEGORY = "beleza_saude"
PLANTED_START, PLANTED_END = pd.Timestamp("2018-04-01"), pd.Timestamp("2018-06-30 23:59:59")
SELLER_BAD_1, SELLER_BAD_2 = "seller_bad_0001", "seller_bad_0002"

STATES = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "GO", "ES", "PE", "CE"]
STATE_W = np.array([42, 13, 12, 6, 6, 4, 4, 3, 3, 2, 3, 2], dtype=float)
FMT = "%Y-%m-%d %H:%M:%S"


def _hid(prefix: str, i: int) -> str:
    return hashlib.md5(f"{prefix}-{i}".encode()).hexdigest()


def generate(out_dir: Path, n_orders: int = 6000, seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_p = STATE_W / STATE_W.sum()

    # ---------- geolocation / zip prefixes ----------
    zips = rng.integers(1000, 99000, size=400)
    geo = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": np.repeat(zips, 3),
            "geolocation_lat": rng.uniform(-30, -5, size=zips.size * 3).round(6),
            "geolocation_lng": rng.uniform(-52, -35, size=zips.size * 3).round(6),
            "geolocation_city": "sao paulo",
            "geolocation_state": rng.choice(STATES, size=zips.size * 3, p=state_p),
        }
    )

    # ---------- products ----------
    cat_names = list(CATEGORIES)
    cat_w = np.array([CATEGORIES[c][1] for c in cat_names], dtype=float)
    n_products = 1500
    prod_cat = rng.choice(cat_names, size=n_products, p=cat_w / cat_w.sum())
    base_price = np.array([CATEGORIES[c][2] for c in prod_cat]) * rng.lognormal(0, 0.45, n_products)
    products = pd.DataFrame(
        {
            "product_id": [_hid("p", i) for i in range(n_products)],
            "product_category_name": prod_cat,
            "product_name_lenght": rng.integers(20, 70, n_products),
            "product_description_lenght": rng.integers(100, 2000, n_products),
            "product_photos_qty": rng.integers(1, 8, n_products),
            "product_weight_g": rng.integers(100, 8000, n_products).astype(float),
            "product_length_cm": rng.integers(10, 80, n_products).astype(float),
            "product_height_cm": rng.integers(2, 50, n_products).astype(float),
            "product_width_cm": rng.integers(8, 60, n_products).astype(float),
        }
    )
    missing_cat = rng.random(n_products) < 0.03
    products.loc[missing_cat, "product_category_name"] = np.nan  # real data has these too
    translation = pd.DataFrame(
        [(pt, en) for pt, (en, _, _) in CATEGORIES.items() if en is not None],
        columns=["product_category_name", "product_category_name_english"],
    )

    # ---------- sellers ----------
    n_sellers = 120
    seller_ids = [SELLER_BAD_1, SELLER_BAD_2] + [_hid("s", i) for i in range(n_sellers - 2)]
    sellers = pd.DataFrame(
        {
            "seller_id": seller_ids,
            "seller_zip_code_prefix": rng.choice(zips, n_sellers),
            "seller_city": "sao paulo",
            "seller_state": rng.choice(STATES, n_sellers, p=state_p),
        }
    )
    sellers.loc[:1, "seller_state"] = "SP"
    pools: dict[str, list[str]] = {c: [] for c in cat_names}
    for i, sid in enumerate(seller_ids):
        for c in rng.choice(cat_names, size=2, replace=False):
            pools[c].append(sid)
        if i < 2:
            pools[PLANTED_CATEGORY].append(sid)
    for c in cat_names:  # make sure every pool has enough sellers
        while len(pools[c]) < 4:
            pools[c].append(seller_ids[int(rng.integers(2, n_sellers))])
    # the two planted sellers dominate the planted category
    pools[PLANTED_CATEGORY] += [SELLER_BAD_1, SELLER_BAD_2] * 6

    # ---------- order timeline ----------
    months = pd.period_range("2017-01", "2018-08", freq="M")
    growth = np.linspace(0.3, 1.0, len(months))
    season = np.array([1.6 if (m.month == 11 and m.year == 2017) else 1.0 for m in months])
    month_p = growth * season / (growth * season).sum()
    order_months = rng.choice(len(months), size=n_orders, p=month_p)
    purchase = []
    for mi in order_months:
        start = months[mi].start_time
        days = months[mi].days_in_month
        purchase.append(
            start + pd.Timedelta(days=int(rng.integers(0, days)), seconds=int(rng.integers(0, 86400)))
        )
    purchase = pd.Series(purchase)

    # ---------- customers (repeat buyers ~3%) ----------
    n_unique = int(n_orders * 0.97)
    unique_ids = [_hid("cu", i) for i in range(n_unique)]
    cust_unique = np.concatenate([np.arange(n_unique), rng.integers(0, n_unique, n_orders - n_unique)])
    rng.shuffle(cust_unique)
    customers = pd.DataFrame(
        {
            "customer_id": [_hid("c", i) for i in range(n_orders)],
            "customer_unique_id": [unique_ids[i] for i in cust_unique],
            "customer_zip_code_prefix": rng.choice(zips, n_orders),
            "customer_city": "sao paulo",
            "customer_state": rng.choice(STATES, n_orders, p=state_p),
        }
    )

    # ---------- orders, items, payments, reviews ----------
    prod_by_cat = {c: products.index[products["product_category_name"] == c].to_numpy() for c in cat_names}
    order_rows, item_rows, pay_rows, rev_rows = [], [], [], []
    status_vals = ["delivered", "canceled", "shipped", "unavailable", "invoiced", "processing"]
    status_p = [0.965, 0.012, 0.009, 0.006, 0.004, 0.004]

    for i in range(n_orders):
        oid = _hid("o", i)
        ts = purchase[i]
        in_window = PLANTED_START <= ts <= PLANTED_END
        # category weights, with the planted demand drop
        w = cat_w.copy()
        if in_window:
            w[cat_names.index(PLANTED_CATEGORY)] *= 0.55
        n_items = int(rng.choice([1, 2, 3], p=[0.88, 0.09, 0.03]))
        touches_bad_seller = False
        total_price = total_freight = 0.0
        for k in range(n_items):
            cat = cat_names[int(rng.choice(len(cat_names), p=w / w.sum()))]
            cand = prod_by_cat[cat]
            if len(cand) == 0:
                continue
            pidx = int(rng.choice(cand))
            sid = str(rng.choice(pools[cat]))
            if sid in (SELLER_BAD_1, SELLER_BAD_2) and cat == PLANTED_CATEGORY and in_window:
                touches_bad_seller = True
            price = round(float(base_price[pidx] * rng.uniform(0.9, 1.1)), 2)
            freight = round(
                float(max(5.0, 7 + products.at[pidx, "product_weight_g"] * 0.0018 + rng.normal(0, 2))), 2
            )
            total_price += price
            total_freight += freight
            item_rows.append(
                {
                    "order_id": oid,
                    "order_item_id": k + 1,
                    "product_id": products.at[pidx, "product_id"],
                    "seller_id": sid,
                    "shipping_limit_date": ts + pd.Timedelta(days=int(rng.integers(2, 6))),
                    "price": price,
                    "freight_value": freight,
                }
            )
        status = str(rng.choice(status_vals, p=status_p))
        est = ts + pd.Timedelta(days=int(rng.integers(12, 30)))
        approved = ts + pd.Timedelta(hours=int(rng.integers(1, 30)))
        carrier = delivered = pd.NaT
        late = False
        if status in ("delivered", "shipped"):
            carrier = approved + pd.Timedelta(days=int(rng.integers(1, 4)))
        if status == "delivered":
            p_late = 0.70 if touches_bad_seller else 0.07
            late = bool(rng.random() < p_late)
            offset = rng.uniform(1, 14) if late and touches_bad_seller else rng.uniform(1, 8)
            delivered = est + pd.Timedelta(days=offset if late else -offset)
            delivered = max(delivered, carrier + pd.Timedelta(days=2))
            late = delivered > est
        order_rows.append(
            {
                "order_id": oid,
                "customer_id": customers.at[i, "customer_id"],
                "order_status": status,
                "order_purchase_timestamp": ts,
                "order_approved_at": approved if status != "created" else pd.NaT,
                "order_delivered_carrier_date": carrier,
                "order_delivered_customer_date": delivered,
                "order_estimated_delivery_date": est,
            }
        )

        # payments (10% split across voucher + other method)
        total = round(total_price + total_freight, 2)
        ptype = str(
            rng.choice(["credit_card", "boleto", "voucher", "debit_card"], p=[0.74, 0.19, 0.055, 0.015])
        )
        if rng.random() < 0.10 and total > 20:
            v = round(total * rng.uniform(0.1, 0.4), 2)
            splits = [("voucher", v), (ptype if ptype != "voucher" else "credit_card", round(total - v, 2))]
        else:
            splits = [(ptype, total)]
        for seq, (pt, val) in enumerate(splits, start=1):
            pay_rows.append(
                {
                    "order_id": oid,
                    "payment_sequential": seq,
                    "payment_type": pt,
                    "payment_installments": int(rng.integers(1, 10)) if pt == "credit_card" else 1,
                    "payment_value": val,
                }
            )

        # reviews: lateness drives score
        if status in ("delivered", "canceled") and rng.random() < 0.98:
            if status == "canceled":
                p = [0.5, 0.3, 0.1, 0.07, 0.03]
            elif late:
                p = [0.40, 0.20, 0.13, 0.12, 0.15]
            else:
                p = [0.08, 0.04, 0.08, 0.20, 0.60]
            n_rev = 2 if rng.random() < 0.01 else 1
            for _ in range(n_rev):
                score = int(rng.choice([1, 2, 3, 4, 5], p=p))
                created = (delivered if pd.notna(delivered) else ts) + pd.Timedelta(days=1)
                rev_rows.append(
                    {
                        "review_id": _hid("r", len(rev_rows)),
                        "order_id": oid,
                        "review_score": score,
                        "review_comment_title": np.nan,
                        "review_comment_message": (
                            "Produto chegou atrasado" if late and score <= 2 else np.nan
                        ),
                        "review_creation_date": created,
                        "review_answer_timestamp": created + pd.Timedelta(days=int(rng.integers(1, 4))),
                    }
                )

    tables = {
        "customers": customers,
        "orders": pd.DataFrame(order_rows),
        "order_items": pd.DataFrame(item_rows),
        "payments": pd.DataFrame(pay_rows),
        "reviews": pd.DataFrame(rev_rows),
        "products": products,
        "sellers": sellers,
        "geolocation": geo,
        "category_translation": translation,
    }
    for name, df in tables.items():
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime(FMT)
        df.to_csv(out_dir / TABLE_FILES[name], index=False)
    return tables
