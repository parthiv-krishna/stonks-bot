import requests
import json
import os
from datetime import date
import queue

def track_portfolio(func):
    def wrapper(*args, **kwargs):
        rval = func(*args, **kwargs)
        self = args[0]
        self.get_curr_val()
        return rval
    return wrapper


class Broker():

    def __init__(self, FINANCIAL_MODELING_API_KEYS, starting_amount = float(1000000)):
        """Takes list of api keys to use and starting amount"""
        self._curr_key_idx = 0
        self.balance = starting_amount

        self.owned_shares = {}
        self.cost_basis = {}
        self.portfolio_history = {}

        self.order_queue = queue.Queue()

        if isinstance(FINANCIAL_MODELING_API_KEYS, str):
            self.FINANCIAL_MODELING_API_KEYS = [FINANCIAL_MODELING_API_KEYS]
        else:
            self.FINANCIAL_MODELING_API_KEYS = list(FINANCIAL_MODELING_API_KEYS)

    def get_curr_prices(self, tickers):
        """Takes iterable of UPPERCASE ticker symbols, then returns dictionary of prices corresponding to those tickers"""

        if tickers is None:
            raise Exception('No tickers given')
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

    def execute_queue_orders(self):
        print("executing queue")
        if self.market_is_open():
            while not self.order_queue.empty():
                order = self.order_queue.get()
                if order[0] == 'BUY':
                    self.buy_stocks(order[1])
                else:
                    self.sell_stocks(order[1])

    def get_curr_key(self):
        """Cycles through API keys"""
        self._curr_key_idx = (self._curr_key_idx + 1) % len(self.FINANCIAL_MODELING_API_KEYS)
        return self.FINANCIAL_MODELING_API_KEYS[self._curr_key_idx]

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

                    buy_info.append(f'Bought {buy_order[ticker]} shares of {ticker} at price {prices[ticker]} for a total of {cost}.')

                else:
                    buy_info.append(f'Cannot afford {buy_order[ticker]} shares of {ticker}.')
        else: # market not open, add order to queue
            self.order_queue.put(('BUY', buy_order))
            buy_info.append('Market not open, adding buy order to queue. Here is your order:')
            for ticker in prices:
                buy_info.append(f'BUY {buy_order[ticker]} shares of {ticker} at roughly {prices[ticker]} per share.')
        return buy_info

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
                    sell_info.append(f'Sold {sell_order[ticker]} shares of {ticker} at price {prices[ticker]} for a total of {gain}.')
        else: # market not open
            self.order_queue.put(('SELL', sell_order))
            sell_info.append('Market not open, adding sell order to queue. Here is your order:')
            for ticker in prices:
                sell_info.append(f'SELL {sell_order[ticker]} shares of {ticker} at roughly {prices[ticker]} per share.')

        return sell_info

    def get_curr_val(self):
        """Returns current portfolio value, updates portfolio history with current value"""
        self.execute_queue_orders()

        total = self.balance

        if self.owned_shares:
            prices = self.get_curr_prices(self.owned_shares)
            for ticker in self.owned_shares:
                total += prices[ticker] * self.owned_shares[ticker]

        self.portfolio_history[date.today().strftime("%d/%m/%Y")] = total

        return total

    def market_is_open(self):
        params = { 'apikey' : self.get_curr_key() }
        response = requests.get('https://financialmodelingprep.com/api/v3/is-the-market-open', params)
        if response.status_code != 200:
            raise Exception(f"Bad response code, response code {response.status_code}")

        data = response.json()
        return data['isTheStockMarketOpen']
