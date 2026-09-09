import base64
import json
import os
import re
import subprocess
import sys
import time
import shutil
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if os.name == "nt":
    os.system("")

SOURCE_REPO = "Dashrath175/GitBot"
API_BASE = "https://api.github.com"

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
    return re.sub(r"\033\[[0-9;]*m", "", text)

def print_box(lines, border_color=C.CYAN, width=76):
    inner = width - 4
    top = f"{border_color}┌" + "─" * (width - 2) + f"┐{C.RESET}"
    bot = f"{border_color}└" + "─" * (width - 2) + f"┘{C.RESET}"
    print(top)
    for line in lines:
        if line == "---":
            sep = f"{border_color}├" + "─" * (width - 2) + f"┤{C.RESET}"
            print(sep)
            continue

        raw_words = line.split(" ")
        segments = []
        current_seg = ""
        for w in raw_words:
            candidate = f"{current_seg} {w}".strip() if current_seg else w
            if len(strip_ansi(candidate)) <= inner - 2:
                current_seg = candidate
            else:
                if current_seg:
                    segments.append(current_seg)
                current_seg = w
        if current_seg:
            segments.append(current_seg)
        if not segments:
            segments = [""]

        for seg in segments:
            vis_len = len(strip_ansi(seg))
            pad = max(0, inner - 2 - vis_len)
            print(f"{border_color}│{C.RESET}  {seg}" + (" " * pad) + f"{border_color}│{C.RESET}")
    print(bot)

def banner():
    print(f"""
{C.CYAN}{C.BOLD}   ____ _ _   ____        _   
  / ___(_) |_| __ )  ___ | |_ 
 | |  _| | __|  _ \ / _ \| __|
 | |_| | | |_| |_) | (_) | |_ 
  \____|_|\__|____/ \___/ \__|{C.RESET}
{C.GRAY}  One-Command Autonomous Cloud Bot Installer{C.RESET}
""")

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def parse_gh_auth_status(raw_text):
    """
    Parses `gh auth status` output to discover all logged-in accounts on github.com.
    Returns a list of dicts:
    [
        {"username": str, "is_active": bool, "auth_method": str}
    ]
    """
    accounts = []
    current = None
    for line in raw_text.splitlines():
        line_clean = line.strip()
        m_acc = re.search(r"account\s+([A-Za-z0-9_\-]+)(?:\s*\(([^)]+)\))?", line_clean)
        if ("Logged in to" in line_clean or "account " in line_clean) and m_acc:
            uname = m_acc.group(1)
            method = m_acc.group(2) or "keyring"
            current = {
                "username": uname,
                "is_active": False,
                "auth_method": method
            }
            accounts.append(current)
            continue
        if current:
            m_act = re.search(r"Active account:\s*(true|false)", line_clean, re.IGNORECASE)
            if m_act:
                current["is_active"] = (m_act.group(1).lower() == "true")

    if accounts and not any(a["is_active"] for a in accounts):
        accounts[0]["is_active"] = True

    return accounts

def verify_identity_chain(selected_username, repository):
    """Fail closed unless CLI identity, repository ownership, node id and Git remote agree."""
    code, api_login, _ = run_cmd("gh api user --jq .login")
    if code != 0 or api_login.strip().lower() != selected_username.lower():
        return False, "GitHub CLI API identity does not match the selected account"
    code, repo_json, _ = run_cmd(f"gh repo view {repository} --json nameWithOwner,id,isPrivate")
    if code != 0:
        return False, "connected repository cannot be verified through GitHub"
    try:
        repo = json.loads(repo_json)
    except ValueError:
        return False, "GitHub returned invalid repository metadata"
    if repo.get("nameWithOwner", "").lower() != repository.lower() or not repo.get("id") or not repo.get("isPrivate"):
        return False, "repository owner, node id, or private visibility does not match"
    code, remote, _ = run_cmd(f"git ls-remote https://github.com/{repository}.git HEAD")
    if code != 0:
        return False, "Git credential authentication could not access the selected repository"
    return True, repo["id"]

