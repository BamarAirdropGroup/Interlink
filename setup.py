from aiohttp import ClientResponseError, ClientSession, ClientTimeout, BasicAuth
from aiohttp_socks import ProxyConnector
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

    def log_success(self, action: str, message: str = ""):
        self.log(f"{Fore.GREEN}✔ SUCCESS{Style.RESET_ALL} | {Fore.WHITE}{action}{Style.RESET_ALL}" + 
                 (f" → {Fore.LIGHTGREEN_EX}{message}{Style.RESET_ALL}" if message else ""))

    def log_failed(self, action: str, error: str = ""):
        self.log(f"{Fore.RED}✘ FAILED{Style.RESET_ALL}  | {Fore.WHITE}{action}{Style.RESET_ALL}" + 
                 (f" → {Fore.YELLOW}{error}{Style.RESET_ALL}" if error else ""))

    def log_retry(self, action: str, attempt: int, max_retries: int):
        self.log(f"{Fore.YELLOW}⟳ RETRYING{Style.RESET_ALL} | {Fore.WHITE}{action}{Style.RESET_ALL} {Fore.CYAN}(Attempt {attempt}/{max_retries}){Style.RESET_ALL}")

    def welcome(self):
        print(f"""
{Fore.GREEN}{Style.BRIGHT}╔════════════════════════════════════════════════════════════╗
║               INTERLINK LABS AUTO BOT v{self.VERSION}               ║
║                   Developed with ❤️ by BAMAR AIRDROP GROUP                    ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
        """)

    def mask_account(self, email: str):
        if "@" not in email: return email
        local, domain = email.split('@', 1)
        return f"{local[:3]}***{local[-3:]}@{domain}" if len(local) > 6 else f"***@{domain}"

    def generate_device_id(self):
        return os.urandom(8).hex()

    def initialize_headers(self, email: str):
        return {
            "Host": "prod.interlinklabs.ai",
            "Accept": "*/*",
            "Version": self.VERSION,
            "X-Platform": "android",
            "X-Date": str(int(time.time()) * 1000),
            "X-Unique-Id": self.accounts[email]["deviceId"],
            "X-Model": "25053PC47G",
            "X-Brand": "POCO",
            "X-System-Name": "Android",
            "X-Device-Id": self.accounts[email]["deviceId"],
            "X-Bundle-Id": "org.ai.interlinklabs.interlinkId",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "okhttp/4.12.0",
            "Content-Type": "application/json"
        }

    def print_question(self):
        while True:
            print(f"\n{Fore.WHITE}{Style.BRIGHT}Choose Proxy Mode:{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}1.{Style.RESET_ALL} Run With Proxy")
            print(f"  {Fore.CYAN}2.{Style.RESET_ALL} Run Without Proxy")
            try:
                choice = int(input(f"\n{Fore.BLUE}Enter choice (1/2) → {Style.RESET_ALL}").strip())
                if choice in [1, 2]:
                    self.USE_PROXY = (choice == 1)
                    self.log(f"{Fore.GREEN}▶ Mode Selected: {Fore.WHITE}{'With Proxy' if self.USE_PROXY else 'Without Proxy'}{Style.RESET_ALL}")
                    break
            except:
                self.log(f"{Fore.RED}Please enter 1 or 2 only!{Style.RESET_ALL}")

        if self.USE_PROXY:
            while True:
                rot = input(f"{Fore.BLUE}Rotate proxy when failed? (y/n) → {Style.RESET_ALL}").strip().lower()
                if rot in ['y', 'n']:
                    self.ROTATE_PROXY = (rot == 'y')
                    break

    # ====================== PROXY FUNCTIONS ======================
    async def load_proxies(self):
        try:
            with open("proxy.txt", 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            if self.proxies:
                self.log(f"{Fore.GREEN}✅ Loaded {len(self.proxies)} proxies{Style.RESET_ALL}")
        except FileNotFoundError:
            self.log(f"{Fore.RED}❌ proxy.txt not found!{Style.RESET_ALL}")
        except Exception as e:
            self.log(f"{Fore.RED}❌ Failed to load proxies: {e}{Style.RESET_ALL}")

    def check_proxy_schemes(self, proxy):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        return proxy if any(proxy.startswith(s) for s in schemes) else f"http://{proxy}"

    def get_next_proxy_for_account(self, email):
        if email not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[email] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[email]

    def build_proxy_config(self, proxy_url=None):
        if not proxy_url:
            return None, None, None
        if proxy_url.startswith("socks"):
            return ProxyConnector.from_url(proxy_url), None, None
        elif proxy_url.startswith("http"):
            match = re.match(r"http://(.*):(.*)@(.*)", proxy_url)
            if match:
                user, pw, host = match.groups()
                return None, f"http://{host}", BasicAuth(user, pw)
            return None, proxy_url, None
        return None, None, None

    # ====================== API FUNCTIONS ======================
    async def ensure_ok(self, response):
        if response.status >= 400:
            text = await response.text()
            raise Exception(f"HTTP {response.status}: {text[:200]}")

    async def check_connection(self, proxy_url=None):
        url = "https://api.ipify.org?format=json"
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=15)) as session:
                async with session.get(url, proxy=proxy, proxy_auth=auth) as resp:
                    await self.ensure_ok(resp)
                    self.log_success("Connection Check", "Proxy / Internet is working")
                    return True
        except Exception as e:
            self.log_failed("Connection Check", str(e))
            return False

    async def request_otp(self, email: str, proxy_url=None, retries=3):
        url = f"{self.BASE_API}/api/v1/auth/send-otp-email-verify-login"
        for attempt in range(1, retries + 1):
            try:
                connector, proxy, auth = self.build_proxy_config(proxy_url)
                headers = self.initialize_headers(email)
                payload = {
                    "loginId": self.accounts[email]["interlinkId"],
                    "passcode": self.accounts[email]["passcode"],
                    "email": email,
                    "deviceId": self.accounts[email]["deviceId"]
                }
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url, headers=headers, json=payload, proxy=proxy, proxy_auth=auth) as resp:
                        await self.ensure_ok(resp)
                        self.log_success("Request OTP", "OTP sent to email")
                        return True
            except Exception as e:
                if attempt < retries:
                    self.log_retry("Request OTP", attempt, retries)
                    await asyncio.sleep(5)
                else:
                    self.log_failed("Request OTP", str(e))
                    return False

    async def verify_otp(self, email: str, otp_code: str, proxy_url=None, retries=3):
        url = f"{self.BASE_API}/api/v1/auth/check-otp-email-verify-login?v=2"
        for attempt in range(1, retries + 1):
            try:
                connector, proxy, auth = self.build_proxy_config(proxy_url)
                headers = self.initialize_headers(email)
                payload = {
                    "loginId": self.accounts[email]["interlinkId"],
                    "otp": otp_code,
                    "deviceId": self.accounts[email]["deviceId"]
                }
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url, headers=headers, json=payload, proxy=proxy, proxy_auth=auth) as resp:
                        await self.ensure_ok(resp)
                        data = await resp.json()
                        self.log_success("Verify OTP", "OTP verified successfully")
                        return data
            except Exception as e:
                if attempt < retries:
                    self.log_retry("Verify OTP", attempt, retries)
                    await asyncio.sleep(5)
                else:
                    self.log_failed("Verify OTP", str(e))
                    return None

    # ====================== MAIN PROCESS ======================
    async def process_accounts(self, email: str):
        proxy_url = self.get_next_proxy_for_account(email) if self.USE_PROXY else None

        if self.USE_PROXY:
            self.log(f"{Fore.MAGENTA}Proxy : {Fore.WHITE}{proxy_url or 'None'}{Style.RESET_ALL}")

        # Check Connection
        if not await self.check_connection(proxy_url):
            if self.ROTATE_PROXY and self.proxies:
                self.log(f"{Fore.YELLOW}Rotating proxy...{Style.RESET_ALL}")
                proxy_url = self.get_next_proxy_for_account(email)  # rotate
            else:
                self.log_failed("Process Account", "Connection failed")
                return

        # Request OTP
        if not await self.request_otp(email, proxy_url):
            return

        # Input OTP
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        otp_code = input(f"{Fore.CYAN}[{timestamp}]{Style.RESET_ALL} │ {Fore.BLUE}Enter OTP Code → {Style.RESET_ALL}")

        # Verify OTP
        result = await self.verify_otp(email, otp_code, proxy_url)
        if not result:
            return

        # Save Tokens
        access_token = result.get("data", {}).get("accessToken")
        refresh_token = result.get("data", {}).get("refreshToken")

        account_data = [{
            "email": email,
            "interlinkId": self.accounts[email]["interlinkId"],
            "passcode": self.accounts[email]["passcode"],
            "deviceId": self.accounts[email]["deviceId"],
            "tokens": {
                "accessToken": access_token,
                "refreshToken": refresh_token
            }
        }]

        self.save_accounts(account_data)
        self.log_success("Process Account", f"Account {self.mask_account(email)} completed successfully!")

    def save_accounts(self, new_accounts):
        try:
            filename = "accounts.json"
            existing = []
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    existing = json.load(f)

            account_dict = {acc.get("email"): acc for acc in existing}
            for acc in new_accounts:
                account_dict[acc["email"]] = {**account_dict.get(acc["email"], {}), **acc}

            with open(filename, 'w') as f:
                json.dump(list(account_dict.values()), f, indent=4)

            self.log_success("Save Accounts", "Tokens saved successfully")
        except Exception as e:
            self.log_failed("Save Accounts", str(e))

    async def main(self):
        try:
            accounts = []
            if os.path.exists("accounts.json"):
                with open("accounts.json", 'r') as f:
                    accounts = json.load(f)

            if not accounts:
                self.log(f"{Fore.RED}No accounts found in accounts.json{Style.RESET_ALL}")
                return

            self.print_question()
            self.clear_terminal()
            self.welcome()

            if self.USE_PROXY:
                await self.load_proxies()

            print(f"\n{Fore.CYAN}{'═' * 75}{Style.RESET_ALL}")

            for idx, acc in enumerate(accounts, 1):
                email = acc.get("email")
                if not email:
                    continue

                print(f"\n{Fore.CYAN}╔{'═' * 73}╗{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}ACCOUNT {idx}/{len(accounts)} — {self.mask_account(email)}{Style.RESET_ALL}".ljust(74) + f"{Fore.CYAN}║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}╚{'═' * 73}╝{Style.RESET_ALL}\n")

                if email not in self.accounts:
                    self.accounts[email] = {
                        "interlinkId": acc.get("interlinkId"),
                        "passcode": acc.get("passcode"),
                        "deviceId": acc.get("deviceId") or self.generate_device_id()
                    }

                await self.process_accounts(email)
                await asyncio.sleep(random.uniform(2.5, 4.0))

        except Exception as e:
            self.log_failed("Main Process", str(e))
        except KeyboardInterrupt:
            print(f"\n\n{Fore.RED}⏹️  Bot stopped by user.{Style.RESET_ALL}")

if __name__ == "__main__":
    bot = Interlink()
    asyncio.run(bot.main())
