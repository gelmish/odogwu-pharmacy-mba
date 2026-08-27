"""
Step 1: Generate synthetic pharmacy sales data and load into SQLite.
Simulates 12 months of transactions at Odogwu Pharmacy.
"""

import sqlite3
import random
import pandas as pd
from datetime import datetime, timedelta

random.seed(42)

DB_PATH = "/home/claude/odogwu_pharmacy.db"

# ── Product catalogue ──────────────────────────────────────────────────────────
PRODUCTS = [
    # (product_id, name, category, unit_price)
    (1,  "Paracetamol 500mg",        "Analgesics",         150),
    (2,  "Ibuprofen 400mg",          "Analgesics",         200),
    (3,  "Vitamin C 1000mg",         "Vitamins",           350),
    (4,  "Zinc Supplement",          "Vitamins",           280),
    (5,  "Amoxicillin 500mg",        "Antibiotics",        600),
    (6,  "Metronidazole 400mg",      "Antibiotics",        400),
    (7,  "ORS Sachets",              "Rehydration",        120),
    (8,  "Omeprazole 20mg",          "Gastro",             450),
    (9,  "Antacid Suspension",       "Gastro",             300),
    (10, "Chloroquine 250mg",        "Antimalarials",      350),
    (11, "Artemether-Lumefantrine",  "Antimalarials",      900),
    (12, "Folic Acid 5mg",           "Maternal Health",    180),
    (13, "Iron Supplement",          "Maternal Health",    250),
    (14, "Cetirizine 10mg",          "Antihistamines",     200),
    (15, "Loratadine 10mg",          "Antihistamines",     220),
    (16, "Cough Syrup",              "Respiratory",        380),
    (17, "Nasal Decongestant",       "Respiratory",        260),
    (18, "Multivitamin Tablets",     "Vitamins",           500),
    (19, "Blood Pressure Monitor",   "Devices",           5500),
    (20, "Glucometer Strips",        "Devices",           1200),
    (21, "Metformin 500mg",          "Diabetes",           350),
    (22, "Amlodipine 5mg",           "Cardiovascular",     400),
    (23, "Lisinopril 10mg",          "Cardiovascular",     450),
    (24, "Atorvastatin 20mg",        "Cardiovascular",     600),
    (25, "Sunscreen SPF50",          "Skincare",           800),
]

# Realistic co-purchase patterns (cross-sell pairs)
BUNDLES = [
    ([1, 2],       0.30),   # dual analgesics
    ([1, 7],       0.25),   # fever + ORS
    ([3, 4],       0.40),   # Vit C + Zinc (immune combo)
    ([3, 18],      0.35),   # Vit C + multivitamin
    ([5, 8],       0.28),   # antibiotic + PPI (gut protection)
    ([5, 6],       0.20),   # dual antibiotics (common Rx)
    ([10, 11],     0.15),   # malaria meds
    ([11, 7],      0.30),   # malaria + ORS
    ([12, 13],     0.55),   # maternal health combo
    ([14, 16],     0.35),   # allergy + cough
    ([17, 16],     0.40),   # cold combo
    ([21, 22],     0.25),   # diabetes + BP
    ([21, 20],     0.45),   # metformin + glucometer strips
    ([22, 23],     0.20),   # dual BP meds
    ([22, 24],     0.30),   # BP + statin
    ([19, 20],     0.50),   # BP monitor + glucometer strips
    ([8,  9],      0.35),   # dual gastro
]


def generate_transactions(n_transactions=3000):
    rows = []
    base_date = datetime(2024, 1, 1)
    product_ids = [p[0] for p in PRODUCTS]

    for txn_id in range(1, n_transactions + 1):
        # Random date across 12 months, with slight weekend boost
        day_offset = random.randint(0, 364)
        txn_date = base_date + timedelta(days=day_offset)

        # Basket size: 1-5 items, weighted toward smaller baskets
        basket_size = random.choices([1, 2, 3, 4, 5], weights=[35, 30, 20, 10, 5])[0]
        basket = set()

        # Seed with a random product
        seed = random.choice(product_ids)
        basket.add(seed)

        # Apply bundle rules to simulate realistic co-purchases
        for bundle_items, prob in BUNDLES:
            if seed in bundle_items and random.random() < prob:
                for b in bundle_items:
                    basket.add(b)

        # Fill remaining slots randomly
        while len(basket) < basket_size:
            basket.add(random.choice(product_ids))

        basket = list(basket)[:basket_size]

        customer_id = random.randint(1000, 5000)

        for prod_id in basket:
            price = next(p[3] for p in PRODUCTS if p[0] == prod_id)
            qty   = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
            rows.append({
                "transaction_id": txn_id,
                "transaction_date": txn_date.strftime("%Y-%m-%d"),
                "customer_id": customer_id,
                "product_id": prod_id,
                "quantity": qty,
                "unit_price": price,
                "line_total": price * qty,
            })

    return pd.DataFrame(rows)


def build_database():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Tables ─────────────────────────────────────────────────────────────────
    cur.executescript("""
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS transactions;

        CREATE TABLE products (
            product_id   INTEGER PRIMARY KEY,
            product_name TEXT    NOT NULL,
            category     TEXT    NOT NULL,
            unit_price   REAL    NOT NULL
        );

        CREATE TABLE transactions (
            line_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id   INTEGER NOT NULL,
            transaction_date TEXT    NOT NULL,
            customer_id      INTEGER NOT NULL,
            product_id       INTEGER NOT NULL,
            quantity         INTEGER NOT NULL,
            unit_price       REAL    NOT NULL,
            line_total       REAL    NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
    """)

    # ── Insert products ────────────────────────────────────────────────────────
    cur.executemany(
        "INSERT INTO products VALUES (?,?,?,?)", PRODUCTS
    )

    # ── Insert transactions ────────────────────────────────────────────────────
    df = generate_transactions(3000)
    df.to_sql("transactions", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()

    print(f"✓ Database created at {DB_PATH}")
    print(f"  Products    : {len(PRODUCTS)}")
    print(f"  Transactions: {len(df)} line items across {df['transaction_id'].nunique()} baskets")
    print(f"  Date range  : {df['transaction_date'].min()} → {df['transaction_date'].max()}")


if __name__ == "__main__":
    build_database()
