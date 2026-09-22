<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Toxic%20X%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Daily%20Bonus%7CRiddle%7CLessons%7CEarn%20Tasks%7CMining&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Daily%20bonus%20claim;Daily%20riddle%20solver;Education%20lessons;Earn%20task%20runner;Booster%20mining%20management"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-Toxic%20X%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>Toxic X Bot</b> is a full automation bot for the Toxic X Telegram Miniapp.<br/>
  It handles the complete daily cycle: daily bonus, daily riddle, education lessons, the earn task board, booster mining, TMA center voting, the roulette free spin, Match Three and the daily challenges, all running automatically across multiple accounts with a cached coin balance read, proxy support, and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Toxicx-Miniapp.git
cd Toxicx-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening Toxic X on Telegram Web.

An optional `|referrer_code` suffix is tolerated, because the sign-up referral is only used on the very first authorization of an account.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Daily Bonus
Reads the bonus status for the account. When a claim is open the bot settles it and logs the coin and the amount the server credited; when the bonus is still on timer it logs the remaining wait instead of touching it.

### Daily Riddle
Reads the riddle of the day and derives the answer from the clue text the server returns. Solved riddles are settled once and the credited amount is logged; when the riddle was already solved the bot reports that and moves on.

### Education Lessons
Reads the lesson completion list and settles every lesson that is still open, logging the reward of each one. Lessons that were already finished are reported as completed instead of being retried.

### Earn Tasks
Reads the earn board and the per task progress held by the server, then settles every task that still has room left today, including the ad missions and the partner missions. Each task is logged with its own outcome, so a credited task, a task that reached its daily limit, a task sent for review, and a task the server refused are all visible as separate lines.

### Booster Mining
Reads the booster list and buys the cheapest upgrade that can be paid with the mined coin, always keeping a reserve so the account is never drained. Boosters that are priced in a real deposit token are never touched by this bot.

### TMA Center
Places the daily vote for a listed partner app when the account is still allowed to vote and the mined coin balance covers the vote cost, and logs the cost that was charged. When the vote for the day was already used the bot reports that instead of spending again.

### Roulette Free Spin
Reads the roulette status and spins the free spin as soon as it is off cooldown, logging the reward the server returned. Paid spins are never placed by the bot; when the free spin is not ready the remaining cooldown is logged.

### Match Three
Plays the hourly Match Three round once the cooldown is over and logs the coin and share rewards the server credited. While the cooldown is still running the remaining time is logged.

### Daily Challenges
Reads the challenge board and claims every challenge whose progress is already complete, logging the reward of each one. Challenges that are still in progress are reported as such.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Each account is logged with its profile name and its opening and closing coin balance. The cycle number is tracked and logged at the start of each round.

### Proxy Support
Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
ToxicX-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    ├── banner.py   # Banner using yuurisan module
    └── __init__.py # Package marker
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>