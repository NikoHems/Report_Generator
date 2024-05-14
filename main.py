import streamlit as st
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import requests
import json
from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


openai_api_key = 'XXX'  # Replace with your API Key
news_api_key = 'XXX'  # Replace with your API Key
x_rapid_api_key = 'XXX' # Replace with your API Key

######### BACK-END #########

######### API-CALLS #########

def get_stock_symbol(company_name, x_rapid_api_key):
    search_url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/auto-complete"
    search_params = {"q": company_name, "region": "US"}
    search_headers = {
        "X-RapidAPI-Key": x_rapid_api_key,  # Replace with your API Key
        "X-RapidAPI-Host": "apidojo-yahoo-finance-v1.p.rapidapi.com",
    }
    response = requests.get(search_url, headers=search_headers, params=search_params)
    data = response.json()
    quotes = data.get('quotes', [])
    if quotes:
        return quotes[0].get('symbol', None)
    else:
        return None

def get_all_historical_stock_prices(stock_symbol, x_rapid_api_key):
    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v3/get-historical-data"
    headers = {
        "X-RapidAPI-Key": x_rapid_api_key, # Replace with your API Key
        "X-RapidAPI-Host": "apidojo-yahoo-finance-v1.p.rapidapi.com",
    }

    start_date = datetime(2019, 1, 1)
    end_date = datetime.now()

    all_price_data = []

    while start_date < end_date:
        params = {
            "symbol": stock_symbol,
            "region": "US",
            "start": int(start_date.timestamp()),
            "end": int(end_date.timestamp())
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if 'prices' in data:
            for item in data['prices']:
                if 'close' in item:
                    date = datetime.fromtimestamp(item['date']).strftime('%Y-%m-%d')
                    close_price = item['close']
                    all_price_data.append({'date': date, 'close_price': close_price})

        # Move the start date forward (adjust the timedelta as needed)
        start_date += timedelta(days=365)

    return all_price_data

def fetch_company_data(api_key, company_name):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "gpt-4-1106-preview",  # replace with the correct model name if different
        "messages": [{"role": "user", "content": f"Provide information on the following company: {company_name}. Include details like funding rounds, investors, description, business model, and sector. If there is no information available to the specific question, just tell No information about that."}],
        "temperature": 0.7  # adjust as needed
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code}, {response.text}"

def generate_insights(api_key, company_name):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "gpt-4-1106-preview",  # replace with the correct model name if different
        "messages": [{"role": "user", "content": f"Provide a market and competitor analysis for the following company: {company_name}. Also talk about its growth potential."}],
        "temperature": 0.7  # adjust as needed
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code}, {response.text}"

def fetch_swot_analysis(api_key, company_name):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "gpt-4-1106-preview",  # replace with the correct model name if different
        "messages": [{"role": "user", "content": f"Provide a SWOT Analysis on the following company: {company_name}."}],
        "temperature": 0.7  # adjust as needed
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code}, {response.text}"


def fetch_news(api_key, company_name):
    # Set the date range to the past 7 days
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    url = f'https://newsapi.org/v2/everything?q={company_name}&from={start_date}&to={end_date}&sortBy=publishedAt&language=en&apiKey={api_key}'

    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        filtered_articles = [article for article in articles if company_name.lower() in article['title'].lower()]

        if not filtered_articles: 
            return f"No latest news regarding {company_name}"

        news_summary = "\n\n".join([f"Title: {article['title']}\nDescription: {article['description']}" for article in
                                    filtered_articles[:5]])  # Limit to top 5 articles
        return news_summary
    else:
        return f"Error fetching news: {response.status_code}, {response.text}"

######### CHART & REPORT GENERATION #########

def create_pdf_report(company_name, stock_symbol, stock_prices):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'Stock Price Report', 0, 1, 'C')

        def chapter_title(self, title):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, title, 0, 1, 'L')
            self.ln(10)

    if stock_symbol:
        pdf = PDF()
        pdf.add_page()

        pdf.chapter_title(f"Historical Stock Prices for {company_name}:")
        plot_stock_prices(pdf, stock_prices)

        pdf_file = "stock_price_report.pdf"
        pdf.output(pdf_file)
        print(f"PDF report saved as '{pdf_file}'")
    else:
        print("Company is not listed!")

def plot_stock_prices(pdf, stock_prices):

    stock_prices.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
    dates = [datetime.strptime(item['date'], '%Y-%m-%d') for item in stock_prices]
    close_prices = [item['close_price'] for item in stock_prices]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, close_prices, color='green', marker='x')
    plt.title('Historical Stock Prices')
    plt.xlabel('Date')
    plt.ylabel('Closing Price in USD')


    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())

    plt.grid(True)
    plt.tight_layout()

    plt.savefig("stock_prices.png")
    pdf.image("stock_prices.png", x=10, y=None, w=190)
    plt.close()


