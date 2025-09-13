import streamlit as st
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="Valuation App", layout="wide")

# ---------------------------
# Side menu
# ---------------------------
st.sidebar.title("Valuation Dashboard")
menu = st.sidebar.radio("Select Module", ["DCF", "LBO", "Comparables"])

# ---------------------------
# Helper functions
# ---------------------------

demo_api_key = "a50f972afe6637de4b75c22b25793300"

def get_financials(ticker):
    # Fetch financial statements from Financial Modeling Prep
    IS = requests.get(f'https://financialmodelingprep.com/api/v3/income-statement/{ticker}?apikey={demo_api_key}').json()
    BS = requests.get(f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?apikey={demo_api_key}').json()
    return IS, BS

def get_rf():
    # 1-Year US Treasury (^IRX) as proxy for RF
    treasury = yf.download("^IRX", period="1d")
    rf = float(treasury['Close'].iloc[-1])/100
    return rf

def get_sp500_return():
    sp500 = yf.download("^GSPC", start="2019-07-10")
    sp500.dropna(inplace=True)
    yearly_return = (sp500['Close'].iloc[-1] / sp500['Close'].iloc[-252]) - 1
    return yearly_return

def get_beta(ticker):
    profile = requests.get(f'https://financialmodelingprep.com/api/v3/company/profile/{ticker}?apikey={demo_api_key}').json()
    beta = float(profile['profile']['beta'])
    return beta

# ---------------------------
# DCF Module
# ---------------------------
if menu == "DCF":
    st.header("Discounted Cash Flow (DCF) Valuation")

    ticker = st.text_input("Enter Stock Ticker (e.g., AAPL, GOOG)", value="GOOG").upper()
    if ticker:
        IS, BS = get_financials(ticker)

        st.subheader("Revenue Growth Assumption")
        # Calculate simple revenue growth from last two years
        rev_growth = (IS[0]['revenue'] - IS[1]['revenue']) / IS[1]['revenue']
        rev_growth_input = st.number_input("Revenue Growth % (Annual)", value=rev_growth*100)/100

        st.subheader("Long-Term Growth Rate")
        lt_growth = st.number_input("LT Growth Rate", value=0.03)

        st.subheader("WACC Assumptions")
        rf = get_rf()
        beta = get_beta(ticker)
        market_return = get_sp500_return()
        ke = rf + beta*(market_return - rf)
        kd = 0.05  # placeholder for cost of debt
        wacc = st.number_input("WACC", value=0.08)

        st.write(f"**Discount Rate (WACC):** {wacc*100:.2f}%")

        st.subheader("Forecasted Free Cash Flows")
        # Here you can add interactive inputs for FCF projections
        # Example placeholder
        fcf = []
        for year in range(1,6):
            value = st.number_input(f"Year {year} FCF", value=IS[0]['netIncome']*1.05**year)
            fcf.append(value)

        terminal_value = fcf[-1]*(1+lt_growth)/(wacc - lt_growth)
        discounted_fcf = sum([fcf[i]/(1+wacc)**(i+1) for i in range(5)])
        discounted_tv = terminal_value / (1+wacc)**5
        equity_value = discounted_fcf + discounted_tv

        st.write(f"**DCF Equity Value:** ${equity_value:,.2f}")

# ---------------------------
# LBO Module
# ---------------------------
elif menu == "LBO":
    st.header("Leveraged Buyout (LBO) Model")
    ticker = st.text_input("Enter Stock Ticker", value="GOOG").upper()

    # Interactive inputs for LBO parameters
    purchase_price = st.number_input("Purchase Price ($M)", value=10000)
    debt = st.number_input("Debt ($M)", value=5000)
    equity = purchase_price - debt
    interest_rate = st.number_input("Debt Interest Rate (%)", value=5.0)/100
    exit_multiple = st.number_input("Exit EBITDA Multiple", value=10.0)
    years = st.number_input("Investment Horizon (Years)", value=5, step=1)

    st.subheader("Projected Returns")
    # Simple LBO projection
    exit_value = exit_multiple * purchase_price  # placeholder
    equity_exit = exit_value - debt
    cagr = (equity_exit / equity)**(1/years) - 1

    st.write(f"**Equity Exit Value:** ${equity_exit:,.2f}")
    st.write(f"**IRR (CAGR):** {cagr*100:.2f}%")

# ---------------------------
# Comparables Module
# ---------------------------
elif menu == "Comparables":
    st.header("Comps Analysis")
    ticker = st.text_input("Enter Stock Ticker", value="GOOG").upper()

    # Get competitors automatically
    profile = requests.get(f'https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={demo_api_key}').json()
    comps = profile[0].get("companyName", "").split(",")  # placeholder
    comps_input = st.text_area("Edit Competitors", value=", ".join(comps))
    comps_list = [c.strip() for c in comps_input.split(",")]

    st.subheader("Comparable Metrics")
    multiples = ['P/E', 'EV/EBITDA', 'EV/Sales']
    comps_data = {}
    for comp in comps_list:
        comp_profile = requests.get(f'https://financialmodelingprep.com/api/v3/profile/{comp}?apikey={demo_api_key}').json()
        comps_data[comp] = {m: np.nan for m in multiples}  # placeholder, can fetch real metrics

    st.dataframe(pd.DataFrame(comps_data).T)

st.write("Valuation app by Navjot Dhah")
