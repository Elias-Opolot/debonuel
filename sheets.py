import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

SHEETS = {
    "products":  "Products",
    "sales":     "Sales",
    "sale_items":"Sale_Items",
    "suppliers": "Suppliers",
}

HEADERS = {
    "products":   ["id","name","category","buying_price","selling_price","stock","barcode","supplier_id","created_at"],
    "sales":      ["id","date","time","total","profit","items_count"],
    "sale_items": ["id","sale_id","product_id","product_name","qty","unit_price","line_total"],
    "suppliers":  ["id","name","phone","products_supplied","location","payment_terms","notes","created_at"],
}

def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error("Google Sheets connection failed: " + str(e))
        return None

def get_sheet(tab_key):
    client = get_client()
    if not client:
        return None
    try:
        sheet_name = st.secrets["sheet_name"]
        wb = client.open(sheet_name)
        try:
            ws = wb.worksheet(SHEETS[tab_key])
        except gspread.WorksheetNotFound:
            ws = wb.add_worksheet(title=SHEETS[tab_key], rows=1000, cols=20)
            ws.append_row(HEADERS[tab_key])
        return ws
    except Exception as e:
        st.error("Sheet error: " + str(e))
        return None

def read_df(tab_key):
    ws = get_sheet(tab_key)
    if ws is None:
        return pd.DataFrame(columns=HEADERS[tab_key])
    try:
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=HEADERS[tab_key])
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame(columns=HEADERS[tab_key])

def append_row(tab_key, row_dict):
    ws = get_sheet(tab_key)
    if ws is None:
        return False
    try:
        row = [str(row_dict.get(h, "")) for h in HEADERS[tab_key]]
        ws.append_row(row)
        return True
    except Exception as e:
        st.error("Write error: " + str(e))
        return False

def update_row(tab_key, row_id, updates):
    ws = get_sheet(tab_key)
    if ws is None:
        return False
    try:
        records = ws.get_all_records()
        for i, rec in enumerate(records):
            if str(rec.get("id")) == str(row_id):
                row_num = i + 2
                for key, val in updates.items():
                    if key in HEADERS[tab_key]:
                        col = HEADERS[tab_key].index(key) + 1
                        ws.update_cell(row_num, col, str(val))
                return True
        return False
    except Exception as e:
        st.error("Update error: " + str(e))
        return False

def delete_row(tab_key, row_id):
    ws = get_sheet(tab_key)
    if ws is None:
        return False
    try:
        records = ws.get_all_records()
        for i, rec in enumerate(records):
            if str(rec.get("id")) == str(row_id):
                ws.delete_rows(i + 2)
                return True
        return False
    except Exception as e:
        st.error("Delete error: " + str(e))
        return False

def new_id():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")

def today():
    return datetime.now().strftime("%Y-%m-%d")

def now_time():
    return datetime.now().strftime("%H:%M")

def fmt_ugx(n):
    try:
        return "UGX {:,.0f}".format(float(n))
    except:
        return "UGX 0"
