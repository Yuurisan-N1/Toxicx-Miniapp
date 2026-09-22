import asyncio
import html
import json
import os
import re
import signal
import ssl
import sys
import time
import urllib.parse

import aiohttp

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "Toxic X Miniapp"
BASE_URL = "https://app.toxicx.space/api"
REF_CODE = "ref_6004380466"

HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://app.toxicx.space",
    "referer": f"https://app.toxicx.space/index.php?tgWebAppStartParam={REF_CODE}",
    "user-agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
}


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print()
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    text = str(value)
    for symbol in "[]|#!@$%^&*()-":
        text = text.replace(symbol, " ")
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def number_of(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def int_of(value, fallback):
    return int(number_of(value, fallback))


def format_duration(total):
    total = max(0, int(total))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def countdown(seconds):
    for remaining in range(max(0, int(seconds)), 0, -1):
        sys.stdout.write(f"\r{YELLOW}{BOLD}Next cycle starts in {format_duration(remaining)}{RESET}")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write(f"\r{YELLOW}{BOLD}Next cycle starts in {format_duration(0)}{RESET}")
    sys.stdout.flush()
    print()


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def normalize_proxy(raw):
    line = raw.strip()
    if not line:
        return None
    if "://" in line:
        return line
    parts = line.split(":")
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    return None


def load_config():
    if not os.path.isfile("config.json"):
        with open("config.json", "w", encoding="utf-8") as handle:
            json.dump({"settings": {"sleep_seconds": 3600}}, handle, indent=2)
            handle.write("\n")
    try:
        with open("config.json", encoding="utf-8") as handle:
            data = json.load(handle)
        return int(data.get("settings", {}).get("sleep_seconds", 3600))
    except Exception:
        return 3600


def load_accounts():
    if not os.path.isfile("data.txt"):
        return []
    with open("data.txt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    accounts = []
    for line in lines:
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        parts = entry.split("|")
        accounts.append({"init_data": parts[0].strip(), "referral": parts[1].strip() if len(parts) > 1 else ""})
    return accounts


def load_proxies():
    if not os.path.isfile("proxy.txt"):
        return []
    with open("proxy.txt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    proxies = []
    for line in lines:
        normalized = normalize_proxy(line)
        if normalized:
            proxies.append(normalized)
    return proxies


def telegram_id_from(init_data):
    try:
        for chunk in init_data.split("&"):
            if chunk.startswith("user="):
                payload = json.loads(urllib.parse.unquote(chunk[5:]))
                return str(payload.get("id") or "")
    except Exception:
        return ""
    return ""


class ToxicAccount:
    def __init__(self, init_data, referral, proxy_url):
        self.init_data = init_data
        self.referral = referral or REF_CODE
        self.proxy_url = proxy_url
        self.telegram_id = telegram_id_from(init_data)
        self.session = None
        self.connector = None
        self.last_write = 0.0

    async def open(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.connector = aiohttp.TCPConnector(ssl=context)
        self.session = aiohttp.ClientSession(connector=self.connector, headers=HEADERS_BASE,
                                             cookie_jar=aiohttp.CookieJar(unsafe=True))

    async def close(self):
        if self.session is not None:
            await self.session.close()
        if self.connector is not None:
            await self.connector.close()

    async def pace(self):
        gap = 1.5 - (time.monotonic() - self.last_write)
        if gap > 0:
            await asyncio.sleep(gap)
        self.last_write = time.monotonic()

    async def request(self, method, path, payload=None, params=None):
        url = f"{BASE_URL}{path}"
        body_text = None
        if payload is not None:
            body_text = json.dumps(payload, separators=(",", ":"))
        last_error = None
        throttled = False
        if method == "POST":
            await self.pace()
        for attempt in range(4):
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with self.session.request(method, url, data=body_text, params=params,
                                                proxy=self.proxy_url, timeout=timeout) as response:
                    text = (await response.text()).strip()
                    if response.status == 429:
                        throttled = True
                        await asyncio.sleep(30)
                        continue
                    if not text:
                        return response.status, {}
                    try:
                        return response.status, json.loads(text)
                    except json.JSONDecodeError:
                        return response.status, {"_raw": text[:400]}
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(1.5 * (attempt + 1))
        if throttled:
            raise RuntimeError("rate limited")
        raise last_error if last_error else RuntimeError("request failed")

    async def page(self, path):
        url = f"https://app.toxicx.space{path}"
        timeout = aiohttp.ClientTimeout(total=30)
        async with self.session.get(url, proxy=self.proxy_url, timeout=timeout) as response:
            return response.status, await response.text()

    async def get(self, path, params=None):
        return await self.request("GET", path, None, params)

    async def post(self, path, payload=None):
        return await self.request("POST", path, payload if payload is not None else {})

    async def authorize(self):
        status, payload = await self.post("/auth.php",
                                          {"init_data": self.init_data, "referrer_code": self.referral})
        if status != 200 or not isinstance(payload, dict) or not payload.get("success"):
            return {}
        user = payload.get("user") or {}
        if user.get("telegram_id"):
            self.telegram_id = str(user.get("telegram_id"))
        return user

    async def wallet(self):
        status, payload = await self.get("/get_wallet.php", {"telegram_id": self.telegram_id})
        if status == 200 and isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return payload["data"]
        return {}


def task_cards(markup):
    cards = {}
    for block in markup.split("earn-task-card")[1:]:
        chunk = block.split(">", 1)[0]
        found = re.search(r'data-task-id="(\d+)"', chunk)
        if not found:
            continue
        task_id = found.group(1)
        if task_id in cards:
            continue

        def attr(name):
            hit = re.search(rf'data-{name}="([^"]*)"', chunk)
            return hit.group(1) if hit else ""

        cards[task_id] = {
            "id": task_id,
            "name": html.unescape(attr("task-name")),
            "price": attr("task-price"),
            "category": attr("category"),
            "daily_limit": int_of(attr("daily-limit"), 0),
        }
    return cards


def riddle_answer(text):
    tail = str(text or "").split(":")[-1]
    answer = re.sub(r"[^A-Za-z0-9]", "", tail)
    if answer:
        return answer
    words = re.sub(r"[^A-Za-z0-9 ]", " ", str(text or "")).split()
    return words[-1] if words else ""


async def run_daily_bonus(account):
    status, payload = await account.get("/get_daily_bonus_status.php", {"telegram_id": account.telegram_id})
    if status != 200 or not isinstance(payload, dict):
        log_yellow("The daily bonus status could not be read from the server")
        return 0
    if not payload.get("can_claim"):
        wait = format_duration(int_of(payload.get("next_claim_in_seconds"), 0))
        log_yellow(f"The daily bonus is not ready yet and returns in {clean_text(wait, '00:00:00')}")
        return 0
    code, body = await account.post("/claim_daily_bonus.php", {"telegram_id": account.telegram_id})
    if code == 200 and isinstance(body, dict) and body.get("success"):
        amount = number_of(body.get("reward_amount"), 0)
        coin = shorten(body.get("reward_coin") or "TXL", "TXL", 8)
        log_green(f"Daily bonus credited {clean_text(amount, 0)} {clean_text(coin, 'TXL')}")
        return amount
    detail = shorten((body or {}).get("message"), "no reason", 20)
    log_yellow(f"Daily bonus was refused with {clean_text(detail, 'no reason')}")
    return 0


async def run_riddle(account):
    status, payload = await account.get("/get_daily_riddle.php",
                                        {"telegram_id": account.telegram_id, "lang": "en"})
    if status != 200 or not isinstance(payload, dict):
        log_yellow("The daily riddle could not be read from the server")
        return 0
    day = int_of(payload.get("day_number"), 0)
    if payload.get("solved_today"):
        log_green(f"The daily riddle {clean_text(day, 0)} was already solved today")
        return 0
    answer = riddle_answer(payload.get("riddle_text"))
    if not answer:
        log_yellow("The riddle answer could not be derived from the server text")
        return 0
    code, body = await account.post("/submit_daily_riddle.php",
                                    {"telegram_id": account.telegram_id, "answer": answer})
    if code == 200 and isinstance(body, dict) and body.get("success"):
        amount = number_of(body.get("reward"), payload.get("reward_txl"))
        log_green(f"Riddle {clean_text(day, 0)} was solved and {clean_text(amount, 0)} TXL were credited")
        return amount
    detail = shorten((body or {}).get("message"), "no reason", 20)
    log_yellow(f"Riddle {clean_text(day, 0)} was refused with {clean_text(detail, 'no reason')}")
    return 0


async def run_lessons(account):
    status, payload = await account.get("/get_lesson_completions.php", {"telegram_id": account.telegram_id})
    if status != 200 or not isinstance(payload, dict):
        log_yellow("The education lesson list could not be read from the server")
        return 0
    completions = payload.get("completions") or {}
    pending = [key for key, done in completions.items() if not done]
    if not pending:
        log_green("Every education lesson was already completed for this account")
        return 0
    credited = 0
    for lesson_id in sorted(pending, key=lambda value: int_of(value, 0)):
        code, body = await account.post("/complete_lesson.php",
                                        {"lesson_id": int_of(lesson_id, 0), "telegram_id": account.telegram_id})
        if code == 200 and isinstance(body, dict) and body.get("success"):
            amount = number_of(body.get("reward"), 0)
            credited += amount
            log_green(f"Lesson {clean_text(int_of(lesson_id, 0), 0)} was completed and "
                      f"{clean_text(amount, 0)} TXL were credited")
        else:
            detail = shorten((body or {}).get("message"), "no reason", 20)
            log_yellow(f"Lesson {clean_text(int_of(lesson_id, 0), 0)} was refused with "
                       f"{clean_text(detail, 'no reason')}")
    return credited


async def run_tasks(account):
    credited = 0
    status, markup = await account.page("/index.php")
    if status != 200:
        log_yellow("The earn page could not be read from the server")
        return 0
    cards = task_cards(markup)
    if not cards:
        log_yellow("No earn task was listed on the server page")
        return 0
    code, state = await account.get("/get_completed_tasks.php", {"telegram_id": account.telegram_id})
    state = state if code == 200 and isinstance(state, dict) else {}
    completed = {str(item) for item in (state.get("completed_tasks") or [])}
    counts = state.get("daily_counts") or {}
    limits = state.get("daily_limits") or {}
    for task_id in sorted(cards, key=lambda value: int_of(value, 0)):
        card = cards[task_id]
        name = shorten(card.get("name") or task_id, "task", 20)
        limit = int_of(limits.get(task_id), card.get("daily_limit", 0))
        done = int_of(counts.get(task_id), 0)
        if limit > 0:
            if done >= limit:
                log_yellow(f"Task {clean_text(name, 'task')} reached its daily limit")
                continue
        elif task_id in completed:
            log_yellow(f"Task {clean_text(name, 'task')} was already completed earlier")
            continue
        while True:
            code, body = await account.post("/complete_task.php",
                                            {"task_id": int_of(task_id, 0), "telegram_id": account.telegram_id})
            if code != 200 or not isinstance(body, dict) or not body.get("success"):
                detail = shorten((body or {}).get("message"), "no reason", 20)
                log_yellow(f"Task {clean_text(name, 'task')} was refused with {clean_text(detail, 'no reason')}")
                break
            amount = number_of(body.get("reward"), card.get("price"))
            credited += amount
            if body.get("pending"):
                log_yellow(f"Task {clean_text(name, 'task')} was submitted for review")
                break
            log_green(f"Task {clean_text(name, 'task')} credited {clean_text(amount, 0)} TXL")
            if int_of(body.get("remaining_today"), 0) <= 0:
                break
            await asyncio.sleep(1.5)
    return credited


async def run_booster(account):
    status, payload = await account.get("/boosters.php",
                                        {"telegram_id": account.telegram_id, "lang": "en"})
    if status != 200 or not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return 0
    data = payload["data"]
    balance = number_of(data.get("balance"), 0)
    candidates = []
    for group in ("boosters_basic", "boosters_special"):
        for booster in data.get(group) or []:
            if not isinstance(booster, dict):
                continue
            if str(booster.get("pay_token") or "") != "TXL":
                continue
            cost = number_of(booster.get("next_cost") or booster.get("cost"), 0)
            if cost <= 0:
                continue
            candidates.append((cost, booster))
    if not candidates:
        log_yellow("No booster could be bought with TXL on this account")
        return 0
    candidates.sort(key=lambda item: item[0])
    cost, booster = candidates[0]
    if balance < cost * 2:
        log_yellow(f"No booster could be bought with the balance of {clean_text(int_of(balance, 0), 0)} TXL")
        return 0
    name = shorten(re.sub(r"<[^>]+>", " ", html.unescape(str(booster.get("name") or booster.get("id")))),
                   "booster", 16)
    code, body = await account.post("/booster_buy.php",
                                    {"telegram_id": account.telegram_id, "booster_id": int_of(booster.get("id"), 0)})
    if code == 200 and isinstance(body, dict) and body.get("success"):
        log_green(f"Booster {clean_text(name, 'booster')} was upgraded to level "
                  f"{clean_text(int_of(body.get('level'), 0), 0)}")
        return float(cost)
    detail = shorten((body or {}).get("message"), "no reason", 20)
    log_yellow(f"Booster {clean_text(name, 'booster')} was refused with {clean_text(detail, 'no reason')}")
    return 0


async def run_vote(account):
    status, payload = await account.get("/get_tma_center.php", {"telegram_id": account.telegram_id})
    if status != 200 or not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return 0
    data = payload["data"]
    if not data.get("can_vote"):
        log_green("The TMA center vote was already used for this account")
        return 0
    cost = number_of(data.get("vote_cost_txl"), 0)
    balance = number_of(data.get("coin_txl"), 0)
    for app in data.get("apps") or []:
        if not isinstance(app, dict) or app.get("user_voted_this"):
            continue
        if cost <= 0 or balance < cost:
            log_yellow(f"No TMA center vote could be funded with "
                       f"{clean_text(int_of(balance, 0), 0)} TXL")
            return 0
        name = shorten(app.get("apps_name") or app.get("id"), "app", 20)
        code, body = await account.post("/tma_center_vote.php", {"app_id": int_of(app.get("id"), 0)})
        if code == 200 and isinstance(body, dict) and body.get("success"):
            spent = number_of((body.get("data") or {}).get("vote_cost"), cost)
            log_yellow(f"A vote for {clean_text(name, 'app')} was accepted and cost "
                       f"{clean_text(int_of(spent, 0), 0)} TXL")
        else:
            detail = shorten((body or {}).get("message"), "no reason", 20)
            log_yellow(f"A vote for {clean_text(name, 'app')} was refused with {clean_text(detail, 'no reason')}")
        return 1
    log_green("No TMA center vote was open for this account")
    return 0


async def run_roulette(account):
    status, payload = await account.get("/roulette_config.php", {"telegram_id": account.telegram_id})
    if status != 200 or not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return 0
    data = payload["data"]
    if not data.get("free_spin_available"):
        wait = format_duration(int_of(data.get("free_spin_cooldown_sec"), 0))
        log_yellow(f"The roulette free spin returns in {clean_text(wait, '00:00:00')}")
        return 0
    tiers = data.get("stake_tiers") or [0]
    code, body = await account.post("/roulette_spin.php", {"telegram_id": account.telegram_id,
                                                          "use_free_spin": True,
                                                          "stake": number_of(tiers[0], 0),
                                                          "multiplier": 1})
    if code == 200 and isinstance(body, dict) and body.get("success"):
        reward = (body.get("data") or {}).get("reward") or {}
        amount = number_of(reward.get("amount"), 0)
        coin = shorten(reward.get("reward_code") or reward.get("display_name") or "TXL", "TXL", 8)
        log_green(f"The roulette free spin credited {clean_text(amount, 0)} {clean_text(coin, 'TXL')}")
        return amount
    detail = shorten((body or {}).get("message"), "no reason", 20)
    log_yellow(f"The roulette free spin was refused with {clean_text(detail, 'no reason')}")
    return 0


async def run_match_three(account):
    status, payload = await account.get("/match3_config.php", {"telegram_id": account.telegram_id})
    if status != 200 or not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return 0
    data = payload["data"]
    wait = int_of(data.get("cooldown_remaining"), 0)
    if wait > 0:
        log_yellow(f"Match three is on cooldown for {clean_text(format_duration(wait), '00:00:00')}")
        return 0
    code, start = await account.post("/match3_start.php", {"telegram_id": account.telegram_id})
    if code != 200 or not isinstance(start, dict) or not start.get("session_token"):
        detail = shorten((start or {}).get("message"), "no reason", 20)
        log_yellow(f"Match three could not be started and returned {clean_text(detail, 'no reason')}")
        return 0
    await asyncio.sleep(20)
    detail = "no reason"
    for attempt in range(2):
        code, body = await account.post("/match3_claim.php", {"telegram_id": account.telegram_id,
                                                             "score": 300,
                                                             "game_id": int_of(data.get("game_id"), 0),
                                                             "session_token": start.get("session_token")})
        reason = str((body or {}).get("message") or "")
        if code == 200 and isinstance(body, dict) and body.get("success"):
            reward = body.get("data") or {}
            coins = number_of(reward.get("reward_txl"), 0)
            shares = number_of(reward.get("reward_txinv"), 0)
            log_green(f"Match three credited {clean_text(coins, 0)} TXL and {clean_text(shares, 0)} TXINV")
            return coins
        if "claimed" in reason.lower():
            coins = number_of(data.get("initial_reward_txl"), 0)
            shares = number_of(data.get("initial_reward_txinv"), 0)
            log_green(f"Match three credited {clean_text(coins, 0)} TXL and {clean_text(shares, 0)} TXINV")
            return coins
        detail = shorten(reason, "no reason", 20)
        if attempt == 0:
            log_yellow(f"Match three claim is retried after {clean_text(detail, 'no reason')}")
            await asyncio.sleep(25)
    log_yellow(f"Match three was refused with {clean_text(detail, 'no reason')}")
    return 0


async def run_challenges(account):
    status, payload = await account.get("/daily_challenges.php", {"lang": "en"})
    if status != 200 or not isinstance(payload, dict):
        return 0
    credited = 0
    claimed_any = False
    for challenge in payload.get("challenges") or []:
        if not isinstance(challenge, dict) or challenge.get("claimed"):
            continue
        title = shorten(challenge.get("title") or challenge.get("quest_key"), "quest", 20)
        if not challenge.get("ready"):
            log_yellow(f"Challenge {clean_text(title, 'quest')} is still in progress")
            continue
        code, body = await account.post("/daily_challenges.php", {"quest_key": challenge.get("quest_key")})
        if code == 200 and isinstance(body, dict) and body.get("success"):
            amount = number_of(body.get("reward"), challenge.get("reward_txl"))
            credited += amount
            claimed_any = True
            log_green(f"Challenge {clean_text(title, 'quest')} was claimed for {clean_text(amount, 0)} TXL")
        else:
            detail = shorten((body or {}).get("message"), "no reason", 20)
            log_yellow(f"Challenge {clean_text(title, 'quest')} was refused with {clean_text(detail, 'no reason')}")
    if not credited and not claimed_any:
        log_yellow("No daily challenge was ready to be claimed on this run")
    return credited


async def run_account(entry, proxy_url):
    account = ToxicAccount(entry["init_data"], entry["referral"], proxy_url)
    await account.open()
    try:
        user = await account.authorize()
        if not user:
            log_red("The account could not be authorized by the server")
            return None
        label = shorten(user.get("username") or user.get("first_name") or account.telegram_id, "account", 20)
        wallet = await account.wallet()
        start_balance = number_of(wallet.get("coin_txl"), 0)
        if proxy_url is not None:
            log_yellow(f"Using proxy {mask_proxy(proxy_url)}")
        log_green(f"Account {clean_text(label, 'account')} started with "
                  f"{clean_text(int_of(start_balance, 0), 0)} TXL")
        await run_daily_bonus(account)
        await run_riddle(account)
        await run_lessons(account)
        await run_tasks(account)
        await run_booster(account)
        await run_vote(account)
        await run_roulette(account)
        await run_match_three(account)
        await run_challenges(account)
        end_balance = number_of((await account.wallet()).get("coin_txl"), start_balance)
        if end_balance >= start_balance:
            log_green(f"Cycle closed with a balance of {clean_text(int_of(end_balance, 0), 0)} TXL")
        else:
            log_yellow(f"Cycle closed with a balance of {clean_text(int_of(end_balance, 0), 0)} TXL")
        return end_balance
    finally:
        await account.close()


async def main():
    show_banner(MY_PROJECT)
    sleep_seconds = load_config()
    accounts = load_accounts()
    proxies = load_proxies()
    if not accounts:
        log_red("No account was found in data.txt")
        sys.exit(1)
    cycle = 0
    while True:
        cycle += 1
        log_green(f"Starting automation cycle number {clean_text(cycle, 0)}")
        for idx, entry in enumerate(accounts):
            if idx > 0:
                print()
            proxy_url = proxies[idx % len(proxies)] if proxies else None
            try:
                await run_account(entry, proxy_url)
            except Exception as exc:
                log_red(f"Request to the server failed with {clean_text(type(exc).__name__, 'error')}")
        countdown(sleep_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        signal_handler(None, None)
