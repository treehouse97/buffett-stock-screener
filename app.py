import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

# --- DCF Model ---
def calculate_intrinsic_value(fcf_list, growth_rate_initial=0.07, growth_rate_terminal=0.03, discount_rate=0.10, forecast_years=10):
    if not fcf_list or len(fcf_list) < 3:
        return None
    last_fcf = np.mean(fcf_list[-3:])
    intrinsic_value = 0
    for year in range(1, forecast_years + 1):
        growth = (1 + growth_rate_initial) if year <= 5 else (1 + growth_rate_terminal)
        projected_fcf = last_fcf * (growth ** year)
        intrinsic_value += projected_fcf / ((1 + discount_rate) ** year)
    terminal_fcf = last_fcf * ((1 + growth_rate_terminal) ** forecast_years)
    terminal_value = terminal_fcf * (1 + growth_rate_terminal) / (discount_rate - growth_rate_terminal)
    intrinsic_value += terminal_value / ((1 + discount_rate) ** forecast_years)
    return intrinsic_value

# --- Get Financial Data ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        cashflow = stock.cashflow
        balance = stock.balance_sheet
        income = stock.financials

        op_cash = cashflow.get("Total Cash From Operating Activities", pd.Series())
        capex = cashflow.get("Capital Expenditures", pd.Series())
        fcf = (op_cash - capex).dropna().sort_index(ascending=False).values[:10]

        depreciation = cashflow.get("Depreciation", pd.Series())
        net_income = income.get("Net Income", pd.Series())
        owner_earnings = []
        for i in range(min(len(net_income), len(capex), len(depreciation))):
            try:
                oe = net_income[i] + depreciation[i] - capex[i]
                owner_earnings.append(oe)
            except:
                continue

        return {
            "Ticker": ticker,
            "Name": info.get("longName", ""),
            "Sector": info.get("sector", ""),
            "Market Cap": info.get("marketCap", 0),
            "PE Ratio": info.get("trailingPE", None),
            "PB Ratio": info.get("priceToBook", None),
            "ROE": info.get("returnOnEquity", None),
            "ROIC": info.get("returnOnCapital", None),
            "Debt to Equity": info.get("debtToEquity", None),
            "Exec Compensation": info.get("totalCashCompensation", 0),
            "Net Income": net_income[0] if not net_income.empty else None,
            "Peers": info.get("companyOfficers", []),
            "Price": info.get("currentPrice", None),
            "FCF": fcf,
            "Owner Earnings": owner_earnings,
            "Dividend Yield": info.get("dividendYield", None),
            "Forward PE": info.get("forwardPE", None)
        }

    except Exception as e:
        st.error(f"Error retrieving data: {e}")
        return None

# --- Buffett Criteria Scoring ---
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

# --- Benchmarking against S&P 500 average ---
def get_benchmark_data():
    return {
        "PE": 25,
        "ROE": 0.14
    }

# --- Ranking Logic ---
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

# --- Streamlit UI ---
st.set_page_config(page_title="Buffett-Style Stock Screener", layout="wide")
st.title("Buffett-Style Stock Screener")

ticker_input = st.text_input("Enter Stock Ticker (e.g., AAPL, KO, PG):")

# Moat Checklist
st.sidebar.header("Moat Checklist")
moats = {
    "Brand": st.sidebar.checkbox("Brand Power"),
    "Network": st.sidebar.checkbox("Network Effects"),
    "Switching": st.sidebar.checkbox("Switching Costs"),
    "Cost Adv.": st.sidebar.checkbox("Cost Advantage"),
    "Intangible": st.sidebar.checkbox("Intangible Assets")
}
moat_score = sum(moats.values())

if ticker_input:
    data = get_stock_data(ticker_input.upper())
    if data:
        st.subheader(f"{data['Name']} ({data['Ticker']})")
        st.markdown(f"**Sector:** {data['Sector']}")
        st.markdown(f"**Price:** ${data['Price']:.2f}" if data['Price'] else "N/A")
        st.markdown(f"**Dividend Yield:** {data['Dividend Yield'] * 100:.2f}%" if data["Dividend Yield"] else "N/A")

        st.write("---")
        st.subheader("Buffett Criteria")
        score, reasons = evaluate_buffett_criteria(data)
        st.markdown(f"**Score:** {score}/4")
        for note in reasons:
            st.markdown(f"- {note}")

        st.write("---")
        st.subheader("Moat Evaluation")
        for moat, checked in moats.items():
            st.markdown(f"- {'✓' if checked else '✗'} {moat}")
        st.markdown(f"**Moat Score:** {moat_score}/5")

        st.write("---")
        st.subheader("Management Quality")
        if data["Exec Compensation"] and data["Net Income"]:
            comp = data["Exec Compensation"]
            ni = data["Net Income"]
            if comp / abs(ni) < 0.05:
                st.success("✓ Reasonable executive compensation")
            else:
                st.warning("✗ High executive compensation relative to earnings")
        else:
            st.info("Executive compensation data unavailable")

        st.write("---")
        st.subheader("Free Cash Flow Trend")
        if data["FCF"] and len(data["FCF"]) >= 3:
            st.line_chart(pd.DataFrame(data["FCF"], columns=["FCF"]))
        else:
            st.warning("Not enough FCF data")

        st.write("---")
        st.subheader("Intrinsic Value (DCF)")
        try:
            fcf_input = float(st.number_input("Estimated FCF", value=float(data["FCF"][0] if data["FCF"] else 1e7)))
            growth = st.slider("Growth Rate (%)", 2, 20, 8) / 100
            discount = st.slider("Discount Rate (%)", 5, 15, 10) / 100

            intrinsic = calculate_intrinsic_value(data["FCF"], growth, 0.03, discount)
            if intrinsic:
                st.write(f"**Intrinsic Value:** ${intrinsic:,.2f}")
                price = data["Price"]
                mos = (intrinsic - price) / price if price else 0
                st.markdown(f"**Margin of Safety:** {mos * 100:.1f}%")

                # Rank & Recommendation
                rank = calculate_stock_rank(score, moat_score, mos)
                st.write("---")
                st.subheader("Final Verdict")
                st.markdown(f"**Stock Rating:** {rank}")
                if rank in ["Excellent", "Good"]:
                    st.success("This stock may be worth further research.")
                else:
                    st.warning("This may not meet Buffett's standards.")
            else:
                st.warning("Not enough data for DCF.")
        except:
            st.warning("Could not compute intrinsic value.")

        # --- Benchmark Comparison ---
        st.write("---")
        st.subheader("Benchmark Comparison (vs. S&P 500)")
        benchmark = get_benchmark_data()
        st.markdown(f"**PE Ratio:** {data['PE Ratio']} vs. S&P 500 Avg: {benchmark['PE']}")
        st.markdown(f"**ROE:** {data['ROE']:.2f} vs. S&P 500 Avg: {benchmark['ROE']:.2f}" if data["ROE"] else "ROE not available")