import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar
import json
from db import (
    get_products, add_product, update_product, delete_product,
    get_sales, get_sale_items, save_sale,
    get_suppliers, add_supplier, delete_supplier,
    uid, today, now_time, fmt_ugx
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
.ms{font-size:.68rem;color:#555;margin-top:2px}
.rcpt{font-family:monospace;font-size:.8rem;background:#161616;border:1px solid #262626;border-radius:10px;padding:16px;white-space:pre;line-height:1.9;overflow-x:auto}
.supcard{background:#161616;border:1px solid #262626;border-radius:12px;padding:14px;margin-bottom:10px}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────
st.markdown('<div class="logo">DEBO<span>NUEL</span></div>', unsafe_allow_html=True)
st.caption("📅 " + datetime.now().strftime("%A, %d %B %Y  |  %H:%M"))
st.divider()

# ── SESSION STATE ─────────────────────────────────
if "cart" not in st.session_state:
    st.session_state.cart = []
if "last_sale" not in st.session_state:
    st.session_state.last_sale = None

# ── TABS ──────────────────────────────────────────
tabs = st.tabs(["🛒 Sales", "📦 Stock", "📷 Scan", "📊 Reports", "🏭 Suppliers", "💾 Backup"])

# ══════════════════════════════════════════════════
# TAB 1 — SALES
# ══════════════════════════════════════════════════
with tabs[0]:
    st.subheader("🛒 Today's Sales")
    st.caption(f"Date: {today()}")

    prods = get_products()

    if not prods:
        st.info("No products yet. Go to Stock tab to add products.")
    else:
        # Search
        search = st.text_input("🔍 Search product by name or barcode", placeholder="Type to filter...")
        filtered = [p for p in prods if
                    search.lower() in p["name"].lower() or
                    search in str(p.get("barcode", "") or "")
                    ] if search else prods

        if filtered:
            st.markdown("**Tap a product to add it to the sale:**")
            cols = st.columns(2)
            for i, p in enumerate(filtered):
                stock = int(p.get("stock", 0) or 0)
                price = float(p.get("selling_price", 0) or 0)
                icon = "🟢" if stock > 5 else "🟡" if stock > 0 else "🔴"
                label = f"{p['name']}\n{fmt_ugx(price)}\n{icon} Stock: {stock}"
                with cols[i % 2]:
                    if st.button(label, key=f"p_{p['id']}_{i}",
                                 use_container_width=True, disabled=(stock <= 0)):
                        found = False
                        for item in st.session_state.cart:
                            if item["id"] == p["id"]:
                                if item["qty"] < stock:
                                    item["qty"] += 1
                                    item["total"] = item["qty"] * item["price"]
                                found = True
                                break
                        if not found:
                            st.session_state.cart.append({
                                "id": p["id"], "name": p["name"],
                                "qty": 1, "price": price,
                                "cost": float(p.get("buying_price", 0) or 0),
                                "total": price
                            })
                        st.rerun()
        else:
            st.warning("No products match your search.")

    st.divider()

    # ── LIVE SALES TABLE ─────────────────────────
    st.markdown("### 📋 Sales Log")

    if not st.session_state.cart:
        st.info("No items yet. Tap a product above to add it to the sale.")
    else:
        to_del = []
        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
            with c1:
                st.write(f"**{i+1}. {item['name']}**")
            with c2:
                nq = st.number_input("", min_value=1, value=item["qty"],
                                     key=f"q_{i}", label_visibility="collapsed")
                if nq != item["qty"]:
                    item["qty"] = nq
                    item["total"] = nq * item["price"]
            with c3:
                st.write(fmt_ugx(item["price"]))
            with c4:
                st.write(f"**{fmt_ugx(item['total'])}**")
            with c5:
                if st.button("✕", key=f"rm_{i}"):
                    to_del.append(i)

        for idx in sorted(to_del, reverse=True):
            st.session_state.cart.pop(idx)
        if to_del:
            st.rerun()

        total = sum(x["total"] for x in st.session_state.cart)
        count = sum(x["qty"] for x in st.session_state.cart)
        st.divider()

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.markdown(f"**{count} items sold**")
            st.markdown(f"## {fmt_ugx(total)}")
        with c2:
            if st.button("🗑 Clear", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
        with c3:
            if st.button("✅ Checkout", use_container_width=True, type="primary"):
                with st.spinner("Saving sale to database..."):
                    profit = sum((x["price"] - x["cost"]) * x["qty"]
                                 for x in st.session_state.cart)
                    sale_data = {"total": total, "profit": profit}
                    sale_id = save_sale(sale_data, st.session_state.cart)
                    if sale_id:
                        st.session_state.last_sale = {
                            "id": sale_id, "date": today(), "time": now_time(),
                            "items": list(st.session_state.cart),
                            "total": total, "profit": profit
                        }
                        st.session_state.cart = []
                        st.success(f"✅ Sale saved! {fmt_ugx(total)}")
                        st.rerun()

    # ── RECEIPT ──────────────────────────────────
    if st.session_state.last_sale:
        st.divider()
        st.markdown("### 🧾 Last Receipt")
        s = st.session_state.last_sale
        line = "-" * 32
        rcpt = f"        DEBONUEL\n        Receipt\n{line}\n"
        rcpt += f"Date: {s['date']}    Time: {s['time']}\n{line}\n"
        rcpt += f"{'Item':<18}{'Qty':>4}  {'Total':>8}\n{line}\n"
        for it in s["items"]:
            nm = str(it["name"])[:17].ljust(18)
            q = str(it["qty"]).rjust(4)
            am = fmt_ugx(it["total"]).rjust(8)
            rcpt += f"{nm}{q}  {am}\n"
        rcpt += f"{line}\nTOTAL: {fmt_ugx(s['total'])}\n{line}\n"
        rcpt += "  Thank you for shopping!\n  DEBONUEL - Your trusted shop"

        st.markdown(f'<div class="rcpt">{rcpt}</div>', unsafe_allow_html=True)

        r1, r2, r3 = st.columns(3)
        with r1:
            st.download_button("⬇ Receipt TXT", rcpt,
                               file_name=f"Receipt_{s['id'][:8]}.txt",
                               use_container_width=True)
        with r2:
            wa = f"*DEBONUEL Receipt*\nDate: {s['date']} {s['time']}\n"
            for it in s["items"]:
                wa += f"- {it['name']} x{it['qty']}: {fmt_ugx(it['total'])}\n"
            wa += f"*TOTAL: {fmt_ugx(s['total'])}*\nThank you!"
            st.link_button("💬 WhatsApp",
                           "https://wa.me/?text=" + wa.replace(" ", "%20").replace("\n", "%0A"),
                           use_container_width=True)
        with r3:
            if st.button("🖨 Print Receipt", use_container_width=True):
                st.markdown(f"""
                <script>
                var w=window.open('','_blank');
                w.document.write('<html><head><title>Receipt</title>'
                +'<style>body{{font-family:monospace;font-size:13px;padding:16px;'
                +'max-width:300px;margin:0 auto;white-space:pre}}'
                +'@media print{{@page{{margin:4mm}}}}</style></head>'
                +'<body>{rcpt.replace(chr(10), '<br>')}</body></html>');
                w.document.close();setTimeout(function(){{w.print();}},400);
                </script>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# TAB 2 — STOCK
# ══════════════════════════════════════════════════
with tabs[1]:
    st.subheader("📦 Stock / Inventory")

    prods = get_products()
    sups = get_suppliers()

    # Alerts
    low = [p for p in prods if 0 < int(p.get("stock", 0) or 0) <= 5]
    out = [p for p in prods if int(p.get("stock", 0) or 0) <= 0]
    if out:
        st.error(f"🔴 OUT OF STOCK: {', '.join(p['name'] for p in out)}")
    if low:
        st.warning(f"🟡 LOW STOCK: {', '.join(p['name'] for p in low)}")

    # Add product
    with st.expander("➕ Add New Product"):
        with st.form("new_prod"):
            c1, c2 = st.columns(2)
            with c1:
                pn = st.text_input("Product Name *")
                pb = st.number_input("Buying Price (UGX)", min_value=0, value=0)
                pq = st.number_input("Stock Qty", min_value=0, value=0)
                pbc = st.text_input("Barcode (optional)")
            with c2:
                pcat = st.selectbox("Category", ["General","Food and Drinks",
                                                  "Household","Personal Care",
                                                  "Electronics","Other"])
                ps = st.number_input("Selling Price (UGX)", min_value=0, value=0)
                sup_names = ["None"] + [s["name"] for s in sups]
                psup = st.selectbox("Supplier", sup_names)

            if st.form_submit_button("✅ Save Product", type="primary"):
                if not pn:
                    st.error("Enter product name")
                else:
                    sup_id = ""
                    if psup != "None":
                        for s in sups:
                            if s["name"] == psup:
                                sup_id = s["id"]
                                break
                    ok = add_product({
                        "name": pn, "category": pcat,
                        "buying_price": pb, "selling_price": ps,
                        "stock": pq, "barcode": pbc, "supplier_id": sup_id
                    })
                    if ok:
                        st.success(f"'{pn}' added!")
                        st.rerun()

    st.divider()

    # Products list
    if not prods:
        st.info("No products yet. Add your first product above.")
    else:
        for p in prods:
            stk = int(p.get("stock", 0) or 0)
            icon = "🟢" if stk > 5 else "🟡" if stk > 0 else "🔴"
            buy = float(p.get("buying_price", 0) or 0)
            sell = float(p.get("selling_price", 0) or 0)
            mg = round((sell - buy) / sell * 100) if sell > 0 else 0

            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    lbl = " 🔴 OUT" if stk <= 0 else " 🟡 LOW" if stk <= 5 else ""
                    st.markdown(f"**{p['name']}**{lbl}")
                    st.caption(f"{p.get('category','')} | Buy: {fmt_ugx(buy)} | Sell: {fmt_ugx(sell)} | Margin: {mg}%")
                    if p.get("barcode"):
                        st.caption(f"Barcode: {p['barcode']}")
                with c2:
                    st.markdown(f"{icon} **Stock: {stk}**")
                with c3:
                    with st.popover("✏ Edit"):
                        with st.form(f"ep_{p['id']}"):
                            en = st.text_input("Name", value=p["name"])
                            eb = st.number_input("Buy Price", value=buy)
                            es = st.number_input("Sell Price", value=sell)
                            eq = st.number_input("Stock", value=stk, min_value=0)
                            ebc = st.text_input("Barcode", value=str(p.get("barcode","") or ""))
                            cs, cd = st.columns(2)
                            with cs:
                                if st.form_submit_button("Save"):
                                    update_product(p["id"], {
                                        "name": en, "buying_price": eb,
                                        "selling_price": es, "stock": eq,
                                        "barcode": ebc
                                    })
                                    st.rerun()
                            with cd:
                                if st.form_submit_button("Delete"):
                                    delete_product(p["id"])
                                    st.rerun()
                st.divider()

# ══════════════════════════════════════════════════
# TAB 3 — SCANNER
# ══════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📷 Barcode Lookup")
    st.info("Type or paste a barcode below to find the product and add it to the sale.")

    bc = st.text_input("Barcode", placeholder="Scan or type barcode number...")
    if bc:
        prods = get_products()
        match = [p for p in prods if str(p.get("barcode","") or "") == bc.strip()]
        if match:
            p = match[0]
            stk = int(p.get("stock", 0) or 0)
            st.success(f"✅ Found: **{p['name']}**")
            c1, c2 = st.columns(2)
            c1.metric("Selling Price", fmt_ugx(p["selling_price"]))
            c2.metric("Stock", stk)
            if stk > 0:
                if st.button("➕ Add to Sale", type="primary"):
                    found = False
                    for item in st.session_state.cart:
                        if item["id"] == p["id"]:
                            item["qty"] += 1
                            item["total"] = item["qty"] * float(p["selling_price"])
                            found = True
                            break
                    if not found:
                        st.session_state.cart.append({
                            "id": p["id"], "name": p["name"], "qty": 1,
                            "price": float(p["selling_price"]),
                            "cost": float(p.get("buying_price", 0) or 0),
                            "total": float(p["selling_price"])
                        })
                    st.success("Added! Go to Sales tab to checkout.")
            else:
                st.error("Out of stock.")
        else:
            st.warning(f"No product found for barcode: {bc}")

    st.divider()
    st.markdown("### Assign Barcode to Product")
    prods = get_products()
    if prods:
        with st.form("asgn_bc"):
            bc2 = st.text_input("Barcode to assign")
            psel = st.selectbox("Product", [p["name"] for p in prods])
            if st.form_submit_button("Assign"):
                if bc2 and psel:
                    for p in prods:
                        if p["name"] == psel:
                            update_product(p["id"], {"barcode": bc2})
                            st.success(f"Barcode {bc2} assigned to {psel}!")
                            break

# ══════════════════════════════════════════════════
# TAB 4 — REPORTS
# ══════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📊 Reports")

    period = st.radio("Period", ["Daily","Weekly","Monthly","Yearly"], horizontal=True)
    today_dt = datetime.now().date()

    if period == "Daily":
        rd = st.date_input("Date", value=today_dt)
        start, end = str(rd), str(rd)
        label = str(rd)
    elif period == "Weekly":
        rd = st.date_input("Any date in the week", value=today_dt)
        mon = rd - timedelta(days=rd.weekday())
        start, end = str(mon), str(mon + timedelta(days=6))
        label = f"Week of {start}"
    elif period == "Monthly":
        rd = st.date_input("Any date in the month", value=today_dt)
        start = str(rd.replace(day=1))
        last = calendar.monthrange(rd.year, rd.month)[1]
        end = str(rd.replace(day=last))
        label = rd.strftime("%B %Y")
    else:
        y = today_dt.year
        start, end = f"{y}-01-01", f"{y}-12-31"
        label = f"Year {y}"

    with st.spinner("Loading report..."):
        sales = get_sales(start, end)
        sale_ids = [s["id"] for s in sales]
        items = get_sale_items(sale_ids) if sale_ids else []

    rev = sum(float(s.get("total", 0) or 0) for s in sales)
    prof = sum(float(s.get("profit", 0) or 0) for s in sales)
    cnt = len(sales)
    avg = rev / cnt if cnt > 0 else 0
    mg = round(prof / rev * 100) if rev > 0 else 0

    # Stat cards
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
        # Sales chart
        df_sales = pd.DataFrame(sales)
        df_sales["total"] = pd.to_numeric(df_sales["total"], errors="coerce")
        chart = df_sales.groupby("date")["total"].sum().reset_index()
        chart.columns = ["Date", "Revenue"]
        fig = px.bar(chart, x="Date", y="Revenue", title=f"Sales — {label}",
                     color_discrete_sequence=["#c9a84c"])
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b",
                          font_color="#f2ede4", title_font_color="#c9a84c",
                          xaxis=dict(gridcolor="#262626"), yaxis=dict(gridcolor="#262626"))
        st.plotly_chart(fig, use_container_width=True)

        if items:
            # Top products
            df_items = pd.DataFrame(items)
            df_items["qty"] = pd.to_numeric(df_items["qty"], errors="coerce")
            df_items["line_total"] = pd.to_numeric(df_items["line_total"], errors="coerce")
            top = df_items.groupby("product_name")["qty"].sum().reset_index()
            top.columns = ["Product","Units Sold"]
            top = top.sort_values("Units Sold", ascending=False).head(10)
            fig2 = px.bar(top, x="Units Sold", y="Product", orientation="h",
                          title="Top Products", color_discrete_sequence=["#c9a84c"])
            fig2.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b",
                               font_color="#f2ede4", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)

            # Transaction log — every line item
            st.markdown("### Transaction Log")
            log_rows = []
            for s in sales:
                s_items = [it for it in items if it["sale_id"] == s["id"]]
                for it in s_items:
                    log_rows.append({
                        "Date": s["date"], "Time": s["time"],
                        "Item": it["product_name"], "Qty": it["qty"],
                        "Unit Price": fmt_ugx(it["unit_price"]),
                        "Total": fmt_ugx(it["line_total"])
                    })
            if log_rows:
                st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)

        # Downloads
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            csv_data = pd.DataFrame(log_rows).to_csv(index=False) if items else ""
            st.download_button("⬇ CSV", csv_data,
                               file_name=f"DEBONUEL_{label}.csv",
                               mime="text/csv", use_container_width=True)
        with c2:
            # Build HTML report
            html_rep = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
            <title>DEBONUEL Report</title>
            <style>body{{font-family:sans-serif;max-width:700px;margin:0 auto;padding:24px}}
            h1{{color:#c9a84c}}table{{width:100%;border-collapse:collapse;margin-top:12px}}
            th{{background:#f5f2ec;padding:8px;text-align:left;font-size:.8rem}}
            td{{padding:8px;border-bottom:1px solid #eee}}</style></head><body>
            <h1>DEBONUEL</h1><h2>Report &mdash; {label}</h2>
            <p>Revenue: {fmt_ugx(rev)} | Profit: {fmt_ugx(prof)} | Sales: {cnt} | Margin: {mg}%</p>
            <table><tr><th>Date</th><th>Time</th><th>Item</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr>
            {"".join(f"<tr><td>{r['Date']}</td><td>{r['Time']}</td><td>{r['Item']}</td><td>{r['Qty']}</td><td>{r['Unit Price']}</td><td>{r['Total']}</td></tr>" for r in log_rows)}
            </table></body></html>"""
            st.download_button("⬇ Report HTML", html_rep,
                               file_name=f"DEBONUEL_Report_{label}.html",
                               mime="text/html", use_container_width=True)
        with c3:
            wa = f"*DEBONUEL Report - {label}*\n\nRevenue: {fmt_ugx(rev)}\nProfit: {fmt_ugx(prof)}\nMargin: {mg}%\nSales: {cnt}\n\n_DEBONUEL Business System_"
            st.link_button("💬 WhatsApp",
                           "https://wa.me/?text=" + wa.replace(" ", "%20").replace("\n", "%0A"),
                           use_container_width=True)
    else:
        st.info("No sales data for this period.")

# ══════════════════════════════════════════════════
# TAB 5 — SUPPLIERS
# ══════════════════════════════════════════════════
with tabs[4]:
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
                stm = st.selectbox("Payment Terms", ["Cash on Delivery","30 Days Credit",
                                                      "60 Days Credit","Prepayment","Other"])
                snt = st.text_area("Notes")
            if st.form_submit_button("✅ Save Supplier", type="primary"):
                if not sn:
                    st.error("Enter supplier name")
                else:
                    ok = add_supplier({
                        "name": sn, "phone": sph, "products_supplied": spr,
                        "location": slc, "payment_terms": stm, "notes": snt
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
            st.markdown(f"""<div class="supcard">
            <strong>{s['name']}</strong><br>
            <small>📞 {s.get('phone','-')} &nbsp;|&nbsp; 📍 {s.get('location','-')}<br>
            📦 {s.get('products_supplied','-')} &nbsp;|&nbsp; 💳 {s.get('payment_terms','-')}
            {('<br>📝 ' + str(s['notes'])) if s.get('notes') else ''}</small>
            </div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if s.get("phone"):
                    ph = str(s["phone"]).replace("+","").replace(" ","").replace("-","")
                    st.link_button("💬 WhatsApp", f"https://wa.me/{ph}", use_container_width=True)
            with c2:
                if st.button("🗑 Delete", key=f"ds_{s['id']}", use_container_width=True):
                    delete_supplier(s["id"])
                    st.rerun()
            st.divider()

# ══════════════════════════════════════════════════
# TAB 6 — BACKUP
# ══════════════════════════════════════════════════
with tabs[5]:
    st.subheader("💾 Backup & Data")

    st.success("✅ All data saves automatically to Supabase database in real time!")
    st.info("Your database URL: https://mjlslbhulkznxymjmzxv.supabase.co")

    st.divider()
    st.markdown("### Export / Download")

    with st.spinner("Loading data..."):
        prods = get_products()
        sales = get_sales()
        items = get_sale_items()
        sups = get_suppliers()

    c1, c2 = st.columns(2)
    with c1:
        backup = {
            "products": prods, "sales": sales,
            "sale_items": items, "suppliers": sups,
            "exported_at": datetime.now().isoformat(),
            "shop": "DEBONUEL"
        }
        st.download_button(
            "⬇ Full Backup (JSON)",
            json.dumps(backup, indent=2),
            file_name=f"DEBONUEL_Backup_{today()}.json",
            mime="application/json",
            use_container_width=True
        )
    with c2:
        if prods:
            st.download_button(
                "⬇ Products (CSV)",
                pd.DataFrame(prods).to_csv(index=False),
                file_name=f"DEBONUEL_Products_{today()}.csv",
                mime="text/csv",
                use_container_width=True
            )

    st.divider()
    st.markdown("### Summary")
    total_rev = sum(float(s.get("total", 0) or 0) for s in sales)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Products", len(prods))
    m2.metric("Total Sales", len(sales))
    m3.metric("Suppliers", len(sups))
    m4.metric("Total Revenue", fmt_ugx(total_rev))