def create_clean_slate_staging(username, display_name, email, personalized_config):
    """
    Creates an isolated staging Git repository with exactly 1 initial commit:
    'feat: initialize GitBot [INITIALIZATION]'
    Guarantees 0 leaked commits, 0 previous-day history, and 0 commits from Dashrath175.
    """
    temp_dir = tempfile.mkdtemp(prefix="gitbot_clean_")
    run_cmd(f'git -C "{temp_dir}" init -b main')
    run_cmd(f'git -C "{temp_dir}" config user.name "{display_name or username}"')
    run_cmd(f'git -C "{temp_dir}" config user.email "{email}"')

    source_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(temp_dir, ".github", "workflows"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "data"), exist_ok=True)

    wf_src = os.path.join(source_dir, ".github", "workflows", "contribute.yml")
    if os.path.exists(wf_src):
        shutil.copy2(wf_src, os.path.join(temp_dir, ".github", "workflows", "contribute.yml"))

    for f in ["bot.py", "engine.py", "cli.py", "installer.py", "test_gitbot.py", "README.md", "LICENSE", "install.ps1", "install.sh", "gitbot.cmd", "gitbot.ps1", ".gitignore"]:
        src_f = os.path.join(source_dir, f)
        if os.path.exists(src_f):
            shutil.copy2(src_f, os.path.join(temp_dir, f))
    for directory in ["assets", "docs"]:
        src_dir = os.path.join(source_dir, directory)
        if os.path.isdir(src_dir):
            shutil.copytree(src_dir, os.path.join(temp_dir, directory), dirs_exist_ok=True)

    cfg_path = os.path.join(temp_dir, "config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(personalized_config, f, indent=2)

    clean_state = {
        "date": None,
        "today_target": 0,
        "today_done": 0,
        "runs_completed_today": 0,
        "yesterday_target": 80,
        "current_month": None,
        "spikes_this_month": 0,
        "last_spike_date": None,
        "history": []
    }
    with open(os.path.join(temp_dir, "data", "state.json"), "w", encoding="utf-8") as f:
        json.dump(clean_state, f, indent=2)

    clean_activity = {
        "total_contributions": 0,
        "last_updated": None,
        "history": []
    }
    with open(os.path.join(temp_dir, "data", "activity.json"), "w", encoding="utf-8") as f:
        json.dump(clean_activity, f, indent=2)
    with open(os.path.join(temp_dir, "data", "provenance.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": 1, "events": {}, "sessions": {}}, f, indent=2)

    run_cmd(f'git -C "{temp_dir}" add .')
    run_cmd(f'git -C "{temp_dir}" commit -m "feat: initialize GitBot [INITIALIZATION]"')
    run_cmd(f'git -C "{temp_dir}" branch -M main')

    return temp_dir

def reset_local_repo_state(repo_dir):
    """
    Guarantees that state.json and activity.json in the repository
    are pristine templates with 0 commits before pushing to a user's GitHub repo.
    """
    state_file = os.path.join(repo_dir, "data", "state.json")
    act_file = os.path.join(repo_dir, "data", "activity.json")
    clean_state = {
        "date": None,
        "today_target": 0,
        "today_done": 0,
        "runs_completed_today": 0,
        "yesterday_target": 80,
        "current_month": None,
        "spikes_this_month": 0,
        "last_spike_date": None,
        "history": []
    }
    clean_activity = {
        "total_contributions": 0,
        "last_updated": None,
        "history": []
    }
    os.makedirs(os.path.join(repo_dir, "data"), exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(clean_state, f, indent=2)
    with open(act_file, "w", encoding="utf-8") as f:
        json.dump(clean_activity, f, indent=2)
    run_cmd(f'git -C "{repo_dir}" add data/state.json data/activity.json')
    code, diff, _ = run_cmd(f'git -C "{repo_dir}" diff --cached --name-only')
    if diff:
        run_cmd(f'git -C "{repo_dir}" commit -m "chore: initialize clean activity and state template"')

def check_gh_cli():
    code, out, _ = run_cmd("gh auth status")
    return code == 0

def send_welcome_notification(username, display_name, email):
    title = "🤖 GitBot Activity & Notification Feed"
    body = f"""# 🎉 Welcome to GitBot!

Hello **{display_name}** (@{username}),

Your autonomous cloud contribution engine is now **successfully installed and activated** in your GitHub account!

### ⚡ Operational Overview
- **Repository**: `{username}/GitBot`
- **Schedule**: 4 daily sessions (Morning, Midday, Afternoon, Evening)
- **Intensity**: 50–250 commits/day with organic Markov pacing
- **Default Mode**: Daily Digest (Recommended)
- **Registered Email**: `{email}`

### 💻 Interactive Control Shell
You can manage GitBot anytime directly from your computer's terminal:
- `gitbot` — Launches the interactive REPL shell (just like Antigravity!)
- Inside the shell, run commands directly without retyping `gitbot`:
  - `status` — Live operations dashboard
  - `roadmap` / `today` — View today's 4-session cloud agenda & countdown
  - `notify` — Configure GitHub notification attempts with arrow keys (↑/↓)
  - `intensity` — Switch pacing presets (Active, Consistent, Hardcore)
  - `weekend` — Toggle weekend pacing (Normal, Light, Off)
  - `pause` / `resume` — Pause or resume automated cloud commits
  - `doctor` — Run 7-point health check & diagnostics
  - `exit` / `q` — Quit the shell

*This thread serves as your official GitBot notification and activity digest feed.*
"""
    # Check if notification feed issue already exists to prevent duplicate issues.
    code, out, _ = run_cmd(f"gh issue list --repo {username}/GitBot --state all --json number,title")
    if code == 0 and out.strip():
        try:
            issues = json.loads(out)
            for iss in issues:
                if isinstance(iss, dict) and iss.get("title") == title:
                    print(f"[+] Activity & notification feed already exists (#{iss.get('number')}). Skipping duplicate.")
                    return
        except Exception:
            pass

    print("[+] Creating initial GitHub notification feed issue (delivery is unverified)...")
    run_cmd(f'gh issue create --repo {username}/GitBot --title "{title}" --body "{body}"')

try:
    from cli import select_menu
except ImportError:
    def select_menu(prompt_title, options, default_index=0):
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

def install_via_gh():
    # 1. Multi-Account Discovery via gh auth status
    code, out, err = run_cmd("gh auth status")
    combined_status = f"{out}\n{err}"
    accounts = parse_gh_auth_status(combined_status)

    active_acc = next((a for a in accounts if a["is_active"]), None)
    if not active_acc and accounts:
        active_acc = accounts[0]

    if not active_acc:
        code, user_out, _ = run_cmd("gh api user --jq .login")
        if code == 0 and user_out:
            active_acc = {"username": user_out.strip(), "is_active": True, "auth_method": "cli"}
            accounts = [active_acc]
        else:
            print("[-] Could not retrieve username from gh CLI. Run 'gh auth login' and restart setup.")
            return False

    username = active_acc["username"]

    # 2. Interactive Selection Menu
    options = [
        {
            "key": f"use_{username}",
            "title": f"Continue as @{username} (Active)",
            "desc": f"Set up GitBot in your active @{username} GitHub account"
        }
    ]

    for acc in accounts:
        if acc["username"].lower() != username.lower():
            options.append({
                "key": f"switch_{acc['username']}",
                "title": f"Switch to @{acc['username']}",
                "desc": f"Use already authenticated account @{acc['username']}"
            })

    options.append({
        "key": "authorize_new",
        "title": "Authorize Another GitHub Account (Browser)",
        "desc": "Authorize a new GitHub account via browser one-time device code"
    })
    options.append({
        "key": "token",
        "title": "Enter Personal Access Token",
        "desc": "Authorize via GitHub Personal Access Token (classic flow)"
    })

    chosen = select_menu("Select GitHub Account", options, default_index=0)
    if not chosen:
        print("[-] Setup cancelled.")
        return False

    if chosen.startswith("switch_"):
        target_user = chosen.split("switch_")[1]
        print(f"\n[*] Switching active GitHub CLI account to @{target_user}...")
        sw_code, sw_out, sw_err = run_cmd(f"gh auth switch --user {target_user}")
        if sw_code != 0:
            print(f"[-] Failed to switch account ({sw_err or sw_out}). Retrying with active account.")
        else:
            username = target_user
            print(f"[+] Successfully switched active account to @{username}!")
    elif chosen == "authorize_new":
        print("\n[*] Opening GitHub authorization in your browser...")
        print("[*] Note: The one-time code will be COPIED to your clipboard automatically!")
        print("[*] When the browser opens, just press Ctrl+V to paste the code and click 'Authorize'!\n")
        subprocess.run("gh auth login --web --clipboard -p https -s repo,workflow --skip-ssh-key", shell=True)
        time.sleep(1)
        code, user_out, _ = run_cmd("gh api user --jq .login")
        if code == 0 and user_out:
            username = user_out.strip()
            print(f"\n[+] Switched successfully! Proceeding as @{username}...")
        else:
            print("[-] Could not verify new login. Continuing with active account...")
    elif chosen == "token":
        print("\n[-] Personal-access-token installation is disabled: GitBot never places tokens in URLs or command lines. Use 'gh auth login' and rerun setup.")
        return False

    # 3. Setup Git credential helper securely via gh
    run_cmd("gh auth setup-git")

    # 4. Retrieve author details and build personalized config
    code, name_out, _ = run_cmd("gh api user --jq .name")
    display_name = name_out.strip() if code == 0 and name_out and name_out != "null" else username

    code, email_out, _ = run_cmd("gh api user/emails --jq '.[0].email'")
    email = email_out.strip() if code == 0 and email_out and email_out != "null" else f"{username}@users.noreply.github.com"

    print(f"[+] Personalizing GitBot for {display_name} <{email}>...")
    personalized_config = {
        "author_name": display_name,
        "author_email": email,
        "connected_repo": f"{username}/GitBot",
        "preset": "active",
        "min_daily_commits": 50,
        "max_daily_commits": 250,
        "normal_max_commits": 145,
        "spike_min_commits": 170,
        "spike_max_commits": 240,
        "max_spikes_per_month": 4,
        "runs_per_day": 4,
        "max_delta_per_day": 32,
        "weekend_mode": "normal",
        "is_paused": False,
        "notification_mode": "every-batch",
        "vacation_mode": False,
        "vacation_end_date": None,
    }

    # 5. Check if repository already exists, or create direct 100% PRIVATE repository
    gitbot_dir = os.path.expanduser("~/.gitbot")
    code, repo_check, _ = run_cmd(f"gh repo view {username}/GitBot --json name --jq .name")
    if code == 0 and repo_check.strip() == "GitBot":
        print(f"\n[+] Repository @{username}/GitBot already exists in your account! Reusing existing repository...")
    else:
        print(f"\n[+] Creating new secure private repository @{username}/GitBot...")
        create_cmd = f"gh repo create {username}/GitBot --private"
        c_code, c_out, c_err = run_cmd(create_cmd)
        time.sleep(2)

        # Initialize clean-slate repository (Single initial commit, 0 leaked history!)
        print("[+] Initializing clean-slate repository template (1 initial commit)...")
        staging_dir = create_clean_slate_staging(username, display_name, email, personalized_config)
        run_cmd(f'git -C "{staging_dir}" remote add origin https://github.com/{username}/GitBot.git')
        p_code, p_out, p_err = run_cmd(f'git -C "{staging_dir}" push -u origin main')
        shutil.rmtree(staging_dir, ignore_errors=True)
        if p_code != 0:
            print(f"[-] Initial push failed ({p_err or p_out}).")
            return False

    # 6. Set workflow write permissions
    verified, detail = verify_identity_chain(username, f"{username}/GitBot")
    if not verified:
        print(f"[-] Installation stopped safely: {detail}.")
        return False
    print("[+] Enabling GitHub Actions workflow write permissions...")
    perm_cmd = f"gh api -X PUT /repos/{username}/GitBot/actions/permissions/workflow -f default_workflow_permissions=write"
    run_cmd(perm_cmd)

    # 7. Update local ~/.gitbot clone so local CLI points to user's repo and starts clean!
    if os.path.exists(gitbot_dir):
        print(f"[+] Linking local gitbot installation to @{username}/GitBot...")
        run_cmd(f'git -C "{gitbot_dir}" remote set-url origin https://github.com/{username}/GitBot.git')
        if display_name or username:
            run_cmd(f'git -C "{gitbot_dir}" config user.name "{display_name or username}"')
        if email:
            run_cmd(f'git -C "{gitbot_dir}" config user.email "{email}"')
        # Never overwrite an existing local installation or its generated state.
        code, dirty, _ = run_cmd(f'git -C "{gitbot_dir}" status --porcelain')
        if code == 0 and dirty:
            print("[-] Existing local GitBot installation has changes; preserving it. Resolve or reinstall manually.")
            return False
        run_cmd(f'git -C "{gitbot_dir}" fetch origin main')

    # 8. Dispatch welcome notification issue thread
    send_welcome_notification(username, display_name, email)

    # 9. Trigger first cloud run
    print("[+] Triggering your first automated cloud run...")
    run_cmd(f"gh workflow run contribute.yml --repo {username}/GitBot")

    show_success(username, is_private=True)
    return True

def install_via_api(is_fallback=False):
    """Legacy PAT installation was removed; GitBot uses authenticated gh CLI only."""
    print("[-] Personal-access-token installation has been removed. Run 'gh auth login' and restart setup.")
    return False

def show_success(username, is_private=True):
    print(f"\n{C.CYAN}{C.BOLD}" + "═" * 76 + f"{C.RESET}")
    print(f"{C.GREEN}{C.BOLD}             🎉  GITBOT INSTALLED & ACTIVATED SUCCESSFULLY!  🎉{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}" + "═" * 76 + f"{C.RESET}\n")

    print(f"{C.BOLD}  Repository :{C.RESET}  {C.CYAN}https://github.com/{username}/GitBot{C.RESET}")
    print(f"{C.BOLD}  Actions    :{C.RESET}  {C.CYAN}https://github.com/{username}/GitBot/actions{C.RESET}")
    print(f"{C.BOLD}  Profile    :{C.RESET}  {C.CYAN}https://github.com/{username}{C.RESET}\n")

    cloud_lines = [
        f"{C.GREEN}{C.BOLD}⚡ CLOUD AUTOMATION ACTIVE{C.RESET}",
        "---",
        f"{C.GREEN}✓{C.RESET} {C.BOLD}100% Cloud-Native:{C.RESET} Runs entirely via GitHub Actions in the cloud.",
        f"{C.GREEN}✓{C.RESET} {C.BOLD}Zero Dependency:{C.RESET}   Your computer/laptop can be powered off.",
        f"{C.GREEN}✓{C.RESET} {C.BOLD}Cadence Schedule:{C.RESET}  4 daily windows (09:45 AM, 02:45 PM, 06:45 PM, 10:45 PM IST).",
        f"{C.GREEN}✓{C.RESET} {C.BOLD}Commit Intensity:{C.RESET}  50–250 commits/day with smooth momentum pacing.",
        f"{C.GREEN}✓{C.RESET} {C.BOLD}Realistic Spikes:{C.RESET}  3–4 active surge days (170–240 commits) per month."
    ]
    print_box(cloud_lines, border_color=C.GREEN, width=76)
    print()

    cli_lines = [
        f"{C.CYAN}{C.BOLD}💻 INTERACTIVE REPL SHELL READY: gitbot{C.RESET}",
        "---",
        f"{C.WHITE}Type {C.CYAN}{C.BOLD}gitbot{C.RESET}{C.WHITE} in any terminal to enter your interactive shell.{C.RESET}",
        f"{C.GRAY}Execute commands directly without retyping 'gitbot' every time:{C.RESET}",
        f"{C.WHITE}  • {C.CYAN}status{C.RESET}    / {C.CYAN}roadmap{C.RESET}  - Live dashboard and session countdown (IST)",
        f"{C.WHITE}  • {C.CYAN}notify{C.RESET}    / {C.CYAN}intensity{C.RESET}- Arrow-key configuration menus (↑/↓ + Enter)",
        f"{C.WHITE}  • {C.CYAN}vacation{C.RESET}  / {C.CYAN}weekend{C.RESET}  - Vacation mode & weekend pacing",
        f"{C.WHITE}  • {C.CYAN}pause{C.RESET}     / {C.CYAN}resume{C.RESET}   - Instant cloud engine controls",
        f"{C.WHITE}  • {C.CYAN}help{C.RESET}      / {C.CYAN}exit{C.RESET}     - Command cheat-sheet and exit"
    ]
    print_box(cli_lines, border_color=C.CYAN, width=76)
    print()

    warning_lines = [
        f"{C.YELLOW}{C.BOLD}⚠️  ACTION REQUIRED: SHOW PRIVATE CONTRIBUTIONS ON GITHUB{C.RESET}",
        "---",
        f"{C.WHITE}Your bot repository is {C.BOLD}100% Private{C.RESET}{C.WHITE} for total stealth.{C.RESET}",
        f"{C.YELLOW}To make your green contribution squares visible on your GitHub profile:{C.RESET}",
        "",
        f" {C.CYAN}1.{C.RESET} Open your GitHub profile in your browser:",
        f"    {C.WHITE}{C.BOLD}https://github.com/{username}{C.RESET}",
        f" {C.CYAN}2.{C.RESET} Scroll down to your {C.BOLD}Contribution Activity{C.RESET} graph.",
        f" {C.CYAN}3.{C.RESET} Click {C.BOLD}'Contribution settings'{C.RESET} (top-right dropdown above graph).",
        f" {C.CYAN}4.{C.RESET} Check: {C.GREEN}{C.BOLD}☑ 'Include private contributions on my profile'{C.RESET}",
        "",
        f"{C.GREEN}{C.BOLD}✓ Done!{C.RESET} Your entire contribution graph will immediately light up green!"
    ]
    print_box(warning_lines, border_color=C.YELLOW, width=76)
    print()

def main():
    banner()
    if not check_gh_cli():
        print("[-] GitHub CLI authentication is required. Run: gh auth login --web -p https -s repo,workflow")
        return 1
    try:
        return 0 if install_via_gh() else 1
    except Exception as e:
        print(f"[-] Secure GitHub CLI setup failed: {str(e).splitlines()[0]}")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[!] Setup cancelled by user. Run the installer or 'gitbot' again anytime.\n")
        sys.exit(0)
