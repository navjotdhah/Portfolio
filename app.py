import streamlit as st
import requests
import pandas as pd
import numpy as np
import datetime
import pandas_datareader.data as web

st.set_page_config(page_title="Equity Valuation Tool", layout="wide")

# ------------------------
# API Key and Helper Functions
# ------------------------
demo = 'a50f972afe6637de4b75c22b25793300'

def get_income_statement(ticker):
    return requests.get(f'https://financialmodelingprep.com/api/v3/income-statement/{ticker}?apikey={demo}').json()

def get_balance_sheet(ticker):
    return requests.get(f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?apikey={demo}').json()

def get_company_profile(ticker):
    return requests.get(f'https://financialmodelingprep.com/api/v3/company/profile/{ticker}?apikey={demo}').json()

def get_enterprise_values(ticker):
    return requests.get(f'https://financialmodelingprep.com/api/v3/enterprise-values/{ticker}?apikey={demo}').json()

def get_peers(ticker):
    response = requests.get(f"https://financialmodelingprep.com/api/v4/stock_peers?symbol={ticker}&apikey={demo}")
    return response.json().get("peersList", [])

# ------------------------
# Sidebar Menu
# ------------------------
option = st.sidebar.selectbox(
    "Choose a Valuation Method",
    ["LBO","DCF","Comparables"]
)

# ------------------------
# LBO Section
# ------------------------
if option == "LBO":
    st.header("Leveraged Buyout (LBO) Analysis")

    st.subheader("Inputs")
    purchase_price = st.number_input("Purchase Price ($M)", value=500)
    debt_percentage = st.slider("Debt % of Purchase Price", 0, 100, 60)
    interest_rate = st.number_input("Debt Interest Rate (%)", value=5.0)
    equity_contribution = st.number_input("Equity Contribution ($M)", value=200)
    revenue_growth = st.number_input("Revenue Growth (%)", value=5.0)/100
    ebitda_margin = st.number_input("EBITDA Margin (%)", value=25.0)/100
    exit_multiple = st.number_input("Exit EV/EBITDA Multiple", value=8.0)
    holding_period = st.number_input("Holding Period (Years)", value=5)

    # ------------------------
    # LBO Calculations
    # ------------------------
    debt = purchase_price * debt_percentage/100
    equity = purchase_price - debt
    cash_flow_to_debt = (purchase_price * ebitda_margin * (1 + revenue_growth)**holding_period) - debt*(interest_rate/100)*holding_period
    exit_ev = ebitda_margin * purchase_price * (1 + revenue_growth)**holding_period * exit_multiple
    equity_value_exit = exit_ev - debt

    st.subheader("Results")
    st.write(f"Debt: ${debt:,.2f}M")
    st.write(f"Equity: ${equity:,.2f}M")
    st.write(f"Exit Enterprise Value: ${exit_ev:,.2f}M")
    st.write(f"Equity Value at Exit: ${equity_value_exit:,.2f}M")
    st.write(f"Cash Flow to Debt: ${cash_flow_to_debt:,.2f}M")

# ------------------------
# DCF Section
# ------------------------
elif option == "DCF":
    st.header("Discounted Cash Flow (DCF) Analysis")

    st.subheader("Inputs")
    company = st.text_input("Company Ticker", value="GOOG").upper()
    revenue_growth = st.number_input("Revenue Growth (%)", value=5.0)/100
    ebitda_margin = st.number_input("EBITDA Margin (%)", value=25.0)/100
    wacc = st.number_input("WACC (%)", value=8.0)/100
    lt_growth = st.number_input("Perpetuity Growth (%)", value=3.0)/100
    forecast_years = st.number_input("Forecast Years", value=5)

    # Fetch latest IS
    IS = get_income_statement(company)[0]
    revenue = IS['revenue']
    ebitda = IS['ebitda']

    # Forecast free cash flows
    fcfs = []
    for i in range(1, forecast_years+1):
        rev_forecast = revenue*(1+revenue_growth)**i
        ebitda_forecast = rev_forecast * ebitda_margin
        fcfs.append(ebitda_forecast)

    # Discount FCFs
    discounted_fcfs = [fcf/(1+wacc)**i for i, fcf in enumerate(fcfs, 1)]
    terminal_value = fcfs[-1]*(1+lt_growth)/(wacc-lt_growth)
    terminal_value_discounted = terminal_value/(1+wacc)**forecast_years
    total_value = sum(discounted_fcfs) + terminal_value_discounted

    st.subheader("Results")
    st.write("Forecasted Free Cash Flows ($M):", [f"{x:,.2f}" for x in fcfs])
    st.write(f"Discounted FCFs ($M): {[f'{x:,.2f}' for x in discounted_fcfs]}")
    st.write(f"Terminal Value ($M): {terminal_value:,.2f}")
    st.write(f"Total Enterprise Value ($M): {total_value:,.2f}")

# ------------------------
# Comparables Section
# ------------------------
elif option == "Comparables":
    st.header("Comparable Company Analysis")

    st.subheader("Inputs")
    company = st.text_input("Enter Ticker for Analysis", value="GOOG").upper()
    competitor_list = st.text_area(
        "Enter Competitor Tickers (comma separated) or leave blank for auto-fetch"
    )
    competitors = [c.strip().upper() for c in competitor_list.split(",") if c.strip()]

    # Auto-fetch competitors
    if not competitors:
        competitors = get_peers(company)
        if not competitors:
            st.warning("No peers found. Please enter competitors manually.")
            competitors = []

    if company not in competitors:
        competitors.append(company)

    st.write(f"Competitors to be analyzed: {', '.join(competitors)}")

    # Fetch financial data
    comp_data = []
    for comp in competitors:
        profile = get_company_profile(comp)['profile']
        IS = get_income_statement(comp)[0]
        BS = get_balance_sheet(comp)[0]
        EV_data = get_enterprise_values(comp)[0]

        market_cap = profile.get('mktCap', np.nan)
        price = profile.get('price', np.nan)
        shares = market_cap / price if price else np.nan
        revenue = IS.get('revenue', np.nan)
        ebitda = IS.get('ebitda', np.nan)
        net_income = IS.get('netIncome', np.nan)
        book_value = BS.get('totalStockholdersEquity', np.nan)
        ev = EV_data.get('enterpriseValue', np.nan)

        # Calculate multiples
        pe = price / (net_income / shares) if shares and net_income else np.nan
        ev_ebitda = ev / ebitda if ev and ebitda else np.nan
        ev_sales = ev / revenue if ev and revenue else np.nan
        pb = price / (book_value / shares) if shares and book_value else np.nan

        comp_data.append({
            'Ticker': comp,
            'Market Cap ($M)': market_cap/1e6,
            'Enterprise Value ($M)': ev/1e6 if ev else np.nan,
            'Revenue ($M)': revenue/1e6,
            'EBITDA ($M)': ebitda/1e6,
            'Net Income ($M)': net_income/1e6,
            'Book Value ($M)': book_value/1e6,
            'Price ($)': price,
            'P/E': pe,
            'EV/EBITDA': ev_ebitda,
            'EV/Revenue': ev_sales,
            'P/B': pb
        })

    df_comp = pd.DataFrame(comp_data)

    # Summary statistics
    multiples = ['P/E','EV/EBITDA','EV/Revenue','P/B']
    summary = pd.DataFrame(df_comp[multiples].agg(['mean','median'])).T
    summary.rename(columns={'mean':'Average','median':'Median'}, inplace=True)

    st.subheader("Comparable Companies Data")
    st.dataframe(df_comp.style.format({
        'Market Cap ($M)': "{:,.0f}", 
        'Enterprise Value ($M)': "{:,.0f}", 
        'Revenue ($M)': "{:,.0f}",
        'EBITDA ($M)': "{:,.0f}", 
        'Net Income ($M)': "{:,.0f}", 
        'Book Value ($M)': "{:,.0f}",
        'Price ($)': "{:,.2f}",
        'P/E': "{:,.2f}", 
        'EV/EBITDA': "{:,.2f}",
        'EV/Revenue': "{:,.2f}",
        'P/B': "{:,.2f}"
    }))

    st.subheader("Summary Multiples")
    st.dataframe(summary.style.format("{:,.2f}"))

    # Implied price using median P/E
    target_pe = summary.loc['P/E','Median']
    company_net_income = df_comp[df_comp['Ticker']==company]['Net Income ($M)'].values[0]*1e6
    company_shares = profile.get('mktCap', np.nan)/price if price else np.nan
    implied_price = (target_pe * (company_net_income / company_shares)) if company_shares and target_pe else np.nan
    st.subheader(f"Implied Target Price Based on Median P/E: ${implied_price:,.2f}")
