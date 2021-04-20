import discord
from discord.ext.tasks import loop
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
from charts import save_chart

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
FINNHUB_KEY = os.getenv('FINNHUB_KEY')
STONKS_EMOJI = os.getenv('STONKS_EMOJI')
UNSTONKS_EMOJI = os.getenv('UNSTONKS_EMOJI')
STATUS_UPDATE_SECS = int(os.getenv('STATUS_UPDATE_SECS'))

status_ticker = os.getenv('STATUS_TICKER')

client = discord.Client()

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
    
async def ticker_message(ticker, message):
    quote = get_quote(ticker)
    if quote == None:
        msg = f"No information found for ticker **{ticker}**."
    else:
        msg = "**{symbol}**: ${c:.2f} ({change} {emoji} {percent}%) *Open*: {o:.2f} *High*: ${h:.2f} *Low*: ${l:.2f} *Prev. Close*: ${pc:.2f}".format(**quote)
    print("MESSAGE", msg)
    await message.channel.send(msg)

@loop(seconds=STATUS_UPDATE_SECS)
async def ticker_status():
    await client.wait_until_ready()
    quote = get_quote(status_ticker)
    if quote == None:
        stat = f"ERROR: {status_ticker}"
    else:
        stat = "{symbol} ${c:.2f} {percent}%".format(**quote)
    print("STATUS", stat)
    game = discord.Activity(name=stat, type=discord.ActivityType.watching)
    await client.change_presence(status=discord.Status.online, activity=game)
    new_name = "stonks" if quote['c'] > quote['pc'] else "unstonks"
    stonks_channel = client.get_channel(int(os.getenv('STONKS_CHANNEL')))
    await stonks_channel.edit(name=new_name)

async def chart_message(ticker, message):
    async with message.channel.typing():
        save_chart(ticker)
        print("CHART", ticker)
        await message.channel.send(file=discord.File('stonks.jpg'))
        await ticker_message(ticker.upper(), message)

ticker_status.start()
client.run(TOKEN)