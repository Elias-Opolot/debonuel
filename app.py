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
.mv3{font-family:'Syne',sans-serif;font-weight:700;font-size:1.15rem;color:#d95555}
.ms{font-size:.68rem;color:#555;margin-top:2px}
.rcpt{font-family:monospace;font-size:.82rem;background:#161616;border:1px solid #262626;border-radius:10px;padding:16px;white-space:pre;line-height:1.9;overflow-x:auto;color:#f2ede4}
.supcard{background:#161616;border:1px solid #262626;border-radius:12px;padding:14px;margin-bottom:10px}
.day-banner{background:linear-gradient(135deg,#1a1500,#0b0b0b);border:1px solid #c9a84c;border-radius:14px;padding:16px;margin-bottom:14px;text-align:center}
.day-active{color:#c9a84c;font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem}
.srow{display:flex;align-items:center;padding:8px 0;border-bottom:1px solid #262626;gap:8px}
.stbl-head{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;background:#1d1d1d;border-radius:8px;padding:8px 10px;font-size:.72rem;color:#777;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px}
.stbl-row{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;padding:8px 10px;border-bottom:1px solid #1a1a1a;font-size:.88rem;align-items:center}
.prd-btn{background:#1d1d1d;border:1px solid #262626;border-radius:10px;padding:12px;cursor:pointer;text-align:center;transition:border-color .2s}
.alert-red{background:rgba(217,85,85,.1);border:1px solid rgba(217,85,85,.3);border-radius:10px;padding:10px 14px;color:#d95555;font-size:.83rem;margin-bottom:8px}
.alert-gold{background:rgba(201,168,76,.1);border:1px solid rgba(201,168,76,.3);border-radius:10px;padding:10px 14px;color:#c9a84c;font-size:.83rem;margin-bottom:8px}
div[data-testid="stButton"] button{border-radius:10px;font-family:'DM Sans',sans-serif;font-weight:500;transition:all .2s}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────
st.markdown('<div class="logo">DEBO<span>NUEL</span></div>', unsafe_allow_html=True)
st.caption("📅 " + datetime.now().strftime("%A, %d %B %Y  |  %H:%M"))
st.divider()

# ── SESSION STATE ─────────────────────────────────
for key, val in {
    "cart": [], "last_sale": None,
    "day_started": False, "sale_date": today(),
    "day_sales": [], "scanned_code": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── TABS ──────────────────────────────────────────
tabs = st.tabs(["🛒 Sales", "📦 Stock", "📷 Scan", "📊 Reports", "💰 Expenses", "🏭 Suppliers", "💾 Backup"])

# ══════════════════════════════════════════════════
# TAB 1 — SALES
# ══════════════════════════════════════════════════
with tabs[0]:

    # ── DAY CONTROL ───────────────────────────────
    if not st.session_state.day_started:
        st.markdown("### Start a Sales Day")
        st.markdown("Select the date and start recording sales for the day.")
        col1, col2 = st.columns([2, 1])
        with col1:
            sel_date = st.date_input(
                "Sales Date",
                value=datetime.now().date(),
                key="date_picker"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("▶ Start Day", type="primary", use_container_width=True):
                st.session_state.day_started = True
                st.session_state.sale_date = str(sel_date)
                st.session_state.cart = []
                st.session_state.day_sales = []
                st.rerun()

        # Show previous day summary if exists
        st.divider()
        st.markdown("### Recent Sales")
        recent = get_sales()[:5]
        if recent:
            for s in recent:
                items = get_sale_items([s["id"]])
                names = ", ".join(set(it["product_name"] for it in items))
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**{s['date']}** at {s['time']} — {names}")
                with c2:
                    st.write(fmt_ugx(s["total"]))
        else:
            st.info("No sales recorded yet.")

    else:
        # ── ACTIVE DAY ────────────────────────────
        day_sales_today = get_sales(
            st.session_state.sale_date,
            st.session_state.sale_date
        )
        day_total = sum(float(s.get("total", 0) or 0) for s in day_sales_today)
        day_profit = sum(float(s.get("profit", 0) or 0) for s in day_sales_today)
        day_count = len(day_sales_today)

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

        # Check if a barcode was scanned from Scan tab
        if st.session_state.scanned_code:
            code = st.session_state.scanned_code
            prods = get_products()
            match = [p for p in prods if str(p.get("barcode","") or "") == code]
            if match:
                p = match[0]
                stk = int(p.get("stock", 0) or 0)
                if stk > 0:
                    found = False
                    for item in st.session_state.cart:
                        if item["id"] == p["id"]:
                            item["qty"] += 1
                            item["total"] = item["qty"] * item["price"]
                            found = True
                            break
                    if not found:
                        st.session_state.cart.append({
                            "id": p["id"], "name": p["name"], "qty": 1,
                            "price": float(p.get("selling_price", 0) or 0),
                            "cost": float(p.get("buying_price", 0) or 0),
                            "total": float(p.get("selling_price", 0) or 0)
                        })
                    st.success(f"✅ Added from scan: {p['name']}")
            st.session_state.scanned_code = ""

        # Product search and quick add
        prods = get_products()
        search = st.text_input("🔍 Search product", placeholder="Type name or barcode...", key="pos_search")
        filtered = [p for p in prods if
                    search.lower() in p["name"].lower() or
                    search in str(p.get("barcode","") or "")
                    ] if search else prods

        if filtered:
            cols = st.columns(2)
            for i, p in enumerate(filtered):
                stk = int(p.get("stock", 0) or 0)
                price = float(p.get("selling_price", 0) or 0)
                icon = "🟢" if stk > 5 else "🟡" if stk > 0 else "🔴"
                with cols[i % 2]:
                    btn_label = f"**{p['name']}**\n{fmt_ugx(price)}\n{icon} Stock: {stk}"
                    if st.button(btn_label, key=f"add_{p['id']}_{i}",
                                 use_container_width=True, disabled=(stk <= 0)):
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
        else:
            if search:
                st.warning("No products match your search.")

        st.divider()

        # ── LIVE SALES TABLE ──────────────────────
        st.markdown("### 📋 Current Sale")

        if not st.session_state.cart:
            st.info("No items yet. Tap a product above or scan a barcode.")
        else:
            # Table header
            h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 2, 1])
            h1.markdown("**Item**")
            h2.markdown("**Qty**")
            h3.markdown("**Price**")
            h4.markdown("**Total**")
            h5.markdown("")
            st.divider()

            to_del = []
            for i, item in enumerate(st.session_state.cart):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
                with c1:
                    st.write(f"{i+1}. {item['name']}")
                with c2:
                    nq = st.number_input("", min_value=1, value=item["qty"],
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
                    if st.session_state.last_sale:
                        st.session_state.show_receipt = True
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

        # ── TODAY'S TRANSACTIONS TABLE ────────────
        st.divider()
        st.markdown("### 📋 Today's Full Sales Log")
        if day_sales_today:
            all_items = get_sale_items([s["id"] for s in day_sales_today])
            rows = []
            for s in day_sales_today:
                s_items = [it for it in all_items if it["sale_id"] == s["id"]]
                for j, it in enumerate(s_items):
                    rows.append({
                        "#": len(rows) + 1,
                        "Time": s["time"],
                        "Item": it["product_name"],
                        "Qty": int(it["qty"]),
                        "Unit Price": fmt_ugx(it["unit_price"]),
                        "Total": fmt_ugx(it["line_total"])
                    })
            if rows:
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True
                )
                # Day totals
                c1, c2, c3 = st.columns(3)
                c1.metric("Day Revenue", fmt_ugx(day_total))
                c2.metric("Day Profit", fmt_ugx(day_profit))
                c3.metric("Transactions", day_count)
        else:
            st.info("No sales recorded today yet.")

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
                st.download_button("⬇ Receipt", rcpt,
                                   file_name=f"Receipt_{s['id'][:8]}.txt",
                                   use_container_width=True)
            with r2:
                wa = f"*DEBONUEL Receipt*\nDate: {s['date']} {s['time']}\n"
                for it in s["items"]:
                    wa += f"- {it['name']} x{it['qty']}: {fmt_ugx(it['total'])}\n"
                wa += f"*TOTAL: {fmt_ugx(s['total'])}*\nThank you for shopping at DEBONUEL!"
                st.link_button("💬 WhatsApp",
                               "https://wa.me/?text=" + wa.replace(" ", "%20").replace("\n", "%0A"),
                               use_container_width=True)
            with r3:
                st.download_button("🖨 Print (HTML)", f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Receipt</title>
<style>body{{font-family:monospace;font-size:13px;padding:16px;max-width:300px;margin:0 auto;white-space:pre}}
@media print{{@page{{margin:4mm}}}}</style></head>
<body onload="window.print()">{rcpt}</body></html>""",
                                   file_name=f"Print_Receipt_{s['id'][:8]}.html",
                                   mime="text/html",
                                   use_container_width=True)

        # ── END DAY ───────────────────────────────
        st.divider()
        if st.button("⏹ End Day & Close Sales", use_container_width=True):
            st.session_state.day_started = False
            st.session_state.cart = []
            wa_summary = f"*DEBONUEL Day Summary — {st.session_state.sale_date}*\n\n"
            wa_summary += f"Revenue: {fmt_ugx(day_total)}\n"
            wa_summary += f"Profit: {fmt_ugx(day_profit)}\n"
            wa_summary += f"Total Sales: {day_count}\n\n"
            wa_summary += "_DEBONUEL Business System_"
            st.success(f"Day closed! Revenue: {fmt_ugx(day_total)} | Profit: {fmt_ugx(day_profit)}")
            st.link_button("💬 Share Day Summary on WhatsApp",
                           "https://wa.me/?text=" + wa_summary.replace(" ", "%20").replace("\n", "%0A"))
            st.rerun()

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
        st.markdown(f'<div class="alert-red">🔴 OUT OF STOCK: {", ".join(p["name"] for p in out)}</div>', unsafe_allow_html=True)
    if low:
        st.markdown(f'<div class="alert-gold">⚠ LOW STOCK: {", ".join(p["name"] + " (" + str(int(p.get("stock",0) or 0)) + ")" for p in low)}</div>', unsafe_allow_html=True)

    with st.expander("➕ Add New Product"):
        with st.form("new_prod"):
            c1, c2 = st.columns(2)
            with c1:
                pn = st.text_input("Product Name *")
                pb = st.number_input("Buying Price (UGX)", min_value=0, value=0)
                pq = st.number_input("Opening Stock", min_value=0, value=0)
                pbc = st.text_input("Barcode (optional)")
            with c2:
                pcat = st.selectbox("Category", ["General","Food and Drinks",
                                                  "Household","Personal Care",
                                                  "Electronics","Other"])
                ps_price = st.number_input("Selling Price (UGX)", min_value=0, value=0)
                sup_names = ["None"] + [s["name"] for s in sups]
                psup = st.selectbox("Supplier", sup_names)
                pmin = st.number_input("Reorder Level (alert when stock hits this)", min_value=0, value=5)

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
                    st.caption(f"{p.get('category','')} | Buy: {fmt_ugx(buy)} | Sell: {fmt_ugx(sell)} | Margin: {mg}%")
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
                            ebc = st.text_input("Barcode", value=str(p.get("barcode","") or ""))
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
# TAB 3 — SCAN
# ══════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📷 Barcode Scanner")

    # ── HOW SCANNING WORKS ────────────────────────
    st.info(
        "**How to scan a barcode:**\n\n"
        "1. Click the **Open Scanner** button below — it opens a scanner page in a new tab\n"
        "2. Allow camera access when asked\n"
        "3. Point your camera at the barcode — it reads automatically\n"
        "4. The barcode number appears on screen — copy it\n"
        "5. Come back here and paste it in the box below"
    )

    # Build the scanner page as a data URL so it opens in new tab
    scanner_page = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>DEBONUEL Scanner</title>
<script src="https://unpkg.com/@zxing/library@latest/umd/index.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0b0b;color:#f2ede4;font-family:sans-serif;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:20px}
h1{color:#c9a84c;font-size:1.4rem;margin-bottom:6px;letter-spacing:.08em}
p{color:#777;font-size:.83rem;margin-bottom:16px;text-align:center}
#video{width:100%;max-width:480px;border-radius:14px;background:#000;min-height:260px;display:block}
#result-box{width:100%;max-width:480px;margin-top:14px;background:#161616;border:2px solid #262626;border-radius:12px;padding:16px;text-align:center}
#result-label{font-size:.72rem;color:#777;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px}
#result-code{font-size:1.4rem;font-weight:700;color:#c9a84c;letter-spacing:.05em;min-height:36px;word-break:break-all}
#status{font-size:.82rem;color:#777;margin-top:8px}
.btn{width:100%;max-width:480px;padding:13px;border:none;border-radius:10px;font-size:1rem;font-weight:600;cursor:pointer;margin-top:10px}
.btn-gold{background:#c9a84c;color:#000}
.btn-dark{background:#262626;color:#f2ede4}
#copy-btn{display:none}
</style>
</head>
<body>
<h1>DEBONUEL Scanner</h1>
<p>Point camera at barcode to scan</p>
<video id="video" playsinline autoplay muted></video>
<div id="result-box">
  <div id="result-label">Scanned Barcode</div>
  <div id="result-code">---</div>
  <div id="status">Press Start to begin</div>
</div>
<button class="btn btn-gold" onclick="startScan()">Start Camera</button>
<button class="btn btn-dark" onclick="stopScan()">Stop Camera</button>
<button class="btn btn-gold" id="copy-btn" onclick="copyCode()">Copy Barcode Number</button>

<script>
var stream = null;
var reader = null;
var scanned = '';

function startScan() {
  var status = document.getElementById('status');
  status.textContent = 'Starting camera...';
  status.style.color = '#777';
  navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } }
  }).then(function(s) {
    stream = s;
    var vid = document.getElementById('video');
    vid.srcObject = stream;
    vid.play();
    status.textContent = 'Camera on — point at barcode...';
    status.style.color = '#c9a84c';
    if (window.ZXing) {
      reader = new ZXing.BrowserMultiFormatReader();
      reader.decodeFromVideoElement(vid, function(result, err) {
        if (result) {
          scanned = result.getText();
          document.getElementById('result-code').textContent = scanned;
          document.getElementById('status').textContent = 'Barcode scanned successfully!';
          document.getElementById('status').style.color = '#4caf7d';
          document.getElementById('result-box').style.borderColor = '#4caf7d';
          document.getElementById('copy-btn').style.display = 'block';
          stopScan();
        }
      });
    } else {
      status.textContent = 'Scanner library loading... please wait and try again.';
    }
  }).catch(function(err) {
    if (err.name === 'NotAllowedError') {
      status.textContent = 'Camera permission denied. Please allow camera access.';
    } else {
      status.textContent = 'Error: ' + err.message;
    }
    status.style.color = '#d95555';
  });
}

function stopScan() {
  if (stream) { stream.getTracks().forEach(function(t) { t.stop(); }); stream = null; }
  if (reader) { try { reader.reset(); } catch(e) {} reader = null; }
}

function copyCode() {
  if (scanned) {
    navigator.clipboard.writeText(scanned).then(function() {
      document.getElementById('status').textContent = 'Copied! Go back and paste it in the app.';
    }).catch(function() {
      document.getElementById('status').textContent = 'Copy manually: ' + scanned;
    });
  }
}

window.onload = function() { startScan(); };
</script>
</body>
</html>"""

    SCANNER_URL = "https://elias-opolot.github.io/debonuel/scanner.html"

    st.link_button(
        "📷 Open Camera Scanner",
        SCANNER_URL,
        use_container_width=True
    )

    st.divider()

    # Manual barcode entry
    st.markdown("### Enter Barcode Number")
    st.caption("After scanning, paste the barcode number here to find the product.")
    bc = st.text_input("Type or paste barcode number", placeholder="e.g. 6001255", key="manual_bc")
    if bc:
        prods = get_products()
        match = [p for p in prods if str(p.get("barcode","") or "") == bc.strip()]
        if match:
            p = match[0]
            stk = int(p.get("stock", 0) or 0)
            st.success(f"✅ Found: **{p['name']}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Selling Price", fmt_ugx(p["selling_price"]))
            c2.metric("Buying Price", fmt_ugx(p.get("buying_price", 0)))
            c3.metric("Stock", stk)
            if stk > 0:
                if st.button("➕ Add to Current Sale", type="primary", use_container_width=True):
                    if not st.session_state.day_started:
                        st.warning("Start a sales day first in the Sales tab.")
                    else:
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
                        st.success(f"Added {p['name']} to sale! Go to Sales tab.")
            else:
                st.error("This product is out of stock.")
        elif bc:
            st.warning(f"No product found with barcode: {bc}")
            st.info("You can assign this barcode to a product below.")

    st.divider()
    st.markdown("### Assign Barcode to Product")
    prods = get_products()
    if prods:
        with st.form("asgn_bc"):
            bc2 = st.text_input("Barcode number")
            psel = st.selectbox("Select Product", [p["name"] for p in prods])
            if st.form_submit_button("Assign Barcode", type="primary"):
                if bc2 and psel:
                    for p in prods:
                        if p["name"] == psel:
                            update_product(p["id"], {"barcode": bc2})
                            st.success(f"✅ Barcode '{bc2}' assigned to {psel}!")
                            break
    else:
        st.info("Add products first in the Stock tab.")

# ══════════════════════════════════════════════════
# TAB 4 — REPORTS
# ══════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📊 Reports")

    period = st.radio("Period", ["Daily","Weekly","Monthly","Yearly"], horizontal=True)
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
        chart_data.columns = ["Date","Revenue"]
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
            top = df_it.groupby("product_name")["qty"].sum().reset_index()
            top.columns = ["Product","Units Sold"]
            top = top.sort_values("Units Sold", ascending=False).head(10)
            fig2 = px.bar(top, x="Units Sold", y="Product", orientation="h",
                          title="Top Products", color_discrete_sequence=["#c9a84c"])
            fig2.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b",
                               font_color="#f2ede4", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)

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
        c1, c2, c3 = st.columns(3)
        with c1:
            csv_d = pd.DataFrame(log_rows).to_csv(index=False) if items else ""
            st.download_button("⬇ CSV", csv_d,
                               file_name=f"DEBONUEL_{label}.csv",
                               mime="text/csv", use_container_width=True)
        with c2:
            html_r = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>DEBONUEL Report</title>
<style>body{{font-family:sans-serif;max-width:700px;margin:0 auto;padding:24px}}h1{{color:#c9a84c}}
table{{width:100%;border-collapse:collapse}}th{{background:#f5f2ec;padding:8px;text-align:left}}
td{{padding:8px;border-bottom:1px solid #eee}}</style></head><body>
<h1>DEBONUEL</h1><h2>Report &mdash; {label}</h2>
<p>Revenue: {fmt_ugx(rev)} | Profit: {fmt_ugx(prof)} | Sales: {cnt} | Margin: {mg}%</p>
<table><tr><th>Date</th><th>Time</th><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr>
{"".join(f"<tr><td>{r['Date']}</td><td>{r['Time']}</td><td>{r['Item']}</td><td>{r['Qty']}</td><td>{r['Unit Price']}</td><td>{r['Total']}</td></tr>" for r in log_rows)}
</table></body></html>"""
            st.download_button("⬇ Report HTML", html_r,
                               file_name=f"DEBONUEL_Report_{label}.html",
                               mime="text/html", use_container_width=True)
        with c3:
            wa = f"*DEBONUEL Report - {label}*\n\nRevenue: {fmt_ugx(rev)}\nProfit: {fmt_ugx(prof)}\nMargin: {mg}%\nSales: {cnt}\n\n_DEBONUEL Business System_"
            st.link_button("💬 WhatsApp",
                           "https://wa.me/?text=" + wa.replace(" ","%20").replace("\n","%0A"),
                           use_container_width=True)
    else:
        st.info("No sales data for this period.")

# ══════════════════════════════════════════════════
# TAB 5 — EXPENSES
# ══════════════════════════════════════════════════
with tabs[4]:
    st.subheader("💰 Expenses Tracker")
    st.caption("Track your daily business expenses to see your true net profit.")

    with st.form("add_exp"):
        c1, c2, c3 = st.columns(3)
        with c1:
            exp_date = st.date_input("Date", value=datetime.now().date())
            exp_cat = st.selectbox("Category", [
                "Stock Purchase","Rent","Electricity","Water",
                "Transport","Staff Salary","Packaging","Other"
            ])
        with c2:
            exp_desc = st.text_input("Description", placeholder="e.g. Bought sugar from supplier")
            exp_amt = st.number_input("Amount (UGX)", min_value=0, value=0)
        with c3:
            exp_supplier = st.text_input("Supplier / Paid To", placeholder="optional")
            st.markdown("<br>", unsafe_allow_html=True)
            save_exp = st.form_submit_button("✅ Save Expense", type="primary", use_container_width=True)

        if save_exp:
            if exp_amt <= 0:
                st.error("Enter an amount")
            else:
                from db import get_client
                get_client().table("expenses").insert({
                    "id": uid(),
                    "date": str(exp_date),
                    "category": exp_cat,
                    "description": exp_desc,
                    "amount": exp_amt,
                    "supplier": exp_supplier,
                    "created_at": datetime.now().isoformat()
                }).execute()
                st.success(f"Expense saved: {fmt_ugx(exp_amt)}")
                st.rerun()

    st.divider()

    # Show expenses
    try:
        from db import get_client
        exp_start = st.date_input("Show expenses from", value=datetime.now().date().replace(day=1))
        exp_end = st.date_input("To", value=datetime.now().date())
        exps = get_client().table("expenses").select("*")\
            .gte("date", str(exp_start)).lte("date", str(exp_end))\
            .order("date", desc=True).execute().data or []

        if exps:
            total_exp = sum(float(e.get("amount",0) or 0) for e in exps)
            st.metric("Total Expenses", fmt_ugx(total_exp))

            # Expenses by category chart
            df_exp = pd.DataFrame(exps)
            df_exp["amount"] = pd.to_numeric(df_exp["amount"], errors="coerce")
            by_cat = df_exp.groupby("category")["amount"].sum().reset_index()
            fig_e = px.pie(by_cat, values="amount", names="category",
                           title="Expenses by Category",
                           color_discrete_sequence=px.colors.sequential.Oranges_r)
            fig_e.update_layout(paper_bgcolor="#0b0b0b", font_color="#f2ede4")
            st.plotly_chart(fig_e, use_container_width=True)

            # Profit vs Expenses
            sales_period = get_sales(str(exp_start), str(exp_end))
            gross_profit = sum(float(s.get("profit",0) or 0) for s in sales_period)
            net_profit = gross_profit - total_exp
            c1, c2, c3 = st.columns(3)
            c1.metric("Gross Profit", fmt_ugx(gross_profit))
            c2.metric("Total Expenses", fmt_ugx(total_exp))
            c3.metric("Net Profit", fmt_ugx(net_profit),
                      delta=f"{'+' if net_profit >= 0 else ''}{fmt_ugx(net_profit)}")

            st.divider()
            for e in exps:
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                c1.write(f"**{e['date']}** — {e.get('description','')}")
                c2.write(e.get("category",""))
                c3.write(fmt_ugx(e.get("amount",0)))
                with c4:
                    if st.button("🗑", key=f"de_{e['id']}"):
                        get_client().table("expenses").delete().eq("id", e["id"]).execute()
                        st.rerun()
        else:
            st.info("No expenses recorded for this period.")
    except Exception as ex:
        st.warning("Expenses table not set up yet. Run the setup SQL again with the expenses table added.")

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
            st.markdown(f'<div class="supcard"><strong>{s["name"]}</strong><br><small>📞 {s.get("phone","-")} &nbsp;|&nbsp; 📍 {s.get("location","-")}<br>📦 {s.get("products_supplied","-")} &nbsp;|&nbsp; 💳 {s.get("payment_terms","-")}{("<br>📝 " + str(s["notes"])) if s.get("notes") else ""}</small></div>', unsafe_allow_html=True)
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
# TAB 7 — BACKUP
# ══════════════════════════════════════════════════
with tabs[6]:
    st.subheader("💾 Backup & Data")
    st.success("✅ All data saves automatically to Supabase in real time!")

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
        st.download_button("⬇ Full Backup (JSON)",
                           json.dumps(backup, indent=2),
                           file_name=f"DEBONUEL_Backup_{today()}.json",
                           mime="application/json", use_container_width=True)
    with c2:
        if prods:
            st.download_button("⬇ Products (CSV)",
                               pd.DataFrame(prods).to_csv(index=False),
                               file_name=f"DEBONUEL_Products_{today()}.csv",
                               mime="text/csv", use_container_width=True)

    st.divider()
    total_rev = sum(float(s.get("total",0) or 0) for s in sales)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Products", len(prods))
    m2.metric("Total Sales", len(sales))
    m3.metric("Suppliers", len(sups))
    m4.metric("All-time Revenue", fmt_ugx(total_rev))
