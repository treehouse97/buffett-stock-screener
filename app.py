import streamlit as st
import yfinance as yf
import requests
import numpy as np
import pandas as pd

# === CONFIG ===
FMP_API_KEY = "6eb3b2309d6df5458b579baeff53accb"
FMP_URL = "https://financialmodelingprep.com/api/v3"

# === DATA FETCHING UTILITIES ===

def get_fmp_json(endpoint):
    url = f"{FMP_URL}/{endpoint}&apikey={FMP_API_KEY}"
    res = requests.get(url)
    return res.json() if res.status_code == 200 else {}

def get_stock_data_fmp(ticker):
    try:
        profile = get_fmp_json(f"profile/{ticker}?")[0]
        income = get_fmp_json(f"income-statement/{ticker}?limit=5")
        balance = get_fmp_json(f"balance-sheet-statement/{ticker}?limit=5")
        cashflow = get_fmp_json(f"cash-flow-statement/{ticker}?limit=10")
        metrics = get_fmp_json(f"key-metrics-ttm/{ticker}?")[0]

        fcf = [row["freeCashFlow"] for row in cashflow if row.get("freeCashFlow")]

        return {
            "Source": "FMP",
            "Ticker": ticker,
            "Name": profile.get("companyName", ""),
            "Sector": profile.get("sector", ""),
            "Market Cap": profile.get("mktCap", 0),
            "PE Ratio": profile.get("pe", None),
            "PB Ratio": profile.get("priceToBookRatio", None),
            "ROE": float(metrics.get("roe", 0)),
            "Debt to Equity": float(metrics.get("debtToEquity", 0)),
            "Price": profile.get("price", None),
            "Dividend Yield": profile.get("lastDiv", 0) / profile.get("price", 1),
            "FCF": fcf,
            "Net Income": income[0].get("netIncome", None),
            "Exec Compensation": profile.get("ceoPay", None)
        }
    except Exception as e:
        st.error(f"Error retrieving data from FMP: {e}")
        return None

def get_stock_data_yf(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        cashflow = stock.cashflow
        op_cash = cashflow.loc["Total Cash From Operating Activities"] if "Total Cash From Operating Activities" in cashflow.index else pd.Series()
        capex = cashflow.loc["Capital Expenditures"] if "Capital Expenditures" in cashflow.index else pd.Series()
        fcf = (op_cash - capex).dropna().sort_index(ascending=False).values[:10]

        return {
            "Source": "yfinance",
            "Ticker": ticker,
            "Name": info.get("longName", ""),
            "Sector": info.get("sector", ""),
            "Market Cap": info.get("marketCap", 0),
            "PE Ratio": info.get("trailingPE", None),
            "PB Ratio": info.get("priceToBook", None),
            "ROE": info.get("returnOnEquity", None),
            "Debt to Equity": info.get("debtToEquity", None),
            "Price": info.get("currentPrice", None),
            "Dividend Yield": info.get("dividendYield", None),
            "FCF": fcf,
            "Net Income": info.get("netIncomeToCommon", None),
            "Exec Compensation": None
        }
    except Exception as e:
        st.error(f"Error retrieving data from yfinance: {e}")
        return None

# === BUFFETT SCORE ===
def evaluate_buffett_criteria(data):
    score = 0
    reasons = []

    if data["ROE"] and data["ROE"] > 0.15:
        score += 1
        reasons.append("✓ ROE > 15%")
    else:
        reasons.append("✗ ROE < 15%")

    if data["PE Ratio"] and data["PE Ratio"] < 20:
        score += 1
        reasons.append("✓ PE < 20")
    else:
        reasons.append("✗ PE too high")

    if data["Debt to Equity"] and data["Debt to Equity"] < 0.5:
        score += 1
        reasons.append("✓ Low Debt-to-Equity")
    else:
        reasons.append("✗ High leverage")

    if data["PB Ratio"] and data["PB Ratio"] < 3:
        score += 1
        reasons.append("✓ Price/Book < 3")
    else:
        reasons.append("✗ Price/Book too high")

    return score, reasons

# === DCF CALCULATION ===
def calculate_intrinsic_value(fcf_list, growth_rate_initial=0.07, growth_rate_terminal=0.03, discount_rate=0.10, forecast_years=10):
    if not fcf_list or len(fcf_list) < 3:
        return None
    avg_fcf = np.mean(fcf_list[-3:])
    intrinsic_value = 0
    for year in range(1, forecast_years + 1):
        growth = (1 + growth_rate_initial) if year <= 5 else (1 + growth_rate_terminal)
        projected_fcf = avg_fcf * (growth ** year)
        intrinsic_value += projected_fcf / ((1 + discount_rate) ** year)
    terminal_value = projected_fcf * (1 + growth_rate_terminal) / (discount_rate - growth_rate_terminal)
    intrinsic_value += terminal_value / ((1 + discount_rate) ** forecast_years)
    return intrinsic_value

# === FINAL VERDICT ===
def calculate_stock_rank(buffett_score, moat_score, margin_of_safety):
    total = buffett_score + moat_score
    if margin_of_safety > 0.3 and total >= 6:
        return "Excellent"
    elif margin_of_safety > 0.2 and total >= 5:
        return "Good"
    elif total >= 4:
        return "Average"
    else:
        return "Avoid"

# === STREAMLIT UI ===
st.set_page_config(page_title="Buffett-Style Stock Screener", layout="wide")
st.title("Buffett-Style Stock Screener")

# === Sidebar Controls ===
source_choice = st.sidebar.radio("Select Data Source", ("FMP (accurate)", "yfinance (estimated)"))
ticker_input = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL, KO, PG):")

