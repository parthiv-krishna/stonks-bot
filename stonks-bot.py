import discord
import os
from dotenv import load_dotenv
import requests

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
FINNHUB_KEY = os.getenv('FINNHUB_KEY')
STONKS_EMOJI = os.getenv('STONKS_EMOJI')
UNSTONKS_EMOJI = os.getenv('UNSTONKS_EMOJI')

client = discord.Client()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('stonks'):
        tokens = message.content.strip().split(' ')
        for token in tokens[1:]:
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
        msg = "Quote for **{symbol}**: ${c:.2f} ({change} {emoji} {percent}%) O: {o:.2f} H: ${h:.2f} L: ${l:.2f} PC: ${pc:.2f}".format(**quote)
    print(msg)
    await message.channel.send(msg)

client.run(TOKEN)