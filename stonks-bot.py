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


client = discord.Client()

broker = Broker(FINANCIALMODELING_KEYS, test_mode=TEST_MODE)

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not message.content.lower().startswith('stonks'):
        if "unstonks" in message.content:
            await message.add_reaction("unstonks:" + UNSTONKS_EMOJI)
        elif "stonks" in message.content:
            await message.add_reaction("stonks:" + STONKS_EMOJI)
        return

    async with message.channel.typing():

        tokens = [tok for tok in message.content.strip().split(' ')[1:] if tok]

        if len(tokens) == 0:
            await message.add_reaction("stonks:" + STONKS_EMOJI)
            return

        if tokens[0].lower() == "status":
            global status_ticker
            status_ticker = tokens[1].upper()
            await ticker_status()
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
                    await chart_message(tokens[1], message, time_span=tokens[2].upper())
                    return
                else:
                    await message.channel.send(f"Unrecognized timescale {tokens[2]}. (`W`, `M`, `Y`, `F` supported). Defaulting to `M` (month)")
            await chart_message(tokens[1], message)
            return

        if tokens[0].lower() == "info":
            for token in tokens[1:]:
                await info_message(token.upper(), message)
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
            msgs = broker.buy_stocks(buy_orders)
            for msg in msgs:
                await message.channel.send(msg)
            await message.channel.send(f"Available cash balance: ${broker.balance:,.2f}")
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
            msgs = broker.sell_stocks(sell_orders)
            for msg in msgs:
                await message.channel.send(msg)
            await message.channel.send(f"Available cash balance: ${broker.balance:,.2f}")
            return
        
        if tokens[0].lower() == "info":
            for token in tokens[1:]:
                await info_message(token.upper(), message)
            return

        if tokens[0].lower() == "portfolio":
            await portfolio_message(message)
            return

        if tokens[0].lower() == "help":
            await help_message(message)
            return

        if tokens[0].lower() == "queue":
            if len(tokens) > 1 and tokens[1].lower() == "remove":
                try:
                    idx = int(tokens[2])
                except:
                    await message.channel.send("Please provide an order number to remove.")
                    return
                await remove_order(idx, message)
                return

            await queue_message(message)
            return

        for token in tokens:
            ticker = token.upper()
            await ticker_message(ticker, message)

def get_quote(symbol):
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

async def ticker_message(ticker, message, quote="default"):
    if quote == "default":
        quote = get_quote(ticker)
    if quote == None:
        msg = f"No information found for ticker **{ticker}**."
    else:
        msg = "**{symbol}**: ${c:,.2f} ({change} {emoji} {percent}%) *Open*: ${o:,.2f} *High*: ${h:,.2f} *Low*: ${l:,.2f} *Prev. Close*: ${pc:,.2f}".format(**quote)
    print("MESSAGE", msg)
    await message.channel.send(msg)

@loop(seconds=STATUS_UPDATE_SECS)
async def ticker_status():
    if not client.is_ready():
        await client.wait_until_ready()
        stonks_channel = client.get_channel(int(os.getenv('STONKS_CHANNEL')))
        await stonks_channel.send("stonks bot active in " + ("test" if TEST_MODE else "live") + " mode. send `stonks help` for a list of commands")
    stonks_channel = client.get_channel(int(os.getenv('STONKS_CHANNEL')))
    if broker.order_queue and broker.market_is_open():
        msg = await stonks_channel.send("Executing order queue")
        broker.execute_queue_orders()
        await portfolio_message(msg)
    
    if status_ticker == "PORTFOLIO":
        quote = {}
        quote['c'] = broker.get_curr_val()
        quote['symbol'] = ""
        quote['pc'] = broker.get_prev_close()

        percent = round((((quote['c'] / quote['pc']) - 1)*100), 2)
        quote['percent'] = '+' + str(percent) if percent > 0 else str(percent)

    else:
        quote = get_quote(status_ticker)

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