st.sidebar.header("Moat Checklist")
moats = {
    "Brand Power": st.sidebar.checkbox("Brand Power"),
    "Network Effects": st.sidebar.checkbox("Network Effects"),
    "Switching Costs": st.sidebar.checkbox("Switching Costs"),
    "Cost Advantage": st.sidebar.checkbox("Cost Advantage"),
    "Intangible Assets": st.sidebar.checkbox("Intangible Assets")
}
moat_score = sum(moats.values())

# === Main App Logic ===
if ticker_input:
    if source_choice == "FMP (accurate)":
        data = get_stock_data_fmp(ticker_input.upper())
    else:
        data = get_stock_data_yf(ticker_input.upper())

    if data:
        st.subheader(f"{data['Name']} ({data['Ticker']}) - Source: {data['Source']}")
        st.markdown(f"**Sector:** {data['Sector']}")
        st.markdown(f"**Price:** ${data['Price']:.2f}" if data["Price"] else "N/A")
        st.markdown(f"**Dividend Yield:** {data['Dividend Yield'] * 100:.2f}%" if data["Dividend Yield"] else "N/A")

        # Buffett Score
        st.write("---")
        st.subheader("Buffett Criteria")
        score, notes = evaluate_buffett_criteria(data)
        st.markdown(f"**Score:** {score}/4")
        for note in notes:
            st.markdown(f"- {note}")

        st.markdown(f"**ROE:** {data['ROE']:.2f}" if data["ROE"] else "ROE not available")
        st.markdown(f"**PE Ratio:** {data['PE Ratio']:.2f}" if data["PE Ratio"] else "PE not available")
        st.markdown(f"**Debt to Equity:** {data['Debt to Equity']:.2f}" if data["Debt to Equity"] else "D/E not available")
        st.markdown(f"**Price/Book Ratio:** {data['PB Ratio']:.2f}" if data["PB Ratio"] else "PB not available")

        # Moat
        st.write("---")
        st.subheader("Moat Evaluation")
        for k, v in moats.items():
            st.markdown(f"- {'✓' if v else '✗'} {k}")
        st.markdown(f"**Moat Score:** {moat_score}/5")

        # Management
        st.write("---")
        st.subheader("Management Quality")
        if data["Exec Compensation"] and data["Net Income"]:
            ratio = data["Exec Compensation"] / abs(data["Net Income"])
            if ratio < 0.05:
                st.success("✓ Reasonable executive compensation")
            else:
                st.warning("✗ High executive compensation relative to net income")
        else:
            st.info("Executive compensation data not available")

        # FCF Chart
        st.write("---")
        st.subheader("Free Cash Flow Trend")
        if data["FCF"] and len(data["FCF"]) >= 3:
            df_fcf = pd.DataFrame(data["FCF"], columns=["FCF"])
            st.line_chart(df_fcf[::-1])
        else:
            st.warning("Not enough FCF data")

        # DCF
        st.write("---")
        st.subheader("Intrinsic Value (DCF)")
        try:
            fcf_input = float(st.number_input("Estimated FCF", value=float(data["FCF"][0] if data["FCF"] else 1e7)))
            growth = st.slider("Growth Rate (%)", 2, 20, 8) / 100
            discount = st.slider("Discount Rate (%)", 5, 15, 10) / 100
            intrinsic = calculate_intrinsic_value(data["FCF"], growth, 0.03, discount)
            if intrinsic:
                st.markdown(f"**Intrinsic Value:** ${intrinsic:,.2f}")
                margin = (intrinsic - data["Price"]) / data["Price"]
                st.markdown(f"**Margin of Safety:** {margin * 100:.2f}%")

                # Final rating
                rating = calculate_stock_rank(score, moat_score, margin)
                st.write("---")
                st.subheader("Final Verdict")
                st.markdown(f"**Stock Rating:** {rating}")
                if rating in ["Excellent", "Good"]:
                    st.success("This stock may be worth further research.")
                else:
                    st.warning("This may not meet Buffett's standards.")
        except:
            st.warning("Could not calculate intrinsic value.")
