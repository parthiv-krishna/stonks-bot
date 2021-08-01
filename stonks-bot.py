import discord
from discord.ext.tasks import loop
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
from charts import save_chart
from broker import Broker
import textwrap

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
FINNHUB_KEY = os.getenv('FINNHUB_KEY')
ALPHAVANTAGE_KEY = os.getenv('ALPHAVANTAGE_KEY')
FINANCIALMODELING_KEYS = os.getenv('FINANCIALMODELING_KEYS').split(',')

STONKS_EMOJI = os.getenv('STONKS_EMOJI')
UNSTONKS_EMOJI = os.getenv('UNSTONKS_EMOJI')
STATUS_UPDATE_SECS = int(os.getenv('STATUS_UPDATE_SECS'))
INFO_WIDTH = int(os.getenv('INFO_WIDTH'))

TEST_MODE = (os.getenv('TEST_MODE') == 'True')

status_ticker = os.getenv('STATUS_TICKER')
pfp_panik = bytearray(open("pfp/panik.jpg", 'rb').read())
pfp_kalm = bytearray(open("pfp/kalm.jpg", 'rb').read())


class StonksBot(discord.Client):
    def __init__(self):
        super().__init__()

        self.attach_ready_handler()
        self.attach_message_handler()
        self.broker = Broker(FINANCIALMODELING_KEYS, test_mode=TEST_MODE)
        self.ticker_status.start()

    def attach_ready_handler(self):
        @self.event
        async def on_ready():
            print('We have logged in as {0.user}'.format(self))

    def attach_message_handler(self):
        @self.event
        async def on_message(message):
            if message.author == self.user:
                return
            await self.add_emoji(message)
            await self.process_message(message)

    async def add_emoji(self, message):
        content = message.content.lower()
        if "unstonk" in content:
            await message.add_reaction(UNSTONKS_EMOJI)
        elif "stonk" in content:
            await message.add_reaction(STONKS_EMOJI)

    async def process_message(self, message):
        content = message.content.lower()
        tokens = content.split()
        if tokens[0] != "stonks":
            return

        async with message.channel.typing():

            tokens = [tok for tok in message.content.strip().split(' ')[1:] if tok]

            if len(tokens) == 0:
                await message.add_reaction(STONKS_EMOJI)
                return

            if tokens[0].lower() == "status":
                global status_ticker
                status_ticker = tokens[1].upper()
                await self.ticker_status()
                await message.channel.send(f"Updated status to track {status_ticker}.")
                return
            
            if tokens[0].lower() == "chart":
                if len(tokens) < 2:
                    await message.channel.send("Please provide a ticker to chart.")
                    return
                if len(tokens) > 3:
                    await message.channel.send(f"Only charting {tokens[1].upper()}.")
                if len(tokens) == 2:
                    tokens.append("M")
                    if tokens[1].upper() != "PORTFOLIO":
                        await message.channel.send("Defaulting to month timescale.")
                else:
                    if tokens[2].upper() in "WMYF" and len(tokens[2]) == 1:
                        await self.chart_message(tokens[1], message, time_span=tokens[2].upper())
                        return
                    else:
                        await message.channel.send(f"Unrecognized timescale {tokens[2]}. (`W`, `M`, `Y`, `F` supported). Defaulting to `M` (month)")
                await self.chart_message(tokens[1], message)
                return

            if tokens[0].lower() == "info":
                for token in tokens[1:]:
                    await self.info_message(token.upper(), message)
                return

            if tokens[0].lower() == "buy":
                buy_orders = {}
                if len(tokens) % 2 == 0:
                    await message.channel.send("Buy format: `stonks buy ABC 1 DEFG 2 H 3`")
                    return
                for i in range(1, len(tokens) - 1, 2):
                    ticker = tokens[i].upper()
                    try:
                        count = int(tokens[i+1])
                        if count <= 0:
                            await message.channel.send(f"Shorting is not supported. Skipping order for {count}x{ticker}")
                            continue
                    except:
                        await message.channel.send("Buy format: `stonks buy ABC 1 DEFG 2 H 3`")
                        return
                    buy_orders[ticker] = count
                msgs = self.broker.buy_stocks(buy_orders)
                for msg in msgs:
                    await message.channel.send(msg)
                await message.channel.send(f"Available cash balance: ${self.broker.balance:,.2f}")
                return

            if tokens[0].lower() == "sell":
                sell_orders = {}
                if len(tokens) % 2 == 0:
                    await message.channel.send("Sell format: `stonks sell ABC 1 DEFG 2 H 3`")
                    return
                for i in range(1, len(tokens) - 1, 2):
                    ticker = tokens[i].upper()
                    try:
                        count = int(tokens[i+1])
                        if count <= 0:
                            await message.channel.send(f"Shorting is not supported. Skipping order for {count}x{ticker}")
                            continue
                    except:
                        await message.channel.send("Buy format: `stonks sell ABC 1 DEFG 2 H 3`")
                        return
                    sell_orders[ticker] = count
                msgs = self.broker.sell_stocks(sell_orders)
                for msg in msgs:
                    await message.channel.send(msg)
                await message.channel.send(f"Available cash balance: ${self.broker.balance:,.2f}")
                return
            
            if tokens[0].lower() == "info":
                for token in tokens[1:]:
                    await self.info_message(token.upper(), message)
                return

            if tokens[0].lower() == "portfolio":
                await self.portfolio_message(message)
                return

            if tokens[0].lower() == "help":
                await self.help_message(message)
                return

            if tokens[0].lower() == "queue":
                if len(tokens) > 1 and tokens[1].lower() == "remove":
                    try:
                        idx = int(tokens[2])
                    except:
                        await message.channel.send("Please provide an order number to remove.")
                        return
                    await self.remove_order(idx, message)
                    return

                await self.queue_message(message)
                return

            for token in tokens:
                ticker = token.upper()
                await self.ticker_message(ticker, message)
        
    async def send_message(self, channel, message, **kwargs):
        await channel.send(message, **kwargs)
        
    def get_quote(self, symbol):
        url = 'https://finnhub.io/api/v1/quote?symbol=' + symbol + '&token=' + FINNHUB_KEY
        response = requests.get(url)
        quote = response.json()
        if quote['c'] == 0:
            return None
        change = round(quote['c'] - quote['pc'], 2)
        quote['change'] = '+$' + str(change) if change > 0 else '-$' + str(abs(change))
        percent = round((((quote['c'] / quote['pc']) - 1)*100), 2)
        quote['percent'] = '+' + str(percent) if percent > 0 else str(percent)
        quote['symbol'] = symbol
        quote['emoji'] = STONKS_EMOJI if change > 0 else UNSTONKS_EMOJI
        return quote

    async def ticker_message(self, ticker, message, quote="default"):
        if quote == "default":
            quote = self.get_quote(ticker)
        if quote == None:
            msg = f"No information found for ticker **{ticker}**."
        else:
            msg = "**{symbol}**: ${c:,.2f} ({change} {emoji} {percent}%) *Open*: ${o:,.2f} *High*: ${h:,.2f} *Low*: ${l:,.2f} *Prev. Close*: ${pc:,.2f}".format(**quote)
        print("MESSAGE", msg)
        await message.channel.send(msg)

    @loop(seconds=STATUS_UPDATE_SECS)
    async def ticker_status(self):
        if not client.is_ready():
            await client.wait_until_ready()
            stonks_channel = client.get_channel(int(os.getenv('STONKS_CHANNEL')))
            await stonks_channel.send("stonks bot active in " + ("test" if TEST_MODE else "live") + " mode. send `stonks help` for a list of commands")
        stonks_channel = client.get_channel(int(os.getenv('STONKS_CHANNEL')))
        if self.broker.order_queue and self.broker.market_is_open():
            msg = await stonks_channel.send("Executing order queue")
            self.broker.execute_queue_orders()
            await self.portfolio_message(msg)
        
        if status_ticker == "PORTFOLIO":
            quote = {}
            quote['c'] = self.broker.get_curr_val()
            quote['symbol'] = ""
            quote['pc'] = self.broker.get_prev_close()

            percent = round((((quote['c'] / quote['pc']) - 1)*100), 2)
            quote['percent'] = '+' + str(percent) if percent > 0 else str(percent)

        else:
            quote = self.get_quote(status_ticker)

        if quote == None:
            stat = f"ERROR: {status_ticker}"
        else:
            stat = "{symbol} ${c:,.2f} {percent}%".format(**quote)
        print("STATUS", stat)
        game = discord.Activity(name=stat, type=discord.ActivityType.watching)
        await client.change_presence(status=discord.Status.online, activity=game)
        new_name = "stonks" if quote['c'] > quote['pc'] else "unstonks"
        if new_name != stonks_channel.name:
            print("Updating channel name to: " + new_name)
            await stonks_channel.edit(name=new_name)
            new_pfp = pfp_kalm if quote['c'] > quote['pc'] else pfp_panik
            await client.user.edit(avatar=new_pfp)
            print("Changing picture")

    async def chart_message(self, ticker, message, time_span="M"):
        quote = self.get_quote(ticker.upper())

        if ticker.upper() == "PORTFOLIO":
            self.broker.save_chart_of_portfolio_history()
        elif not save_chart(ticker, realtime=quote, time_span=time_span):
            await(message.channel.send(ticker.upper() + " not found."))
            return
        print("CHART", ticker)
        await message.channel.send(file=discord.File('stonks.jpg'))
        if ticker.upper() == "PORTFOLIO":
            await message.channel.send(f"Portfolio value: ${self.broker.get_curr_val():,.2f} (`stonks portfolio` for full holdings)")
        else:
            await self.ticker_message(ticker.upper(), message, quote=quote)

    async def info_message(self, symbol, message):
        if symbol == "PORTFOLIO":
            await self.portfolio_message(message)
            return

        url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol=' + symbol + '&apikey=' + ALPHAVANTAGE_KEY
        response = requests.get(url)
        info = response.json()
        desc = info['Description']
        desc_lines = textwrap.wrap(desc, width=INFO_WIDTH)
        with open('stonks.txt', mode="w") as f:
            f.write('\n'.join(desc_lines))
        period = desc.find(".", 50) # skip period from Corp. etc
        first_sentence = desc[:period+1]
        msg = "Info for **" + symbol + "**: " + first_sentence + " [Open attached file for full info]"
        await message.channel.send(msg, file=discord.File('stonks.txt'))

    async def portfolio_message(self, message):
        msg = "Current portfolio: \n```"
        total = self.broker.balance
        if self.broker.owned_shares:
            prices = self.broker.get_curr_prices(self.broker.owned_shares)
            for ticker in self.broker.owned_shares:
                n_shares = self.broker.owned_shares[ticker]
                cost = self.broker.cost_basis[ticker]
                cost_str = f"{cost:.2f}"
                msg += f"{ticker.ljust(5)}{str(n_shares).rjust(6)} @ ${cost_str.ljust(9)}"
                price = prices[ticker]
                price_str = f"{price:,.2f}"
                msg += f" Current: ${price_str.ljust(8)} (total: "
                subtotal = prices[ticker] * self.broker.owned_shares[ticker]
                subtotal_str = f"{subtotal:,.2f}"
                percent = ((price - cost)/cost) * 100
                percent_str = f"+{percent:.2f}" if percent > 0 else f"{percent:.2f}"
                msg += f"${subtotal_str.ljust(10)} | {percent_str}%)\n"
                total += subtotal
        msg += f"\nCash Balance:          ${self.broker.balance:,.2f}\n"
        msg += f"Total portfolio value: ${total:,.2f}\n"
        msg += "```"
        await message.channel.send(msg)


    async def help_message(self, message):
        msg =  """  
        Usage for stonks-bot: send `stonks` and then a command.```
        help                       : display this message

        ### Stock Watching ###
        quote TICKER1 TICKER2...   : get quote for specified tickers
        info TICKER1 TICKER2...    : get company info for specified tickers
        status TICKER              : watch company (or PORTFOLIO) in bot status
        chart TICKER TIMESCALE     : draw chart for specified ticker. Timescales: W, M, Y, F (full)

        ### Paper Trading ###
        buy TICKER1 QTY1 T2 Q2...  : buy shares (or add to order queue to execute at market open)
        sell TICKER1 QTY1 T2 Q2... : sell shares (or add to order queue to execute at market open)
        queue                      : show the current order queue
        queue remove i             : remove the i'th order from the queue
        portfolio                  : get current holdings information
        info portfolio             : also get current holdings information
        chart portfolio            : draw chart of holdings value over time```
        """

        msg = textwrap.dedent(msg)

        await message.channel.send(msg)

    async def queue_message(self, message):
        if self.broker.order_queue:   
            msg = "Order queue: ```\n"
            for i, order in enumerate(self.broker.order_queue):
                msg += f"{i} ({order[0]}): "
                for ticker in order[1]:
                    msg += f"{ticker} x{order[1][ticker]}   "
                msg += "\n"
            msg += "```Use `stonks queue remove i` to remove the `i`th order."
        else:
            msg = "Order queue is empty."
        await message.channel.send(msg)

    async def remove_order(self, idx, message):
        order = self.broker.remove_order(idx)
        msg =  f"Removed order from the queue:\n"
        msg += f"`{idx} ({order[0]}): "
        for ticker in order[1]:
            msg += f"{ticker} x{order[1][ticker]}   "
        msg += '`\n `stonks queue` to see the updated queue.'
        await message.channel.send(msg)

if __name__ == "__main__":
    stonks_bot = StonksBot()
    stonks_bot.run(TOKEN)