async def chart_message(ticker, message, time_span="M"):
    quote = get_quote(ticker.upper())

    if ticker.upper() == "PORTFOLIO":
        broker.save_chart_of_portfolio_history()
    elif not save_chart(ticker, realtime=quote, time_span=time_span):
        await(message.channel.send(ticker.upper() + " not found."))
        return
    print("CHART", ticker)
    await message.channel.send(file=discord.File('stonks.jpg'))
    if ticker.upper() == "PORTFOLIO":
        await message.channel.send(f"Portfolio value: ${broker.get_curr_val():,.2f} (`stonks portfolio` for full holdings)")
    else:
        await ticker_message(ticker.upper(), message, quote=quote)

async def info_message(symbol, message):
    if symbol == "PORTFOLIO":
        await portfolio_message(message)
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

async def portfolio_message(message):
    msg = "Current portfolio: \n```"
    total = broker.balance
    if broker.owned_shares:
        prices = broker.get_curr_prices(broker.owned_shares)
        for ticker in broker.owned_shares:
            n_shares = broker.owned_shares[ticker]
            cost = broker.cost_basis[ticker]
            cost_str = f"{cost:.2f}"
            msg += f"{ticker.ljust(5)}{str(n_shares).rjust(6)} @ ${cost_str.ljust(9)}"
            price = prices[ticker]
            price_str = f"{price:,.2f}"
            msg += f" Current: ${price_str.ljust(7)} (total: "
            subtotal = prices[ticker] * broker.owned_shares[ticker]
            subtotal_str = f"{subtotal:,.2f}"
            percent = ((price - cost)/cost) * 100
            percent_str = f"+{percent:.2f}" if percent > 0 else f"{percent:.2f}"
            msg += f"${subtotal_str.ljust(10)} | {percent_str}%)\n"
            total += subtotal
    msg += f"\nCash Balance:          ${broker.balance:,.2f}\n"
    msg += f"Total portfolio value: ${total:,.2f}\n"
    msg += "```"
    await message.channel.send(msg)


async def help_message(message):
    msg =  "Usage for stonks-bot:\n```"
    msg += "stonks help                     : display this message\n"
    msg += "\n### Stock Watching ###\n"
    msg += "stonks TICKER1 TICKER2...       : get quote for specified tickers\n"
    msg += "stonks info TICKER1 TICKER2...  : get company info for specified tickers\n"
    msg += "stonks status TICKER            : watch company (or PORTFOLIO) in bot status\n"
    msg += "stonks chart TICKER TIMESCALE   : draw chart for specified ticker\n"
    msg += "    +---- available timescales  : W (week), M (month), Y (year), F (full)\n\n"
    msg += "\n### Paper Trading ###\n"
    msg += "stonks buy TICKER1 QTY1 TICKER2 QTY2...\n"
    msg += "    +---- buy shares (or add to order queue to execute at market open)\n\n"
    msg += "stonks sell TICKER1 QTY1 TICKER2 QTY2...\n"
    msg += "    +---- sell shares (or add to order queue to execute at market open)\n\n"
    msg += "stonks queue                    : show the current order queue\n"
    msg += "stonks queue remove i           : remove the i'th order from the queue\n"
    msg += "stonks portfolio                : get current holdings information\n"
    msg += "stonks info portfolio           : also get current holdings information\n"
    msg += "stonks chart portfolio          : draw chart of holdings value over time\n"
    msg += "```"

    await message.channel.send(msg)

async def queue_message(message):
    if broker.order_queue:   
        msg = "Order queue: ```\n"
        for i, order in enumerate(broker.order_queue):
            msg += f"{i} ({order[0]}): "
            for ticker in order[1]:
                msg += f"{ticker} x{order[1][ticker]}   "
            msg += "\n"
        msg += "```Use `stonks queue remove i` to remove the `i`th order."
    else:
        msg += "Order queue is empty."
    await message.channel.send(msg)

async def remove_order(idx, message):
    order = broker.remove_order(idx)
    msg =  f"Removed order from the queue:\n"
    msg += f"`{idx} ({order[0]}): "
    for ticker in order[1]:
        msg += f"{ticker} x{order[1][ticker]}   "
    msg += '`\n `stonks queue` to see the updated queue.'
    await message.channel.send(msg)

ticker_status.start()
client.run(TOKEN)