def generate_report(company_name, company_data, insight, swot_analysis, company_news, include_company_data, include_insights, include_swot, include_news, include_stock_chart, stock_prices, pdf):
    pdf.set_font("helvetica", '', 12)
    pdf.add_page()


    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, f"Company Name: {company_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if include_company_data:
        # Company Data
        add_section_to_pdf(pdf, "Company Data:", company_data)

    if include_insights:
        # General Insights
        add_section_to_pdf(pdf, "Description and Business Model:", insight)

    if include_swot:
        # SWOT Analysis
        add_section_to_pdf(pdf, "SWOT Analysis:", swot_analysis)

    if include_news:
        # News Summary
        add_section_to_pdf(pdf, "Latest News:", company_news)

    if include_stock_chart and stock_prices:
     
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(0, 10, "Historical Stock Prices:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10)  
        plot_stock_prices(pdf, stock_prices)


def add_section_to_pdf(pdf, title, content):

    sanitized_content = content.replace('\u2014', '-').replace('\u2019', "'").replace('#', '').replace('*', '').replace("–", "-").replace("\u2026", "...").replace('\u2018', "'")

    line_height = 6

    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 12)
    pdf.multi_cell(0, line_height, sanitized_content)
    pdf.set_xy(10, pdf.get_y() + 10)


######### FRONT-END #########

# Streamlit UI
st.title("Company Report Generator")

# Brief Description
description = """
This application provides a comprehensive analysis of public companies. 
It utilizes AI to fetch and compile essential information about a chosen company, 
including its funding rounds, investors, business model, and sector analysis.
Users can generate a customized report containing a SWOT analysis, 
latest news summaries, general insights, and detailed company data. 
Ideal for venture capitalists, investors, and business analysts seeking 
in-depth knowledge about startup ventures.
"""

st.write(description)  

with st.expander("Instructions and Code Information"):
    st.write("""
    Here you can add detailed instructions on how to use the program, as well as explanations on how the code was built.

    ### How to Input Data
    - Step 1: Enter the company name in the provided input field.
    - Step 2: Select the checkboxes for the data you wish to include in the report.

    ### Understanding the Program
    - The program fetches data using the OpenAI and NewsAPI.
    - It generates a PDF report based on user selections.

    ### Technical Details
    - This program is built using Python with the Streamlit framework.
    - Data fetching and processing are key components of the workflow.

    ### Support
    For further queries or support, feel free to reach out to our support team.
    """)

st.divider()

company_name = st.text_input("Please enter the Company Name")

include_company_data = st.checkbox("Include Company Data (Recommended)", value=True)
include_insights = st.checkbox("Include General Insights (Recommended", value=True)
include_swot = st.checkbox("Include SWOT Analysis", value=True)
include_news = st.checkbox("Include News Summary", value=True)
include_stock_chart = st.checkbox("Include Stock Chart", value=True)

if st.button("Generate Report"):

    progress_bar = st.progress(0)
    progress_value = 0

    with st.spinner("Fetching Data..."):
  
        if include_company_data:
            progress_value += 25 
            progress_bar.progress(progress_value)
            company_data = fetch_company_data(openai_api_key, company_name)
        else:
            company_data = ""

        if include_insights:
            progress_value += 25
            progress_bar.progress(progress_value)
            insight = generate_insights(openai_api_key, company_name)
        else:
            insight = ""

        if include_swot:
            progress_value += 25
            progress_bar.progress(progress_value)
            swot_analysis = fetch_swot_analysis(openai_api_key, company_name)
        else:
            swot_analysis = ""

        if include_news:
            progress_value += 25
            progress_bar.progress(progress_value)
            company_news = fetch_news(news_api_key, company_name)
        else:
            company_news = ""

        stock_prices = None
        if include_stock_chart:
            stock_symbol = get_stock_symbol(company_name)
            if stock_symbol:
                stock_prices = get_all_historical_stock_prices(stock_symbol)
            else:
                st.error("Stock symbol not found for the given company name.")

        pdf = FPDF()
        pdf.set_margins(left=10, top=10, right=10)
        generate_report(company_name, company_data, insight, swot_analysis, company_news, include_company_data, include_insights, include_swot, include_news, include_stock_chart, stock_prices, pdf)

        pdf_output_filename = f"{company_name}_Report.pdf"
        pdf.output(pdf_output_filename)

   
        progress_bar.progress(100)

        st.success("Report generated!")
        with open(pdf_output_filename, "rb") as file:
            st.download_button(label="Download Report", data=file, file_name=pdf_output_filename, mime='application/octet-stream')