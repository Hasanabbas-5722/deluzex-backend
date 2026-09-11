import logging
import os
import sys
import time
from datetime import datetime

# Ensure Windows console supports UTF-8 and ANSI sequences
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

if sys.platform == "win32":
    try:
        os.system("")
    except Exception:
        pass

# ─── ANSI Palette ───
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

# Text Colors
FG_BLACK = "\033[30m"
FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_MAGENTA = "\033[35m"
FG_CYAN = "\033[36m"
FG_WHITE = "\033[37m"

# Bright Text Colors
FG_BRIGHT_RED = "\033[91m"
FG_BRIGHT_GREEN = "\033[92m"
FG_BRIGHT_YELLOW = "\033[93m"
FG_BRIGHT_BLUE = "\033[94m"
FG_BRIGHT_MAGENTA = "\033[95m"
FG_BRIGHT_CYAN = "\033[96m"
FG_BRIGHT_WHITE = "\033[97m"

# Background Colors
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"

# Gold & Luxury Accents
GOLD = "\033[38;2;196;154;69m"
GOLD_BOLD = "\033[1;38;2;196;154;69m"
EMERALD = "\033[38;2;16;185;129m"
SLATE = "\033[38;2;148;163;184m"

LEVEL_BADGES = {
    logging.DEBUG: f"{BOLD}{FG_MAGENTA}[DEBUG]{RESET}",
    logging.INFO: f"{BOLD}{FG_BRIGHT_CYAN}[INFO]{RESET} ",
    logging.WARNING: f"{BOLD}{FG_BRIGHT_YELLOW}[WARN]{RESET} ",
    logging.ERROR: f"{BOLD}{FG_BRIGHT_RED}[ERROR]{RESET}",
    logging.CRITICAL: f"{BOLD}{BG_RED}{FG_BRIGHT_WHITE}[CRITICAL]{RESET}",
}

class DeluzexColoredFormatter(logging.Formatter):
    """Custom formatter producing clean, colored terminal log output."""
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        time_str = f"{DIM}{SLATE}[{timestamp}]{RESET}"
        level_badge = LEVEL_BADGES.get(record.levelno, f"[{record.levelname}]")
        module_str = f"{DIM}{GOLD}{record.name:<18}{RESET}"
        
        message = record.getMessage()
        if record.levelno >= logging.ERROR:
            message = f"{FG_BRIGHT_RED}{message}{RESET}"
        elif record.levelno == logging.WARNING:
            message = f"{FG_BRIGHT_YELLOW}{message}{RESET}"
            
        formatted = f"{time_str} {level_badge} {module_str} │ {message}"
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        return formatted


def setup_logger(name: str = "deluzex") -> logging.Logger:
    """Configures and returns a custom logger with formatted console output."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(DeluzexColoredFormatter())
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger

app_logger = setup_logger("deluzex.app")


# ─── HTTP Method Badges ───
def format_method(method: str) -> str:
    m = method.upper()
    if m == "GET":
        return f"{BOLD}{FG_BLACK}{BG_GREEN} GET {RESET}"
    elif m == "POST":
        return f"{BOLD}{FG_BRIGHT_WHITE}{BG_BLUE} POST {RESET}"
    elif m in ("PUT", "PATCH"):
        return f"{BOLD}{FG_BLACK}{BG_YELLOW} {m} {RESET}"
    elif m == "DELETE":
        return f"{BOLD}{FG_BRIGHT_WHITE}{BG_RED} DEL {RESET}"
    return f"{BOLD}{FG_BLACK}{BG_WHITE} {m} {RESET}"


# ─── HTTP Status Badges ───
def format_status(status_code: int) -> str:
    if 200 <= status_code < 300:
        return f"{BOLD}{FG_BRIGHT_GREEN}{status_code} OK{RESET}"
    elif 300 <= status_code < 400:
        return f"{BOLD}{FG_BRIGHT_CYAN}{status_code} REDIR{RESET}"
    elif 400 <= status_code < 500:
        return f"{BOLD}{FG_BRIGHT_YELLOW}{status_code} CLIENT ERR{RESET}"
    else:
        return f"{BOLD}{FG_BRIGHT_RED}{status_code} SERVER ERR{RESET}"


# ─── Latency Formatting ───
def format_latency(duration_ms: float) -> str:
    if duration_ms < 50.0:
        return f"{BOLD}{FG_BRIGHT_GREEN}{duration_ms:>6.1f}ms{RESET}"
    elif duration_ms < 250.0:
        return f"{BOLD}{FG_GREEN}{duration_ms:>6.1f}ms{RESET}"
    elif duration_ms < 1000.0:
        return f"{BOLD}{FG_BRIGHT_YELLOW}{duration_ms:>6.1f}ms{RESET}"
    else:
        return f"{BOLD}{FG_BRIGHT_RED}{duration_ms:>6.1f}ms{RESET}"


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    client_ip: str = "-",
    request_id: str = None,
    user_info: str = None
):
    """Produces a clean single-line structured log for an HTTP transaction."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    time_str = f"{DIM}{SLATE}[{timestamp}]{RESET}"
    method_badge = format_method(method)
    status_str = format_status(status_code)
    latency_str = format_latency(duration_ms)
    ip_str = f"{DIM}{client_ip:<15}{RESET}"
    
    id_tag = f" {DIM}#{request_id[:8]}{RESET}" if request_id else ""
    user_tag = f" {GOLD}[{user_info}]{RESET}" if user_info else ""
    
    line = f"{time_str} {method_badge} {BOLD}{path:<32}{RESET} {status_str} │ {latency_str} │ {ip_str}{id_tag}{user_tag}"
    print(line)


def print_startup_banner(
    project_name: str,
    host: str,
    port: int,
    db_connected: bool,
    db_name: str = "",
    db_ping_ms: float = 0.0,
    routes_count: int = 0
):
    """Prints a styled luxury ASCII banner for the Deluzex API server."""
    status_symbol = f"{FG_BRIGHT_GREEN}● ONLINE{RESET}"
    db_symbol = (
        f"{FG_BRIGHT_GREEN}✓ Connected{RESET} {DIM}({db_name}, {db_ping_ms:.1f}ms ping){RESET}"
        if db_connected
        else f"{FG_BRIGHT_RED}✗ Disconnected{RESET}"
    )

    banner = f"""
{GOLD_BOLD}╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ✦  {FG_BRIGHT_WHITE}{project_name:<30}{GOLD_BOLD}                 v1.0.0      ║
║   ✦  {DIM}Luxury Architectural Lighting Backend Service{GOLD_BOLD}                     ║
║                                                                           ║
║   {SLATE}Server Status :{RESET} {status_symbol:<45}    {GOLD_BOLD}║
║   {SLATE}API Gateway   :{RESET} {FG_BRIGHT_CYAN}http://{host}:{port}{RESET:<40}  {GOLD_BOLD}║
║   {SLATE}Documentation :{RESET} {FG_BRIGHT_CYAN}http://{host}:{port}/docs{RESET:<35}  {GOLD_BOLD}║
║   {SLATE}ReDoc View    :{RESET} {FG_BRIGHT_CYAN}http://{host}:{port}/redoc{RESET:<34}  {GOLD_BOLD}║
║   {SLATE}Database      :{RESET} {db_symbol:<45}    {GOLD_BOLD}║
║   {SLATE}Active Routes :{RESET} {FG_BRIGHT_WHITE}{routes_count} endpoints loaded{RESET:<34}  {GOLD_BOLD}║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝{RESET}
"""
    print(banner)
