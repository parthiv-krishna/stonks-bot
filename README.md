# stonks-bot
Discord bot with S&amp;P 500 info

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

If all went well, you should see version 3.10 when the venv is activated. Now, install the dependencies with pip.

```bash
python -m pip install -r requirements.txt
```

### 

* Create a bot following [these instructions](https://discordpy.readthedocs.io/en/stable/discord.html#discord-intro).
* Obtain a [Finnhub](https://finnhub.io) API key.
* Update the information in `sample.env`.
