import requests
import json
import os

class Broker():

    def __init__(self, FINANCIAL_MODELING_API_KEYS, starting_amount = float(1000000)):
        """Takes list of api keys to use and starting amount"""
        self._curr_key_idx = 0
        self.balance = starting_amount

        self.owned_shares = {}
        self.cost_basis = {}

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

    def get_curr_key(self):
        """Cycles through API keys"""
        self._curr_key_idx = (self._curr_key_idx + 1) % len(self.FINANCIAL_MODELING_API_KEYS)
        return self.FINANCIAL_MODELING_API_KEYS[self._curr_key_idx]

    def buy_stocks(self, buy_order):
        """Takes dictionary buy_order, mapping from ticker symbol to number of shares to buy, then buys one at a time"""
        prices = self.get_curr_prices(buy_order)
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
            else:
                print(f'Cannot afford {buy_order[ticker]} shares of {ticker}.')

    def sell_stocks(self, sell_order):
        """Takes dictionary sell_order, mapping from ticker symbol to number of shares to sell"""
        prices = self.get_curr_prices(sell_order)
        for ticker in prices:
            if ticker not in self.owned_shares:
                print(f'You do not own {ticker}.')
            elif sell_order[ticker] > self.owned_shares[ticker]:
                print(f'You have {self.owned_shares[ticker]} shares of {ticker} but tried to sell {sell_order[ticker]} shares.')
            else:
                gain = sell_order[ticker] * prices[ticker]
                self.owned_shares[ticker] -= sell_order[ticker]
                self.balance += gain

    def get_curr_val(self):
        """Returns current portfolio value"""
        total = self.balance

        if self.owned_shares:
            prices = self.get_curr_prices(self.owned_shares)
            for ticker in self.owned_shares:
                total += prices[ticker] * self.owned_shares[ticker]

        return total