"""Streamlit frontend dashboard for TradeStoreDB."""
import datetime
import requests
import streamlit as st

API_BASE_URL = "http://localhost:1000/api/v1"

st.set_page_config(
    page_title="Trade Store Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Trade Store Management Dashboard")
st.markdown("View stored trades, insert new trade records, or trigger business operations.")

# Sidebar for actions
st.sidebar.header("Operations & Actions")

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

if st.sidebar.button("⏰ Run Expiry Scan"):
    try:
        resp = requests.post(f"{API_BASE_URL}/trades/expire")
        if resp.status_code == 200:
            st.sidebar.success(resp.json().get("message"))
        else:
            st.sidebar.error(f"Error {resp.status_code}: {resp.text}")
    except Exception as e:
        st.sidebar.error(f"Failed to connect to API: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Backend API URL:** `{API_BASE_URL}`")

# Main Tabs
tab1, tab2, tab3 = st.tabs(["📋 View Trades", "➕ Insert / Update Trade", "🗑️ Delete Trade"])

# Tab 1: View Trades
with tab1:
    st.subheader("All Trades in Database")
    try:
        resp = requests.get(f"{API_BASE_URL}/trades")
        if resp.status_code == 200:
            trades = resp.json()
            if trades:
                st.dataframe(trades, use_container_width=True)
                st.info(f"Total Trades: {len(trades)}")
            else:
                st.warning("No trades found in the store.")
        else:
            st.error(f"Failed to fetch trades: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to backend server. Make sure `python run.py` is running on port 1000.")

# Tab 2: Insert / Update Trade
with tab2:
    st.subheader("Insert or Update Trade Record")
    with st.form("trade_form"):
        col1, col2 = st.columns(2)
        with col1:
            trade_id = st.text_input("Trade ID *", value="T1")
            version = st.number_input("Version *", min_value=1, value=1, step=1)
            counter_party_id = st.text_input("Counter Party ID *", value="CP-1")
        with col2:
            portfolio_id = st.text_input("Portfolio ID *", value="B1")
            maturity_date = st.date_input("Maturity Date *", value=datetime.date.today() + datetime.timedelta(days=30))
            created_date = st.date_input("Created Date", value=datetime.date.today())

        submitted = st.form_submit_button("Submit Trade")
        if submitted:
            payload = {
                "trade_id": trade_id.strip(),
                "version": int(version),
                "counter_party_id": counter_party_id.strip(),
                "portfolio_id": portfolio_id.strip(),
                "maturity_date": maturity_date.strftime("%d/%m/%Y"),
                "created_date": created_date.strftime("%d/%m/%Y")
            }
            try:
                resp = requests.post(f"{API_BASE_URL}/trades", json=payload)
                if resp.status_code == 201:
                    st.success(f"✅ Trade '{trade_id}' stored/updated successfully!")
                    st.json(resp.json())
                else:
                    err_msg = resp.json().get("error") if resp.headers.get("content-type") == "application/json" else resp.text
                    st.error(f"❌ Error ({resp.status_code}): {err_msg}")
            except Exception as e:
                st.error(f"Failed to submit trade: {e}")

# Tab 3: Delete Trade
with tab3:
    st.subheader("Delete Trade")
    del_trade_id = st.text_input("Enter Trade ID to Delete", value="")
    if st.button("Delete"):
        if del_trade_id:
            try:
                resp = requests.delete(f"{API_BASE_URL}/trades/{del_trade_id.strip()}")
                if resp.status_code == 200:
                    st.success(resp.json().get("message"))
                else:
                    st.error(f"Error {resp.status_code}: {resp.json().get('error')}")
            except Exception as e:
                st.error(f"Failed to connect: {e}")
        else:
            st.warning("Please enter a Trade ID.")

