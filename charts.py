import requests
import json
import os
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import plotly.graph_objs as go

load_dotenv()
ALPHAVANTAGE_KEY = os.getenv('ALPHAVANTAGE_KEY')


def save_chart(ticker, realtime=None, time_span = 'M', file = "stonks.jpg"):
    ticker = ticker.upper()   
    params = {
        'apikey'     : ALPHAVANTAGE_KEY,
        'function'   : 'TIME_SERIES_DAILY_ADJUSTED',
        'symbol'     : ticker,
        'outputsize' : 'full'
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

        if time_span == 'W':
            delta = timedelta(days = -7)
        elif time_span == 'M':
            delta = timedelta(days = -30)
        elif time_span == 'Y':
            delta = timedelta(days = -365)
        else:
            delta = timedelta(days = -7) # default 
        start_date_obj = datetime.now().date() + delta

        for d in data['Time Series (Daily)']:
            date_obj = datetime.strptime(d, "%Y-%m-%d").date()

            if date_obj > start_date_obj or time_span == 'F':
                dates.append(d)
                open_prices.append(data['Time Series (Daily)'][d]['1. open'])
                high_prices.append(data['Time Series (Daily)'][d]['2. high'])
                low_prices.append(data['Time Series (Daily)'][d]['3. low'])
                close_prices.append(data['Time Series (Daily)'][d]['4. close'])
            
        candlestick_data = [go.Candlestick(x=dates, open=open_prices, high=high_prices, low=low_prices, close=close_prices)]

        layout = {'title' : data['Meta Data']['2. Symbol'],
                  'xaxis' : go.layout.XAxis(title=go.layout.xaxis.Title( text="Date")),
                  'yaxis' : go.layout.YAxis(title=go.layout.yaxis.Title( text="Price"))}
            
        fig = go.Figure(data=candlestick_data, layout=layout)
        fig.update_layout(xaxis_rangeslider_visible=False)

        fig.write_image(file)
        print("success")
        return True

if __name__ == '__main__':
    ticker = input('Enter ticker\n').upper()
    save_chart(ticker, time_span='Y')