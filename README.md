# 💊 Odogwu Pharmacy — Market Basket Analysis

> A Python-based market basket analysis pipeline that identifies cross-sell opportunities from pharmacy transaction data, with an interactive HTML dashboard for stakeholders.

---

## 📌 Overview

This project was built to surface product combinations that customers frequently buy together at **Odogwu Pharmacy** — patterns that are invisible in raw sales data but highly actionable for bundling experiments and pricing strategy.

**Stack:** Python · Pandas · NumPy · mlxtend (Apriori) · SQLite · HTML/Chart.js

---

## 🗂 Project Structure

```
odogwu-pharmacy-mba/
│
├── 01_generate_data.py           # Generates synthetic sales data → SQLite DB
├── 02_market_basket_analysis.py  # Apriori algorithm + pricing analysis → JSON
├── odogwu_pharmacy_dashboard.html # Standalone interactive dashboard
├── requirements.txt              # Python dependencies
└── README.md
```

---

## ⚙️ How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate the database

```bash
python 01_generate_data.py
```

Creates `odogwu_pharmacy.db` (SQLite) with:
- `products` table — 25 pharmacy SKUs with categories and ₦ prices
- `transactions` table — 3,000 baskets, ~6,400 line items across 12 months

### 3. Run the analysis

```bash
python 02_market_basket_analysis.py
```

Outputs `analysis_results.json` containing:
- KPIs (total revenue, avg basket value, basket count)
- Monthly revenue trend
- Revenue by category
- Top 10 products by revenue
- Association rules with lift, confidence, support, and bundle pricing

### 4. View the dashboard

Open `odogwu_pharmacy_dashboard.html` in any browser — no server required.

---

## 🔬 Methodology

| Step | Tool | Description |
|------|------|-------------|
| Data loading | `sqlite3` + `pandas` | SQL query → DataFrame |
| Basket matrix | `pandas.pivot_table` | Transactions → boolean matrix (baskets × products) |
| Frequent itemsets | `mlxtend.apriori` | min_support=2%, max_len=3 |
| Association rules | `mlxtend.association_rules` | min_lift=1.2, min_confidence=30% |
| Bundle pricing | Custom | 10% discount on combined item prices |

**Lift score interpretation:**
- Lift = 1.0 → no relationship (random co-occurrence)
- Lift > 2.0 → meaningful cross-sell signal
- Lift > 4.0 → very strong, prioritise in bundling experiment

---

## 📊 Sample Results

| Rule | Lift | Confidence | Bundle Price |
|------|------|------------|--------------|
| Iron Supplement → Folic Acid 5mg | 4.21× | 35% | ₦387 (save ₦43) |
| Folic Acid 5mg → Iron Supplement | 4.21× | 34% | ₦387 (save ₦43) |
| Nasal Decongestant → Cough Syrup | 3.37× | 35% | ₦576 (save ₦64) |

---

## 🔄 Connecting to Real Data

To run against your actual pharmacy database, update the connection in `02_market_basket_analysis.py`:

```python
# SQLite (default)
conn = sqlite3.connect("your_database.db")

# PostgreSQL
import psycopg2
conn = psycopg2.connect(host="...", dbname="...", user="...", password="...")

# MySQL
import mysql.connector
conn = mysql.connector.connect(host="...", database="...", user="...", password="...")
```

The SQL query expects columns: `transaction_id`, `product_name`, `category`, `quantity`, `unit_price`, `line_total`.

---

## 📁 Output Files

| File | Description |
|------|-------------|
| `odogwu_pharmacy.db` | SQLite database (generated) |
| `analysis_results.json` | Full analysis output |
| `odogwu_pharmacy_dashboard.html` | Stakeholder dashboard (open in browser) |

---

## 👤 Author

**CIO, Odogwu Pharmacy**  
GitHub: [@gelmish](https://github.com/gelmish)

---

## 📄 License

MIT
