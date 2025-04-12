
import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

st.set_page_config(page_title="Buffett-Style Stock Screener", layout="wide")

st.title("Buffett-Style Stock Screener")

# Input for stock ticker
ticker_input = st.text_input("Enter Stock Ticker Symbol (e.g., AAPL, KO, PG):")

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        financials = stock.financials
        return {
            "Ticker": ticker,
            "Name": info.get("longName", ""),
            "Sector": info.get("sector", ""),
            "Market Cap": info.get("marketCap", 0),
            "PE Ratio": info.get("trailingPE", None),
            "PB Ratio": info.get("priceToBook", None),
            "ROE": info.get("returnOnEquity", None),
            "Debt to Equity": info.get("debtToEquity", None),
            "FCF": financials.loc["Total Cash From Operating Activities"][0] if "Total Cash From Operating Activities" in financials.index else None,
            "Price": info.get("currentPrice", None)
        }
    except Exception as e:
        st.error(f"Error retrieving data: {e}")
        return None

def evaluate_buffett_criteria(data):
    score = 0
    reasons = []

    if data["ROE"] and data["ROE"] > 0.15:
        score += 1
        reasons.append("ROE > 15%")
    else:
        reasons.append("ROE too low")

    if data["PE Ratio"] and data["PE Ratio"] < 20:
        score += 1
        reasons.append("PE Ratio < 20")
    else:
        reasons.append("PE Ratio too high")

    if data["Debt to Equity"] and data["Debt to Equity"] < 0.5:
        score += 1
        reasons.append("Low Debt to Equity")
    else:
        reasons.append("Too much leverage")

    if data["PB Ratio"] and data["PB Ratio"] < 3:
        score += 1
        reasons.append("Price/Book < 3")
    else:
        reasons.append("Price/Book too high")

    return score, reasons

if ticker_input:
    data = get_stock_data(ticker_input.upper())

    if data:
        st.subheader(f"Analysis for {data['Name']} ({data['Ticker']})")
        st.write("**Sector:**", data["Sector"])
        st.write("**Market Cap:**", f"{data['Market Cap']:,}")
        st.write("**Price:**", f"${data['Price']}")

        st.write("---")
        st.subheader("Buffett Criteria Evaluation")
        score, notes = evaluate_buffett_criteria(data)

        st.write("**Score:**", f"{score}/4")
        for reason in notes:
            st.markdown(f"- {reason}")

        if score >= 3:
            st.success("This stock meets most Buffett-style criteria. Consider investigating further.")
        else:
            st.warning("This stock does not meet enough Buffett-style filters.")
