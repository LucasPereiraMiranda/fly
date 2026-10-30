<h1 align="center">
  <br/>

  fly ✈️
</h1>

<p align="center">
  <img alt="GitHub language count" src="https://img.shields.io/github/languages/count/LucasPereiraMiranda/fly">

  <img alt="Repository size" src="https://img.shields.io/github/repo-size/LucasPereiraMiranda/fly">

  <a href="https://github.com/LucasPereiraMiranda/fly/commits/main">
    <img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/LucasPereiraMiranda/fly">
  </a>

  <a href="https://github.com/LucasPereiraMiranda/fly/issues">
    <img alt="Repository issues" src="https://img.shields.io/github/issues/LucasPereiraMiranda/fly">
  </a>

  <a href="https://github.com/LucasPereiraMiranda/fly/blob/main/LICENSE">
    <img alt="GitHub license" src="https://img.shields.io/github/license/LucasPereiraMiranda/fly">
  </a>
</p>

<br>


## 🚀 Techs

fly was developed with these technologies

- [Python 3.12](https://www.python.org/)
- [httpx](https://www.python-httpx.org/)
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)
- [SQLite](https://www.sqlite.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [pytest](https://docs.pytest.org/)

## 💻 Project

I have miles, I live in Belo Horizonte and I'm always up for a trip, as long as the deal is really worth it. Once I found a flight to Maceió for 8 thousand miles when it usually costs 30 to 40 thousand, and that's exactly the kind of deal I don't want to miss again.

fly does the boring part for me. It keeps an eye on flight deal blogs, picks the ones departing from Belo Horizonte to places I'd like to go, checks if the price is really far below the usual and sends me a message on Telegram when it is. Everything else goes into a short daily summary, so I can take a look over coffee.

It runs quietly on my Mac, every 30 minutes, without opening anything.

## :boom: Installation

```bash
# clone this repo
$ git clone git@github.com:LucasPereiraMiranda/fly.git
$ cd fly

# create a virtual environment with python 3.12
$ python3.12 -m venv .venv

# install dependencies
$ .venv/bin/pip install -e ".[dev]"

# add your Telegram bot token and chat id
$ cp .env.example .env

# look for new deals right now
$ .venv/bin/python -m fly run

# send the daily summary
$ .venv/bin/python -m fly digest

# run the tests
$ .venv/bin/pytest

```

### Running on a schedule (macOS)

```bash
# check for deals every 30 minutes and send the summary every day at 9am
$ scripts/install_launchd.sh

```

Want to tweak what counts as a good deal? Destinations live in `config/destinations.toml` and the usual price of each region in `config/seeds.toml`.

## License

This project is under the MIT license. See the [LICENSE](LICENSE) file for more details.
