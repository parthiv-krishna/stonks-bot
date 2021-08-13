from typing import Dict
import discord
import asyncio
import os
from dotenv import load_dotenv
import requests
from charts import save_chart
from broker import Broker
import textwrap
from distutils.util import strtobool

class StonksBot(discord.Client):
    def __init__(self, cfg: Dict):
        super().__init__()

        self.__dict__.update(cfg)

        self.attach_ready_handler()
        self.attach_message_handler()

        self.loop.create_task(self.status_update_task())

        self.broker = Broker(self.financialmodeling_keys, test_mode=self.test_mode)

    def activate(self):
        self.run(self.discord_token)

    def attach_ready_handler(self):
        @self.event
        async def on_ready():
            print('We have logged in as {0.user}'.format(self))
            mode = "test" if self.test_mode else "live"
            stonks_channel = self.get_channel(self.stonks_channel)
            msg = f"stonks bot active in {mode} mode. Send `stonks help` for a list of commands"
            await self.send_message(stonks_channel, msg)


    def attach_message_handler(self):
        @self.event
        async def on_message(message):
            if message.author == self.user:
                return
            await self.add_emoji(message)
            await self.process_message(message)
    
    async def status_update_task(self):
        await self.wait_until_ready()
        await asyncio.sleep(self.status_update_secs)
        print("updating status")
        await self.ticker_status()

    async def add_emoji(self, message):
        content = message.content.lower()
        if "unstonk" in content:
            await message.add_reaction(self.unstonks_emoji)
        elif "stonk" in content:
            await message.add_reaction(self.stonks_emoji)

    async def process_message(self, message):
        content = message.content.strip().lower()
        tokens = content.split()
        if len(tokens) <= 1 or tokens[0] != "stonks":
            return
        channel = message.channel
        async with channel.typing():
            # At least 2 tokens, token 0 is "stonks". We need to process
            match tokens[1:]:
                case ["help", *_]:
                    await self.help_message(channel)

                case ["quote", *tickers]:
                    for ticker in tickers:
                        await self.quote_message(channel, ticker)

                case ["info", *tickers]:
                    for ticker in tickers:
                        await self.info_message(channel, ticker)

                case ["status", ticker]:
                    print("status", ticker)

                case ["status", ticker, *_]:
                    print("bad status")

                case ["chart", ticker, ("w" | "m" | "y" | "f") as timescale]:
                    await self.chart_message(channel, ticker, timescale.upper())

                case ["chart", *_]:
                    await self.send_message(channel, "Usage: `stonks chart TICKER TIMESCALE`. `TIMESCALE` should be one of `[W, M, Y, F]`.")

                case [("buy" | "sell") as order_type, *orders]:
                   await self.process_order(channel, order_type, orders)

                case ["queue", "remove", i]:
                    await self.remove_order(channel, i)

                case ["queue", *_]:
                    await self.queue_message(channel)

                case ["portfolio", *_]:
                    await self.portfolio_message(channel)

            # if tokens[0].lower() == "chart":
            #     if len(tokens) < 2:
            #         await message.channel.send("Please provide a ticker to chart.")
            #         return
            #     if len(tokens) > 3:
            #         await message.channel.send(f"Only charting {tokens[1].upper()}.")
            #     if len(tokens) == 2:
            #         tokens.append("M")
            #         if tokens[1].upper() != "PORTFOLIO":
            #             await message.channel.send("Defaulting to month timescale.")
            #     else:
            #         if tokens[2].upper() in "WMYF" and len(tokens[2]) == 1:
            #             await self.chart_message(tokens[1], message, time_span=tokens[2].upper())
            #             return
            #         else:
            #             await message.channel.send(f"Unrecognized timescale {tokens[2]}. (`W`, `M`, `Y`, `F` supported). Defaulting to `M` (month)")
            #     await self.chart_message(tokens[1], message)
            #     return

            # if tokens[0].lower() == "info":
            #     for token in tokens[1:]:
            #         await self.info_message(token.upper(), message)
            #     return

            # if tokens[0].lower() == "buy":
            #     buy_orders = {}
            #     if len(tokens) % 2 == 0:
            #         await message.channel.send("Buy format: `stonks buy ABC 1 DEFG 2 H 3`")
            #         return
            #     for i in range(1, len(tokens) - 1, 2):
            #         ticker = tokens[i].upper()
            #         try:
            #             count = int(tokens[i+1])
            #             if count <= 0:
            #                 await message.channel.send(f"Shorting is not supported. Skipping order for {count}x{ticker}")
            #                 continue
            #         except:
            #             await message.channel.send("Buy format: `stonks buy ABC 1 DEFG 2 H 3`")
            #             return
            #         buy_orders[ticker] = count
            #     msgs = self.broker.buy_stocks(buy_orders)
            #     for msg in msgs:
            #         await message.channel.send(msg)
            #     await message.channel.send(f"Available cash balance: ${self.broker.balance:,.2f}")
            #     return

            # if tokens[0].lower() == "sell":
            #     sell_orders = {}
            #     if len(tokens) % 2 == 0:
            #         await message.channel.send("Sell format: `stonks sell ABC 1 DEFG 2 H 3`")
            #         return
            #     for i in range(1, len(tokens) - 1, 2):
            #         ticker = tokens[i].upper()
            #         try:
            #             count = int(tokens[i+1])
            #             if count <= 0:
            #                 await message.channel.send(f"Shorting is not supported. Skipping order for {count}x{ticker}")
            #                 continue
            #         except:
            #             await message.channel.send("Buy format: `stonks sell ABC 1 DEFG 2 H 3`")
            #             return
            #         sell_orders[ticker] = count
            #     msgs = self.broker.sell_stocks(sell_orders)
            #     for msg in msgs:
            #         await message.channel.send(msg)
            #     await message.channel.send(f"Available cash balance: ${self.broker.balance:,.2f}")
            #     return
            
            # if tokens[0].lower() == "info":
            #     for token in tokens[1:]:
            #         await self.info_message(token.upper(), message)
            #     return

            # if tokens[0].lower() == "portfolio":
            #     await self.portfolio_message(message)
            #     return

            # if tokens[0].lower() == "help":
            #     await self.help_message(message)
            #     return

            # if tokens[0].lower() == "queue":
            #     if len(tokens) > 1 and tokens[1].lower() == "remove":
            #         try:
            #             idx = int(tokens[2])
            #         except:
            #             await message.channel.send("Please provide an order number to remove.")
            #             return
            #         await self.remove_order(idx, message)
            #         return

            #     await self.queue_message(message)
            #     return

            # for token in tokens:
            #     ticker = token.upper()
            #     await self.ticker_message(ticker, message)
        
    async def send_message(self, channel, message, **kwargs):
        await channel.send(message, **kwargs)
        
    async def help_message(self, channel):
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
        chart portfolio            : draw chart of holdings value over time```
        """

        msg = textwrap.dedent(msg)
        await channel.send(msg)
        
    def get_quote(self, symbol):
        url = 'https://finnhub.io/api/v1/quote?symbol=' + symbol + '&token=' + self.finnhub_key
        response = requests.get(url)
        quote = response.json()
        if quote['c'] == 0:
            return None
        change = round(quote['c'] - quote['pc'], 2)
        quote['change'] = '+$' + str(change) if change > 0 else '-$' + str(abs(change))
        percent = round((((quote['c'] / quote['pc']) - 1)*100), 2)
        quote['percent'] = '+' + str(percent) if percent > 0 else str(percent)
        quote['symbol'] = symbol
        quote['emoji'] = self.stonks_emoji if change >= 0 else self.unstonks_emoji
        return quote

    async def quote_message(self, channel, symbol):
        quote = self.get_quote(symbol.upper())
        if quote == None:
            msg = f"No information found for ticker **{symbol}**."
        else:
            msg = "**{symbol}**: ${c:,.2f} ({change} {emoji} {percent}%) *Open*: ${o:,.2f} *High*: ${h:,.2f} *Low*: ${l:,.2f} *Prev. Close*: ${pc:,.2f}".format(**quote)
        await channel.send(msg)

    async def info_message(self, channel, symbol):
        if symbol == "PORTFOLIO":
            await self.portfolio_message(channel)
            return

        url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol=' + symbol.upper() + '&apikey=' + self.alphavantage_key
        response = requests.get(url)
        info = response.json()
        desc = info['Description']
        desc_lines = textwrap.wrap(desc, width=self.info_width)
        with open('stonks.txt', mode="w") as f:
            f.write('\n'.join(desc_lines))
        period = desc.find(".", 50) # skip period from Corp. etc
        first_sentence = desc[:period+1]
        msg = "Info for **" + symbol + "**: " + first_sentence + " [Open attached file for full info]"
        await channel.send(msg, file=discord.File('stonks.txt'))

    async def ticker_status(self):
        stonks_channel = self.get_channel(self.stonks_channel)
        print("updating", self.broker.order_queue)
        if self.broker.order_queue and self.broker.market_is_open():
            msg = await stonks_channel.send("Executing order queue")
            self.broker.execute_queue_orders()
            await self.portfolio_message(stonks_channel)
        
        if self.status_ticker == "PORTFOLIO":
            quote = {}
            quote['c'] = self.broker.get_curr_val()
            quote['symbol'] = ""
            quote['pc'] = self.broker.get_prev_close()

            percent = round((((quote['c'] / quote['pc']) - 1)*100), 2)
            quote['percent'] = '+' + str(percent) if percent > 0 else str(percent)

        else:
            quote = self.get_quote(self.status_ticker)

        if quote == None:
            stat = f"ERROR: {self.status_ticker}"
        else:
            stat = "{symbol} ${c:,.2f} {percent}%".format(**quote)
        print("STATUS", stat)
        game = discord.Activity(name=stat, type=discord.ActivityType.watching)
        await self.change_presence(status=discord.Status.online, activity=game)
        new_name = "stonks" if quote['c'] > quote['pc'] else "unstonks"
        if new_name != stonks_channel.name:
            print("Updating channel name to: " + new_name)
            await stonks_channel.edit(name=new_name)
            new_pfp = self.pfp_kalm if quote['c'] > quote['pc'] else self.pfp_panik
            await self.user.edit(avatar=new_pfp)
            print("Changing picture")

    async def chart_message(self, channel, ticker, time_span="M"):
        quote = self.get_quote(ticker.upper())

        if ticker.upper() == "PORTFOLIO":
            self.broker.save_chart_of_portfolio_history()
        elif not save_chart(ticker, realtime=quote, time_span=time_span):
            await(channel.send(ticker.upper() + " not found."))
            return
        print("CHART", ticker)
        await channel.send(file=discord.File('stonks.jpg'))
        if ticker.upper() == "PORTFOLIO":
            await channel.send(f"Portfolio value: ${self.broker.get_curr_val():,.2f} (`stonks portfolio` for full holdings)")
        else:
            await self.quote_message(channel, ticker.upper())

    async def process_order(self, channel, order_type, orders):
        orders_dict = {}
        if len(orders) % 2 == 1:
            await channel.send("Buy format: `stonks buy ABC 1 DEFG 2 H 3`")
            return
        for i in range(0, len(orders), 2):
            ticker = orders[i].upper()
            try:
                count = int(orders[i+1])
                if count <= 0:
                    await channel.send(f"Shorting is not supported. Skipping order for {count}x{ticker}")
                    continue
            except:
                await channel.send(f"Buy format: `stonks {order_type} ABC 1 DEFG 2 H 3`")
                return
            orders_dict[ticker] = count
        match order_type:
            case "buy":
                msgs = self.broker.buy_stocks(orders_dict)
            case "sell":
                msgs = self.broker.sell_stocks(orders_dict)
        for msg in msgs:
            await channel.send(msg)
        await channel.send(f"Available cash balance: ${self.broker.balance:,.2f}")

    async def remove_order(self, channel, idx):
        try:
            idx = int(idx)
            order = self.broker.remove_order(idx)
            msg =  f"Removed order from the queue:\n"
            msg += f"`{idx} ({order[0]}): "
            for ticker in order[1]:
                msg += f"{ticker} x{order[1][ticker]}   "
            msg += '`\n `stonks queue` to see the updated queue.'
        except ValueError:
            msg = f"Could not convert index {idx} to an integer"

        await channel.send(msg)

    async def queue_message(self, channel):
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
        await channel.send(msg)

    async def portfolio_message(self, channel):
        msg = "Current portfolio: \n```"
        total = self.broker.balance
        if self.broker.owned_shares:
            prices = self.broker.get_curr_prices(self.broker.owned_shares)
            for ticker in self.broker.owned_shares:
                n_shares = self.broker.owned_shares[ticker]
                cost = self.broker.cost_basis[ticker]
                cost_str = f"{cost:,.2f}"
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
        await channel.send(msg)

if __name__ == "__main__":
    load_dotenv()
    cfg = {
        "discord_token": os.getenv('DISCORD_TOKEN'),
        "discord_guild": os.getenv('DISCORD_GUILD'),
        "stonks_channel": int(os.getenv('STONKS_CHANNEL')),
        "finnhub_key": os.getenv('FINNHUB_KEY'),
        "alphavantage_key": os.getenv('ALPHAVANTAGE_KEY'),
        "financialmodeling_keys": os.getenv('FINANCIALMODELING_KEYS').split(','),
        "stonks_emoji": os.getenv('STONKS_EMOJI'),
        "unstonks_emoji": os.getenv('UNSTONKS_EMOJI'),
        "status_ticker": os.getenv('STATUS_TICKER'),
        "status_update_secs": int(os.getenv('STATUS_UPDATE_SECS')),
        "pfp_panik": bytearray(open("pfp/panik.jpg", 'rb').read()),
        "pfp_kalm": bytearray(open("pfp/kalm.jpg", 'rb').read()),
        "info_width": int(os.getenv("INFO_WIDTH")),
        "test_mode": bool(strtobool(os.getenv('TEST_MODE', 'True')))
    }

    stonks_bot = StonksBot(cfg)
    stonks_bot.activate()