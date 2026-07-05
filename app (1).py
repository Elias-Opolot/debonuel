import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import json
from sheets import (
    read_df, append_row, update_row, delete_row,
    new_id, today, now_time, fmt_ugx
)

st.set_page_config(
    page_title="DEBONUEL",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── CUSTOM CSS ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2rem;
    color: #c9a84c;
    letter-spacing: .1em;
    margin-bottom: 0;
}
.logo span { color: #f2ede4; font-weight: 600; opacity: .7; }

.metric-card {
    background: #161616;
    border: 1px solid #262626;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    margin-bottom: 8px;
}
.metric-label { font-size: .72rem; color: #777; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 4px; }
.metric-value { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1.2rem; color: #c9a84c; }
.metric-sub { font-size: .7rem; color: #555; margin-top: 2px; }

.receipt-box {
    font-family: monospace;
    font-size: .82rem;
    background: #161616;
    border: 1px solid #262626;
    border-radius: 10px;
    padding: 16px;
    white-space: pre;
    line-height: 1.8;
    overflow-x: auto;
}

div[data-testid="stButton"] button {
    border-radius: 10px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
}

.gold-badge {
    background: rgba(201,168,76,.15);
    color: #c9a84c;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: .75rem;
    font-weight: 600;
}
.red-badge {
    background: rgba(217,85,85,.15);
    color: #d95555;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: .75rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── HEADER ─────────────────────────────────────────
st.markdown('<div class="logo">DEBO<span>NUEL</span></div>', unsafe_allow_html=True)
st.caption(datetime.now().strftime("%A, %d %B %Y  |  %H:%M"))
st.divider()

# ── SESSION STATE ──────────────────────────────────
if "cart" not in st.session_state:
    st.session_state.cart = []
if "last_sale" not in st.session_state:
    st.session_state.last_sale = None
if "tab" not in st.session_state:
    st.session_state.tab = "Sales"

# ── NAVIGATION ─────────────────────────────────────
tabs = st.tabs(["🛒 Sales", "📦 Stock", "📷 Scan", "📊 Reports", "🏭 Suppliers", "💾 Backup"])

# ══════════════════════════════════════════════════
# TAB 1 — SALES
# ══════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Today's Sales")

    # Load products
    prods_df = read_df("products")

    if prods_df.empty:
        st.info("No products yet. Go to the Stock tab to add products.")
    else:
        # Search box
        search = st.text_input("Search product by name or barcode", placeholder="Type to search...")

        filtered = prods_df.copy()
        if search:
            mask = (
                filtered["name"].str.contains(search, case=False, na=False) |
                filtered["barcode"].astype(str).str.contains(search, na=False)
            )
            filtered = filtered[mask]

        # Product buttons grid
        if not filtered.empty:
            st.markdown("**Tap a product to add to sale:**")
            cols = st.columns(2)
            for i, (_, p) in enumerate(filtered.iterrows()):
                stock = int(p.get("stock", 0) or 0)
                price = float(p.get("selling_price", 0) or 0)
                stock_color = "🟢" if stock > 5 else "🟡" if stock > 0 else "🔴"
                with cols[i % 2]:
                    if st.button(
                        f"{p['name']}\n{fmt_ugx(price)}\n{stock_color} Stock: {stock}",
                        key=f"add_{p['id']}_{i}",
                        use_container_width=True,
                        disabled=(stock <= 0)
                    ):
                        # Add to cart
                        found = False
                        for item in st.session_state.cart:
                            if item["id"] == str(p["id"]):
                                if item["qty"] < stock:
                                    item["qty"] += 1
                                    item["total"] = item["qty"] * item["price"]
                                    found = True
                                break
                        if not found:
                            st.session_state.cart.append({
                                "id": str(p["id"]),
                                "name": p["name"],
                                "qty": 1,
                                "price": price,
                                "cost": float(p.get("buying_price", 0) or 0),
                                "total": price
                            })
                        st.rerun()
        else:
            st.warning("No products match your search.")

    st.divider()

    # ── LIVE SALES TABLE ──────────────────────────
    st.markdown("### Today's Sales Log")
    st.caption(f"Date: {today()}")

    if not st.session_state.cart:
        st.info("No items yet. Tap a product above to add it.")
    else:
        # Display editable table
        total = 0
        rows_to_delete = []

        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
            with c1:
                st.write(f"**{i+1}. {item['name']}**")
            with c2:
                new_qty = st.number_input(
                    "Qty", min_value=1, value=item["qty"],
                    key=f"qty_{i}", label_visibility="collapsed"
                )
                if new_qty != item["qty"]:
                    item["qty"] = new_qty
                    item["total"] = new_qty * item["price"]
            with c3:
                st.write(fmt_ugx(item["price"]))
            with c4:
                st.write(f"**{fmt_ugx(item['total'])}**")
            with c5:
                if st.button("✕", key=f"del_{i}"):
                    rows_to_delete.append(i)

        for idx in sorted(rows_to_delete, reverse=True):
            st.session_state.cart.pop(idx)
        if rows_to_delete:
            st.rerun()

        total = sum(item["total"] for item in st.session_state.cart)
        item_count = sum(item["qty"] for item in st.session_state.cart)

        st.divider()
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"**{item_count} items**")
            st.markdown(f"### {fmt_ugx(total)}")
        with col2:
            if st.button("🗑 Clear Cart", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
            if st.button("✅ Checkout", use_container_width=True, type="primary"):
                if st.session_state.cart:
                    with st.spinner("Saving sale..."):
                        sale_id = new_id()
                        profit = sum((item["price"] - item["cost"]) * item["qty"] for item in st.session_state.cart)

                        # Save sale header
                        append_row("sales", {
                            "id": sale_id,
                            "date": today(),
                            "time": now_time(),
                            "total": total,
                            "profit": profit,
                            "items_count": len(st.session_state.cart)
                        })

                        # Save each line item
                        prods_df2 = read_df("products")
                        for item in st.session_state.cart:
                            append_row("sale_items", {
                                "id": new_id(),
                                "sale_id": sale_id,
                                "product_id": item["id"],
                                "product_name": item["name"],
                                "qty": item["qty"],
                                "unit_price": item["price"],
                                "line_total": item["total"]
                            })
                            # Deduct stock
                            if not prods_df2.empty:
                                row = prods_df2[prods_df2["id"].astype(str) == str(item["id"])]
                                if not row.empty:
                                    old_stock = int(row.iloc[0]["stock"] or 0)
                                    new_stock = max(0, old_stock - item["qty"])
                                    update_row("products", item["id"], {"stock": new_stock})

                        st.session_state.last_sale = {
                            "id": sale_id,
                            "date": today(),
                            "time": now_time(),
                            "items": list(st.session_state.cart),
                            "total": total,
                            "profit": profit
                        }
                        st.session_state.cart = []
                        st.success(f"Sale saved! {fmt_ugx(total)}")
                        st.rerun()

    # ── RECEIPT ───────────────────────────────────
    if st.session_state.last_sale:
        st.divider()
        st.markdown("### Last Receipt")
        sale = st.session_state.last_sale
        line = "-" * 32
        rcpt = f"DEBONUEL\n        Receipt\n{line}\n"
        rcpt += f"Date: {sale['date']}  Time: {sale['time']}\n{line}\n"
        rcpt += f"{'Item':<18} {'Qty':>3}  {'Total':>8}\n{line}\n"
        for it in sale["items"]:
            nm = it["name"][:17].ljust(18)
            q = str(it["qty"]).rjust(3)
            am = fmt_ugx(it["total"]).rjust(8)
            rcpt += f"{nm} {q}  {am}\n"
        rcpt += f"{line}\nTOTAL: {fmt_ugx(sale['total'])}\n{line}\n"
        rcpt += "  Thank you for shopping!\n  DEBONUEL - Your trusted shop"

        st.markdown(f'<div class="receipt-box">{rcpt}</div>', unsafe_allow_html=True)

        r1, r2 = st.columns(2)
        with r1:
            wa_msg = f"*DEBONUEL Receipt*\nDate: {sale['date']} {sale['time']}\n"
            for it in sale["items"]:
                wa_msg += f"- {it['name']} x{it['qty']}: {fmt_ugx(it['total'])}\n"
            wa_msg += f"*Total: {fmt_ugx(sale['total'])}*\nThank you!"
            st.link_button(
                "💬 Share via WhatsApp",
                f"https://wa.me/?text={wa_msg.replace(' ', '%20').replace('\n', '%0A')}",
                use_container_width=True
            )
        with r2:
            st.download_button(
                "⬇ Download Receipt",
                rcpt,
                file_name=f"DEBONUEL_Receipt_{sale['id']}.txt",
                use_container_width=True
            )

# ══════════════════════════════════════════════════
# TAB 2 — STOCK / INVENTORY
# ══════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Stock / Inventory")

    prods_df = read_df("products")
    sups_df = read_df("suppliers")

    # Low stock alerts
    if not prods_df.empty:
        prods_df["stock"] = pd.to_numeric(prods_df["stock"], errors="coerce").fillna(0).astype(int)
        low = prods_df[prods_df["stock"] <= 5]
        out = prods_df[prods_df["stock"] <= 0]
        if not out.empty:
            st.error(f"⚠ {len(out)} product(s) out of stock: {', '.join(out['name'].tolist())}")
        if not low[low['stock'] > 0].empty:
            st.warning(f"⚠ {len(low[low['stock']>0])} product(s) running low: {', '.join(low[low['stock']>0]['name'].tolist())}")

    # Add product form
    with st.expander("➕ Add New Product", expanded=False):
        with st.form("add_prod_form"):
            c1, c2 = st.columns(2)
            with c1:
                p_name = st.text_input("Product Name *", placeholder="e.g. Sugar 2kg")
                p_buy = st.number_input("Buying Price (UGX)", min_value=0, value=0)
                p_stock = st.number_input("Stock Quantity", min_value=0, value=0)
                p_bc = st.text_input("Barcode (optional)")
            with c2:
                p_cat = st.selectbox("Category", ["General","Food and Drinks","Household","Personal Care","Electronics","Other"])
                p_sell = st.number_input("Selling Price (UGX)", min_value=0, value=0)
                sup_options = ["None"] + (sups_df["name"].tolist() if not sups_df.empty else [])
                p_sup = st.selectbox("Supplier (optional)", sup_options)

            if st.form_submit_button("Save Product", type="primary"):
                if not p_name:
                    st.error("Enter product name")
                else:
                    sup_id = ""
                    if p_sup != "None" and not sups_df.empty:
                        row = sups_df[sups_df["name"] == p_sup]
                        if not row.empty:
                            sup_id = str(row.iloc[0]["id"])
                    with st.spinner("Saving..."):
                        append_row("products", {
                            "id": new_id(), "name": p_name, "category": p_cat,
                            "buying_price": p_buy, "selling_price": p_sell,
                            "stock": p_stock, "barcode": p_bc,
                            "supplier_id": sup_id,
                            "created_at": datetime.now().isoformat()
                        })
                    st.success(f"Product '{p_name}' added!")
                    st.rerun()

    st.divider()

    # Products list
    if prods_df.empty:
        st.info("No products yet. Add your first product above.")
    else:
        prods_df["selling_price"] = pd.to_numeric(prods_df["selling_price"], errors="coerce").fillna(0)
        prods_df["buying_price"] = pd.to_numeric(prods_df["buying_price"], errors="coerce").fillna(0)
        prods_df["margin"] = prods_df.apply(
            lambda r: round((r["selling_price"] - r["buying_price"]) / r["selling_price"] * 100) if r["selling_price"] > 0 else 0, axis=1
        )

        for _, p in prods_df.iterrows():
            stock = int(p.get("stock", 0) or 0)
            icon = "🟢" if stock > 5 else "🟡" if stock > 0 else "🔴"
            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    status = " 🔴 OUT" if stock <= 0 else " 🟡 LOW" if stock <= 5 else ""
                    st.markdown(f"**{p['name']}**{status}")
                    st.caption(f"{p.get('category','')} | Buy: {fmt_ugx(p['buying_price'])} | Sell: {fmt_ugx(p['selling_price'])} | Margin: {p['margin']}%")
                with c2:
                    st.markdown(f"{icon} **Stock: {stock}**")
                    if p.get("barcode"):
                        st.caption(f"Barcode: {p['barcode']}")
                with c3:
                    with st.popover("Edit"):
                        with st.form(f"edit_{p['id']}"):
                            new_name = st.text_input("Name", value=str(p["name"]))
                            new_buy = st.number_input("Buy Price", value=float(p["buying_price"]))
                            new_sell = st.number_input("Sell Price", value=float(p["selling_price"]))
                            new_stock = st.number_input("Stock", value=stock, min_value=0)
                            new_bc = st.text_input("Barcode", value=str(p.get("barcode","") or ""))
                            col_s, col_d = st.columns(2)
                            with col_s:
                                if st.form_submit_button("Save"):
                                    with st.spinner("Updating..."):
                                        update_row("products", p["id"], {
                                            "name": new_name, "buying_price": new_buy,
                                            "selling_price": new_sell, "stock": new_stock,
                                            "barcode": new_bc
                                        })
                                    st.rerun()
                            with col_d:
                                if st.form_submit_button("Delete", type="secondary"):
                                    with st.spinner("Deleting..."):
                                        delete_row("products", p["id"])
                                    st.rerun()
                st.divider()

# ══════════════════════════════════════════════════
# TAB 3 — SCANNER
# ══════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Barcode Scanner")

    st.info("📷 Type or paste a barcode number below to find a product and add it to the sale.")

    bc_input = st.text_input("Enter Barcode Number", placeholder="Scan or type barcode...")

    if bc_input:
        prods_df = read_df("products")
        if not prods_df.empty:
            match = prods_df[prods_df["barcode"].astype(str) == bc_input.strip()]
            if not match.empty:
                p = match.iloc[0]
                stock = int(p.get("stock", 0) or 0)
                st.success(f"Found: **{p['name']}**")
                st.metric("Selling Price", fmt_ugx(p["selling_price"]))
                st.metric("Stock", stock)
                if stock > 0:
                    if st.button("➕ Add to Sale", type="primary"):
                        found = False
                        for item in st.session_state.cart:
                            if item["id"] == str(p["id"]):
                                item["qty"] += 1
                                item["total"] = item["qty"] * float(p["selling_price"])
                                found = True
                                break
                        if not found:
                            st.session_state.cart.append({
                                "id": str(p["id"]),
                                "name": p["name"],
                                "qty": 1,
                                "price": float(p["selling_price"]),
                                "cost": float(p.get("buying_price", 0) or 0),
                                "total": float(p["selling_price"])
                            })
                        st.success("Added to sale! Go to Sales tab to checkout.")
                else:
                    st.error("This product is out of stock.")
            else:
                st.warning(f"No product found with barcode: {bc_input}")

    st.divider()
    st.markdown("### Assign Barcode to Product")
    prods_df = read_df("products")
    if not prods_df.empty:
        with st.form("assign_bc"):
            bc_val = st.text_input("Barcode to assign")
            prod_sel = st.selectbox("Select Product", prods_df["name"].tolist())
            if st.form_submit_button("Assign Barcode"):
                if bc_val and prod_sel:
                    row = prods_df[prods_df["name"] == prod_sel]
                    if not row.empty:
                        with st.spinner("Assigning..."):
                            update_row("products", row.iloc[0]["id"], {"barcode": bc_val})
                        st.success(f"Barcode {bc_val} assigned to {prod_sel}")
                        st.rerun()
    else:
        st.info("Add products first in the Stock tab.")

# ══════════════════════════════════════════════════
# TAB 4 — REPORTS
# ══════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Reports")

    rep_type = st.radio("Report Period", ["Daily","Weekly","Monthly","Yearly"], horizontal=True)

    today_dt = datetime.now().date()
    if rep_type == "Daily":
        rep_date = st.date_input("Select Date", value=today_dt)
        start = str(rep_date)
        end = str(rep_date)
        label = str(rep_date)
    elif rep_type == "Weekly":
        rep_date = st.date_input("Any date in the week", value=today_dt)
        start = str(rep_date - timedelta(days=rep_date.weekday()))
        end = str(rep_date - timedelta(days=rep_date.weekday()) + timedelta(days=6))
        label = f"Week of {start}"
    elif rep_type == "Monthly":
        rep_date = st.date_input("Any date in the month", value=today_dt)
        start = str(rep_date.replace(day=1))
        import calendar
        last_day = calendar.monthrange(rep_date.year, rep_date.month)[1]
        end = str(rep_date.replace(day=last_day))
        label = rep_date.strftime("%B %Y")
    else:
        y = today_dt.year
        start = f"{y}-01-01"
        end = f"{y}-12-31"
        label = f"Year {y}"

    # Load data
    sales_df = read_df("sales")
    items_df = read_df("sale_items")

    if not sales_df.empty:
        sales_df = sales_df[
            (sales_df["date"] >= start) & (sales_df["date"] <= end)
        ]
        sales_df["total"] = pd.to_numeric(sales_df["total"], errors="coerce").fillna(0)
        sales_df["profit"] = pd.to_numeric(sales_df["profit"], errors="coerce").fillna(0)

    rev = sales_df["total"].sum() if not sales_df.empty else 0
    prof = sales_df["profit"].sum() if not sales_df.empty else 0
    cnt = len(sales_df) if not sales_df.empty else 0
    avg = rev / cnt if cnt > 0 else 0
    margin = round(prof / rev * 100) if rev > 0 else 0

    # Stats
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Revenue</div><div class="metric-value">{fmt_ugx(rev)}</div><div class="metric-sub">{cnt} sales</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Profit</div><div class="metric-value" style="color:#4caf7d">{fmt_ugx(prof)}</div><div class="metric-sub">Margin {margin}%</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Transactions</div><div class="metric-value">{cnt}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Avg Sale</div><div class="metric-value">{fmt_ugx(avg)}</div></div>', unsafe_allow_html=True)

    # Chart
    if not sales_df.empty and not items_df.empty:
        items_in = items_df[items_df["sale_id"].isin(sales_df["id"].astype(str))]
        items_in["line_total"] = pd.to_numeric(items_in["line_total"], errors="coerce").fillna(0)
        items_in["qty"] = pd.to_numeric(items_in["qty"], errors="coerce").fillna(0)

        # Sales chart
        chart_data = sales_df.groupby("date")["total"].sum().reset_index()
        chart_data.columns = ["Date", "Revenue (UGX)"]
        fig = px.bar(chart_data, x="Date", y="Revenue (UGX)", title=f"Sales — {label}",
                     color_discrete_sequence=["#c9a84c"])
        fig.update_layout(
            plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b",
            font_color="#f2ede4", title_font_color="#c9a84c",
            xaxis=dict(gridcolor="#262626"), yaxis=dict(gridcolor="#262626")
        )
        st.plotly_chart(fig, use_container_width=True)

        # Top products
        if not items_in.empty:
            top = items_in.groupby("product_name")["qty"].sum().reset_index()
            top.columns = ["Product", "Units Sold"]
            top = top.sort_values("Units Sold", ascending=False).head(10)
            fig2 = px.bar(top, x="Units Sold", y="Product", orientation="h",
                          title="Top Products", color_discrete_sequence=["#c9a84c"])
            fig2.update_layout(
                plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b",
                font_color="#f2ede4", title_font_color="#c9a84c",
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Transaction log
        st.markdown("### Transaction Log")
        if not items_in.empty:
            log = items_in.merge(
                sales_df[["id","date","time"]].rename(columns={"id":"sale_id"}),
                on="sale_id", how="left"
            )[["date","time","product_name","qty","unit_price","line_total"]]
            log.columns = ["Date","Time","Item","Qty","Unit Price","Total"]
            log["Unit Price"] = log["Unit Price"].apply(lambda x: fmt_ugx(x))
            log["Total"] = log["Total"].apply(lambda x: fmt_ugx(x))
            st.dataframe(log, use_container_width=True, hide_index=True)

    else:
        st.info("No sales data for this period.")

    # Download buttons
    if not sales_df.empty:
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            csv = sales_df.to_csv(index=False)
            st.download_button("⬇ Download CSV", csv,
                               file_name=f"DEBONUEL_{label}.csv", mime="text/csv",
                               use_container_width=True)
        with c2:
            items_csv = items_df.to_csv(index=False) if not items_df.empty else ""
            st.download_button("⬇ Items CSV", items_csv,
                               file_name=f"DEBONUEL_Items_{label}.csv", mime="text/csv",
                               use_container_width=True)
        with c3:
            wa_msg = f"*DEBONUEL Report - {label}*\n\nRevenue: {fmt_ugx(rev)}\nProfit: {fmt_ugx(prof)}\nMargin: {margin}%\nSales: {cnt}\n\n_DEBONUEL Business System_"
            st.link_button(
                "💬 WhatsApp",
                f"https://wa.me/?text={wa_msg.replace(' ','%20').replace(chr(10),'%0A')}",
                use_container_width=True
            )

# ══════════════════════════════════════════════════
# TAB 5 — SUPPLIERS
# ══════════════════════════════════════════════════
with tabs[4]:
    st.subheader("Suppliers")

    with st.expander("➕ Add New Supplier", expanded=False):
        with st.form("add_sup_form"):
            c1, c2 = st.columns(2)
            with c1:
                s_name = st.text_input("Supplier Name *", placeholder="e.g. Kampala Wholesale Ltd")
                s_phone = st.text_input("Phone / WhatsApp", placeholder="+256...")
                s_prods = st.text_input("Products Supplied", placeholder="e.g. Sugar, Flour, Oil")
            with c2:
                s_loc = st.text_input("Location", placeholder="e.g. Nakasero Market")
                s_terms = st.selectbox("Payment Terms", ["Cash on Delivery","30 Days Credit","60 Days Credit","Prepayment","Other"])
                s_notes = st.text_area("Notes", placeholder="Any notes...")

            if st.form_submit_button("Save Supplier", type="primary"):
                if not s_name:
                    st.error("Enter supplier name")
                else:
                    with st.spinner("Saving..."):
                        append_row("suppliers", {
                            "id": new_id(), "name": s_name, "phone": s_phone,
                            "products_supplied": s_prods, "location": s_loc,
                            "payment_terms": s_terms, "notes": s_notes,
                            "created_at": datetime.now().isoformat()
                        })
                    st.success(f"Supplier '{s_name}' added!")
                    st.rerun()

    st.divider()
    sups_df = read_df("suppliers")
    if sups_df.empty:
        st.info("No suppliers yet. Add your first supplier above.")
    else:
        for _, s in sups_df.iterrows():
            with st.container():
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{s['name']}**")
                    st.caption(
                        f"📞 {s.get('phone','-')} | 📍 {s.get('location','-')} | "
                        f"📦 {s.get('products_supplied','-')} | 💳 {s.get('payment_terms','-')}"
                    )
                    if s.get("notes"):
                        st.caption(f"📝 {s['notes']}")
                with c2:
                    if s.get("phone"):
                        phone = str(s["phone"]).replace(" ","").replace("+","").replace("-","")
                        st.link_button("💬 WhatsApp", f"https://wa.me/{phone}", use_container_width=True)
                    if st.button("🗑 Delete", key=f"delsup_{s['id']}"):
                        with st.spinner("Deleting..."):
                            delete_row("suppliers", s["id"])
                        st.rerun()
                st.divider()

# ══════════════════════════════════════════════════
# TAB 6 — BACKUP
# ══════════════════════════════════════════════════
with tabs[5]:
    st.subheader("Backup & Data")

    st.success("✅ Your data is saved directly to Google Sheets in real time — no manual backup needed!")

    st.markdown("### Export Data")
    c1, c2 = st.columns(2)

    prods_df = read_df("products")
    sales_df = read_df("sales")
    items_df = read_df("sale_items")
    sups_df = read_df("suppliers")

    with c1:
        all_data = {
            "products": prods_df.to_dict("records") if not prods_df.empty else [],
            "sales": sales_df.to_dict("records") if not sales_df.empty else [],
            "sale_items": items_df.to_dict("records") if not items_df.empty else [],
            "suppliers": sups_df.to_dict("records") if not sups_df.empty else [],
            "exported_at": datetime.now().isoformat(),
            "shop": "DEBONUEL"
        }
        st.download_button(
            "⬇ Download Full Backup (JSON)",
            json.dumps(all_data, indent=2),
            file_name=f"DEBONUEL_Backup_{today()}.json",
            mime="application/json",
            use_container_width=True
        )
    with c2:
        if not prods_df.empty:
            st.download_button(
                "⬇ Download Products (CSV)",
                prods_df.to_csv(index=False),
                file_name=f"DEBONUEL_Products_{today()}.csv",
                mime="text/csv",
                use_container_width=True
            )

    st.divider()
    st.markdown("### Data Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Products", len(prods_df) if not prods_df.empty else 0)
    m2.metric("Total Sales", len(sales_df) if not sales_df.empty else 0)
    m3.metric("Suppliers", len(sups_df) if not sups_df.empty else 0)
    if not sales_df.empty:
        sales_df["total"] = pd.to_numeric(sales_df["total"], errors="coerce").fillna(0)
        m4.metric("Total Revenue", fmt_ugx(sales_df["total"].sum()))
    else:
        m4.metric("Total Revenue", "UGX 0")

    st.divider()
    st.markdown("### Google Sheets Link")
    try:
        sheet_name = st.secrets.get("sheet_name", "DEBONUEL Sales Data")
        st.info(f"Your data is stored in Google Sheet: **{sheet_name}**")
        st.caption("Open it anytime at sheets.google.com to see all your records.")
    except:
        st.info("Connect your Google Sheet using the setup instructions.")
