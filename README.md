# stonks-bot
Discord bot with stock quotes, charts, and paper trading. The bot runs on Python 3.10, and makes use of the new `match` structural pattern matching feature.

## Usage

### Installing Python 3.10
Python 3.10 is currently in beta, so it takes a little more work to install. You can follow [these instructions](https://www.python.org/downloads/release/python-3100b4/) to install it. Alternatively, on Ubuntu, you can do the following:

```bash
$ sudo add-apt-repository ppa:deadsnakes/ppa
$ sudo apt update
$ sudo apt install python3.10 python3.10-dev python3.10-distutils python3.10-distutils
```

Now, you can launch Python 3.10 with `python3.10`.

Note: I think this code will work on other platforms, but I have only tested this on Ubuntu 20.04 in Python 3.10.0b4.

### Setting up a virtual environment
To manage dependencies, it is advisable to create a virtual environment. Generally, I prefer to use `conda`, but since `conda` does not support 3.10 yet, we will use the `venv` module built in to python.

```bash
$ python3.10 -m venv .venv
$ source .venv/bin/activate
(.venv) $ python
Python 3.10.0b4 ...
```

If all went well, you should see version 3.10 when the venv is activated. You can exit the Python interpreter by typing `exit()` then enter. Now, install the dependencies with pip.

```bash
python -m pip install -r requirements.txt
```

### Register bot with Discord
Copy `sample.env` into a new file `.env` (or just rename `sample.env` to `.env`). Create a bot following [these instructions](https://discordpy.readthedocs.io/en/stable/discord.html#discord-intro). Finally, update `.env` with your Discord bot key, guild name (server name), and the ID for the channel you'd like `stonks-bot` to track.


### Obtain API keys
Obtain API keys for [Finnhub](https://finnhub.io), [Alpha Vantage](https://www.alphavantage.co/), and [Financial Modeling](https://financialmodelingprep.com/developer/docs). Add these to the `.env` file as well.

### Optional customization
There are some more configuration options in `.env`. 
* You can use custom emojis to react to messages containing "stonks" or "unstonks". If the emojis are standard unicode emojis, you can just replace them in the `.env` directly. If they are custom discord emojis from your server, type `\:emoji-name:` in a channel in your server and press enter to get emoji ID. It should look something like `<:stonks:123456789123456789>`. Paste the entire thing `<:name:id>` into the `.env` file. 
* You can change the ticker that the bot's status tracks. By setting this to `PORTFOLIO`, it will just track the value of the paper trading portfolio. Additionally, you can change the update time (keep this bigger for `PORTFOLIO` to avoid hitting daily rate limits).
* You can enable test mode, which will let you test the "order queue" functionality. Rather than actually checking whether the markets are open before executing a trade or adding it to the queue, it will treat the markets as open when the current minute is even and closed when the current minute is odd.
* Additional options are documented in the `sample.env` file. 