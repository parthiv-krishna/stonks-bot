import requests
import json
import os
from dotenv import load_dotenv
import plotly.graph_objs as go
from datetime import date

load_dotenv()
ALPHAVANTAGE_KEY = os.getenv('ALPHAVANTAGE_KEY')

def save_chart(ticker, realtime=None, file="stonks.jpg"):
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
        return False
    
    else:
        dates = []
        open_prices = []
        high_prices = []
        low_prices = []
        close_prices = []

        if realtime is not None:
            today = date.today().strftime("%Y-%m-%d")
            dates.append(today)
            open_prices.append(realtime['o'])
            high_prices.append(realtime['h'])
            low_prices.append(realtime['l'])
            close_prices.append(realtime['c'])

        for point in data['Time Series (Daily)']:
            dates.append(point)
            open_prices.append(data['Time Series (Daily)'][point]['1. open'])
            high_prices.append(data['Time Series (Daily)'][point]['2. high'])
            low_prices.append(data['Time Series (Daily)'][point]['3. low'])
            close_prices.append(data['Time Series (Daily)'][point]['4. close'])
            
        candlestick_data = [go.Candlestick(x=dates, open=open_prices, high=high_prices, low=low_prices, close=close_prices)]

        layout = {'title' : data['Meta Data']['2. Symbol'],
                  'xaxis' : go.layout.XAxis(title=go.layout.xaxis.Title( text="Date")),
                  'yaxis' : go.layout.YAxis(title=go.layout.yaxis.Title( text="Price"))}

        fig = go.Figure(data=candlestick_data, layout=layout)
        fig.update_layout(xaxis_rangeslider_visible=False)

        fig.write_image(file)

        return True

if __name__ == '__main__':
    ticker = input('Enter ticker: ')
    save_chart(ticker)