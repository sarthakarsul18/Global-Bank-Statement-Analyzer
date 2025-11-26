import pdfplumber
import pandas as pd
import re
from datetime import datetime

def extract_tables_from_pdf(file, password=None):
    with pdfplumber.open(file, password=password) as pdf:
        all_tables = []
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                all_tables.extend(table)
    if not all_tables:
        raise ValueError("No tables found in the PDF.")
    df = pd.DataFrame(all_tables[1:], columns=all_tables[0])
    return df

def clean_and_standardize(df):
    df = df.copy()
    df.columns = [col.lower().strip() for col in df.columns]
    
    
    date_cols = ['date', 'posting date', 'value date', 'txn date', 'transaction date']
    desc_cols = ['description', 'particulars', 'narration', 'details', 'remarks']
    debit_cols = ['debit', 'withdrawal', 'dr', 'amount debited']
    credit_cols = ['credit', 'deposit', 'cr', 'amount credited']
    balance_cols = ['balance', 'running balance', 'closing balance']

    def find_column(cols):
        for c in cols:
            if any(col in c for col in df.columns):
                return next(col for col in df.columns if col in c)
        return None

    date_col = find_column(date_cols)
    desc_col = find_column(desc_cols)
    debit_col = find_column(debit_cols)
    credit_col = find_column(credit_cols)
    balance_col = find_column(balance_cols)

    if not date_col or not desc_col:
        raise ValueError("Could not detect Date or Description column.")

    
    def clean_amount(x):
        if pd.isna(x): return 0.0
        s = str(x).replace(',', '').replace(' ', '').strip()
        if s.startswith('₹'):
            s = s[1:]  
        try:
            return float(s or 0)
        except ValueError:
            return 0.0

    df['date'] = pd.to_datetime(df[date_col], errors='coerce')
    df['description'] = df[desc_col].fillna("Unknown")

    debit = df[debit_col].apply(clean_amount) if debit_col else 0
    credit = df[credit_col].apply(clean_amount) if credit_col else 0
    df['amount'] = credit - debit

    if balance_col:
        df['balance'] = df[balance_col].apply(clean_amount)

    df = df.dropna(subset=['date', 'amount'])
    df = df.sort_values('date').reset_index(drop=True)
    
    return df

def categorize_transaction(desc):
    desc = str(desc).lower()
    categories = {
        'Food': ['zomato', 'swiggy', 'uber eats', 'restaurant', 'cafe', 'dominos'],
        'Shopping': ['amazon', 'flipkart', 'myntra', 'shopping', 'mall'],
        'Transport': ['uber', 'ola', 'rapido', 'fuel', 'petrol', 'parking'],
        'Bills': ['electricity', 'internet', 'phone', 'recharge', 'bill'],
        'Entertainment': ['netflix', 'spotify', 'movie', 'cinema'],
        'Health': ['pharmacy', 'hospital', 'medicine'],
        'Transfer': ['imps', 'neft', 'rtgs', 'transfer', 'upi'],
        'Salary': ['salary', 'credit', 'income']
    }
    for cat, keywords in categories.items():
        if any(k in desc for k in keywords):
            return cat
    return 'Other'

def analyze(df):
    df['category'] = df['description'].apply(categorize_transaction)
    df['month'] = df['date'].dt.strftime('%Y-%m')

    total_income = df[df['amount'] > 0]['amount'].sum()
    total_expense = abs(df[df['amount'] < 0]['amount'].sum())
    net_savings = total_income - total_expense

    category_expense = df[df['amount'] < 0].groupby('category')['amount'].sum().abs()
    monthly_summary = df.groupby('month')['amount'].sum()

    insights = {
        "Total Income": total_income,
        "Total Expenses": total_expense,
        "Net Savings": net_savings,
        "Transactions": len(df),
        "Average Expense": total_expense / len(df[df['amount'] < 0]) if len(df[df['amount'] < 0]) > 0 else 0,
        "Top Category": category_expense.idxmax() if not category_expense.empty else "N/A",
        "Highest Expense": category_expense.max() if not category_expense.empty else 0
    }

    return insights, df, category_expense, monthly_summary