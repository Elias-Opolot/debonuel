import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
import json
from db import (
    get_products, add_product, update_product, delete_product,
    get_sales, get_sale_items, save_sale,
    get_suppliers, add_supplier, delete_supplier,
    uid, today, now_time, fmt_ugx, get_client
)

st.set_page_config(
    page_title="DEBONUEL",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.logo{font-family:'Syne',sans-serif;font-weight:800;font-size:2rem;color:#c9a84c;letter-spacing:.1em}
.logo span{color:#f2ede4;opacity:.6}
.mcard{background:#161616;border:1px solid #262626;border-radius:12px;padding:14px;text-align:center;margin-bottom:6px}
.ml{font-size:.7rem;color:#777;text-transform:uppercase;letter-spacing:.1em;margin-bottom:3px}
.mv{font-family:'Syne',sans-serif;font-weight:700;font-size:1.15rem;color:#c9a84c}
.mv2{font-family:'Syne',sans-serif;font-weight:700;font-size:1.15rem;color:#4caf7d}
.mv3{font-family:'Syne',sans-serif;font-weight:700;font-size:1.15rem;color:#d95555}
.ms{font-size:.68rem;color:#555;margin-top:2px}
.rcpt{font-family:monospace;font-size:.82rem;background:#161616;border:1px solid #262626;border-radius:10px;padding:16px;white-space:pre;line-height:1.9;overflow-x:auto;color:#f2ede4}
.supcard{background:#161616;border:1px solid #262626;border-radius:12px;padding:14px;margin-bottom:10px}
.debtcard{background:#1a0a0a;border:1px solid #d95555;border-radius:12px;padding:14px;margin-bottom:10px}
.day-banner{background:linear-gradient(135deg,#1a1500,#0b0b0b);border:1px solid #c9a84c;border-radius:14px;padding:16px;margin-bottom:14px;text-align:center}
.day-active{color:#c9a84c;font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem}
.calc-display{background:#1d1d1d;border:1px solid #262626;border-radius:12px;padding:16px;text-align:right;margin-bottom:10px}
.calc-expr{font-size:.82rem;color:#777;min-height:20px}
.calc-val{font-family:'Syne',sans-serif;font-weight:700;font-size:2rem;color:#c9a84c;word-break:break-all}
div[data-testid="stButton"] button{border-radius:10px;font-family:'DM Sans',sans-serif;font-weight:500}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────
st.markdown('<div class="logo">DEBO<span>NUEL</span></div>', unsafe_allow_html=True)
st.caption("📅 " + datetime.now().strftime("%A, %d %B %Y  |  %H:%M"))
st.divider()

# ── SESSION STATE ─────────────────────────────────
defaults = {
    "cart": [], "last_sale": None,
    "day_started": False, "sale_date": today(),
    "calc_expr": "", "calc_display": "0",
    "calc_result": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── TABS ──────────────────────────────────────────
tabs = st.tabs([
    "🛒 Sales", "📦 Stock", "📊 Reports",
    "💰 Expenses", "🧾 Credits", "🏭 Suppliers",
    "🧮 Calculator", "💾 Backup"
])

# ══════════════════════════════════════════════════
# TAB 1 — SALES
# ══════════════════════════════════════════════════
with tabs[0]:

    if not st.session_state.day_started:
        st.markdown("### Start a Sales Day")
        st.info("Select the date and press Start Day to begin recording sales.")
        col1, col2 = st.columns([2, 1])
        with col1:
            sel_date = st.date_input("Sales Date", value=datetime.now().date(), key="date_picker")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("▶ Start Day", type="primary", use_container_width=True):
                st.session_state.day_started = True
                st.session_state.sale_date = str(sel_date)
                st.session_state.cart = []
                st.rerun()

        st.divider()
        st.markdown("### Recent Sales")
        recent = get_sales()[:10]
        if recent:
            for s in recent:
                items_r = get_sale_items([s["id"]])
                names = ", ".join(set(it["product_name"] for it in items_r))
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**{s['date']}** at {s['time']} — {names[:40]}")
                with c2:
                    st.write(fmt_ugx(s["total"]))
        else:
            st.info("No sales recorded yet.")

    else:
        # ── ACTIVE DAY ────────────────────────────
        day_sales = get_sales(st.session_state.sale_date, st.session_state.sale_date)
        day_total = sum(float(s.get("total", 0) or 0) for s in day_sales)
        day_profit = sum(float(s.get("profit", 0) or 0) for s in day_sales)
        day_count = len(day_sales)

        st.markdown(f"""
        <div class="day-banner">
            <div class="day-active">🟢 Day Active — {st.session_state.sale_date}</div>
            <div style="margin-top:8px;display:flex;justify-content:center;gap:24px">
                <div><div style="font-size:.7rem;color:#777">Revenue</div><div style="color:#c9a84c;font-weight:700">{fmt_ugx(day_total)}</div></div>
                <div><div style="font-size:.7rem;color:#777">Profit</div><div style="color:#4caf7d;font-weight:700">{fmt_ugx(day_profit)}</div></div>
                <div><div style="font-size:.7rem;color:#777">Sales</div><div style="color:#f2ede4;font-weight:700">{day_count}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Product search and quick add
        prods = get_products()
        search = st.text_input("🔍 Search product", placeholder="Type name or barcode...", key="pos_search")
        filtered = [p for p in prods if
                    search.lower() in p["name"].lower() or
                    search in str(p.get("barcode", "") or "")
                    ] if search else prods

        if filtered:
            cols = st.columns(2)
            for i, p in enumerate(filtered):
                stk = int(p.get("stock", 0) or 0)
                price = float(p.get("selling_price", 0) or 0)
                icon = "🟢" if stk > 5 else "🟡" if stk > 0 else "🔴"
                with cols[i % 2]:
                    if st.button(
                        f"**{p['name']}**\n{fmt_ugx(price)}\n{icon} Stock: {stk}",
                        key=f"add_{p['id']}_{i}",
                        use_container_width=True,
                        disabled=(stk <= 0)
                    ):
                        found = False
                        for item in st.session_state.cart:
                            if item["id"] == p["id"]:
                                if item["qty"] < stk:
                                    item["qty"] += 1
                                    item["total"] = item["qty"] * item["price"]
                                found = True
                                break
                        if not found:
                            st.session_state.cart.append({
                                "id": p["id"], "name": p["name"], "qty": 1,
                                "price": price,
                                "cost": float(p.get("buying_price", 0) or 0),
                                "total": price
                            })
                        st.rerun()

        st.divider()

        # ── LIVE SALES TABLE ──────────────────────
        st.markdown("### 📋 Current Sale")
        if not st.session_state.cart:
            st.info("No items yet. Tap a product above to add it.")
        else:
            h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 2, 1])
            h1.markdown("**Item**"); h2.markdown("**Qty**")
            h3.markdown("**Price**"); h4.markdown("**Total**"); h5.markdown("")
            st.divider()

            to_del = []
            for i, item in enumerate(st.session_state.cart):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
                with c1:
                    st.write(f"{i+1}. {item['name']}")
                with c2:
                    nq = st.number_input("Qty", min_value=1, value=item["qty"],
                                         key=f"q_{i}", label_visibility="collapsed")
                    if nq != item["qty"]:
                        item["qty"] = nq
                        item["total"] = nq * item["price"]
                with c3:
                    st.write(fmt_ugx(item["price"]))
                with c4:
                    st.markdown(f"**{fmt_ugx(item['total'])}**")
                with c5:
                    if st.button("✕", key=f"rm_{i}"):
                        to_del.append(i)

            for idx in sorted(to_del, reverse=True):
                st.session_state.cart.pop(idx)
            if to_del:
                st.rerun()

            st.divider()
            total = sum(x["total"] for x in st.session_state.cart)
            count = sum(x["qty"] for x in st.session_state.cart)
            profit = sum((x["price"] - x["cost"]) * x["qty"] for x in st.session_state.cart)

            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                st.markdown(f"**{count} items**")
                st.markdown(f"### {fmt_ugx(total)}")
                st.caption(f"Profit: {fmt_ugx(profit)}")
            with c2:
                if st.button("🗑 Clear", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
            with c3:
                if st.button("🧾 Receipt", use_container_width=True):
                    pass
            with c4:
                if st.button("✅ Checkout", use_container_width=True, type="primary"):
                    with st.spinner("Saving..."):
                        sale_data = {"total": total, "profit": profit}
                        sale_id = save_sale(sale_data, st.session_state.cart)
                        if sale_id:
                            st.session_state.last_sale = {
                                "id": sale_id, "date": st.session_state.sale_date,
                                "time": now_time(), "items": list(st.session_state.cart),
                                "total": total, "profit": profit
                            }
                            st.session_state.cart = []
                            st.success(f"✅ Sale saved! {fmt_ugx(total)}")
                            st.rerun()

        # ── TODAY'S FULL LOG ──────────────────────
        st.divider()
        st.markdown("### 📋 Today's Full Sales Log")
        if day_sales:
            all_items = get_sale_items([s["id"] for s in day_sales])
            rows = []
            for s in day_sales:
                s_items = [it for it in all_items if it["sale_id"] == s["id"]]
                for it in s_items:
                    rows.append({
                        "#": len(rows) + 1,
                        "Time": s["time"],
                        "Item": it["product_name"],
                        "Qty": int(it["qty"]),
                        "Unit Price": fmt_ugx(it["unit_price"]),
                        "Total": fmt_ugx(it["line_total"])
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("Day Revenue", fmt_ugx(day_total))
                c2.metric("Day Profit", fmt_ugx(day_profit))
                c3.metric("Transactions", day_count)
        else:
            st.info("No sales recorded for this day yet.")

        # ── RECEIPT ───────────────────────────────
        if st.session_state.last_sale:
            st.divider()
            st.markdown("### 🧾 Last Receipt")
            s = st.session_state.last_sale
            line = "-" * 34
            rcpt = f"          DEBONUEL\n          Receipt\n{line}\n"
            rcpt += f"Date: {s['date']}    Time: {s['time']}\n{line}\n"
            rcpt += f"{'Item':<18}{'Qty':>4}  {'Total':>9}\n{line}\n"
            for it in s["items"]:
                nm = str(it["name"])[:17].ljust(18)
                q = str(it["qty"]).rjust(4)
                am = fmt_ugx(it["total"]).rjust(9)
                rcpt += f"{nm}{q}  {am}\n"
            rcpt += f"{line}\nTOTAL:  {fmt_ugx(s['total'])}\n{line}\n"
            rcpt += "   Thank you for shopping!\n   DEBONUEL - Your trusted shop"
            st.markdown(f'<div class="rcpt">{rcpt}</div>', unsafe_allow_html=True)

            r1, r2, r3 = st.columns(3)
            with r1:
                st.download_button("⬇ Download Receipt", rcpt,
                                   file_name=f"Receipt_{s['id'][:8]}.txt",
                                   use_container_width=True)
            with r2:
                wa = f"*DEBONUEL Receipt*\nDate: {s['date']} {s['time']}\n"
                for it in s["items"]:
                    wa += f"- {it['name']} x{it['qty']}: {fmt_ugx(it['total'])}\n"
                wa += f"*TOTAL: {fmt_ugx(s['total'])}*\nThank you for shopping at DEBONUEL!"
                st.link_button("💬 WhatsApp Receipt",
                               "https://wa.me/?text=" + wa.replace(" ", "%20").replace("\n", "%0A"),
                               use_container_width=True)
            with r3:
                st.download_button("🖨 Print Receipt",
                                   f'<html><head><style>body{{font-family:monospace;font-size:13px;padding:16px;max-width:300px;margin:0 auto;white-space:pre}}</style></head><body onload="window.print()">{rcpt}</body></html>',
                                   file_name=f"Print_{s['id'][:8]}.html",
                                   mime="text/html", use_container_width=True)

        # ── END DAY ───────────────────────────────
        st.divider()
        if st.button("⏹ End Day & Close Sales", use_container_width=True):
            wa_summary = (
                f"*DEBONUEL Day Summary — {st.session_state.sale_date}*\n\n"
                f"Revenue: {fmt_ugx(day_total)}\n"
                f"Profit: {fmt_ugx(day_profit)}\n"
                f"Total Sales: {day_count}\n\n"
                f"_DEBONUEL Business System_"
            )
            st.success(f"Day closed! Revenue: {fmt_ugx(day_total)} | Profit: {fmt_ugx(day_profit)}")
            st.link_button(
                "💬 Share Day Summary on WhatsApp",
                "https://wa.me/?text=" + wa_summary.replace(" ", "%20").replace("\n", "%0A")
            )
            st.session_state.day_started = False
            st.session_state.cart = []

# ══════════════════════════════════════════════════
# TAB 2 — STOCK
# ══════════════════════════════════════════════════
with tabs[1]:
    st.subheader("📦 Stock / Inventory")
    prods = get_products()
    sups = get_suppliers()

    low = [p for p in prods if 0 < int(p.get("stock", 0) or 0) <= 5]
    out = [p for p in prods if int(p.get("stock", 0) or 0) <= 0]
    if out:
        st.error(f"🔴 OUT OF STOCK: {', '.join(p['name'] for p in out)}")
    if low:
        st.warning(f"⚠ LOW STOCK: {', '.join(p['name'] + ' (' + str(int(p.get('stock',0) or 0)) + ')' for p in low)}")

    # WhatsApp reorder alert
    if low or out:
        low_list = "\n".join(f"- {p['name']} (stock: {int(p.get('stock',0) or 0)})" for p in (out + low))
        wa_reorder = f"*DEBONUEL Stock Alert*\n\nThe following items need restocking:\n{low_list}\n\nPlease supply urgently.\n_DEBONUEL Shop_"
        st.link_button(
            "📲 Send Reorder Alert via WhatsApp",
            "https://wa.me/?text=" + wa_reorder.replace(" ", "%20").replace("\n", "%0A")
        )

    with st.expander("➕ Add New Product"):
        with st.form("new_prod"):
            c1, c2 = st.columns(2)
            with c1:
                pn = st.text_input("Product Name *")
                pb = st.number_input("Buying Price (UGX)", min_value=0, value=0)
                pq = st.number_input("Opening Stock", min_value=0, value=0)
                pbc = st.text_input("Barcode (optional)")
            with c2:
                pcat = st.selectbox("Category", ["General", "Food and Drinks",
                                                  "Household", "Personal Care",
                                                  "Electronics", "Other"])
                ps_price = st.number_input("Selling Price (UGX)", min_value=0, value=0)
                sup_names = ["None"] + [s["name"] for s in sups]
                psup = st.selectbox("Supplier", sup_names)
                pmin = st.number_input("Reorder Level", min_value=0, value=5)

            if st.form_submit_button("✅ Save Product", type="primary"):
                if not pn:
                    st.error("Enter product name")
                elif ps_price <= 0:
                    st.error("Enter a selling price")
                else:
                    sup_id = ""
                    if psup != "None":
                        for s in sups:
                            if s["name"] == psup:
                                sup_id = s["id"]
                                break
                    ok = add_product({
                        "name": pn, "category": pcat,
                        "buying_price": pb, "selling_price": ps_price,
                        "stock": pq, "barcode": pbc,
                        "supplier_id": sup_id, "reorder_level": pmin
                    })
                    if ok:
                        st.success(f"'{pn}' added!")
                        st.rerun()

    st.divider()
    if not prods:
        st.info("No products yet. Add your first product above.")
    else:
        search_inv = st.text_input("🔍 Search inventory", placeholder="Search by name...")
        filtered_inv = [p for p in prods if search_inv.lower() in p["name"].lower()] if search_inv else prods

        for p in filtered_inv:
            stk = int(p.get("stock", 0) or 0)
            buy = float(p.get("buying_price", 0) or 0)
            sell = float(p.get("selling_price", 0) or 0)
            mg = round((sell - buy) / sell * 100) if sell > 0 else 0
            icon = "🟢" if stk > 5 else "🟡" if stk > 0 else "🔴"
            lbl = " 🔴 OUT" if stk <= 0 else " 🟡 LOW" if stk <= 5 else ""

            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(f"**{p['name']}**{lbl}")
                    st.caption(f"{p.get('category', '')} | Buy: {fmt_ugx(buy)} | Sell: {fmt_ugx(sell)} | Margin: {mg}%")
                    if p.get("barcode"):
                        st.caption(f"Barcode: {p['barcode']}")
                with c2:
                    st.markdown(f"{icon} **Stock: {stk}**")
                with c3:
                    with st.popover("✏ Edit"):
                        with st.form(f"ep_{p['id']}"):
                            en = st.text_input("Name", value=p["name"])
                            eb = st.number_input("Buy Price", value=buy, min_value=0.0)
                            es = st.number_input("Sell Price", value=sell, min_value=0.0)
                            eq = st.number_input("Stock", value=stk, min_value=0)
                            ebc = st.text_input("Barcode", value=str(p.get("barcode", "") or ""))
                            cs2, cd2 = st.columns(2)
                            with cs2:
                                if st.form_submit_button("Save"):
                                    update_product(p["id"], {
                                        "name": en, "buying_price": eb,
                                        "selling_price": es, "stock": eq,
                                        "barcode": ebc
                                    })
                                    st.rerun()
                            with cd2:
                                if st.form_submit_button("Delete"):
                                    delete_product(p["id"])
                                    st.rerun()
                st.divider()

# ══════════════════════════════════════════════════
# TAB 3 — REPORTS
# ══════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📊 Reports")

    period = st.radio("Period", ["Daily", "Weekly", "Monthly", "Yearly"], horizontal=True)
    today_dt = datetime.now().date()

    if period == "Daily":
        rd = st.date_input("Date", value=today_dt, key="rep_date")
        start, end = str(rd), str(rd)
        label = str(rd)
    elif period == "Weekly":
        rd = st.date_input("Any date in the week", value=today_dt, key="rep_date")
        mon = rd - timedelta(days=rd.weekday())
        start, end = str(mon), str(mon + timedelta(days=6))
        label = f"Week of {start}"
    elif period == "Monthly":
        rd = st.date_input("Any date in the month", value=today_dt, key="rep_date")
        start = str(rd.replace(day=1))
        last = calendar.monthrange(rd.year, rd.month)[1]
        end = str(rd.replace(day=last))
        label = rd.strftime("%B %Y")
    else:
        y = today_dt.year
        start, end = f"{y}-01-01", f"{y}-12-31"
        label = f"Year {y}"

    with st.spinner("Loading..."):
        sales = get_sales(start, end)
        sale_ids = [s["id"] for s in sales]
        items = get_sale_items(sale_ids) if sale_ids else []

    rev = sum(float(s.get("total", 0) or 0) for s in sales)
    prof = sum(float(s.get("profit", 0) or 0) for s in sales)
    cnt = len(sales)
    avg = rev / cnt if cnt > 0 else 0
    mg = round(prof / rev * 100) if rev > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="mcard"><div class="ml">Revenue</div><div class="mv">{fmt_ugx(rev)}</div><div class="ms">{cnt} sales</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="mcard"><div class="ml">Profit</div><div class="mv2">{fmt_ugx(prof)}</div><div class="ms">Margin {mg}%</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="mcard"><div class="ml">Transactions</div><div class="mv">{cnt}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="mcard"><div class="ml">Avg Sale</div><div class="mv">{fmt_ugx(avg)}</div></div>', unsafe_allow_html=True)

    if sales:
        df_sales = pd.DataFrame(sales)
        df_sales["total"] = pd.to_numeric(df_sales["total"], errors="coerce")
        chart_data = df_sales.groupby("date")["total"].sum().reset_index()
        chart_data.columns = ["Date", "Revenue"]
        fig = px.bar(chart_data, x="Date", y="Revenue", title=f"Sales — {label}",
                     color_discrete_sequence=["#c9a84c"])
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b",
                          font_color="#f2ede4", title_font_color="#c9a84c",
                          xaxis=dict(gridcolor="#262626"), yaxis=dict(gridcolor="#262626"))
        st.plotly_chart(fig, use_container_width=True)

        if items:
            df_it = pd.DataFrame(items)
            df_it["qty"] = pd.to_numeric(df_it["qty"], errors="coerce")
            df_it["line_total"] = pd.to_numeric(df_it["line_total"], errors="coerce")

            # Top products by quantity
            top_qty = df_it.groupby("product_name")["qty"].sum().reset_index()
            top_qty.columns = ["Product", "Units Sold"]
            top_qty = top_qty.sort_values("Units Sold", ascending=False).head(10)

            # Top products by revenue
            top_rev = df_it.groupby("product_name")["line_total"].sum().reset_index()
            top_rev.columns = ["Product", "Revenue"]
            top_rev = top_rev.sort_values("Revenue", ascending=False).head(10)

            col1, col2 = st.columns(2)
            with col1:
                fig2 = px.bar(top_qty, x="Units Sold", y="Product", orientation="h",
                              title="Top by Units Sold",
                              color_discrete_sequence=["#c9a84c"])
                fig2.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b",
                                   font_color="#f2ede4", yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig2, use_container_width=True)
            with col2:
                fig3 = px.bar(top_rev, x="Revenue", y="Product", orientation="h",
                              title="Top by Revenue",
                              color_discrete_sequence=["#4caf7d"])
                fig3.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b",
                                   font_color="#f2ede4", yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig3, use_container_width=True)

            st.markdown("### Full Transaction Log")
            log_rows = []
            for s in sales:
                s_items = [it for it in items if it["sale_id"] == s["id"]]
                for it in s_items:
                    log_rows.append({
                        "Date": s["date"], "Time": s["time"],
                        "Item": it["product_name"],
                        "Qty": int(it["qty"]),
                        "Unit Price": fmt_ugx(it["unit_price"]),
                        "Total": fmt_ugx(it["line_total"])
                    })
            if log_rows:
                st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)

        st.divider()
        # Download and share
        c1, c2, c3 = st.columns(3)
        with c1:
            csv_d = pd.DataFrame(log_rows).to_csv(index=False) if items else ""
            st.download_button("⬇ CSV", csv_d,
                               file_name=f"DEBONUEL_{label}.csv",
                               mime="text/csv", use_container_width=True)
        with c2:
            html_r = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>DEBONUEL Report</title>
<style>body{{font-family:sans-serif;max-width:700px;margin:0 auto;padding:24px}}
h1{{color:#c9a84c}}table{{width:100%;border-collapse:collapse}}
th{{background:#f5f2ec;padding:8px;text-align:left}}
td{{padding:8px;border-bottom:1px solid #eee}}</style></head><body>
<h1>DEBONUEL</h1><h2>Report - {label}</h2>
<p>Revenue: {fmt_ugx(rev)} | Profit: {fmt_ugx(prof)} | Sales: {cnt} | Margin: {mg}%</p>
<table><tr><th>Date</th><th>Time</th><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr>
{"".join(f"<tr><td>{r['Date']}</td><td>{r['Time']}</td><td>{r['Item']}</td><td>{r['Qty']}</td><td>{r['Unit Price']}</td><td>{r['Total']}</td></tr>" for r in log_rows)}
</table></body></html>"""
            st.download_button("⬇ Report", html_r,
                               file_name=f"DEBONUEL_Report_{label}.html",
                               mime="text/html", use_container_width=True)
        with c3:
            wa = (
                f"*DEBONUEL Report - {label}*\n\n"
                f"Revenue: {fmt_ugx(rev)}\n"
                f"Profit: {fmt_ugx(prof)}\n"
                f"Margin: {mg}%\n"
                f"Sales: {cnt}\n\n"
                f"_DEBONUEL Business System_"
            )
            st.link_button("💬 WhatsApp",
                           "https://wa.me/?text=" + wa.replace(" ", "%20").replace("\n", "%0A"),
                           use_container_width=True)
    else:
        st.info("No sales data for this period.")

# ══════════════════════════════════════════════════
# TAB 4 — EXPENSES
# ══════════════════════════════════════════════════
with tabs[3]:
    st.subheader("💰 Expenses Tracker")
    st.caption("Track daily expenses to calculate your true net profit.")

    with st.form("add_exp"):
        c1, c2 = st.columns(2)
        with c1:
            exp_date = st.date_input("Date", value=datetime.now().date())
            exp_cat = st.selectbox("Category", [
                "Stock Purchase", "Rent", "Electricity", "Water",
                "Transport", "Staff Salary", "Packaging", "Other"
            ])
            exp_amt = st.number_input("Amount (UGX)", min_value=0, value=0)
        with c2:
            exp_desc = st.text_input("Description", placeholder="e.g. Bought sugar from supplier")
            exp_sup = st.text_input("Paid To", placeholder="e.g. Supplier name")
            st.markdown("<br>", unsafe_allow_html=True)
            save_exp = st.form_submit_button("✅ Save Expense", type="primary", use_container_width=True)

        if save_exp:
            if exp_amt <= 0:
                st.error("Enter an amount greater than 0")
            else:
                try:
                    get_client().table("expenses").insert({
                        "id": uid(), "date": str(exp_date),
                        "category": exp_cat, "description": exp_desc,
                        "amount": exp_amt, "supplier": exp_sup,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    st.success(f"Expense saved: {fmt_ugx(exp_amt)}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    try:
        col1, col2 = st.columns(2)
        with col1:
            exp_start = st.date_input("From", value=datetime.now().date().replace(day=1), key="exp_s")
        with col2:
            exp_end = st.date_input("To", value=datetime.now().date(), key="exp_e")

        exps = get_client().table("expenses").select("*") \
            .gte("date", str(exp_start)).lte("date", str(exp_end)) \
            .order("date", desc=True).execute().data or []

        if exps:
            total_exp = sum(float(e.get("amount", 0) or 0) for e in exps)

            # Get sales for same period for net profit
            sales_p = get_sales(str(exp_start), str(exp_end))
            gross = sum(float(s.get("profit", 0) or 0) for s in sales_p)
            net = gross - total_exp

            c1, c2, c3 = st.columns(3)
            c1.metric("Gross Profit", fmt_ugx(gross))
            c2.metric("Total Expenses", fmt_ugx(total_exp))
            net_color = "normal" if net >= 0 else "inverse"
            c3.metric("Net Profit", fmt_ugx(net))

            # Expenses chart
            df_exp = pd.DataFrame(exps)
            df_exp["amount"] = pd.to_numeric(df_exp["amount"], errors="coerce")
            by_cat = df_exp.groupby("category")["amount"].sum().reset_index()
            fig_e = px.pie(by_cat, values="amount", names="category",
                           title="Expenses by Category",
                           color_discrete_sequence=px.colors.sequential.Oranges_r)
            fig_e.update_layout(paper_bgcolor="#0b0b0b", font_color="#f2ede4")
            st.plotly_chart(fig_e, use_container_width=True)

            st.divider()
            for e in exps:
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                c1.write(f"**{e['date']}** — {e.get('description', '')}")
                c2.write(e.get("category", ""))
                c3.write(fmt_ugx(e.get("amount", 0)))
                with c4:
                    if st.button("🗑", key=f"de_{e['id']}"):
                        get_client().table("expenses").delete().eq("id", e["id"]).execute()
                        st.rerun()

            # WhatsApp expense summary
            wa_exp = (
                f"*DEBONUEL Expense Summary*\n"
                f"Period: {exp_start} to {exp_end}\n\n"
                f"Gross Profit: {fmt_ugx(gross)}\n"
                f"Total Expenses: {fmt_ugx(total_exp)}\n"
                f"Net Profit: {fmt_ugx(net)}\n\n"
            )
            for cat, amt in by_cat.values:
                wa_exp += f"- {cat}: {fmt_ugx(amt)}\n"
            wa_exp += "\n_DEBONUEL Business System_"
            st.link_button(
                "💬 Share Expense Summary on WhatsApp",
                "https://wa.me/?text=" + wa_exp.replace(" ", "%20").replace("\n", "%0A")
            )
        else:
            st.info("No expenses for this period.")
    except Exception as ex:
        st.warning(f"Run the update_database.sql first to enable expenses. Error: {ex}")

# ══════════════════════════════════════════════════
# TAB 5 — CREDITS / DEBT TRACKER
# ══════════════════════════════════════════════════
with tabs[4]:
    st.subheader("🧾 Credit / Debt Tracker")
    st.caption("Track customers who buy on credit and what they owe you.")

    with st.expander("➕ Add Credit Sale"):
        with st.form("add_credit"):
            c1, c2 = st.columns(2)
            with c1:
                cr_name = st.text_input("Customer Name *")
                cr_phone = st.text_input("Phone", placeholder="+256...")
                cr_date = st.date_input("Date", value=datetime.now().date())
            with c2:
                cr_items = st.text_area("Items Bought", placeholder="e.g. 2kg Sugar, 1L Oil")
                cr_amt = st.number_input("Amount Owed (UGX)", min_value=0, value=0)
                cr_due = st.date_input("Due Date")

            if st.form_submit_button("✅ Record Credit", type="primary"):
                if not cr_name or cr_amt <= 0:
                    st.error("Enter customer name and amount")
                else:
                    try:
                        get_client().table("credits").insert({
                            "id": uid(), "customer_name": cr_name,
                            "phone": cr_phone, "date": str(cr_date),
                            "items": cr_items, "amount": cr_amt,
                            "paid": 0, "due_date": str(cr_due),
                            "status": "unpaid",
                            "created_at": datetime.now().isoformat()
                        }).execute()
                        st.success(f"Credit recorded for {cr_name}: {fmt_ugx(cr_amt)}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}. Run the SQL update first.")

    st.divider()

    try:
        credits = get_client().table("credits").select("*") \
            .order("date", desc=True).execute().data or []

        if credits:
            total_owed = sum(float(c.get("amount", 0) or 0) - float(c.get("paid", 0) or 0)
                             for c in credits if c.get("status") != "paid")
            unpaid = [c for c in credits if c.get("status") != "paid"]
            paid = [c for c in credits if c.get("status") == "paid"]

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Owed to You", fmt_ugx(total_owed))
            c2.metric("Unpaid Credits", len(unpaid))
            c3.metric("Paid Credits", len(paid))

            if unpaid:
                st.markdown("### ⚠ Unpaid Credits")
                for c in unpaid:
                    bal = float(c.get("amount", 0) or 0) - float(c.get("paid", 0) or 0)
                    st.markdown(f"""<div class="debtcard">
                    <strong>{c['customer_name']}</strong> — owes <strong style="color:#d95555">{fmt_ugx(bal)}</strong><br>
                    <small>📞 {c.get('phone','-')} | Date: {c['date']} | Due: {c.get('due_date','-')}<br>
                    Items: {c.get('items','-')}</small></div>""", unsafe_allow_html=True)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if c.get("phone"):
                            ph = str(c["phone"]).replace("+", "").replace(" ", "").replace("-", "")
                            wa_remind = (
                                f"Hello {c['customer_name']}, this is a reminder from DEBONUEL. "
                                f"You have an outstanding balance of {fmt_ugx(bal)} "
                                f"for {c.get('items','')}. "
                                f"Please pay by {c.get('due_date','')}. Thank you!"
                            )
                            st.link_button(
                                "💬 Send Reminder",
                                f"https://wa.me/{ph}?text={wa_remind.replace(' ', '%20')}",
                                use_container_width=True
                            )
                    with col2:
                        if st.button("✅ Mark Paid", key=f"paid_{c['id']}", use_container_width=True):
                            get_client().table("credits").update({
                                "status": "paid", "paid": c.get("amount", 0)
                            }).eq("id", c["id"]).execute()
                            st.rerun()
                    with col3:
                        if st.button("🗑 Delete", key=f"dcr_{c['id']}", use_container_width=True):
                            get_client().table("credits").delete().eq("id", c["id"]).execute()
                            st.rerun()
                    st.divider()

            if paid:
                with st.expander("✅ Paid Credits"):
                    for c in paid:
                        st.write(f"**{c['customer_name']}** — {fmt_ugx(c.get('amount', 0))} — Paid ✅")
        else:
            st.info("No credit records yet. Add one above.")

    except Exception as ex:
        st.warning(f"Run the SQL update to enable credits tracking. Error: {ex}")

# ══════════════════════════════════════════════════
# TAB 6 — SUPPLIERS
# ══════════════════════════════════════════════════
with tabs[5]:
    st.subheader("🏭 Suppliers")

    with st.expander("➕ Add Supplier"):
        with st.form("new_sup"):
            c1, c2 = st.columns(2)
            with c1:
                sn = st.text_input("Supplier Name *")
                sph = st.text_input("Phone / WhatsApp", placeholder="+256...")
                spr = st.text_input("Products Supplied")
            with c2:
                slc = st.text_input("Location")
                stm = st.selectbox("Payment Terms", ["Cash on Delivery", "30 Days Credit",
                                                      "60 Days Credit", "Prepayment", "Other"])
                snt = st.text_area("Notes")
            if st.form_submit_button("✅ Save Supplier", type="primary"):
                if not sn:
                    st.error("Enter supplier name")
                else:
                    ok = add_supplier({
                        "name": sn, "phone": sph,
                        "products_supplied": spr, "location": slc,
                        "payment_terms": stm, "notes": snt
                    })
                    if ok:
                        st.success(f"'{sn}' added!")
                        st.rerun()

    st.divider()
    sups = get_suppliers()
    if not sups:
        st.info("No suppliers yet.")
    else:
        for s in sups:
            st.markdown(f'<div class="supcard"><strong>{s["name"]}</strong><br><small>📞 {s.get("phone", "-")} &nbsp;|&nbsp; 📍 {s.get("location", "-")}<br>📦 {s.get("products_supplied", "-")} &nbsp;|&nbsp; 💳 {s.get("payment_terms", "-")}{("<br>📝 " + str(s["notes"])) if s.get("notes") else ""}</small></div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if s.get("phone"):
                    ph = str(s["phone"]).replace("+", "").replace(" ", "").replace("-", "")
                    st.link_button("💬 WhatsApp", f"https://wa.me/{ph}", use_container_width=True)
            with c2:
                if s.get("phone"):
                    order_msg = (
                        f"Hello {s['name']}, I would like to order the following items for DEBONUEL shop. "
                        f"Please confirm availability and price. Thank you!"
                    )
                    st.link_button(
                        "🛒 Send Order",
                        f"https://wa.me/{ph}?text={order_msg.replace(' ', '%20')}",
                        use_container_width=True
                    )
            with c3:
                if st.button("🗑 Delete", key=f"ds_{s['id']}", use_container_width=True):
                    delete_supplier(s["id"])
                    st.rerun()
            st.divider()

# ══════════════════════════════════════════════════
# TAB 7 — CALCULATOR
# ══════════════════════════════════════════════════
with tabs[6]:
    st.subheader("🧮 Business Calculator")
    st.caption("Quick calculator for prices, profits and quantities.")

    # Display
    st.markdown(f"""
    <div class="calc-display">
        <div class="calc-expr">{st.session_state.calc_expr}</div>
        <div class="calc-val">{st.session_state.calc_display}</div>
    </div>
    """, unsafe_allow_html=True)

    # Calculator as HTML component — renders properly on mobile
    calc_result = st.session_state.get("calc_result", "")

    calc_html = """
<style>
.calc-wrap{background:#0b0b0b;border-radius:16px;padding:12px;max-width:400px;margin:0 auto;font-family:sans-serif}
.calc-screen{background:#1d1d1d;border-radius:12px;padding:16px 14px 10px;text-align:right;margin-bottom:10px;min-height:80px}
.calc-expr-disp{font-size:.8rem;color:#666;min-height:18px;word-break:break-all}
.calc-num{font-size:2rem;font-weight:700;color:#c9a84c;word-break:break-all;min-height:44px}
.calc-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.cbtn{padding:18px 4px;border:none;border-radius:10px;font-size:1.1rem;font-weight:600;cursor:pointer;width:100%;transition:opacity .15s}
.cbtn:active{opacity:.7}
.cbtn-num{background:#1d1d1d;color:#f2ede4;border:1px solid #2a2a2a}
.cbtn-op{background:#4caf7d;color:#fff}
.cbtn-eq{background:#c9a84c;color:#000}
.cbtn-fn{background:#2a2a2a;color:#f2ede4}
.cbtn-cl{background:#d95555;color:#fff}
</style>
<div class="calc-wrap">
  <div class="calc-screen">
    <div class="calc-expr-disp" id="expr"></div>
    <div class="calc-num" id="disp">0</div>
  </div>
  <div class="calc-grid">
    <button class="cbtn cbtn-cl" onclick="press('C')">C</button>
    <button class="cbtn cbtn-fn" onclick="press('±')">±</button>
    <button class="cbtn cbtn-fn" onclick="press('%')">%</button>
    <button class="cbtn cbtn-op" onclick="press('÷')">÷</button>

    <button class="cbtn cbtn-num" onclick="press('7')">7</button>
    <button class="cbtn cbtn-num" onclick="press('8')">8</button>
    <button class="cbtn cbtn-num" onclick="press('9')">9</button>
    <button class="cbtn cbtn-op" onclick="press('×')">×</button>

    <button class="cbtn cbtn-num" onclick="press('4')">4</button>
    <button class="cbtn cbtn-num" onclick="press('5')">5</button>
    <button class="cbtn cbtn-num" onclick="press('6')">6</button>
    <button class="cbtn cbtn-op" onclick="press('−')">−</button>

    <button class="cbtn cbtn-num" onclick="press('1')">1</button>
    <button class="cbtn cbtn-num" onclick="press('2')">2</button>
    <button class="cbtn cbtn-num" onclick="press('3')">3</button>
    <button class="cbtn cbtn-op" onclick="press('+')">+</button>

    <button class="cbtn cbtn-num" onclick="press('0')">0</button>
    <button class="cbtn cbtn-num" onclick="press('.')">.</button>
    <button class="cbtn cbtn-fn" onclick="press('⌫')">⌫</button>
    <button class="cbtn cbtn-eq" onclick="press('=')">=</button>
  </div>
</div>

<script>
var expr = '';
var justCalc = false;

function press(btn) {
  var disp = document.getElementById('disp');
  var exprEl = document.getElementById('expr');

  if (btn === 'C') {
    expr = '';
    disp.textContent = '0';
    exprEl.textContent = '';
    justCalc = false;
  } else if (btn === '⌫') {
    if (justCalc) { expr = ''; justCalc = false; }
    expr = expr.slice(0, -1);
    disp.textContent = expr || '0';
    exprEl.textContent = '';
  } else if (btn === '=') {
    try {
      exprEl.textContent = expr;
      var safe = expr.replace(/×/g,'*').replace(/÷/g,'/').replace(/−/g,'-');
      var result = Function('"use strict"; return (' + safe + ')')();
      if (Number.isInteger(result)) {
        disp.textContent = result.toLocaleString();
      } else {
        disp.textContent = parseFloat(result.toFixed(4)).toLocaleString();
      }
      expr = String(result);
      justCalc = true;
    } catch(e) {
      disp.textContent = 'Error';
      expr = '';
    }
  } else if (btn === '±') {
    try {
      var v = parseFloat(expr) * -1;
      expr = String(v);
      disp.textContent = v.toLocaleString();
    } catch(e) {}
  } else if (btn === '%') {
    try {
      var v = parseFloat(expr) / 100;
      expr = String(v);
      disp.textContent = v;
    } catch(e) {}
  } else {
    if (justCalc && !isNaN(btn)) { expr = ''; justCalc = false; }
    expr += btn;
    disp.textContent = expr;
    exprEl.textContent = '';
  }
}
</script>
"""
    st.components.v1.html(calc_html, height=420)

    st.divider()

    # Business calculators
    st.markdown("### 💡 Quick Business Tools")

    tool = st.selectbox("Select tool", [
        "Profit Margin Calculator",
        "Selling Price Calculator",
        "VAT Calculator",
        "Percentage Change Calculator",
        "Bulk Discount Calculator"
    ])

    if tool == "Profit Margin Calculator":
        c1, c2 = st.columns(2)
        with c1:
            buy_p = st.number_input("Buying Price (UGX)", min_value=0, value=0, key="t1_buy")
        with c2:
            sell_p = st.number_input("Selling Price (UGX)", min_value=0, value=0, key="t1_sell")
        if sell_p > 0:
            profit_amt = sell_p - buy_p
            margin = (profit_amt / sell_p) * 100
            markup = (profit_amt / buy_p * 100) if buy_p > 0 else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Profit per Unit", fmt_ugx(profit_amt))
            c2.metric("Margin %", f"{margin:.1f}%")
            c3.metric("Markup %", f"{markup:.1f}%")

    elif tool == "Selling Price Calculator":
        c1, c2 = st.columns(2)
        with c1:
            cost = st.number_input("Buying Price (UGX)", min_value=0, value=0, key="t2_cost")
        with c2:
            target_margin = st.number_input("Target Margin %", min_value=0, max_value=100, value=20, key="t2_mg")
        if cost > 0 and target_margin < 100:
            suggested = cost / (1 - target_margin / 100)
            st.success(f"Suggested Selling Price: **{fmt_ugx(round(suggested))}**")
            st.caption(f"Profit per unit: {fmt_ugx(round(suggested - cost))}")

    elif tool == "VAT Calculator":
        c1, c2 = st.columns(2)
        with c1:
            vat_amt = st.number_input("Amount (UGX)", min_value=0, value=0, key="t3_amt")
        with c2:
            vat_rate = st.number_input("VAT Rate %", min_value=0, max_value=100, value=18, key="t3_rate")
        if vat_amt > 0:
            vat = vat_amt * vat_rate / 100
            total_vat = vat_amt + vat
            c1, c2 = st.columns(2)
            c1.metric("VAT Amount", fmt_ugx(vat))
            c2.metric("Total with VAT", fmt_ugx(total_vat))

    elif tool == "Percentage Change Calculator":
        c1, c2 = st.columns(2)
        with c1:
            old_v = st.number_input("Old Value (UGX)", min_value=0, value=0, key="t4_old")
        with c2:
            new_v = st.number_input("New Value (UGX)", min_value=0, value=0, key="t4_new")
        if old_v > 0:
            pct = ((new_v - old_v) / old_v) * 100
            direction = "increase" if pct >= 0 else "decrease"
            st.metric("Change", f"{abs(pct):.1f}% {direction}", delta=fmt_ugx(new_v - old_v))

    elif tool == "Bulk Discount Calculator":
        c1, c2, c3 = st.columns(3)
        with c1:
            unit_price = st.number_input("Unit Price (UGX)", min_value=0, value=0, key="t5_up")
        with c2:
            quantity = st.number_input("Quantity", min_value=1, value=1, key="t5_qty")
        with c3:
            discount = st.number_input("Discount %", min_value=0, max_value=100, value=0, key="t5_disc")
        if unit_price > 0:
            subtotal = unit_price * quantity
            disc_amt = subtotal * discount / 100
            final = subtotal - disc_amt
            c1, c2, c3 = st.columns(3)
            c1.metric("Subtotal", fmt_ugx(subtotal))
            c2.metric("Discount", fmt_ugx(disc_amt))
            c3.metric("Final Price", fmt_ugx(final))

# ══════════════════════════════════════════════════
# TAB 8 — BACKUP
# ══════════════════════════════════════════════════
with tabs[7]:
    st.subheader("💾 Backup & Data")
    st.success("✅ All data saves automatically to Supabase database in real time!")

    with st.spinner("Loading..."):
        prods = get_products()
        sales = get_sales()
        items = get_sale_items()
        sups = get_suppliers()

    c1, c2 = st.columns(2)
    with c1:
        backup = {
            "products": prods, "sales": sales,
            "sale_items": items, "suppliers": sups,
            "exported_at": datetime.now().isoformat(), "shop": "DEBONUEL"
        }
        st.download_button(
            "⬇ Full Backup (JSON)",
            json.dumps(backup, indent=2),
            file_name=f"DEBONUEL_Backup_{today()}.json",
            mime="application/json", use_container_width=True
        )
    with c2:
        if prods:
            st.download_button(
                "⬇ Products (CSV)",
                pd.DataFrame(prods).to_csv(index=False),
                file_name=f"DEBONUEL_Products_{today()}.csv",
                mime="text/csv", use_container_width=True
            )

    st.divider()
    total_rev = sum(float(s.get("total", 0) or 0) for s in sales)
    total_prof = sum(float(s.get("profit", 0) or 0) for s in sales)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Products", len(prods))
    m2.metric("Total Sales", len(sales))
    m3.metric("Suppliers", len(sups))
    m4.metric("All-time Revenue", fmt_ugx(total_rev))

    st.divider()
    st.markdown("### All-time Profit Summary")
    c1, c2 = st.columns(2)
    c1.metric("All-time Gross Profit", fmt_ugx(total_prof))
    if prods:
        out_of_stock = len([p for p in prods if int(p.get("stock", 0) or 0) <= 0])
        c2.metric("Products Out of Stock", out_of_stock)
