from aiohttp import ClientResponseError, ClientSession, ClientTimeout, BasicAuth
from aiohttp_socks import ProxyConnector
from base64 import urlsafe_b64decode
from datetime import datetime
from colorama import Fore, Style, init
import asyncio, random, time, json, sys, re, os

init(autoreset=True)

class Interlink:
    def __init__(self) -> None:
        self.BASE_API = "https://prod.interlinklabs.ai"
        self.VERSION = "5.0.0"

        self.USE_PROXY = False
        self.ROTATE_PROXY = False

        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.accounts = {}

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{Fore.CYAN}[{timestamp}]{Style.RESET_ALL} │ {message}", flush=True)

    def log_success(self, action: str, detail: str = ""):
        self.log(f"{Fore.GREEN}✔ {action}{Style.RESET_ALL}" + (f" → {detail}" if detail else ""))

    def log_failed(self, action: str, error: str = ""):
        self.log(f"{Fore.RED}✘ {action}{Style.RESET_ALL}" + (f" → {Fore.YELLOW}{error}{Style.RESET_ALL}" if error else ""))

    def log_info(self, action: str, detail: str = ""):
        self.log(f"{Fore.CYAN}ℹ {action}{Style.RESET_ALL}" + (f" → {detail}" if detail else ""))

    def welcome(self):
        print(f"""
{Fore.GREEN}{Style.BRIGHT}╔════════════════════════════════════════════════════════════╗
║              INTERLINK LABS AUTO BOT v{self.VERSION}              ║
║                   Developed with ❤️ by BAMAR AIRDROUP GROUP                    ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
        """)

    def mask_account(self, email: str):
        if "@" not in email:
            return email
        local, domain = email.split('@', 1)
        return f"{local[:3]}***{local[-3:]}@{domain}" if len(local) > 6 else f"***@{domain}"

    def generate_device_id(self):
        return os.urandom(8).hex()

    def generate_timestamp(self):
        return str(int(time.time()) * 1000)

    def initialize_headers(self, email: str):
        return {
            "Host": "prod.interlinklabs.ai",
            "Accept": "*/*",
            "Version": self.VERSION,
            "X-Platform": "android",
            "X-Date": self.generate_timestamp(),
            "X-Unique-Id": self.accounts[email]["deviceId"],
            "X-Model": "25053PC47G",
            "X-Brand": "POCO",
            "X-System-Name": "Android",
            "X-Device-Id": self.accounts[email]["deviceId"],
            "X-Bundle-Id": "org.ai.interlinklabs.interlinkId",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "okhttp/4.12.0"
        }

    def print_question(self):
        while True:
            print(f"\n{Fore.WHITE}{Style.BRIGHT}Proxy Mode:{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}1.{Style.RESET_ALL} Run With Proxy")
            print(f"  {Fore.CYAN}2.{Style.RESET_ALL} Run Without Proxy")
            try:
                choice = int(input(f"{Fore.BLUE}Choose (1/2) → {Style.RESET_ALL}").strip())
                if choice in [1, 2]:
                    self.USE_PROXY = (choice == 1)
                    self.log(f"{Fore.GREEN}▶ Mode: {'With Proxy' if self.USE_PROXY else 'Without Proxy'}{Style.RESET_ALL}")
                    break
            except:
                self.log_failed("Input", "Invalid choice")

        if self.USE_PROXY:
            while True:
                rot = input(f"{Fore.BLUE}Rotate proxy on failure? (y/n) → {Style.RESET_ALL}").strip().lower()
                if rot in ['y', 'n']:
                    self.ROTATE_PROXY = (rot == 'y')
                    break

    # ====================== PROXY ======================
    async def load_proxies(self):
        try:
            with open("proxy.txt", "r") as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            if self.proxies:
                self.log(f"{Fore.GREEN}✅ Loaded {len(self.proxies)} proxies{Style.RESET_ALL}")
        except FileNotFoundError:
            self.log_failed("Proxy", "proxy.txt not found")
        except Exception as e:
            self.log_failed("Proxy Load", str(e))

    def check_proxy_schemes(self, proxy):
        if any(proxy.startswith(s) for s in ["http://", "https://", "socks4://", "socks5://"]):
            return proxy
        return f"http://{proxy}"

    def get_next_proxy_for_account(self, email):
        if email not in self.account_proxies and self.proxies:
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[email] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies.get(email)

    def build_proxy_config(self, proxy=None):
        if not proxy:
            return None, None, None
        if proxy.startswith("socks"):
            return ProxyConnector.from_url(proxy), None, None
        if proxy.startswith("http"):
            match = re.match(r"http://(.*):(.*)@(.*)", proxy)
            if match:
                user, pw, host = match.groups()
                return None, f"http://{host}", BasicAuth(user, pw)
            return None, proxy, None
        return None, None, None

    # ====================== UTILITY ======================
    async def ensure_ok(self, response):
        if response.status >= 400:
            raise Exception(f"HTTP {response.status}: {await response.text()}")

    def decode_token(self, email: str):
        try:
            token = self.accounts[email].get("accessToken")
            if not token:
                return None
            _, payload, _ = token.split(".")
            decoded = urlsafe_b64decode(payload + "==").decode("utf-8")
            return json.loads(decoded).get("exp")
        except:
            return None

    # ====================== API CALLS ======================
    async def check_connection(self, proxy_url=None):
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=15)) as session:
                async with session.get("https://api.ipify.org?format=json", proxy=proxy, proxy_auth=auth) as resp:
                    await self.ensure_ok(resp)
                    return True
        except Exception as e:
            self.log_failed("Connection", str(e))
            return False

    async def refresh_token(self, email: str, proxy_url=None):
        url = f"{self.BASE_API}/api/v1/auth/token"
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            headers = self.initialize_headers(email)
            headers["Authorization"] = f"Bearer {self.accounts[email]['accessToken']}"
            headers["Content-Type"] = "application/json"

            async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                async with session.post(url, headers=headers, json={"refreshToken": self.accounts[email]["refreshToken"]}, 
                                      proxy=proxy, proxy_auth=auth) as resp:
                    await self.ensure_ok(resp)
                    data = await resp.json()
                    self.log_success("Token Refresh", "Successful")
                    return data
        except Exception as e:
            self.log_failed("Token Refresh", str(e))
            return None

    async def token_balance(self, email: str, proxy_url=None):
        url = f"{self.BASE_API}/api/v1/token/get-token"
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            headers = self.initialize_headers(email)
            headers["Authorization"] = f"Bearer {self.accounts[email]['accessToken']}"

            async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                async with session.get(url, headers=headers, proxy=proxy, proxy_auth=auth) as resp:
                    await self.ensure_ok(resp)
                    return await resp.json()
        except Exception as e:
            self.log_failed("Fetch Balance", str(e))
            return None

    async def claimable_check(self, email: str, proxy_url=None):
        url = f"{self.BASE_API}/api/v1/token/check-is-claimable"
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            headers = self.initialize_headers(email)
            headers["Authorization"] = f"Bearer {self.accounts[email]['accessToken']}"

            async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                async with session.get(url, headers=headers, proxy=proxy, proxy_auth=auth) as resp:
                    await self.ensure_ok(resp)
                    return await resp.json()
        except Exception as e:
            self.log_failed("Claimable Check", str(e))
            return None

    async def claim_airdrop(self, email: str, proxy_url=None):
        url = f"{self.BASE_API}/api/v1/token/claim-airdrop"
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            headers = self.initialize_headers(email)
            headers["Authorization"] = f"Bearer {self.accounts[email]['accessToken']}"
            headers["Content-Type"] = "application/json"

            async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                async with session.post(url, headers=headers, json={}, proxy=proxy, proxy_auth=auth) as resp:
                    await self.ensure_ok(resp)
                    return await resp.json()
        except Exception as e:
            self.log_failed("Claim Airdrop", str(e))
            return None

    # ====================== PROCESS ======================
    async def process_accounts(self, email: str):
        proxy_url = self.get_next_proxy_for_account(email) if self.USE_PROXY else None

        if self.USE_PROXY:
            self.log_info("Proxy", proxy_url or "None")

        if not await self.check_connection(proxy_url):
            if self.ROTATE_PROXY and self.proxies:
                proxy_url = self.get_next_proxy_for_account(email)
            else:
                return

        # Token Check & Refresh
        exp = self.decode_token(email)
        if not exp or int(time.time()) > exp:
            refreshed = await self.refresh_token(email, proxy_url)
            if refreshed and refreshed.get("data"):
                data = refreshed["data"]
                self.accounts[email]["accessToken"] = data.get("accessToken")
                self.accounts[email]["refreshToken"] = data.get("refreshToken")
                self.save_accounts([self.accounts[email]])

        # Balance
        balance = await self.token_balance(email, proxy_url)
        if balance and balance.get("data"):
            d = balance["data"]
            self.log(f"{Fore.MAGENTA}Balance:{Style.RESET_ALL}")
            self.log(f"   {Fore.BLUE}• Interlink Token :{Style.RESET_ALL} {Fore.WHITE}{d.get('interlinkTokenAmount', 0)}{Style.RESET_ALL}")
            self.log(f"   {Fore.BLUE}• Silver          :{Style.RESET_ALL} {Fore.WHITE}{d.get('interlinkSilverTokenAmount', 0)}{Style.RESET_ALL}")
            self.log(f"   {Fore.BLUE}• Gold            :{Style.RESET_ALL} {Fore.WHITE}{d.get('interlinkGoldTokenAmount', 0)}{Style.RESET_ALL}")
            self.log(f"   {Fore.BLUE}• Diamond         :{Style.RESET_ALL} {Fore.WHITE}{d.get('interlinkDiamondTokenAmount', 0)}{Style.RESET_ALL}")

        # Claim
        claimable = await self.claimable_check(email, proxy_url)
        if claimable and claimable.get("data"):
            if claimable["data"].get("isClaimable"):
                claim = await self.claim_airdrop(email, proxy_url)
                if claim:
                    self.log_success("Mining", f"Claimed! Reward: {claim.get('data', 'N/A')}")
            else:
                next_ts = claimable["data"].get("nextFrame", 0) / 1000
                next_time = datetime.fromtimestamp(next_ts).strftime('%Y-%m-%d %H:%M:%S')
                self.log(f"{Fore.YELLOW}⏳ Already Claimed → Next at: {next_time}{Style.RESET_ALL}")

    def save_accounts(self, new_accounts):
        try:
            filename = "accounts.json"
            existing = []
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    existing = json.load(f)

            acc_dict = {a.get("email"): a for a in existing}
            for acc in new_accounts:
                acc_dict[acc["email"]] = {**acc_dict.get(acc["email"], {}), **acc}

            with open(filename, "w") as f:
                json.dump(list(acc_dict.values()), f, indent=4)
        except Exception as e:
            self.log_failed("Save Accounts", str(e))

    async def main(self):
        try:
            accounts = self.load_accounts() or []
            if not accounts:
                self.log_failed("Load Accounts", "accounts.json is empty or not found")
                return

            self.print_question()
            self.clear_terminal()
            self.welcome()

            while True:
                if self.USE_PROXY:
                    await self.load_proxies()

                self.log(f"{Fore.GREEN}Total Accounts: {Fore.WHITE}{len(accounts)}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'═' * 80}{Style.RESET_ALL}")

                for idx, acc in enumerate(accounts, 1):
                    email = acc.get("email")
                    if not email:
                        continue

                    print(f"\n{Fore.CYAN}╔{'═' * 76}╗{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}ACCOUNT {idx}/{len(accounts)} - {self.mask_account(email)}{Style.RESET_ALL}".ljust(77) + f"{Fore.CYAN}║{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}╚{'═' * 76}╝{Style.RESET_ALL}\n")

                    tokens = acc.get("tokens", {})
                    self.accounts[email] = {
                        "interlinkId": acc.get("interlinkId"),
                        "passcode": acc.get("passcode"),
                        "deviceId": acc.get("deviceId") or self.generate_device_id(),
                        "accessToken": tokens.get("accessToken"),
                        "refreshToken": tokens.get("refreshToken")
                    }

                    await self.process_accounts(email)
                    await asyncio.sleep(random.uniform(2.5, 4.0))

                # Countdown
                self.log_info("Cycle Complete", "Waiting for next round...")
                seconds = 4 * 60 * 60  # 4 hours
                while seconds > 0:
                    print(f"{Fore.CYAN}[ Waiting {self.format_seconds(seconds)} for next cycle... ]{Style.RESET_ALL}", end="\r")
                    await asyncio.sleep(1)
                    seconds -= 1
                print("\n")

        except KeyboardInterrupt:
            print(f"\n{Fore.RED}⏹️  Bot stopped by user.{Style.RESET_ALL}")
        except Exception as e:
            self.log_failed("Main Process", str(e))

    def format_seconds(self, seconds):
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

    def load_accounts(self):
        try:
            if not os.path.exists("accounts.json"):
                self.log_failed("Load", "accounts.json not found")
                return []
            with open("accounts.json", "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            self.log_failed("Load Accounts", str(e))
            return []

if __name__ == "__main__":
    bot = Interlink()
    asyncio.run(bot.main())
