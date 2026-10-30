<h1 align="center">
  <br/>

  fly ✈️
</h1>

<p align="center">
  <a href="https://github.com/LucasPereiraMiranda/fly/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/LucasPereiraMiranda/fly/actions/workflows/ci.yml/badge.svg?branch=main">
  </a>

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

fly monitors flight deals departing from Belo Horizonte, in miles and in cash.

It keeps an eye on flight deal blogs, picks the deals for the destinations of interest and checks whether the price is really far below the usual for that route. When it is, a message arrives on Telegram right away. The other interesting deals go into a short daily summary.

It runs in the background on macOS, every 30 minutes.

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
