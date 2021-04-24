import requests
import json
import os
from datetime import date, datetime
from collections import deque
import plotly.graph_objs as go
import pickle

def save(func):
    def wrapper(*args, **kwargs):
        rval = func(*args, **kwargs)
        self = args[0]
        self.pickle_data()
        return rval
    return wrapper

class Broker():

    def __init__(self, FINANCIAL_MODELING_API_KEYS, starting_amount = float(1000000), pickle_file = 'broker_data.pickle'):
        """Takes list of api keys to use and starting amount"""

        self.TEST_MODE = True

        self.balance = starting_amount
        self.owned_shares = {}
        self.cost_basis = {}
        self.portfolio_history = {}
        self.order_queue = deque()
        
        # updates data from pickle
        self.load_data()

        self._curr_key_idx = 0

        if isinstance(FINANCIAL_MODELING_API_KEYS, str):
            self.FINANCIAL_MODELING_API_KEYS = [FINANCIAL_MODELING_API_KEYS]
        else:
            self.FINANCIAL_MODELING_API_KEYS = list(FINANCIAL_MODELING_API_KEYS)

    def get_curr_prices(self, tickers):
        """Takes iterable of UPPERCASE ticker symbols, then returns dictionary of prices corresponding to those tickers"""

        if not tickers:
            raise Exception('Empty list of tickers given')

        params = { 'apikey' : self.get_curr_key() }
        response = requests.get('https://financialmodelingprep.com/api/v3/quote/' + ','.join(tickers), params)

        if response.status_code != 200:
            raise Exception(f"Bad response code, response code {response.status_code}")

        data = response.json()

        if 'Error Message' in data:
            raise Exception('Unable to get ticker info from https://financialmodelingprep.com/api/v3/quote/')

        prices = {}
        for stock in data:
            prices[stock['symbol']] = stock['price']

        return prices

    @save
    def execute_queue_orders(self):
        if self.market_is_open():
            while self.order_queue:
                order_type, order = self.order_queue.popleft()
                if order_type == 'BUY':
                    self.buy_stocks(order)
                else:
                    self.sell_stocks(order)

    def get_curr_key(self):
        """Cycles through API keys"""
        self._curr_key_idx = (self._curr_key_idx + 1) % len(self.FINANCIAL_MODELING_API_KEYS)
        return self.FINANCIAL_MODELING_API_KEYS[self._curr_key_idx]

    @save
    def buy_stocks(self, buy_order):
        """Takes dictionary buy_order, mapping from ticker symbol to number of shares to buy, then buys one at a time"""
        buy_info = []
        prices = self.get_curr_prices(buy_order)
        if self.market_is_open():
            for ticker in prices:
                if ticker not in self.owned_shares:
                    self.owned_shares[ticker] = 0
                    self.cost_basis[ticker] = 0

                cost = buy_order[ticker] * prices[ticker]
                if cost < self.balance:

                    prev_total = self.owned_shares[ticker] * self.cost_basis[ticker]

                    new_total = prev_total + cost

                    self.owned_shares[ticker] += buy_order[ticker]

                    self.cost_basis[ticker] = new_total / self.owned_shares[ticker]

                    self.balance -= cost

                    buy_info.append(f'Bought {buy_order[ticker]} shares of {ticker} at price ${prices[ticker]:.2f} for a total of ${cost:.2f}.')

                else:
                    buy_info.append(f'Cannot afford {buy_order[ticker]} shares of {ticker}. Current balance: ${self.balance:.2f}')
        else: # market not open, add order to queue
            self.order_queue.append(('BUY', buy_order))
            buy_info.append('Market not open, adding buy order to queue. Here is your order:')
            for ticker in prices:
                buy_info.append(f'BUY {buy_order[ticker]} shares of {ticker} at roughly ${prices[ticker]:.2f} per share.')
        return buy_info

    @save
    def sell_stocks(self, sell_order):
        """Takes dictionary sell_order, mapping from ticker symbol to number of shares to sell"""
        sell_info = []
        prices = self.get_curr_prices(sell_order)
        if self.market_is_open():
            for ticker in prices:
                if ticker not in self.owned_shares:
                    sell_info.append(f'You do not own {ticker}.')
                elif sell_order[ticker] > self.owned_shares[ticker]:
                    sell_info.append(f'You have {self.owned_shares[ticker]} shares of {ticker} but tried to sell {sell_order[ticker]} shares.')
                else:
                    gain = sell_order[ticker] * prices[ticker]
                    self.owned_shares[ticker] -= sell_order[ticker]
                    self.balance += gain
                    if (self.owned_shares[ticker] == 0):
                        self.owned_shares.pop(ticker, None)
                    sell_info.append(f'Sold {sell_order[ticker]} shares of {ticker} at price ${prices[ticker]:.2f} for a total of ${gain:.2f}.')
        else: # market not open
            self.order_queue.append(('SELL', sell_order))
            sell_info.append('Market not open, adding sell order to queue. Here is your order:')
            for ticker in prices:
                sell_info.append(f'SELL {sell_order[ticker]} shares of {ticker} at roughly ${prices[ticker]:.2f} per share.')

        return sell_info

    def get_curr_val(self):
        """Returns current portfolio value, updates portfolio history with current value"""
        total = self.balance

        if self.owned_shares:
            prices = self.get_curr_prices(self.owned_shares)
            for ticker in self.owned_shares:
                total += prices[ticker] * self.owned_shares[ticker]

        self.update_history(total)

        return total

    @save
    def update_history(self, total):
        d = date.today().strftime("%d/%m/%Y")
        if d not in self.portfolio_history:
            self.portfolio_history[d] = { 'open' : total, 'high' : total, 'low' : total, 'close' : total }
        if total < self.portfolio_history[d]['low']:
            self.portfolio_history[d]['low'] = total
        if total > self.portfolio_history[d]['high']:
            self.portfolio_history[d]['high'] = total

        self.portfolio_history[d]['close'] = total


    def market_is_open(self):
        if self.TEST_MODE:
            now = datetime.now()
            return (now.minute % 2 == 0)
        
        params = { 'apikey' : self.get_curr_key() }
        response = requests.get('https://financialmodelingprep.com/api/v3/is-the-market-open', params)
        if response.status_code != 200:
            raise Exception(f"Bad response code, response code {response.status_code}")

        data = response.json()
        return data['isTheStockMarketOpen']

    def save_chart_of_portfolio_history(self, file = "stonks.jpg"):
        dates = []
        open_prices = []
        high_prices = []
        low_prices = []
        close_prices = []

        for date in self.portfolio_history:
            dates.append(date)
            open_prices.append(self.portfolio_history[date]['open'])
            high_prices.append(self.portfolio_history[date]['high'])
            low_prices.append(self.portfolio_history[date]['low'])
            close_prices.append(self.portfolio_history[date]['close'])
            
        candlestick_data = [go.Candlestick(x=dates, open=open_prices, high=high_prices, low=low_prices, close=close_prices)]

        layout = {'title' : 'Portfolio Value',
                  'xaxis' : go.layout.XAxis(title=go.layout.xaxis.Title( text="Date")),
                  'yaxis' : go.layout.YAxis(title=go.layout.yaxis.Title( text="Total Value"))}
            
        fig = go.Figure(data=candlestick_data, layout=layout)
        fig.update_layout(xaxis_rangeslider_visible=False)

        fig.write_image(file)

    def pickle_data(self):
        print("saving data")
        data = {
            'balance': self.balance,
            'owned_shares': self.owned_shares,
            'cost_basis': self.cost_basis,
            'portfolio_history': self.portfolio_history,
            'order_queue': self.order_queue
        }
        with open('broker.pickle', 'wb') as f:
            pickle.dump(data, f)

    def load_data(self):
        try:
            with open('broker.pickle', 'rb') as f:
                data = pickle.load(f)
                self.balance = data['balance']
                self.owned_shares = data['owned_shares']
                self.cost_basis = data['cost_basis']
                self.portfolio_history = data['portfolio_history']
                self.order_queue = data['order_queue']
        except:
            pass