import requests
import numpy as np
import pandas as pd

# === CONFIG ===
API_KEY = "6eb3b2309d6df5458b579baeff53accb"
FMP_URL = "https://financialmodelingprep.com/api/v3"

# === DATA FETCHING ===
def get_fmp_json(endpoint):
    url = f"{FMP_URL}/{endpoint}&apikey={API_KEY}"
    res = requests.get(url)
    return res.json() if res.status_code == 200 else {}

def get_stock_data_fmp(ticker):
    try:
        profile = get_fmp_json(f"profile/{ticker}?")[0]
        income = get_fmp_json(f"income-statement/{ticker}?limit=5")
        balance = get_fmp_json(f"balance-sheet-statement/{ticker}?limit=5")
        cashflow = get_fmp_json(f"cash-flow-statement/{ticker}?limit=10")
        metrics = get_fmp_json(f"key-metrics-ttm/{ticker}?")[0]

        fcf = [row["freeCashFlow"] for row in cashflow if row.get("freeCashFlow")]

        return {
            "Ticker": ticker,
            "Name": profile.get("companyName", ""),
            "Sector": profile.get("sector", ""),
            "Market Cap": profile.get("mktCap", 0),
            "PE Ratio": profile.get("pe", None),
            "PB Ratio": profile.get("priceToBookRatio", None),
            "ROE": float(metrics.get("roe", 0)),
            "Debt to Equity": float(metrics.get("debtToEquity", 0)),
            "Price": profile.get("price", None),
            "Dividend Yield": profile.get("lastDiv", 0) / profile.get("price", 1),
            "FCF": fcf,
            "Net Income": income[0].get("netIncome", None),
            "Exec Compensation": profile.get("ceoPay", None)
        }
    except Exception as e:
        st.error(f"Error retrieving data: {e}")
        return None

# === DCF Calculation ===
def calculate_intrinsic_value(fcf_list, growth_rate_initial=0.07, growth_rate_terminal=0.03, discount_rate=0.10, forecast_years=10):
    if not fcf_list or len(fcf_list) < 3:
        return None
    avg_fcf = np.mean(fcf_list[-3:])
    intrinsic_value = 0

    for year in range(1, forecast_years + 1):
        growth = (1 + growth_rate_initial) if year <= 5 else (1 + growth_rate_terminal)
        projected_fcf = avg_fcf * (growth ** year)
        intrinsic_value += projected_fcf / ((1 + discount_rate) ** year)

    terminal_value = projected_fcf * (1 + growth_rate_terminal) / (discount_rate - growth_rate_terminal)
    intrinsic_value += terminal_value / ((1 + discount_rate) ** forecast_years)
    return intrinsic_value

# === Buffett Score ===
def evaluate_buffett_criteria(data):
    score = 0
    reasons = []

    if data["ROE"] and data["ROE"] > 0.15:
        score += 1
        reasons.append("✓ ROE > 15%")
    else:
        reasons.append("✗ ROE < 15%")

    if data["PE Ratio"] and data["PE Ratio"] < 20:
        score += 1
        reasons.append("✓ PE < 20")
    else:
        reasons.append("✗ PE too high")

    if data["Debt to Equity"] and data["Debt to Equity"] < 0.5:
        score += 1
        reasons.append("✓ Low Debt-to-Equity")
    else:
        reasons.append("✗ High leverage")

    if data["PB Ratio"] and data["PB Ratio"] < 3:
        score += 1
        reasons.append("✓ Price/Book < 3")
    else:
        reasons.append("✗ Price/Book too high")

    return score, reasons

# === Benchmark Comparison ===
def get_benchmark_data():
    return {"PE": 25, "ROE": 0.14}

