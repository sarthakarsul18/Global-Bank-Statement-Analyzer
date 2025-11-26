import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from analyzer import extract_tables_from_pdf, clean_and_standardize, analyze
import pandas as pd

st.set_page_config(page_title="Global Bank Statement Analyzer", layout="wide")
st.title("Global Bank Statement Analyzer")
st.markdown("Upload any bank's PDF statement (even password protected) → Get instant insights!")

uploaded_file = st.file_uploader("Upload Bank Statement PDF", type="pdf")
password = st.text_input("PDF Password (if any)", type="password")

if uploaded_file and st.button("Analyze Statement"):
    with st.spinner("Extracting and analyzing your statement..."):
        try:
            
            raw_df = extract_tables_from_pdf(uploaded_file, password or None)
            df = clean_and_standardize(raw_df)
            insights, df_final, cat_exp, monthly = analyze(df)

            st.success("Analysis Complete!")

            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Income", f"₹{insights['Total Income']:,.2f}")
            col2.metric("Total Expenses", f"₹{insights['Total Expenses']:,.2f}", delta=f"-₹{insights['Total Expenses']:,.0f}")
            col3.metric("Net Savings", f"₹{insights['Net Savings']:,.2f}", 
                       delta="Good" if insights['Net Savings'] > 0 else "Warning")
            col4.metric("Transactions", insights['Transactions'])

            st.markdown("---")

            
            col1, col2 = st.columns(2)

            with col1:
                fig_pie = px.pie(values=cat_exp.values, names=cat_exp.index, 
                                title="Expenses by Category")
                st.plotly_chart(fig_pie, use_container_width=True)

            with col2:
                fig_bar = px.bar(x=monthly.index, y=monthly.values, 
                                labels={'x': 'Month', 'y': 'Net Amount'},
                                title="Monthly Net Flow")
                fig_bar.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_bar, use_container_width=True)

            if 'balance' in df_final.columns:
                fig_balance = px.line(df_final, x='date', y='balance', title="Balance Over Time")
                st.plotly_chart(fig_balance, use_container_width=True)

            
            st.subheader("Top 10 Expenses")
            top_expenses = df_final[df_final['amount'] < 0].nsmallest(10, 'amount')[['date', 'description', 'amount']]
            top_expenses['amount'] = top_expenses['amount'].abs()
            st.dataframe(top_expenses.style.format({'amount': '₹{:,.2f}'}), use_container_width=True)

            
            csv = df_final.to_csv(index=False).encode()
            st.download_button("Download Full Analyzed Data", csv, "analyzed_statement.csv", "text/csv")

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Tip: Try with correct password or check if PDF has readable tables.")