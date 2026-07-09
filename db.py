from supabase import create_client
import streamlit as st
from datetime import datetime
import uuid

SUPABASE_URL = "https://mjlslbhulkznxymjmzxv.supabase.co"
SUPABASE_KEY = "sb_publishable_Te-gOz78RBPBVvmAZM4jDQ_-oH9I8o7"

@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def uid():
    return str(uuid.uuid4())

def today():
    return datetime.now().strftime("%Y-%m-%d")

def now_time():
    return datetime.now().strftime("%H:%M")

def fmt_ugx(n):
    try:
        return "UGX {:,.0f}".format(float(n or 0))
    except:
        return "UGX 0"

# ── PRODUCTS ──────────────────────────────────────
def get_products():
    try:
        res = get_client().table("products").select("*").order("name").execute()
        return res.data or []
    except Exception as e:
        st.error("Error loading products: " + str(e))
        return []

def add_product(data):
    try:
        data["id"] = uid()
        data["created_at"] = datetime.now().isoformat()
        get_client().table("products").insert(data).execute()
        return True
    except Exception as e:
        st.error("Error adding product: " + str(e))
        return False

def update_product(pid, data):
    try:
        get_client().table("products").update(data).eq("id", pid).execute()
        return True
    except Exception as e:
        st.error("Error updating product: " + str(e))
        return False

def delete_product(pid):
    try:
        get_client().table("products").delete().eq("id", pid).execute()
        return True
    except Exception as e:
        st.error("Error deleting product: " + str(e))
        return False

# ── SALES ─────────────────────────────────────────
def get_sales(start=None, end=None):
    try:
        q = get_client().table("sales").select("*").order("date", desc=True).order("time", desc=True)
        if start:
            q = q.gte("date", start)
        if end:
            q = q.lte("date", end)
        return q.execute().data or []
    except Exception as e:
        st.error("Error loading sales: " + str(e))
        return []

def get_sale_items(sale_ids=None):
    try:
        q = get_client().table("sale_items").select("*")
        if sale_ids:
            q = q.in_("sale_id", sale_ids)
        return q.execute().data or []
    except Exception as e:
        st.error("Error loading sale items: " + str(e))
        return []

def save_sale(sale, items):
    try:
        sb = get_client()
        sale_id = uid()
        sb.table("sales").insert({
            "id": sale_id,
            "date": today(),
            "time": now_time(),
            "total": sale["total"],
            "profit": sale["profit"],
            "items_count": len(items)
        }).execute()
        for it in items:
            sb.table("sale_items").insert({
                "id": uid(),
                "sale_id": sale_id,
                "product_id": it["id"],
                "product_name": it["name"],
                "qty": it["qty"],
                "unit_price": it["price"],
                "line_total": it["total"]
            }).execute()
            # deduct stock
            prods = get_client().table("products").select("stock").eq("id", it["id"]).execute().data
            if prods:
                old = int(prods[0].get("stock", 0) or 0)
                new_stock = max(0, old - it["qty"])
                get_client().table("products").update({"stock": new_stock}).eq("id", it["id"]).execute()
        return sale_id
    except Exception as e:
        st.error("Error saving sale: " + str(e))
        return None

# ── SUPPLIERS ─────────────────────────────────────
def get_suppliers():
    try:
        res = get_client().table("suppliers").select("*").order("name").execute()
        return res.data or []
    except Exception as e:
        st.error("Error loading suppliers: " + str(e))
        return []

def add_supplier(data):
    try:
        data["id"] = uid()
        data["created_at"] = datetime.now().isoformat()
        get_client().table("suppliers").insert(data).execute()
        return True
    except Exception as e:
        st.error("Error adding supplier: " + str(e))
        return False

def delete_supplier(sid):
    try:
        get_client().table("suppliers").delete().eq("id", sid).execute()
        return True
    except Exception as e:
        st.error("Error deleting supplier: " + str(e))
        return False
