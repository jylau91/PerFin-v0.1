"""
PerFin — Personal Finance Dashboard
Local Streamlit app with SQLite storage.
"""

import os
import sys
from pathlib import Path

import streamlit as st

# Allow importing parser from backend without installing as package
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.parser import parse_pdf
from categoriser import CATEGORIES, categorise_batch
from db import (
    delete_statement,
    get_category_summary,
    get_monthly_summary,
    get_top_merchants,
    init_db,
    insert_statement,
    insert_transactions,
    list_statements,
    list_transactions,
    update_category,
)

# ── Bootstrap ──────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(page_title="PerFin", page_icon="💰", layout="wide")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💰 PerFin")
    page = st.radio("Navigate", ["Dashboard", "Upload", "Transactions", "Statements"])
    st.divider()
    api_key = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Required for AI categorisation",
    )
    st.caption("Supported banks: DBS, POSB, OCBC, UOB, Maybank")


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD PAGE
# ══════════════════════════════════════════════════════════════════════════════
if page == "Upload":
    st.header("Upload Bank Statements")
    uploaded = st.file_uploader(
        "Drop PDF statement(s) here", type="pdf", accept_multiple_files=True
    )

    if uploaded and st.button("Parse & Categorise", type="primary"):
        if not api_key:
            st.error("Enter your Anthropic API key in the sidebar first.")
        else:
            for f in uploaded:
                with st.spinner(f"Processing {f.name}…"):
                    try:
                        result = parse_pdf(f.read(), f.name)

                        descriptions = [t.description for t in result.transactions]
                        categories = categorise_batch(descriptions, api_key)

                        stmt_id = insert_statement(
                            bank=result.bank,
                            account_type=result.account_type,
                            period_start=result.period_start,
                            period_end=result.period_end,
                            filename=f.name,
                        )

                        txns = [
                            {
                                "date": t.date.isoformat(),
                                "description": t.description,
                                "amount": t.amount,
                                "balance": t.balance,
                                "polarity": t.polarity,
                                "category": categories[i],
                            }
                            for i, t in enumerate(result.transactions)
                        ]
                        insert_transactions(stmt_id, txns)

                        st.success(
                            f"✅ **{f.name}** — {result.bank} {result.account_type} "
                            f"| {len(txns)} transactions imported"
                        )
                    except Exception as e:
                        st.error(f"❌ {f.name}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Dashboard":
    import plotly.express as px
    import pandas as pd

    st.header("Dashboard")

    summary = get_category_summary()
    monthly = get_monthly_summary(6)
    merchants = get_top_merchants(5)

    if not summary:
        st.info("No data yet — upload some statements first.")
        st.stop()

    total_spend = sum(r["spend"] for r in summary)
    total_income = sum(r["income"] for r in summary)
    top_cat = max(summary, key=lambda r: r["spend"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Spend", f"${total_spend:,.2f}")
    c2.metric("Total Income", f"${total_income:,.2f}")
    c3.metric("Top Category", top_cat["category"], f"${top_cat['spend']:,.2f}")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Spending by Category")
        df_cat = pd.DataFrame([r for r in summary if r["spend"] > 0])
        fig = px.pie(df_cat, values="spend", names="category", hole=0.4)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Monthly Trend")
        df_monthly = pd.DataFrame(monthly)
        if not df_monthly.empty:
            fig2 = px.bar(
                df_monthly, x="month", y=["spend", "income"],
                barmode="group",
                labels={"value": "SGD", "variable": ""},
                color_discrete_map={"spend": "#ef4444", "income": "#22c55e"},
            )
            fig2.update_layout(margin=dict(t=0, b=0))
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top Merchants")
    for m in merchants:
        st.write(f"**{m['merchant']}** — ${m['total']:,.2f} ({m['count']} txns)")


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Transactions":
    import pandas as pd

    st.header("Transactions")

    # Filters
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    stmts = list_statements()
    stmt_options = {"All": None} | {f"{s['bank']} – {s['filename']}": s["id"] for s in stmts}
    sel_stmt = fcol1.selectbox("Statement", list(stmt_options.keys()))
    sel_cat = fcol2.selectbox("Category", ["All"] + CATEGORIES)
    date_from = fcol3.date_input("From", value=None)
    date_to = fcol4.date_input("To", value=None)

    txns = list_transactions(
        statement_id=stmt_options[sel_stmt],
        category=sel_cat if sel_cat != "All" else None,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
    )

    if not txns:
        st.info("No transactions match the filters.")
        st.stop()

    df = pd.DataFrame(txns)
    st.caption(f"{len(df)} transactions")

    # Editable category column
    edited = st.data_editor(
        df[["id", "date", "description", "amount", "category", "reviewed"]],
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "date": st.column_config.TextColumn("Date", disabled=True),
            "description": st.column_config.TextColumn("Description", disabled=True, width="large"),
            "amount": st.column_config.NumberColumn("Amount", format="$%.2f", disabled=True),
            "category": st.column_config.SelectboxColumn("Category", options=CATEGORIES),
            "reviewed": st.column_config.CheckboxColumn("Reviewed", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
    )

    if st.button("Save changes"):
        changed = 0
        for _, row in edited.iterrows():
            orig = next(t for t in txns if t["id"] == row["id"])
            if orig["category"] != row["category"]:
                update_category(int(row["id"]), row["category"])
                changed += 1
        if changed:
            st.success(f"Saved {changed} change(s).")
            st.rerun()
        else:
            st.info("No changes to save.")


# ══════════════════════════════════════════════════════════════════════════════
# STATEMENTS PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Statements":
    st.header("Statements")
    stmts = list_statements()
    if not stmts:
        st.info("No statements uploaded yet.")
        st.stop()

    for s in stmts:
        cols = st.columns([3, 2, 2, 2, 1])
        cols[0].write(f"**{s['filename']}**")
        cols[1].write(s["bank"])
        cols[2].write(s["account_type"])
        cols[3].write(f"{s['txn_count']} txns")
        if cols[4].button("🗑", key=f"del_{s['id']}"):
            delete_statement(s["id"])
            st.rerun()
