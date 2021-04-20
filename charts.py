import requests
import json
import os
from dotenv import load_dotenv
import plotly.graph_objs as go

load_dotenv()
ALPHAVANTAGE_KEY = os.getenv('ALPHAVANTAGE_KEY')

def save_chart(ticker, file="stonks.jpg"):
    ticker = ticker.upper()
    params = {
        'apikey'     : ALPHAVANTAGE_KEY,
        'function'   : 'TIME_SERIES_DAILY_ADJUSTED',
        'symbol'     : ticker,
        'outputsize' : 'compact'
    }

    response = requests.get('https://www.alphavantage.co/query', params)

    if response.status_code != 200:
        raise Exception("wtf")

    data = response.json()

    if 'Error Message' in data:
        print(f"save_chart: ticker {ticker} not found")
        return -1
    else:
        dates = []
        open_prices = []
        high_prices = []
        low_prices = []
        close_prices = []

        for date in data['Time Series (Daily)']:
            dates.append(date)
            open_prices.append(data['Time Series (Daily)'][date]['1. open'])
            high_prices.append(data['Time Series (Daily)'][date]['2. high'])
            low_prices.append(data['Time Series (Daily)'][date]['3. low'])
            close_prices.append(data['Time Series (Daily)'][date]['4. close'])
            
        candlestick_data = [go.Candlestick(x=dates, open=open_prices, high=high_prices, low=low_prices, close=close_prices)]

        layout = {'title' : data['Meta Data']['2. Symbol'],
                  'xaxis' : go.layout.XAxis(title=go.layout.xaxis.Title( text="Date")),
                  'yaxis' : go.layout.YAxis(title=go.layout.yaxis.Title( text="Price"))}

        fig = go.Figure(data=candlestick_data, layout=layout)
        fig.update_layout(xaxis_rangeslider_visible=False)

        fig.write_image(file)

if __name__ == '__main__':
    ticker = input('Enter ticker: ')
    save_chart(ticker)