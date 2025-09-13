import streamlit as st
import requests
import numpy as np
import pandas as pd
import datetime

st.title("DCF Forecast & WACC Calculator")

# -------------------------------
# User Inputs
# -------------------------------
company = st.text_input("Enter Company Ticker", "GOOG")
demo = 'a50f972afe6637de4b75c22b25793300'

# -------------------------------
# Fetch Financial Data
# -------------------------------
@st.cache_data
def get_income_statement(company):
    url = f'https://financialmodelingprep.com/api/v3/income-statement/{company}?apikey={demo}'
    return requests.get(url).json()

@st.cache_data
def get_balance_sheet(company):
    url = f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{company}?apikey={demo}'
    return requests.get(url).json()

@st.cache_data
def get_company_profile(company):
    url = f'https://financialmodelingprep.com/api/v3/company/profile/{company}?apikey={demo}'
    return requests.get(url).json()

IS = get_income_statement(company)
BS = get_balance_sheet(company)
profile = get_company_profile(company)

# -------------------------------
# Revenue Growth
# -------------------------------
revenue_g = (IS[0]['revenue'] - IS[1]['revenue']) / IS[1]['revenue']
st.write(f"Revenue Growth: {revenue_g:.2%}")

# -------------------------------
# Forecast Income Statement
# -------------------------------
income_statement = pd.DataFrame.from_dict(IS[0], orient='index')[5:26]
income_statement.columns = ['current_year']

# Convert all numeric values, coerce errors to NaN
income_statement = income_statement.apply(pd.to_numeric, errors='coerce')

# Divide by revenue (first row only)
income_statement['as_%_of_revenue'] = income_statement / income_statement.loc['revenue', 'current_year']

# Forecast next 5 years
for i in range(1, 6):
    col_prev = 'current_year' if i == 1 else f'next_{i-1}_year'
    income_statement[f'next_{i}_year'] = (income_statement.loc['revenue', col_prev] * (1 + revenue_g)) * income_statement['as_%_of_revenue']

# -------------------------------
# Forecast Balance Sheet
# -------------------------------
balance_sheet = pd.DataFrame.from_dict(BS[0], orient='index')[5:-2]
balance_sheet.columns = ['current_year']
balance_sheet = balance_sheet.apply(pd.to_numeric, errors='coerce')
balance_sheet['as_%_of_revenue'] = balance_sheet / income_statement.loc['revenue', 'current_year']

for i in range(1, 6):
    col_prev = 'current_year' if i == 1 else f'next_{i-1}_year'
    income_col = f'next_{i}_year'
    balance_sheet[f'next_{i}_year'] = income_statement.loc['revenue', income_col] * balance_sheet['as_%_of_revenue']

# -------------------------------
# Forecast Cash Flows
# -------------------------------
CF_forecast = {}

for i in range(1, 6):
    year_key = f'next_{i}_year'
    prev_key = 'current_year' if i == 1 else f'next_{i-1}_year'
    CF_forecast[year_key] = {}
    CF_forecast[year_key]['netIncome'] = income_statement.loc['netIncome', year_key]
    CF_forecast[year_key]['inc_depreciation'] = income_statement.loc['depreciationAndAmortization', year_key] - income_statement.loc['depreciationAndAmortization', prev_key]
    CF_forecast[year_key]['inc_receivables'] = balance_sheet.loc['netReceivables', year_key] - balance_sheet.loc['netReceivables', prev_key]
    CF_forecast[year_key]['inc_inventory'] = balance_sheet.loc['inventory', year_key] - balance_sheet.loc['inventory', prev_key]
    CF_forecast[year_key]['inc_payables'] = balance_sheet.loc['accountPayables', year_key] - balance_sheet.loc['accountPayables', prev_key]
    CF_forecast[year_key]['CF_operations'] = (
        CF_forecast[year_key]['netIncome'] +
        CF_forecast[year_key]['inc_depreciation'] -
        CF_forecast[year_key]['inc_receivables'] -
        CF_forecast[year_key]['inc_inventory'] +
        CF_forecast[year_key]['inc_payables']
    )
    CF_forecast[year_key]['CAPEX'] = balance_sheet.loc['propertyPlantEquipmentNet', year_key] - balance_sheet.loc['propertyPlantEquipmentNet', prev_key] + income_statement.loc['depreciationAndAmortization', year_key]
    CF_forecast[year_key]['FCF'] = CF_forecast[year_key]['CF_operations'] + CF_forecast[year_key]['CAPEX']

CF_forec = pd.DataFrame.from_dict(CF_forecast, orient='columns')
pd.options.display.float_format = '{:,.0f}'.format
st.write("Forecasted Cash Flows:")
st.dataframe(CF_forec)

# -------------------------------
# Risk-Free Rate (FRED)
# -------------------------------
@st.cache_data
def get_rf():
    url = 'https://api.stlouisfed.org/fred/series/observations?series_id=TB1YR&api_key=YOUR_FRED_KEY&file_type=json'
    data = requests.get(url).json()
    last_val = float(data['observations'][-1]['value'])
    return last_val / 100

RF = get_rf()

# -------------------------------
# Cost of Equity
# -------------------------------
beta = float(profile['profile']['beta'])
market_return = 0.10
ke = RF + beta * (market_return - RF)

# -------------------------------
# Cost of Debt
# -------------------------------
interest_expense = IS[0]['interestExpense']
EBIT = IS[0]['ebitda'] - IS[0]['depreciationAndAmortization']
interest_coverage_ratio = EBIT / interest_expense

def get_credit_spread(icr):
    if icr > 8.5: return 0.0063
    elif icr > 6.5: return 0.0078
    elif icr > 5.5: return 0.0098
    elif icr > 4.25: return 0.0108
    elif icr > 3: return 0.0122
    elif icr > 2.5: return 0.0156
    elif icr > 2.25: return 0.02
    elif icr > 2: return 0.0240
    elif icr > 1.75: return 0.0351
    elif icr > 1.5: return 0.0421
    elif icr > 1.25: return 0.0515
    elif icr > 0.8: return 0.0820
    elif icr > 0.65: return 0.0864
    elif icr > 0.2: return 0.1134
    else: return 0.1512

credit_spread = get_credit_spread(interest_coverage_ratio)
kd = RF + credit_spread

# -------------------------------
# WACC
# -------------------------------
total_debt = BS[0]['totalDebt']
total_equity = BS[0]['totalStockholdersEquity']
ETR = 0.21
Debt_to = total_debt / (total_debt + total_equity)
Equity_to = total_equity / (total_debt + total_equity)
wacc_company = (kd*(1-ETR)*Debt_to) + (ke*Equity_to)
st.write(f"WACC: {wacc_company:.2%}")