# === Final Rating ===
def calculate_stock_rank(buffett_score, moat_score, margin_of_safety):
    total = buffett_score + moat_score
    if margin_of_safety > 0.3 and total >= 6:
        return "Excellent"
    elif margin_of_safety > 0.2 and total >= 5:
        return "Good"
    elif total >= 4:
        return "Average"
    else:
        return "Avoid"

# === STREAMLIT APP ===
st.set_page_config(page_title="Buffett-Style Stock Screener", layout="wide")
st.title("Buffett-Style Stock Screener")

ticker_input = st.text_input("Enter Stock Ticker (e.g., AAPL, KO, PG):")

# Moat Checklist
st.sidebar.header("Moat Checklist")
moats = {
    "Brand Power": st.sidebar.checkbox("Brand Power"),
    "Network Effects": st.sidebar.checkbox("Network Effects"),
    "Switching Costs": st.sidebar.checkbox("Switching Costs"),
    "Cost Advantage": st.sidebar.checkbox("Cost Advantage"),
    "Intangible Assets": st.sidebar.checkbox("Intangible Assets")
}
moat_score = sum(moats.values())

if ticker_input:
    data = get_stock_data_fmp(ticker_input.upper())
    if data:
        st.subheader(f"{data['Name']} ({data['Ticker']})")
        st.markdown(f"**Sector:** {data['Sector']}")
        st.markdown(f"**Price:** ${data['Price']:.2f}")
        st.markdown(f"**Dividend Yield:** {data['Dividend Yield']*100:.2f}%")

        # Buffett Criteria
        st.write("---")
        st.subheader("Buffett Criteria")
        score, notes = evaluate_buffett_criteria(data)
        st.markdown(f"**Score:** {score}/4")
        for note in notes:
            st.markdown(f"- {note}")

        # Moat
        st.write("---")
        st.subheader("Moat Evaluation")
        for k, v in moats.items():
            st.markdown(f"- {'✓' if v else '✗'} {k}")
        st.markdown(f"**Moat Score:** {moat_score}/5")

        # Management
        st.write("---")
        st.subheader("Management Quality")
        if data["Exec Compensation"] and data["Net Income"]:
            ratio = data["Exec Compensation"] / abs(data["Net Income"])
            if ratio < 0.05:
                st.success("✓ Reasonable executive compensation")
            else:
                st.warning("✗ High executive compensation relative to net income")
        else:
            st.info("Executive compensation data not available")

        # FCF Chart
        st.write("---")
        st.subheader("Free Cash Flow Trend")
        if data["FCF"] and len(data["FCF"]) >= 3:
            df_fcf = pd.DataFrame(data["FCF"], columns=["FCF"])
            st.line_chart(df_fcf[::-1])  # Show oldest first
        else:
            st.warning("Not enough FCF data")

        # DCF Calculation
        st.write("---")
        st.subheader("Intrinsic Value (DCF)")
        try:
            fcf_input = float(st.number_input("Estimated FCF", value=float(data["FCF"][0] if data["FCF"] else 1e7)))
            growth = st.slider("Growth Rate (%)", 2, 20, 8) / 100
            discount = st.slider("Discount Rate (%)", 5, 15, 10) / 100
            intrinsic = calculate_intrinsic_value(data["FCF"], growth, 0.03, discount)

            if intrinsic:
                st.markdown(f"**Intrinsic Value:** ${intrinsic:,.2f}")
                margin = (intrinsic - data["Price"]) / data["Price"]
                st.markdown(f"**Margin of Safety:** {margin*100:.2f}%")

                # Final verdict
                rating = calculate_stock_rank(score, moat_score, margin)
                st.write("---")
                st.subheader("Final Verdict")
                st.markdown(f"**Stock Rating:** {rating}")
                if rating in ["Excellent", "Good"]:
                    st.success("This stock may be worth further research.")
                else:
                    st.warning("This may not meet Buffett's standards.")
            else:
                st.warning("Insufficient data for DCF.")
        except:
            st.warning("Could not calculate intrinsic value.")

        # Benchmark
        st.write("---")
        st.subheader("S&P 500 Benchmark Comparison")
        bench = get_benchmark_data()
        st.markdown(f"**PE Ratio:** {data['PE Ratio']} vs. S&P 500 Avg: {bench['PE']}")
        st.markdown(f"**ROE:** {data['ROE']:.2f} vs. S&P 500 Avg: {bench['ROE']:.2f}")