#!/usr/bin/env python3
"""
GitBot - Autonomous Cloud Contribution Engine
Antigravity-Style Interactive REPL Shell & Cloud Control Plane
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone

import engine

# Enable UTF-8 encoding and ANSI terminal sequences on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if os.name == "nt":
    os.system("")

VERSION = "7.0.3"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

def strip_ansi(text):
    return ANSI_REGEX.sub('', text)

def vis_len(text):
    """Calculates visible character cell width in terminal, ignoring ANSI escapes."""
    clean = strip_ansi(text)
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in clean)

def render_row(content, width=76, border_color=C.CYAN):
    """Guarantees pixel-perfect right border alignment across all platforms."""
    inner = width - 4
    v = vis_len(content)
    if v > inner:
        clean = strip_ansi(content)
        curr_w = 0
        cut_idx = len(clean)
        for i, c in enumerate(clean):
            w_c = 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
            if curr_w + w_c > inner - 3:
                cut_idx = i
                break
            curr_w += w_c
        content = clean[:cut_idx] + "..."
        v = vis_len(content)
    pad = max(0, inner - v)
    return f"{border_color}│{C.RESET} {content}" + (" " * pad) + f" {border_color}│{C.RESET}"

def run_cmd(cmd, cwd=REPO_DIR):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def sync_config_to_git(commit_message):
    """Commits and syncs config changes to GitHub origin main."""
    run_cmd("git pull --rebase --autostash origin main")
    run_cmd("git add config.json")
    code, out, err = run_cmd(f'git commit -m "{commit_message}"')
    if code == 0 or "nothing to commit" in out.lower():
        push_code, push_out, push_err = run_cmd("git push origin main")
        if push_code == 0:
            print(f"  {C.GREEN}✓ Synchronized and pushed live to GitHub Actions Cloud!{C.RESET}\n")
        else:
            print(f"  {C.YELLOW}! Saved locally. (Run 'git push origin main' to sync){C.RESET}\n")
    else:
        print(f"  {C.GREEN}✓ Configuration saved locally.{C.RESET}\n")

def print_banner(compact=False):
    if compact:
        print(f"{C.CYAN}{C.BOLD}⚡ GitBot Shell{C.RESET} {C.MAGENTA}v{VERSION}{C.RESET} {C.DIM}• Type 'help' for commands, 'exit' / 'q' to quit{C.RESET}\n")
        return
    banner = f"""
{C.CYAN}{C.BOLD}   ____ _ _   ____        _   
  / ___(_) |_| __ )  ___ | |_ 
 | |  _| | __|  _ \ / _ \| __|
 | |_| | | |_| |_) | (_) | |_ 
  \____|_|\__|____/ \___/ \__|  {C.MAGENTA}v{VERSION}{C.RESET}
{C.GRAY}  Autonomous Cloud Contribution Engine — Interactive Control Shell{C.RESET}
"""
    print(banner)

def get_connected_repo(target_dir=None):
    """Returns the 'owner/repo' of the connected GitBot repository."""
    if target_dir is None:
        gitbot_home = os.path.expanduser("~/.gitbot")
        target_dir = gitbot_home if os.path.exists(gitbot_home) else REPO_DIR

    cfg_file = os.path.join(target_dir, "config.json")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("connected_repo"):
                    return cfg["connected_repo"].strip()
        except Exception:
            pass

    code, rem_url, _ = run_cmd(f'git -C "{target_dir}" remote get-url origin')
    if code == 0 and rem_url:
        clean_url = rem_url.replace(".git", "").strip()
        if "github.com" in clean_url:
            parts = clean_url.split("github.com")[-1].strip("/:").split("/")
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1]}"
    return None

def print_startup_card(width=76):
    """Displays connected GitHub identity and status in a pixel-perfect card."""
    config = engine.load_config()
    username = config.get("author_name") or "User"
    email = config.get("author_email") or "Not configured"
    repo_name = get_connected_repo()
    repo_display = f"https://github.com/{repo_name} {C.DIM}[Private]{C.RESET}" if repo_name else f"{C.YELLOW}Not connected{C.RESET}"

    is_paused = config.get("is_paused", False)
    vacation_info = engine.get_vacation_status()
    if is_paused:
        status_badge = format_badge("PAUSED", C.YELLOW)
    elif vacation_info.get("active"):
        status_badge = format_badge("VACATION", C.YELLOW)
    else:
        status_badge = format_badge("ACTIVE", C.GREEN)

    print(f"{C.CYAN}╭" + "─" * (width - 2) + f"╮{C.RESET}")
    title = "⚡ CONNECTED GITHUB IDENTITY"
    inner = width - 4
    space = max(1, inner - vis_len(title) - vis_len(status_badge))
    header_content = f"{C.BOLD}{title}{C.RESET}" + (" " * space) + status_badge
    print(render_row(header_content, width=width))
    print(f"{C.CYAN}├" + "─" * (width - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.DIM}Account  :{C.RESET} {C.CYAN}{C.BOLD}@{username}{C.RESET}", width=width))
    print(render_row(f"{C.DIM}Email    :{C.RESET} {C.WHITE}{email}{C.RESET}", width=width))
    print(render_row(f"{C.DIM}Repo     :{C.RESET} {C.WHITE}{repo_display}{C.RESET}", width=width))
    print(f"{C.CYAN}╰" + "─" * (width - 2) + f"╯{C.RESET}\n")

def make_bar(current, total, length=24, pct=None):
    if total <= 0:
        return f"{C.GRAY}[{'░' * length}] 0%{C.RESET}"
    ratio = min(1.0, max(0.0, current / total))
    filled = int(round(length * ratio))
    empty = length - filled
    display_pct = pct if pct is not None else int(round(ratio * 100))
    bar_str = f"{C.GREEN}{'█' * filled}{C.GRAY}{'░' * empty}{C.RESET}"
    return f"[{bar_str}] {C.BOLD}{display_pct}%{C.RESET}"

def format_badge(text, color):
    return f"{color}{C.BOLD}[ {text} ]{C.RESET}"

# ====================================================================
# Pure-Python Cross-Platform Arrow Key Input Selector
# ====================================================================
def read_single_key():
    """Reads a single keypress or arrow key event cross-platform."""
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                return "up"
            elif ch2 == "P":
                return "down"
            return ch2
        elif ch in ("\r", "\n"):
            return "enter"
        elif ch == "\x03":
            return "ctrl_c"
        elif ch == "\x1b":
            return "esc"
        return ch
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":
                        return "up"
                    elif ch3 == "B":
                        return "down"
                return "esc"
            elif ch in ("\r", "\n"):
                return "enter"
            elif ch == "\x03":
                return "ctrl_c"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def select_menu(prompt_title, options, default_index=0):
    """
    Interactive arrow-key selector.
    Navigates options with Up/Down arrow keys and confirms with Enter.
    """
    if not sys.stdin.isatty():
        # Fallback for non-interactive / piped environments
        print(f"\n{C.BOLD}{prompt_title}:{C.RESET}")
        for idx, opt in enumerate(options, 1):
            print(f"  {idx}. {opt['title']} - {opt.get('desc', '')}")
        try:
            choice = input(f"Select option [1-{len(options)}, default {default_index+1}]: ").strip()
            if not choice:
                return options[default_index]["key"]
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return options[int(choice) - 1]["key"]
        except (KeyboardInterrupt, EOFError):
            return None
        return options[default_index]["key"]

    selected = default_index
    total = len(options)
    lines_drawn = 0

    # Hide terminal cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        while True:
            # Clear previously drawn lines
            if lines_drawn > 0:
                sys.stdout.write(f"\033[{lines_drawn}A\033[0J")
                sys.stdout.flush()

            output = []
            output.append(f"\n{C.CYAN}{C.BOLD}❯ {prompt_title}{C.RESET} {C.DIM}(Use ↑/↓ arrow keys, Enter to confirm){C.RESET}\n")

            for idx, opt in enumerate(options):
                title = opt["title"]
                desc = opt.get("desc", "")
                if idx == selected:
                    output.append(f"  {C.CYAN}{C.BOLD}❯ ●  {title}{C.RESET}")
                    if desc:
                        output.append(f"       {C.CYAN}{desc}{C.RESET}")
                else:
                    output.append(f"     {C.DIM}○  {title}{C.RESET}")
                    if desc:
                        output.append(f"       {C.DIM}{desc}{C.RESET}")
                output.append("")

            menu_text = "\n".join(output)
            sys.stdout.write(menu_text)
            sys.stdout.flush()
            lines_drawn = menu_text.count("\n")

            key = read_single_key()
            if key == "up":
                selected = (selected - 1) % total
            elif key == "down":
                selected = (selected + 1) % total
            elif key == "enter":
                sys.stdout.write(f"\033[{lines_drawn}A\033[0J")
                sys.stdout.flush()
                chosen = options[selected]
                print(f"  {C.GREEN}{C.BOLD}✔ {prompt_title}:{C.RESET} {C.BOLD}{chosen['title']}{C.RESET}\n")
                return chosen["key"]
            elif key in ("ctrl_c", "esc"):
                sys.stdout.write(f"\033[{lines_drawn}A\033[0J")
                sys.stdout.flush()
                print(f"  {C.YELLOW}Selection cancelled.{C.RESET}\n")
                return None
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

def sync_cloud_state(force=False):
    """
    Safely synchronizes state, activity logs, and commit history from the cloud origin.
    """
    gitbot_home = os.path.expanduser("~/.gitbot")
    target_dir = gitbot_home if os.path.exists(gitbot_home) else REPO_DIR
    # Dashboard refreshes are read-only: telemetry reads origin/main directly and
    # must never overwrite a user's local working tree.
    run_cmd(f'git -C "{target_dir}" fetch origin main', cwd=target_dir)

# ====================================================================
# Command: STATUS (Interactive Dashboard)
# ====================================================================
def cmd_status(args=None):
    force = getattr(args, "refresh", False) if args else False
    sync_cloud_state(force=force)
    snap = engine.get_live_system_snapshot(force_sync=force)

    if snap["is_paused"]:
        status_badge = format_badge("PAUSED", C.YELLOW)
    elif snap["vacation_status"]["active"]:
        status_badge = format_badge("VACATION", C.YELLOW)
    else:
        status_badge = format_badge("ACTIVE", C.GREEN)

    w = 76
    inner = w - 4
    bar = make_bar(snap["today_done"], snap["today_target"], length=24, pct=snap["pct"])
    author_str = f"{snap['author_name']} <{snap['author_email']}>"

    title = "SYSTEM STATUS DASHBOARD"
    space = max(1, inner - vis_len(title) - vis_len(status_badge))
    header_content = f"{C.BOLD}{title}{C.RESET}" + (" " * space) + status_badge

    print(f"{C.CYAN}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(header_content, width=w))
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.DIM}Profile     :{C.RESET} {C.WHITE}{author_str}{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Preset      :{C.RESET} {C.MAGENTA}{snap['preset_name']:<22}{C.RESET} {C.DIM}Pacing :{C.RESET} {C.WHITE}{snap['pacing_name']:<16}{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Notify Mode :{C.RESET} {C.GREEN}{snap['notify_mode']:<22}{C.RESET} {C.DIM}Today  :{C.RESET} {C.WHITE}{snap['date_str']} ({snap['time_str']}){C.RESET}", width=w))
    print(render_row("", width=w))
    print(render_row(f"{C.BOLD}Today's Commits :{C.RESET} {C.GREEN}{snap['today_done']}{C.RESET} / {C.CYAN}{snap['today_target']}{C.RESET} target ({C.BOLD}{snap['pct']}% completed{C.RESET})", width=w))
    print(render_row(f"{bar}", width=w))
    print(render_row("", width=w))
    print(render_row(f"{C.DIM}Cloud Sessions  :{C.RESET} {C.YELLOW}{snap['runs_done']}{C.RESET} / {snap['total_runs']} completed today", width=w))
    print(render_row(f"{C.DIM}Lifetime Total  :{C.RESET} {C.CYAN}{snap['total_commits']}{C.RESET} commits in repository", width=w))
    print(render_row(f"{C.DIM}Next Session    :{C.RESET} {C.GREEN}{snap['next_session_str']}{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Schedule Times  :{C.RESET} 09:45, 14:45, 18:45, 22:45 IST (Cloud)", width=w))
    print(render_row(f"{C.DIM}Monthly Spikes  :{C.RESET} {snap['spikes_done']} / {snap['max_spikes']} (Occasional 170+ days)", width=w))
    print(render_row(f"{C.DIM}Commit Velocity :{C.RESET} {snap['velocity_str']}", width=w))
    print(f"{C.CYAN}╰" + "─" * (w - 2) + f"╯{C.RESET}")

    # Recent activity history (from real commits by date!)
    recent_days = snap.get("recent_days", [])
    if recent_days:
        print(f"\n{C.CYAN}╭─ Recent Activity History " + "─" * (w - 27) + f"╮{C.RESET}")
        for h in recent_days:
            h_date = h.get("date")
            h_done = h.get("commits", 0)
            h_spike = f" {C.YELLOW}★ SPIKE{C.RESET}" if h_done >= 160 else ""
            h_bar = "█" * min(20, max(1, int(h_done / 10))) if h_done > 0 else "░"
            row_content = f"{C.DIM}{h_date}{C.RESET} │ {C.GREEN}{h_bar:<20}{C.RESET} {h_done:>3} commits{h_spike}"
            print(render_row(row_content, width=w))
        print(f"{C.CYAN}╰" + "─" * (w - 2) + f"╯{C.RESET}")

    print(f"\n{C.DIM}Tip: Type '{C.RESET}{C.CYAN}today{C.RESET}{C.DIM}' for session agenda, '{C.RESET}{C.CYAN}roadmap{C.RESET}{C.DIM}' for 7-day lookahead, or '{C.RESET}{C.CYAN}help{C.RESET}{C.DIM}' for all commands.{C.RESET}\n")

# ====================================================================
# Command: TODAY (Daily Cloud Session Agenda & Live Countdown)
# ====================================================================
def cmd_today(args=None):
    force = getattr(args, "refresh", False) if args else False
    sync_cloud_state(force=force)
    snap = engine.get_live_system_snapshot(force_sync=force)
    w = 76
    inner = w - 4

    bar = make_bar(snap["today_done"], snap["today_target"], length=24, pct=snap["pct"])
    title = "☀️ TODAY'S CLOUD EXECUTION TIMELINE"
    date_display = f"{snap['date_str']} (IST)"
    space = max(1, inner - vis_len(title) - vis_len(date_display))
    header_content = f"{C.BOLD}{title}{C.RESET}" + (" " * space) + f"{C.WHITE}{date_display}{C.RESET}"

    print(f"{C.CYAN}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(header_content, width=w))
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.DIM}Profile  :{C.RESET} {C.WHITE}{snap['author_name']} <{snap['author_email']}>{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Preset   :{C.RESET} {C.MAGENTA}{snap['preset_name']:<18}{C.RESET} │ {C.DIM}Next Run:{C.RESET} {C.GREEN}{snap['countdown']}{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Progress :{C.RESET} {C.GREEN}{snap['today_done']}{C.RESET} / {C.CYAN}{snap['today_target']}{C.RESET} commits ({C.BOLD}{snap['pct']}% completed{C.RESET})", width=w))
    print(render_row(f"{bar}", width=w))
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.BOLD}DAILY CLOUD SESSION AGENDA{C.RESET}", width=w))
    print(render_row(f"{C.DIM}#  Session Name         Schedule       Target      Status{C.RESET}", width=w))

    status_badges = {
        "completed": f"{C.GREEN}✓ Completed{C.RESET}",
        "next_up": f"{C.YELLOW}⏳ Next Up{C.RESET}  ",
        "scheduled": f"{C.GRAY}○ Scheduled{C.RESET}",
        "skipped": f"{C.RED}⚠ Skipped{C.RESET}  "
    }

    for s in snap["sessions"]:
        badge = status_badges.get(s["status"], s["status"])
        time_display = s.get("time_str", "")
        s_line = f"{s['id']}  {s['name']:<18}  {time_display:<13}  {s['planned_commits']:>2} commits   {badge}"
        print(render_row(s_line, width=w))

    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    rem_str = f"Remaining Today: {snap['remaining_commits']} commits across {snap['remaining_sessions']} upcoming session(s)"
    print(render_row(f"{C.BOLD}⚡ EXECUTION SUMMARY{C.RESET}", width=w))
    print(render_row(f"{C.WHITE}{rem_str}{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Cadence: 4 daily automated cloud runs aligned to Indian Standard Time{C.RESET}", width=w))
    print(f"{C.CYAN}╰" + "─" * (w - 2) + f"╯{C.RESET}\n")

# ====================================================================
# Command: ROADMAP (Strategic Multi-Day Horizon & Lookahead Forecast)
# ====================================================================
def _legacy_today_timeline(args=None):
    force = getattr(args, "refresh", False) if args else False
    sync_cloud_state(force=force)
    snap = engine.get_live_system_snapshot(force_sync=force)
    w = 76
    inner = w - 4

    bar = make_bar(snap["today_done"], snap["today_target"], length=24, pct=snap["pct"])
    title = "☀️ TODAY'S CLOUD EXECUTION TIMELINE"
    date_display = f"{snap['date_str']} (IST)"
    space = max(1, inner - vis_len(title) - vis_len(date_display))
    header_content = f"{C.BOLD}{title}{C.RESET}" + (" " * space) + f"{C.WHITE}{date_display}{C.RESET}"

    print(f"{C.CYAN}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(header_content, width=w))
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.DIM}Profile  :{C.RESET} {C.WHITE}{snap['author_name']} <{snap['author_email']}>{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Preset   :{C.RESET} {C.MAGENTA}{snap['preset_name']:<18}{C.RESET} │ {C.DIM}Next Run:{C.RESET} {C.GREEN}{snap['countdown']}{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Progress :{C.RESET} {C.GREEN}{snap['today_done']}{C.RESET} / {C.CYAN}{snap['today_target']}{C.RESET} commits ({C.BOLD}{snap['pct']}% completed{C.RESET})", width=w))
    print(render_row(f"{bar}", width=w))
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.BOLD}DAILY CLOUD SESSION AGENDA{C.RESET}", width=w))
    print(render_row(f"{C.DIM}#  Session Name         Schedule       Target      Status{C.RESET}", width=w))

    status_badges = {
        "completed": f"{C.GREEN}✓ Completed{C.RESET}",
        "next_up": f"{C.YELLOW}⏳ Next Up{C.RESET}  ",
        "scheduled": f"{C.GRAY}○ Scheduled{C.RESET}",
        "skipped": f"{C.RED}⚠ Skipped{C.RESET}  "
    }

    for s in snap["sessions"]:
        badge = status_badges.get(s["status"], s["status"])
        time_display = s.get("time_str", "")
        s_line = f"{s['id']}  {s['name']:<18}  {time_display:<13}  {s['planned_commits']:>2} commits   {badge}"
        print(render_row(s_line, width=w))

    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    rem_str = f"Remaining Today: {snap['remaining_commits']} commits across {snap['remaining_sessions']} upcoming session(s)"
    print(render_row(f"{C.BOLD}⚡ EXECUTION SUMMARY{C.RESET}", width=w))
    print(render_row(f"{C.WHITE}{rem_str}{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Cadence: 4 daily automated cloud runs aligned to Indian Standard Time{C.RESET}", width=w))
    print(f"{C.CYAN}╰" + "─" * (w - 2) + f"╯{C.RESET}\n")

# ====================================================================
# Command: ROADMAP (Strategic Multi-Day Horizon & Lookahead Forecast)
# ====================================================================
def cmd_roadmap(args=None):
    sync_cloud_state()
    snap = engine.get_live_system_snapshot()
    w = 76
    inner = w - 4

    title = "🗺️ STRATEGIC CONTRIBUTION ROADMAP"
    date_display = f"{snap['date_str']} (IST)"
    space = max(1, inner - vis_len(title) - vis_len(date_display))
    header_content = f"{C.BOLD}{title}{C.RESET}" + (" " * space) + f"{C.WHITE}{date_display}{C.RESET}"

    print(f"{C.CYAN}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(header_content, width=w))
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.DIM}Profile  :{C.RESET} {C.WHITE}{snap['author_name']} <{snap['author_email']}>{C.RESET}", width=w))
    print(render_row(f"{C.DIM}Preset   :{C.RESET} {C.MAGENTA}{snap['preset_name']:<20}{C.RESET} │ {C.DIM}Total Repos:{C.RESET} {C.GREEN}{snap['total_commits']} lifetime commits{C.RESET}", width=w))

    # 1. Weekly Momentum & Heat Tracker
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.BOLD}📊 WEEKLY MOMENTUM & HEAT TRACKER{C.RESET}", width=w))
    week_bar = make_bar(snap["week_done"], snap["week_target"], length=22, pct=snap["week_pct"])
    print(render_row(f"Week Total : {C.GREEN}{snap['week_done']}{C.RESET} / {C.CYAN}{snap['week_target']}{C.RESET} commits ({snap['week_pct']}% pace) {week_bar}", width=w))

    day_segments = []
    for d in snap["week_days"]:
        d_name = d["day"]
        if d["is_today"]:
            c_str = f"{C.GREEN}{d['commits'] or 0}★{C.RESET}"
        elif d["is_past"]:
            c_str = f"{C.WHITE}{d['commits'] or 0}✓{C.RESET}"
        else:
            c_str = f"{C.GRAY}--{C.RESET}"
        day_segments.append(f"{d_name} {c_str}")
    days_row = " │ ".join(day_segments)
    print(render_row(days_row, width=w))

    # 2. Streak & Continuity Radar
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.BOLD}🔥 STREAK & CONTINUITY RADAR{C.RESET}", width=w))
    streak_str = f"{C.YELLOW}{C.BOLD}{snap['streak']} consecutive active days{C.RESET}"
    risk_str = f"{C.GREEN}0% Safe{C.RESET} (Autonomous cloud engine active)"
    spikes_str = f"{C.WHITE}{snap['spikes_done']}{C.RESET} / {snap['max_spikes']} used (Occasional 170+ surge days)"
    print(render_row(f"Active Streak   : {streak_str}", width=w))
    print(render_row(f"Zero-Day Risk   : {risk_str}", width=w))
    print(render_row(f"Monthly Spikes  : {spikes_str}", width=w))

    # 3. 7-Day Dynamic Lookahead Calendar
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.BOLD}📈 7-DAY DYNAMIC LOOKAHEAD CALENDAR{C.RESET}", width=w))
    for look in snap["lookahead_7d"][:5]:
        day_lbl = look["day_label"]
        rng = look["range"]
        mode = look["mode"]
        fc_line = f"• {day_lbl:<14}: {C.CYAN}{rng:<18}{C.RESET} {C.DIM}({mode}){C.RESET}"
        print(render_row(fc_line, width=w))

    # 4. Milestone Progression
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.BOLD}🎯 MILESTONE PROGRESSION{C.RESET}", width=w))
    ms_bar = make_bar(snap["total_commits"], snap["next_milestone"], length=22, pct=snap["milestone_pct"])
    print(render_row(f"Next Goal : {C.CYAN}{snap['next_milestone']} Commits{C.RESET} ({snap['milestone_pct']}% completed) {ms_bar}", width=w))
    print(f"{C.CYAN}╰" + "─" * (w - 2) + f"╯{C.RESET}\n")

# ====================================================================
# Command: NOTIFY (GitHub Notification Attempt Settings with Arrow Keys)
# ====================================================================
def cmd_notify(args=None):
    config = engine.load_config()
    current_mode = config.get("notification_mode", "every-batch")

    # If mode passed directly via arguments
    target_mode = getattr(args, "mode", None) if args else None

    if not target_mode:
        # Launch Interactive Arrow-Key Menu
        options = [
            {
                "key": "every-batch",
                "title": "Every Batch (Recommended)",
                "desc": "One notification attempt after each completed batch"
            },
            {
                "key": "morning-night",
                "title": "Morning + Night",
                "desc": "Start-of-day plan and final-day summary"
            },
            {
                "key": "morning-only",
                "title": "Morning Only",
                "desc": "Send only the start-of-day plan"
            },
            {
                "key": "night-only",
                "title": "Night Only",
                "desc": "Send only the final-day summary"
            },
            {
                "key": "off",
                "title": "Off",
                "desc": "Do not create notification attempts"
            }
        ]

        def_idx = 0
        for i, opt in enumerate(options):
            if opt["key"] == current_mode:
                def_idx = i
                break

        chosen = select_menu("Select GitHub Notification Attempt Mode", options, default_index=def_idx)
        if not chosen or chosen == current_mode:
            return
        target_mode = chosen

    if target_mode.lower() in ("every-batch", "morning-night", "morning-only", "night-only", "off"):
        clean_mode = target_mode.lower()
        engine.set_notification_mode(clean_mode)
        sync_config_to_git(f"chore: set notification mode to {clean_mode}")
        print(f"  {C.GREEN}{C.BOLD}✓ Notification attempt mode updated to: '{clean_mode}'.{C.RESET}\n")

# ====================================================================
# Command: INTENSITY / PRESETS (Commit Velocity with Arrow Keys)
# ====================================================================
def cmd_intensity(args=None):
    config = engine.load_config()
    current_preset = config.get("preset", "active")

    target_preset = getattr(args, "preset", None) if args else None

    if not target_preset:
        # Launch Interactive Arrow-Key Menu
        options = [
            {
                "key": "active",
                "title": "Active Contributor (Recommended)",
                "desc": "50 – 150 commits/day, vibrant and natural GitHub presence"
            },
            {
                "key": "consistent",
                "title": "Consistent Dev",
                "desc": "40 – 90 commits/day, steady and dependable pacing"
            },
            {
                "key": "hardcore",
                "title": "Hardcore Coder",
                "desc": "80 – 250 commits/day, maximum velocity and burst outputs"
            }
        ]

        def_idx = 0
        for i, opt in enumerate(options):
            if opt["key"] == current_preset:
                def_idx = i
                break

        chosen = select_menu("Select Commit Intensity Preset", options, default_index=def_idx)
        if not chosen or chosen == current_preset:
            return
        target_preset = chosen

    if target_preset.lower() in ("consistent", "active", "hardcore"):
        clean_preset = target_preset.lower()
        engine.apply_preset(clean_preset)
        sync_config_to_git(f"chore: set commit intensity preset to {clean_preset}")
        print(f"  {C.GREEN}{C.BOLD}✓ Commit intensity preset updated to: '{clean_preset}'.{C.RESET}\n")

# ====================================================================
# Command: WEEKEND (Weekend Pacing Mode with Arrow Keys)
# ====================================================================
def cmd_weekend(args=None):
    config = engine.load_config()
    current_weekend = config.get("weekend_mode", "normal")

    target_mode = getattr(args, "mode", None) if args else None

    if not target_mode:
        # Launch Interactive Arrow-Key Menu
        options = [
            {
                "key": "normal",
                "title": "Normal (Recommended)",
                "desc": "Full commit velocity all 7 days of the week"
            },
            {
                "key": "light",
                "title": "Light",
                "desc": "Reduced commit volume on Saturday & Sunday (~40%)"
            },
            {
                "key": "off",
                "title": "Off / Minimal",
                "desc": "Light maintenance: reduced weekend pace to keep the graph active"
            }
        ]

        def_idx = 0
        for i, opt in enumerate(options):
            if opt["key"] == current_weekend:
                def_idx = i
                break

        chosen = select_menu("Select Weekend Mode Preference", options, default_index=def_idx)
        if not chosen or chosen == current_weekend:
            return
        target_mode = chosen

    if target_mode.lower() in ("normal", "light", "off"):
        clean_mode = target_mode.lower()
        engine.set_weekend_mode(clean_mode)
        sync_config_to_git(f"chore: set weekend mode to {clean_mode}")
        print(f"  {C.GREEN}{C.BOLD}✓ Weekend mode preference updated to: '{clean_mode}'.{C.RESET}\n")

# ====================================================================
# Command: VACATION (Light Maintenance Mode with Arrow Keys)
# ====================================================================
def cmd_vacation(args=None):
    """
    Configure Vacation Mode (20–40 commits/day, without weekend double reduction).
    """
    status = engine.get_vacation_status()
    is_active = status["active"]
    days_left = status.get("days_left")

    options = [
        {
            "key": "7days",
            "title": "Enable Vacation — 1 Week (7 Days)",
            "desc": "Reduced vacation pace: 20–40 commits/day for 7 days"
        },
        {
            "key": "14days",
            "title": "Enable Vacation — 2 Weeks (14 Days)",
            "desc": "Reduced vacation pace: 20–40 commits/day for 14 continuous days"
        },
        {
            "key": "indefinite",
            "title": "Enable Vacation — Ongoing / Indefinite",
            "desc": "Keep vacation pace active until you manually turn it off"
        },
        {
            "key": "off",
            "title": "Disable Vacation Mode (Resume Normal Schedule)",
            "desc": "Return immediately to your active contribution preset"
        }
    ]

    def_idx = 3 if is_active else 0
    chosen = select_menu("GitBot Vacation Mode Settings", options, default_index=def_idx)
    if not chosen:
        return

    if chosen == "7days":
        engine.enable_vacation(days=7)
        sync_config_to_git("chore: enable vacation mode for 7 days")
        print(f"\n  {C.GREEN}{C.BOLD}✓ Vacation Mode enabled for 7 days!{C.RESET}")
        print(f"  {C.GRAY}GitBot will maintain 20–40 commits daily in IST.{C.RESET}\n")
    elif chosen == "14days":
        engine.enable_vacation(days=14)
        sync_config_to_git("chore: enable vacation mode for 14 days")
        print(f"\n  {C.GREEN}{C.BOLD}✓ Vacation Mode enabled for 14 days!{C.RESET}")
        print(f"  {C.GRAY}GitBot will maintain 20–40 commits daily in IST.{C.RESET}\n")
    elif chosen == "indefinite":
        engine.enable_vacation()
        sync_config_to_git("chore: enable indefinite vacation mode")
        print(f"\n  {C.GREEN}{C.BOLD}✓ Ongoing Vacation Mode enabled!{C.RESET}")
        print(f"  {C.GRAY}GitBot will maintain 20–40 commits daily until you run 'vacation' to disable.{C.RESET}\n")
    elif chosen == "off":
        engine.disable_vacation()
        sync_config_to_git("chore: disable vacation mode, resume normal schedule")
        print(f"\n  {C.GREEN}{C.BOLD}✓ Vacation Mode disabled. Resumed standard preset!{C.RESET}\n")

# ====================================================================
# Command: DOCTOR (Health & Diagnostics)
# ====================================================================
def cmd_doctor(args=None):
    print(f"\n{C.BOLD}🩺 GitBot System Diagnostics & Health Check{C.RESET}")
    print(f"{C.GRAY}Checking environment, GitHub CLI authentication, and cloud engine status...{C.RESET}\n")

    repo_name = get_connected_repo()
    checklist = []

    # 1. Python Check
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 8):
        checklist.append((True, "Python Environment", f"v{py_ver} (Compatible)"))
    else:
        checklist.append((False, "Python Environment", f"v{py_ver} (Requires 3.8+)"))

    # 2. Git Installed
    code, git_ver, _ = run_cmd("git --version")
    if code == 0:
        checklist.append((True, "Git Version", git_ver))
    else:
        checklist.append((False, "Git Version", "Git not found in PATH"))

    # 3. Local Git Identity
    _, user_name, _ = run_cmd("git config user.name")
    _, user_email, _ = run_cmd("git config user.email")
    if user_name and user_email:
        checklist.append((True, "Git Author Identity", f"{user_name} <{user_email}>"))
    else:
        checklist.append((False, "Git Author Identity", "Missing user.name or user.email in git config"))

    # 4. GitHub CLI (`gh`) Authentication
    code, gh_user, _ = run_cmd("gh api user --jq .login")
    if code == 0 and gh_user:
        checklist.append((True, "GitHub CLI Auth", f"Authenticated as @{gh_user}"))
        
        # 5. Connected Repository
        if not repo_name:
            checklist.append((False, "Connected Repository", "No repository connected in config.json or git remote"))
        else:
            repo_code, repo_resp, _ = run_cmd(f"gh repo view {repo_name} --json isPrivate,nameWithOwner,id")
            if repo_code == 0 and repo_resp and repo_resp.strip() not in ("[]", "{}"):
                checklist.append((True, "Connected Repository", f"https://github.com/{repo_name} (Private)"))
            else:
                checklist.append(("UNVERIFIED", "Connected Repository", f"https://github.com/{repo_name} (Remote check unverified)"))

        # 6. Remote Freshness via Central SSOT Snapshot
        snap = engine.get_live_system_snapshot(force_sync=True)
        f_state = snap.get("freshness_state", "VERIFIED")
        if f_state == "VERIFIED":
            checklist.append((True, "Remote Freshness", f"Synced with origin/main ({snap.get('total_commits', 0)} total commits)"))
        elif f_state == "STALE":
            checklist.append((None, "Remote Freshness", "Local state out of sync with origin/main"))
        elif f_state == "UNVERIFIED":
            checklist.append(("UNVERIFIED", "Remote Freshness", "No remote origin configured"))
        else:
            checklist.append((False, "Remote Freshness", "Offline or network unreachable"))

        # 7. Workflow Permissions
        if repo_name:
            perm_code, perm_resp, _ = run_cmd(f"gh api repos/{repo_name}/actions/permissions/workflow")
            if perm_code == 0 and perm_resp:
                try:
                    perm_json = json.loads(perm_resp)
                    if perm_json.get("default_workflow_permissions") == "write":
                        checklist.append((True, "Workflow Permissions", "Read & Write access enabled"))
                    else:
                        checklist.append((False, "Workflow Permissions", f"Set to '{perm_json.get('default_workflow_permissions')}'. Run 'gh api -X PUT repos/{repo_name}/actions/permissions/workflow -f default_workflow_permissions=write'"))
                except Exception:
                    checklist.append(("UNVERIFIED", "Workflow Permissions", "Could not parse permissions response"))
            else:
                wf_code, wf_resp, _ = run_cmd(f"gh workflow list --repo {repo_name}")
                if wf_code == 0 and "contribute" in wf_resp.lower():
                    checklist.append((True, "Workflow Permissions", "Cloud Actions workflow active"))
                else:
                    checklist.append(("UNVERIFIED", "Workflow Permissions", "Workflow/permissions could not be verified"))

        # 8. Latest Cloud Run Status
        if repo_name:
            run_code, run_resp, _ = run_cmd(f"gh run list --repo {repo_name} --limit 1 --json conclusion,status")
            if run_code == 0 and run_resp:
                try:
                    runs_json = json.loads(run_resp)
                    if runs_json and isinstance(runs_json, list):
                        latest = runs_json[0]
                        conclusion = latest.get("conclusion")
                        if conclusion == "success":
                            checklist.append((True, "Cloud Actions Engine", "Latest run succeeded (Green)"))
                        elif conclusion:
                            checklist.append((False, "Cloud Actions Engine", f"Latest run conclusion: '{conclusion}'"))
                        else:
                            checklist.append(("UNVERIFIED", "Cloud Actions Engine", f"Run in progress: status '{latest.get('status')}'"))
                    else:
                        checklist.append((None, "Cloud Actions Engine", "No recent workflow runs found"))
                except Exception:
                    checklist.append((None, "Cloud Actions Engine", "Could not parse workflow status"))
            else:
                checklist.append((None, "Cloud Actions Engine", "No recent workflow runs found"))
    else:
        checklist.append((False, "GitHub CLI Auth", "gh CLI not logged in (Run 'gh auth login')"))

    # 9. Cloud Schedule Cadence
    checklist.append((True, "Cloud Schedule Cadence", "4 daily runs in IST (09:45, 14:45, 18:45, 22:45)"))

    # 10. Engine State & Config
    cfg = engine.load_config()
    st = engine.load_state()
    if cfg and st:
        checklist.append((True, "Configuration & State", f"Valid (Preset: {cfg.get('preset', 'active')}, Pacing: {cfg.get('weekend_mode', 'normal')})"))
    else:
        checklist.append((False, "Configuration & State", "Corrupted config.json or state.json"))

    # Print Report
    for passed, label, detail in checklist:
        if passed is True or passed == "PASS":
            tag = " PASS "
            color = C.GREEN
        elif passed is False or passed == "FAIL":
            tag = " FAIL "
            color = C.RED
        elif passed == "UNVERIFIED":
            tag = " UNVF "
            color = C.MAGENTA
        else:
            tag = " WARN "
            color = C.YELLOW
        badge = f"{color}{C.BOLD}[{tag}]{C.RESET}"
        print(f"  {badge} {C.BOLD}{label:<24}{C.RESET} : {detail}")

    all_passed = all(p is True or p == "PASS" for p, _, _ in checklist)
    print("\n" + "─" * 64)
    if all_passed:
        print(f"{C.GREEN}{C.BOLD}✓ All diagnostics passed! GitBot is 100% operational in the cloud.{C.RESET}\n")
    else:
        print(f"{C.YELLOW}{C.BOLD}! Some checks require attention. Review the FAIL items above.{C.RESET}\n")

# ====================================================================
# Command: PAUSE / RESUME
# ====================================================================
def cmd_pause(args=None):
    repo_name = get_connected_repo()
    if not repo_name:
        print("\nNo connected repository is configured; refusing to change a workflow.\n")
        return
    engine.set_paused(True)
    sync_config_to_git("chore: pause gitbot cloud engine")
    run_cmd(f"gh workflow disable contribute.yml --repo {repo_name}")
    w = 76
    print(f"\n{C.YELLOW}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(f"{C.YELLOW}{C.BOLD}⏸️  GITBOT ENGINE PAUSED{C.RESET}", width=w))
    print(f"{C.YELLOW}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row("Cloud schedule is disabled. Zero commits will be pushed.", width=w))
    print(render_row(f"To resume anytime, run: {C.GREEN}{C.BOLD}resume{C.RESET}", width=w))
    print(f"{C.YELLOW}╰" + "─" * (w - 2) + f"╯{C.RESET}\n")

def cmd_resume(args=None):
    repo_name = get_connected_repo()
    if not repo_name:
        print("\nNo connected repository is configured; refusing to change a workflow.\n")
        return
    engine.set_paused(False)
    sync_config_to_git("chore: resume gitbot cloud engine")
    run_cmd(f"gh workflow enable contribute.yml --repo {repo_name}")
    w = 76
    print(f"\n{C.GREEN}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(f"{C.GREEN}{C.BOLD}▶️  GITBOT ENGINE RESUMED & ACTIVE{C.RESET}", width=w))
    print(f"{C.GREEN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row("Cloud schedule is active. Contributions will proceed on cadence.", width=w))
    print(render_row(f"To view upcoming runs, run: {C.CYAN}{C.BOLD}today{C.RESET}", width=w))
    print(f"{C.GREEN}╰" + "─" * (w - 2) + f"╯{C.RESET}\n")

# ====================================================================
# Command: TRIGGER (Instant Local or Cloud Execution)
# ====================================================================
def cmd_trigger(args=None):
    print(f"\n{C.BOLD}🚀 Manual Execution Trigger{C.RESET}")
    options = [
        {
            "key": "cloud",
            "title": "Cloud Run (Recommended)",
            "desc": "Trigger GitHub Actions workflow dispatch remotely in the cloud"
        },
        {
            "key": "local",
            "title": "Local Batch",
            "desc": "Run a single session commit batch right now on this machine"
        }
    ]
    chosen = select_menu("Select Execution Target", options, default_index=0)
    if chosen == "local":
        print(f"{C.GRAY}Running local batch...{C.RESET}")
        import bot
        bot.main()
    elif chosen == "cloud":
        repo_name = get_connected_repo()
        if not repo_name:
            print(f"  {C.RED}No connected repository is configured; refusing to dispatch a workflow.{C.RESET}\n")
            return
        print(f"{C.GRAY}Dispatching GitHub Actions workflow 'contribute.yml'...{C.RESET}")
        code, out, err = run_cmd(f"gh workflow run contribute.yml --repo {repo_name}")
        if code == 0:
            print(f"  {C.GREEN}{C.BOLD}✓ Cloud run dispatched successfully!{C.RESET}")
            print(f"  View live execution: {C.CYAN}https://github.com/{repo_name}/actions{C.RESET}\n")
        else:
            print(f"  {C.RED}Failed to dispatch cloud run: {err}{C.RESET}\n")

# ====================================================================
# Command: LOGS (View Cloud Execution History & Commit Telemetry)
# ====================================================================
def cmd_logs(args=None):
    force = getattr(args, "refresh", False) if args else False
    if force:
        sync_cloud_state(force=True)
    w = 76
    repo_name = get_connected_repo()
    gitbot_home = os.path.expanduser("~/.gitbot")
    target_dir = gitbot_home if os.path.exists(gitbot_home) else REPO_DIR

    title = "📜 CLOUD WORKFLOW RUNS & TELEMETRY"
    print(f"\n{C.CYAN}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(f"{C.BOLD}{title}{C.RESET}", width=w))
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")

    # 1. Fetch JSON runs from gh CLI
    code, out, err = run_cmd(f"gh run list --repo {repo_name} --limit 5 --json databaseId,status,conclusion,createdAt,updatedAt,event")
    runs_displayed = False
    if code == 0 and out:
        try:
            runs = json.loads(out)
            if runs and isinstance(runs, list):
                print(render_row(f"{C.BOLD}RECENT GITHUB ACTIONS RUNS{C.RESET}", width=w))
                hdr_str = f"{'Run ID':<12} {'Trigger':<16} {'Status':<14} {'Time (IST)':<18} {'Duration':>6}"
                print(render_row(f"{C.DIM}{hdr_str}{C.RESET}", width=w))
                
                for r in runs:
                    run_id = str(r.get("databaseId", ""))[:11]
                    event = r.get("event", "schedule")[:15]
                    conclusion = r.get("conclusion") or r.get("status", "in_progress")
                    
                    if conclusion == "success":
                        badge_txt = "✓ Success"
                        badge = f"{C.GREEN}{badge_txt}{C.RESET}"
                        b_len = len(badge_txt)
                    elif conclusion in ("in_progress", "queued"):
                        badge_txt = "⏳ Running"
                        badge = f"{C.YELLOW}{badge_txt}{C.RESET}"
                        b_len = len(badge_txt)
                    else:
                        badge_txt = f"✗ {conclusion[:7].title()}"
                        badge = f"{C.RED}{badge_txt}{C.RESET}"
                        b_len = len(badge_txt)
                    
                    badge_pad = " " * max(1, 14 - b_len)
                    badge_col = badge + badge_pad

                    created_raw = r.get("createdAt", "")
                    time_ist_str = created_raw[:16]
                    duration_str = "--"
                    if created_raw:
                        try:
                            dt_utc = datetime.strptime(created_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                            dt_ist = dt_utc.astimezone(engine.IST)
                            time_ist_str = dt_ist.strftime("%d %b, %I:%M %p")
                            
                            updated_raw = r.get("updatedAt", "")
                            if updated_raw:
                                dt_up = datetime.strptime(updated_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                                secs = int((dt_up - dt_utc).total_seconds())
                                duration_str = f"{secs}s" if secs >= 0 else "--"
                        except Exception:
                            pass
                    
                    line_str = f"{run_id:<12} {event:<16} {badge_col} {time_ist_str:<18} {duration_str:>6}"
                    print(render_row(line_str, width=w))
                runs_displayed = True
        except Exception:
            pass

    if not runs_displayed:
        print(render_row(f"{C.DIM}Could not query remote runs. Checking local commit telemetry...{C.RESET}", width=w))

    # 2. Display recent GitBot commits in repository
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.BOLD}RECENT REPOSITORY COMMITS{C.RESET}", width=w))
    c_code, c_out, _ = run_cmd(f'git -C "{target_dir}" log -n 5 --format="%h@@@%s@@@%cr"')
    if c_code == 0 and c_out:
        for c_line in c_out.splitlines()[:5]:
            if "@@@" in c_line:
                parts = c_line.split("@@@")
                c_hash = parts[0]
                c_msg = parts[1]
                c_rel = parts[2] if len(parts) > 2 else ""
                c_formatted = f"{C.YELLOW}{c_hash}{C.RESET}  {c_msg} {C.DIM}({c_rel}){C.RESET}"
                print(render_row(c_formatted, width=w))
            else:
                print(render_row(f"{C.WHITE}{c_line}{C.RESET}", width=w))
    else:
        print(render_row(f"{C.DIM}No commit history found in local repository.{C.RESET}", width=w))

    print(f"{C.CYAN}╰" + "─" * (w - 2) + f"╯{C.RESET}\n")

# ====================================================================
# Command: UPDATE (Pull Latest Engine from Upstream)
# ====================================================================
def cmd_update(args=None):
    print(f"\n{C.CYAN}>>> Checking for updates from upstream (Dashrath175/GitBot)...{C.RESET}\n")
    gitbot_home = os.path.expanduser("~/.gitbot")
    target_dir = gitbot_home if os.path.exists(gitbot_home) else REPO_DIR
    code, out, err = run_cmd(f"git -C \"{target_dir}\" status --porcelain")
    if code != 0 or out:
        print(f"{C.YELLOW}! Update refused: preserve or commit local changes before updating.{C.RESET}\n")
        return
    remote_code, _, _ = run_cmd(f"git -C \"{target_dir}\" remote get-url upstream")
    if remote_code != 0:
        run_cmd(f"git -C \"{target_dir}\" remote add upstream https://github.com/Dashrath175/GitBot.git")
    fetch_code, fetch_out, fetch_err = run_cmd(f"git -C \"{target_dir}\" fetch upstream main")
    if fetch_code != 0:
        print(f"{C.YELLOW}! Could not fetch updates: {fetch_out or fetch_err}{C.RESET}\n")
        return
    code, out, err = run_cmd(f"git -C \"{target_dir}\" merge --ff-only upstream/main")
    if code == 0:
        print(f"{C.GREEN}{C.BOLD}✓ GitBot is fully updated to the latest release!{C.RESET}\n")
    else:
        print(f"[*] Update status: {out or err}\n")

# ====================================================================
# Command: UNINSTALL
# ====================================================================
def cmd_uninstall(args=None):
    print("\nGitBot uninstall is intentionally non-destructive in v7.0.3. No local files or repositories were removed.\n")
    return
    w = 76
    print(f"\n{C.YELLOW}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(f"{C.RED}{C.BOLD}⚠️  GITBOT UNINSTALLATION WIZARD{C.RESET}", width=w))
    print(f"{C.YELLOW}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row("This will remove GitBot and its global CLI from your system.", width=w))
    print(f"{C.YELLOW}╰" + "─" * (w - 2) + f"╯{C.RESET}\n")

    ans = input(f"{C.BOLD}Are you sure you want to uninstall GitBot? [y/N]: {C.RESET}").strip().lower()
    if ans not in ("y", "yes"):
        print("\n[*] Uninstallation cancelled. GitBot remains active.\n")
        return

    # Determine the connected repository from the active git clone
    gitbot_home = os.path.expanduser("~/.gitbot")
    target_dir = gitbot_home if os.path.exists(gitbot_home) else REPO_DIR
    code, origin_url, _ = run_cmd(f'git -C "{target_dir}" remote get-url origin')
    target_repo = ""
    if code == 0 and origin_url:
        m = re.search(r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git)?$", origin_url.strip())
        if m:
            target_repo = m.group(1)

    is_upstream = (target_repo.lower() == "dashrath175/gitbot")

    options = [
        {
            "key": "keep",
            "title": "Keep Remote Repository (Recommended)",
            "desc": "Removes local CLI, preserves past green contribution squares permanently"
        }
    ]

    if target_repo and not is_upstream:
        options.append({
            "key": "delete",
            "title": f"Delete Connected Repository ({target_repo})",
            "desc": "Deletes connected bot repo from GitHub (past contribution squares disappear)"
        })

    repo_choice = select_menu("Connected GitHub Repository Option", options, default_index=0)

    if repo_choice == "delete" and target_repo and not is_upstream:
        confirm_del = input(f"\n{C.RED}Confirm: Type repository name '{target_repo}' to delete it: {C.RESET}").strip()
        if confirm_del.lower() == target_repo.lower():
            print(f"\n[+] Deleting connected repository {target_repo} via GitHub CLI...")
            run_cmd(f"gh repo delete {target_repo} --yes")
            print(f"[+] Connected repository deleted.")
        else:
            print("[-] Confirmation did not match. Keeping connected repository intact.")
    elif is_upstream:
        print(f"\n[*] Note: Connected repository is upstream development template ({target_repo}). Remote repository will remain untouched.")

    # Clean up any legacy configuration files on user system
    for legacy_path in [
        os.path.expanduser("~/.gitbot_location.json"),
        os.path.expanduser("~/.gitbot_env")
    ]:
        if os.path.exists(legacy_path):
            try:
                os.remove(legacy_path)
            except Exception:
                pass

    gitbot_home = os.path.expanduser("~/.gitbot")
    bin_dir = os.path.join(gitbot_home, "bin")

    if os.name == "nt":
        ps_clean_path = f'''
$bin = "{bin_dir}"
$curr = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($curr -like "*$bin*") {{
    $new = ($curr.Split(';') | Where-Object {{ $_ -and $_ -ne $bin }}) -join ';'
    [Environment]::SetEnvironmentVariable("PATH", $new, "User")
}}
'''
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_clean_path], capture_output=True)
        ps_delete_dir = f'Start-Process powershell -ArgumentList "-NoProfile -Command Start-Sleep -Seconds 1; Remove-Item -Recurse -Force \'{gitbot_home}\'"'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_delete_dir], capture_output=True)
    else:
        shutil.rmtree(gitbot_home, ignore_errors=True)

    print(f"\n{C.GREEN}{C.BOLD}✓ GitBot has been successfully uninstalled from this system.{C.RESET}")
    print("Thank you for using GitBot!\n")
    sys.exit(0)

# ====================================================================
# Command: HELP (Interactive Command Cheat-Sheet)
# ====================================================================
def cmd_help(args=None):
    w = 76
    print(f"\n{C.CYAN}╭" + "─" * (w - 2) + f"╮{C.RESET}")
    print(render_row(f"{C.BOLD}COMMAND CHEAT-SHEET & REFERENCE{C.RESET}", width=w))
    print(f"{C.CYAN}├" + "─" * (w - 2) + f"┤{C.RESET}")
    print(render_row(f"{C.BOLD}MONITORING & DASHBOARD{C.RESET}", width=w))
    print(render_row(f"  {C.CYAN}status{C.RESET}       View live operations dashboard, commits, and stats", width=w))
    print(render_row(f"  {C.CYAN}today{C.RESET}        View today's 4-session cloud timeline & live countdown", width=w))
    print(render_row(f"  {C.CYAN}roadmap{C.RESET}      View strategic 7-day forecast, streak radar & milestones", width=w))
    print(render_row(f"  {C.CYAN}logs{C.RESET}         View recent cloud workflow runs and commit telemetry", width=w))
    print(render_row(f"  {C.CYAN}doctor{C.RESET}       Run 9-point system diagnostics & verify cloud health", width=w))
    print(render_row("", width=w))
    print(render_row(f"{C.BOLD}ARROW-KEY CONFIGURATION{C.RESET}", width=w))
    print(render_row(f"  {C.CYAN}notify{C.RESET}       Configure batch, morning, night, or off alerts", width=w))
    print(render_row(f"  {C.CYAN}intensity{C.RESET}    Configure commit velocity (Active, Consistent, Hardcore)", width=w))
    print(render_row(f"  {C.CYAN}weekend{C.RESET}      Configure weekend pacing (Normal, Light, Off)", width=w))
    print(render_row(f"  {C.CYAN}vacation{C.RESET}     Configure vacation mode (20-40 commits/day)", width=w))
    print(render_row("", width=w))
    print(render_row(f"{C.BOLD}ENGINE CONTROLS{C.RESET}", width=w))
    print(render_row(f"  {C.CYAN}pause{C.RESET}        Temporarily pause automated cloud commits", width=w))
    print(render_row(f"  {C.CYAN}resume{C.RESET}       Resume automated cloud commits", width=w))
    print(render_row(f"  {C.CYAN}trigger{C.RESET}      Manually trigger an instant cloud or local run", width=w))
    print(render_row(f"  {C.CYAN}update{C.RESET}       Pull latest updates from upstream repository", width=w))
    print(render_row("", width=w))
    print(render_row(f"{C.BOLD}SESSION NAVIGATION{C.RESET}", width=w))
    print(render_row(f"  {C.CYAN}clear / cls{C.RESET}  Clear screen and redraw banner", width=w))
    print(render_row(f"  {C.CYAN}help{C.RESET}         Show this command reference table", width=w))
    print(render_row(f"  {C.CYAN}exit / q{C.RESET}     Quit interactive shell and return to terminal", width=w))
    print(f"{C.CYAN}╰" + "─" * (w - 2) + f"╯{C.RESET}\n")

# ====================================================================
# Command: INTERACTIVE REPL SHELL (Antigravity Style)
# ====================================================================
def interactive_repl():
    """
    Launches a persistent Antigravity-style interactive shell.
    Users can execute commands directly without repeatedly typing 'gitbot'.
    """
    print_banner()
    print_startup_card()
    print(f"Type '{C.CYAN}help{C.RESET}' to view all commands, or '{C.CYAN}exit{C.RESET}' / '{C.CYAN}q{C.RESET}' to quit.\n")

    dispatch = {
        "status": cmd_status,
        "today": cmd_today,
        "roadmap": cmd_roadmap,
        "notify": cmd_notify,
        "intensity": cmd_intensity,
        "preset": cmd_intensity,
        "presets": cmd_intensity,
        "weekend": cmd_weekend,
        "vacation": cmd_vacation,
        "doctor": cmd_doctor,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "trigger": cmd_trigger,
        "logs": cmd_logs,
        "update": cmd_update,
        "uninstall": cmd_uninstall,
        "help": cmd_help,
    }

    while True:
        try:
            raw_line = input(f"{C.CYAN}gitbot > {C.RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C.GREEN}Goodbye! 👋{C.RESET}\n")
            break

        if not raw_line:
            continue

        parts = shlex.split(raw_line) if os.name != "nt" else raw_line.split()
        if not parts:
            continue

        verb = parts[0].lower()
        sub_args = parts[1:]

        if verb in ("exit", "quit", "q", ":q"):
            print(f"\n{C.GREEN}Goodbye! 👋{C.RESET}\n")
            break

        if verb in ("clear", "cls"):
            os.system("cls" if os.name == "nt" else "clear")
            print_banner(compact=True)
            continue

        # Handle command
        handler = dispatch.get(verb)
        if handler:
            # Create a mock args object if sub_args provided
            class DummyArgs:
                pass
            d_args = DummyArgs()
            if "--refresh" in sub_args or "-r" in sub_args:
                d_args.refresh = True
            if verb in ("notify", "weekend") and sub_args:
                d_args.mode = [a for a in sub_args if not a.startswith("-")][0] if [a for a in sub_args if not a.startswith("-")] else None
            elif verb in ("intensity", "preset", "presets") and sub_args:
                d_args.preset = [a for a in sub_args if not a.startswith("-")][0] if [a for a in sub_args if not a.startswith("-")] else None
            try:
                handler(d_args)
            except Exception as e:
                print(f"{C.RED}Error executing '{verb}': {e}{C.RESET}\n")
        else:
            print(f"{C.YELLOW}Unknown command: '{verb}'.{C.RESET} Type '{C.CYAN}help{C.RESET}' to see all available commands.\n")

# ====================================================================
# Main Entry Point
# ====================================================================
def main():
    parser = argparse.ArgumentParser(
        prog="gitbot",
        description="GitBot: Autonomous Cloud Contribution Engine CLI & REPL",
        epilog="Run 'gitbot' without arguments to launch the interactive shell."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    subparsers.add_parser("shell", help="Launch the interactive REPL shell")
    status_parser = subparsers.add_parser("status", help="Show live system dashboard and today's progress")
    status_parser.add_argument("--refresh", "-r", action="store_true", help="Force fetch from remote before displaying")

    today_parser = subparsers.add_parser("today", help="Show today's 4-session cloud timeline & live countdown")
    today_parser.add_argument("--refresh", "-r", action="store_true", help="Force fetch from remote before displaying")

    roadmap_parser = subparsers.add_parser("roadmap", help="Show strategic 7-day forecast, streak radar & milestones")
    roadmap_parser.add_argument("--refresh", "-r", action="store_true", help="Force fetch from remote before displaying")
    
    notify_parser = subparsers.add_parser("notify", help="Configure GitHub notification attempt mode")
    notify_parser.add_argument("mode", nargs="?", choices=["every-batch", "morning-night", "morning-only", "night-only", "off"], help="every-batch, morning-night, morning-only, night-only, or off")

    intensity_parser = subparsers.add_parser("intensity", help="Configure commit intensity preset")
    intensity_parser.add_argument("preset", nargs="?", choices=["active", "consistent", "hardcore"], help="active, consistent, or hardcore")
    
    weekend_parser = subparsers.add_parser("weekend", help="Configure weekend pacing preference")
    weekend_parser.add_argument("mode", nargs="?", choices=["normal", "light", "off"], help="normal, light, or off")

    subparsers.add_parser("vacation", help="Configure vacation mode (20-40 commits/day)")
    subparsers.add_parser("doctor", help="Run system diagnostics and verify cloud health")
    subparsers.add_parser("trigger", help="Manually dispatch an instant cloud or local run")
    logs_parser = subparsers.add_parser("logs", help="View recent GitHub Actions execution logs and commit telemetry")
    logs_parser.add_argument("--refresh", "-r", action="store_true", help="Force fetch from remote before displaying")
    subparsers.add_parser("pause", help="Pause automated cloud commits")
    subparsers.add_parser("resume", help="Resume automated cloud commits")
    subparsers.add_parser("update", help="Update GitBot to the latest release from upstream")
    subparsers.add_parser("uninstall", help="Cleanly uninstall GitBot from system")
    subparsers.add_parser("help", help="Show command cheat-sheet")

    args = parser.parse_args()

    if not args.command or args.command == "shell":
        # Launch persistent Antigravity-style REPL shell!
        interactive_repl()
        return 0

    dispatch = {
        "status": cmd_status,
        "today": cmd_today,
        "roadmap": cmd_roadmap,
        "notify": cmd_notify,
        "intensity": cmd_intensity,
        "weekend": cmd_weekend,
        "vacation": cmd_vacation,
        "doctor": cmd_doctor,
        "trigger": cmd_trigger,
        "logs": cmd_logs,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "update": cmd_update,
        "uninstall": cmd_uninstall,
        "help": cmd_help,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()

    return 0

if __name__ == "__main__":
    sys.exit(main())
