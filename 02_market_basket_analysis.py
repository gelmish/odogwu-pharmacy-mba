"""
Step 2: Market Basket Analysis — Odogwu Pharmacy
-------------------------------------------------
Reads from SQLite → builds basket matrix → runs Apriori →
generates association rules → outputs results to JSON for dashboard.

Libraries:
  pandas, numpy   — data wrangling
  mlxtend         — Apriori + association rules
  scikit-learn    — optional clustering on product pairs
"""

import sqlite3
import json
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

DB_PATH     = "/home/claude/odogwu_pharmacy.db"
OUTPUT_PATH = "/home/claude/analysis_results.json"


# ── 1. Load data from SQL ──────────────────────────────────────────────────────
def load_data():
    conn = sqlite3.connect(DB_PATH)

    transactions_df = pd.read_sql("""
        SELECT
            t.transaction_id,
            t.transaction_date,
            t.customer_id,
            t.product_id,
            p.product_name,
            p.category,
            t.quantity,
            t.unit_price,
            t.line_total
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
    """, conn)

    products_df = pd.read_sql("SELECT * FROM products", conn)
    conn.close()

    transactions_df["transaction_date"] = pd.to_datetime(transactions_df["transaction_date"])
    return transactions_df, products_df


# ── 2. Build basket matrix (one row per transaction, one col per product) ──────
def build_basket_matrix(df):
    basket = (
        df.groupby(["transaction_id", "product_name"])["quantity"]
        .sum()
        .unstack(fill_value=0)
        .reset_index(drop=True)
    )
    # Convert to boolean (purchased or not)
    basket_bool = basket.map(lambda x: x > 0)
    return basket_bool


# ── 3. Apriori → frequent itemsets → association rules ───────────────────────
def run_apriori(basket_bool, min_support=0.02, min_confidence=0.3, min_lift=1.2):
    frequent_itemsets = apriori(
        basket_bool,
        min_support=min_support,
        use_colnames=True,
        max_len=3,         # pairs and triplets only
    )

    if frequent_itemsets.empty:
        print("No frequent itemsets found — lower min_support.")
        return pd.DataFrame(), pd.DataFrame()

    rules = association_rules(
        frequent_itemsets,
        metric="lift",
        min_threshold=min_lift,
    )

    # Apply confidence filter
    rules = rules[rules["confidence"] >= min_confidence].copy()

    # Clean up frozenset columns for readability
    rules["antecedents_str"] = rules["antecedents"].apply(lambda x: ", ".join(sorted(x)))
    rules["consequents_str"] = rules["consequents"].apply(lambda x: ", ".join(sorted(x)))
    rules["rule"]            = rules["antecedents_str"] + "  →  " + rules["consequents_str"]

    rules = rules.sort_values("lift", ascending=False).reset_index(drop=True)

    print(f"  Frequent itemsets : {len(frequent_itemsets)}")
    print(f"  Association rules : {len(rules)}")
    return frequent_itemsets, rules


# ── 4. Price-point analysis per rule ─────────────────────────────────────────
def price_point_analysis(rules, df, products_df):
    price_map = products_df.set_index("product_name")["unit_price"].to_dict()

    bundle_rows = []
    for _, row in rules.iterrows():
        items      = list(row["antecedents"] | row["consequents"])
        prices     = [price_map.get(i, 0) for i in items]
        total_price = sum(prices)
        bundle_rows.append({
            "rule":          row["rule"],
            "antecedents":   row["antecedents_str"],
            "consequents":   row["consequents_str"],
            "support":       round(row["support"], 4),
            "confidence":    round(row["confidence"], 4),
            "lift":          round(row["lift"], 4),
            "leverage":      round(row["leverage"], 4),
            "items":         items,
            "bundle_price":  total_price,
            "suggested_bundle_price": round(total_price * 0.90, 2),  # 10% bundle discount
            "estimated_saving":       round(total_price * 0.10, 2),
        })

    return pd.DataFrame(bundle_rows)


# ── 5. KPIs and summary stats ─────────────────────────────────────────────────
def compute_kpis(df, rules_df, products_df):
    total_revenue     = df["line_total"].sum()
    total_baskets     = df["transaction_id"].nunique()
    avg_basket_value  = df.groupby("transaction_id")["line_total"].sum().mean()
    avg_basket_size   = df.groupby("transaction_id")["product_id"].count().mean()

    # Top products by revenue
    top_products = (
        df.groupby("product_name")["line_total"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={"line_total": "revenue"})
    )
    top_products["revenue"] = top_products["revenue"].round(2)

    # Revenue by category
    cat_revenue = (
        df.groupby("category")["line_total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"line_total": "revenue"})
    )
    cat_revenue["revenue"] = cat_revenue["revenue"].round(2)

    # Monthly revenue trend
    df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
    monthly = (
        df.groupby("month")
        .agg(revenue=("line_total", "sum"), baskets=("transaction_id", "nunique"))
        .reset_index()
    )
    monthly["revenue"] = monthly["revenue"].round(2)

    # Top cross-sell opportunities (by lift)
    top_rules = rules_df.head(15)[
        ["rule", "antecedents", "consequents", "support",
         "confidence", "lift", "bundle_price", "suggested_bundle_price",
         "estimated_saving"]
    ].to_dict(orient="records")

    return {
        "kpis": {
            "total_revenue":    round(total_revenue, 2),
            "total_baskets":    int(total_baskets),
            "avg_basket_value": round(avg_basket_value, 2),
            "avg_basket_size":  round(avg_basket_size, 2),
            "rules_found":      len(rules_df),
        },
        "top_products":  top_products.to_dict(orient="records"),
        "cat_revenue":   cat_revenue.to_dict(orient="records"),
        "monthly":       monthly.to_dict(orient="records"),
        "top_rules":     top_rules,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Loading data from SQL…")
    df, products_df = load_data()
    print(f"  Loaded {len(df):,} line items across {df['transaction_id'].nunique():,} baskets")

    print("\nBuilding basket matrix…")
    basket_bool = build_basket_matrix(df)
    print(f"  Matrix shape: {basket_bool.shape}")

    print("\nRunning Apriori algorithm…")
    frequent_itemsets, rules = run_apriori(basket_bool)

    if rules.empty:
        print("No rules generated — check thresholds.")
        return

    print("\nRunning price-point analysis…")
    rules_df = price_point_analysis(rules, df, products_df)

    print("\nComputing KPIs and summaries…")
    summary = compute_kpis(df, rules_df, products_df)

    # Save for dashboard
    with open(OUTPUT_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Analysis complete → {OUTPUT_PATH}")
    print(f"\n── Top 5 Cross-Sell Rules ────────────────────────────────────────")
    for i, r in enumerate(summary["top_rules"][:5], 1):
        print(f"  {i}. {r['rule']}")
        print(f"     Lift={r['lift']:.2f}  Conf={r['confidence']:.0%}  "
              f"Bundle Price=₦{r['bundle_price']:,.0f}  "
              f"Suggested=₦{r['suggested_bundle_price']:,.0f}")


if __name__ == "__main__":
    main()
