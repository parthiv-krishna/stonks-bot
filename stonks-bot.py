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

status_ticker = os.getenv('STATUS_TICKER')
pfp_panik = bytearray(open("pfp/panik.jpg", 'rb').read())
pfp_kalm = bytearray(open("pfp/kalm.jpg", 'rb').read())


client = discord.Client()

broker = Broker(FINANCIALMODELING_KEYS)

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not message.content.lower().startswith('stonks'):
        return
    
    tokens = message.content.strip().split(' ')[1:]

    if len(tokens) == 0:
        return

    if tokens[0] == "status":
        global status_ticker
        status_ticker = tokens[1].upper()
        await ticker_status()
        await message.channel.send(f"Updated status to track {status_ticker}.")
        return
    
    if tokens[0] == "chart":
        if len(tokens) < 2:
            await message.channel.send("Please provide a ticker to chart.")
            return
        if len(tokens) > 2:
            await message.channel.send(f"Only charting {tokens[1].upper()}.")
        await chart_message(tokens[1], message)
        return

    if tokens[0] == "info":
        for token in tokens[1:]:
            await info_message(token.upper(), message)
        return

    if tokens[0] == "buy":
        buy_orders = {}
        if len(tokens) % 2 == 0:
            await message.channel.send("Buy format: `stonks buy ABC 1 DEFG 2 H 3`")
            return
        for i in range(1, len(tokens) - 1, 2):
            ticker = tokens[i].upper()
            try:
                count = int(tokens[i+1])
            except:
                await message.channel.send("Buy format: `stonks buy ABC 1 DEFG 2 H 3`")
                return
            buy_orders[ticker] = count
        msgs = broker.buy_stocks(buy_orders)
        for msg in msgs:
            await message.channel.send(msg)
        await message.channel.send(f"Available cash balance: ${broker.balance:.2f}")
        return

    if tokens[0] == "sell":
        sell_orders = {}
        if len(tokens) % 2 == 0:
            await message.channel.send("Sell format: `stonks sell ABC 1 DEFG 2 H 3`")
            return
        for i in range(1, len(tokens) - 1, 2):
            ticker = tokens[i].upper()
            try:
                count = int(tokens[i+1])
            except:
                await message.channel.send("Buy format: `stonks sell ABC 1 DEFG 2 H 3`")
                return
            sell_orders[ticker] = count
        msgs = broker.sell_stocks(sell_orders)
        for msg in msgs:
            await message.channel.send(msg)
        await message.channel.send(f"Available cash balance: ${broker.balance:.2f}")
        return
    
    if tokens[0] == "info":
        for token in tokens[1:]:
            await info_message(token.upper(), message)
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
        msg = "**{symbol}**: ${c:.2f} ({change} {emoji} {percent}%) *Open*: {o:.2f} *High*: ${h:.2f} *Low*: ${l:.2f} *Prev. Close*: ${pc:.2f}".format(**quote)
    print("MESSAGE", msg)
    await message.channel.send(msg)

@loop(seconds=STATUS_UPDATE_SECS)
async def ticker_status():
    if status_ticker == "PORTFOLIO":
        quote = {}
        quote['c'] = broker.get_curr_val()
        quote['symbol'] = ""
        quote['percent'] = 0
        quote['pc'] = 0

    else:
        await client.wait_until_ready()
        quote = get_quote(status_ticker)

    if quote == None:
        stat = f"ERROR: {status_ticker}"
    else:
        stat = "{symbol} ${c:.2f} {percent}%".format(**quote)
    print("STATUS", stat)
    game = discord.Activity(name=stat, type=discord.ActivityType.watching)
    await client.change_presence(status=discord.Status.online, activity=game)
    stonks_channel = client.get_channel(int(os.getenv('STONKS_CHANNEL')))
    new_name = "stonks" if quote['c'] > quote['pc'] else "unstonks"
    if new_name != stonks_channel.name:
        print("Updating channel name to: " + new_name)
        await stonks_channel.edit(name=new_name)
        new_pfp = pfp_kalm if quote['c'] > quote['pc'] else pfp_panik
        await client.user.edit(avatar=new_pfp)
        print("Changing picture")

async def chart_message(ticker, message):
    quote = get_quote(ticker.upper())
    async with message.channel.typing():
        if ticker.upper() == "PORTFOLIO":
            broker.save_chart_of_portfolio_history()
        elif not save_chart(ticker, realtime=quote):
            await(message.channel.send(ticker.upper() + " not found."))
            return
        print("CHART", ticker)
        await message.channel.send(file=discord.File('stonks.jpg'))
        if ticker.upper() == "PORTFOLIO":
            await message.channel.send(f"Portfolio value: ${broker.get_curr_val():.2f}")
        else:
            await ticker_message(ticker.upper(), message, quote=quote)

async def info_message(symbol, message):
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

ticker_status.start()
client.run(TOKEN)