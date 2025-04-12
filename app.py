
import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

st.set_page_config(page_title="Buffett-Style Stock Screener", layout="wide")
st.title("Buffett-Style Stock Screener")

ticker_input = st.text_input("Enter Stock Ticker Symbol (e.g., AAPL, KO, PG):")

# Moat Checklist
st.sidebar.header("Moat Checklist")
moats = {
    "Brand Power": st.sidebar.checkbox("Brand Power"),
    "Network Effects": st.sidebar.checkbox("Network Effects"),
    "Switching Costs": st.sidebar.checkbox("Switching Costs"),
    "Cost Advantage": st.sidebar.checkbox("Cost Advantage"),
}
moat_score = sum(moats.values())

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        financials = stock.financials
        cashflow = stock.cashflow

        
def calculate_intrinsic_value(fcf_list, growth_rate_initial=0.05, growth_rate_terminal=0.02, discount_rate=0.10, forecast_years=10):
    if len(fcf_list) == 0:
        return None

    avg_fcf = np.mean(fcf_list)
    intrinsic_value = 0

    # Stage 1: Forecast period
    for year in range(1, forecast_years + 1):
        projected_fcf = avg_fcf * ((1 + growth_rate_initial) ** year)
        intrinsic_value += projected_fcf / ((1 + discount_rate) ** year)

    # Terminal value
    terminal_value = (avg_fcf * ((1 + growth_rate_initial) ** forecast_years) * (1 + growth_rate_terminal)) / (discount_rate - growth_rate_terminal)
    intrinsic_value += terminal_value / ((1 + discount_rate) ** forecast_years)

    return intrinsic_value


fcf_list = []
        try:
            op_cash = cashflow.loc["Total Cash From Operating Activities"]
            capex = cashflow.loc["Capital Expenditures"]
            fcf_list = (op_cash - capex).dropna().sort_index(ascending=False).values[:10]
        except KeyError:
            fcf_list = []

        return {
            "Ticker": ticker,
            "Name": info.get("longName", ""),
            "Sector": info.get("sector", ""),
            "Market Cap": info.get("marketCap", 0),
            "PE Ratio": info.get("trailingPE", None),
            "PB Ratio": info.get("priceToBook", None),
            "ROE": info.get("returnOnEquity", None),
            "Debt to Equity": info.get("debtToEquity", None),
            "Price": info.get("currentPrice", None),
            "FCF": fcf_list,
            "Dividend Yield": info.get("dividendYield", None),
            "Forward PE": info.get("forwardPE", None)
        }
    except Exception as e:
        st.error(f"Error retrieving data: {e}")
        return None

def evaluate_buffett_criteria(data):
    score = 0
    reasons = []

    if data["ROE"] and data["ROE"] > 0.15:
        score += 1
        reasons.append("✓ ROE > 15%")
    else:
        reasons.append("✗ ROE too low")

    if data["PE Ratio"] and data["PE Ratio"] < 20:
        score += 1
        reasons.append("✓ PE Ratio < 20")
    else:
        reasons.append("✗ PE Ratio too high")

    if data["Debt to Equity"] and data["Debt to Equity"] < 0.5:
        score += 1
        reasons.append("✓ Low Debt to Equity")
    else:
        reasons.append("✗ High leverage")

    if data["PB Ratio"] and data["PB Ratio"] < 3:
        score += 1
        reasons.append("✓ Price/Book < 3")
    else:
        reasons.append("✗ Price/Book too high")

    return score, reasons

def estimate_intrinsic_value(fcf, growth_rate, discount_rate):
    future_values = [fcf * ((1 + growth_rate) ** i) / ((1 + discount_rate) ** i) for i in range(1, 6)]
    terminal_value = (fcf * ((1 + growth_rate) ** 5)) * 15 / ((1 + discount_rate) ** 5)
    return round(sum(future_values) + terminal_value, 2)

if ticker_input:
    data = get_stock_data(ticker_input.upper())

    if data:
        st.subheader(f"Analysis for {data['Name']} ({data['Ticker']})")
        st.write("**Sector:**", data["Sector"])
        st.write("**Market Cap:**", f"{data['Market Cap']:,}")
        st.write("**Price:**", f"${data['Price']}")
        st.write("**Dividend Yield:**", f"{data['Dividend Yield'] * 100:.2f}%" if data["Dividend Yield"] else "N/A")
        st.write("**Forward P/E:**", data["Forward PE"] if data["Forward PE"] else "N/A")

        st.write("---")
        st.subheader("Buffett Criteria Evaluation")
        score, notes = evaluate_buffett_criteria(data)
        st.write("**Score:**", f"{score}/4")
        for note in notes:
            st.markdown(f"- {note}")

        st.write("---")
        st.subheader("Moat Evaluation")
        for k, v in moats.items():
            if v:
                st.markdown(f"- ✓ {k}")
        st.write("**Moat Score:**", f"{moat_score}/4")

        st.write("---")
        st.subheader("Free Cash Flow Consistency")
        if data["FCF"] and len(data["FCF"]) >= 3:
            fcf_df = pd.DataFrame(data["FCF"], columns=["FCF"])
            st.line_chart(fcf_df)
            if all(f > 0 for f in data["FCF"]):
                st.success("Positive Free Cash Flow every year")
            else:
                st.warning("Inconsistent or negative Free Cash Flow")
        else:
            st.warning("Insufficient FCF data or unavailable")

        st.write("---")
        st.subheader("Intrinsic Value Calculator")
        try:
            fcf_input = float(st.number_input("Enter estimated FCF", value=float(data["FCF"][0] if data["FCF"] else 1e7)))
            growth = st.slider("Growth Rate (%)", 1, 20, 8) / 100
            discount = st.slider("Discount Rate (%)", 5, 15, 10) / 100
            intrinsic_value = estimate_intrinsic_value(fcf_input, growth, discount)
            st.write(f"**Estimated Intrinsic Value:** ${intrinsic_value:,.2f}")
            if intrinsic_value > data["Price"] * 1.3:
                st.success("Stock appears undervalued with margin of safety.")
            else:
                st.info("Stock may be fairly or overvalued.")
        except:
            st.warning("Could not compute intrinsic value.")
