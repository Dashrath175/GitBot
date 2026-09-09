import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
import hashlib
import uuid

import engine

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "activity.json")

COMMIT_CATEGORIES = [
    {
        "type": "chore",
        "scope": "sync",
        "messages": [
            "update automated activity checkpoint",
            "sync telemetry state and status log",
            "refresh automated heartbeat log",
            "daily routine telemetry check"
        ]
    },
    {
        "type": "perf",
        "scope": "metrics",
        "messages": [
            "record performance latency snapshot",
            "optimize state cache buffer",
            "update response benchmark metrics",
            "sync compute resource statistics"
        ]
    },
    {
        "type": "fix",
        "scope": "logger",
        "messages": [
            "align timestamp drift in event sequence",
            "sanitize expired log buffer indices",
            "resolve minor event ordering anomaly",
            "normalize telemetry timestamps"
        ]
    },
    {
        "type": "feat",
        "scope": "telemetry",
        "messages": [
            "append system status sample",
            "record new health metric point",
            "register distributed activity event",
            "capture environment diagnostics"
        ]
    },
    {
        "type": "docs",
        "scope": "activity",
        "messages": [
            "refresh runtime snapshot summary",
            "document latest telemetry metrics",
            "update system execution logs"
        ]
    }
]

EVENT_TYPES = [
    "HEALTH_CHECK",
    "METRICS_SYNC",
    "CACHE_FLUSH",
    "STATE_BACKUP",
    "TELEMETRY_SAMPLE",
    "DIAGNOSTIC_PING"
]

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"total_contributions": 0, "last_updated": None, "history": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"total_contributions": 0, "last_updated": None, "history": []}

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, cwd=REPO_DIR, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def generate_random_entry():
    now = engine.get_ist_now()
    seed_str = f"{now.isoformat()}-{random.random()}"
    entry_hash = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:12]
    
    return {
        "id": entry_hash,
        "timestamp": now.isoformat(),
        "event": random.choice(EVENT_TYPES),
        "latency_ms": round(random.uniform(12.5, 95.0), 2),
        "status": "HEALTHY",
        "entropy_seed": round(random.random(), 4)
    }

def make_commit(data, state):
    category = random.choice(COMMIT_CATEGORIES)
    msg_template = random.choice(category["messages"])
    session_id = state.get("active_session_id") or f"{state.get('date', engine.get_current_date_ist())}-run-{state.get('runs_completed_today', 0) + 1}"
    event_id = str(uuid.uuid4())
    commit_msg = (
        f"{category['type']}({category['scope']}): {msg_template}\n\n"
        f"GitBot-Event-Id: {event_id}\n"
        f"GitBot-Session-Id: {session_id}\n"
        f"GitBot-Schema: {engine.CONTROL_SCHEMA}"
    )

    entry = generate_random_entry()
    
    data["total_contributions"] = data.get("total_contributions", 0) + 1
    data["last_updated"] = entry["timestamp"]
    data.setdefault("history", []).append(entry)

    # Keep only the most recent 100 entries so repo stays fast and lean
    if len(data["history"]) > 100:
        data["history"] = data["history"][-100:]

    state["today_done"] = state.get("today_done", 0) + 1
    state["active_session_id"] = session_id

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(DATA_FILE)))
    ledger = engine.load_provenance(repo_dir)
    ledger["events"][event_id] = {
        "session_id": session_id,
        "date": state.get("date", engine.get_current_date_ist()),
        "status": "committed"
    }
    ledger["sessions"].setdefault(session_id, {"date": state.get("date"), "status": "EXECUTING", "events": []})["events"].append(event_id)

    save_data(data)
    engine.save_state(state)
    engine.save_provenance(ledger, repo_dir)

    # Git stage and commit
    run_cmd('git add data/activity.json data/state.json data/provenance.json')
    result = subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, capture_output=True, text=True)
    return result.returncode == 0, commit_msg

def dispatch_notification(report_type, state, config, commits_this_run):
    """
    Records a GitHub Issue notification attempt. Email delivery is intentionally
    not claimed because GitHub account notification preferences control it.
    """
    email = config.get("author_email", "developer")
    today_target = state.get("today_target", 0)
    today_done = state.get("today_done", 0)
    date_str = state.get("date", engine.get_current_date_ist())

    preset_name = "Vacation Mode (20–40 commits/day)" if config.get("vacation_mode") else config.get('preset', 'active').capitalize()

    if report_type == "digest":
        title = f"📊 GitBot Daily Activity Digest — {date_str} (IST)"
        body = f"""### {title}

- **Today's Total**: {today_done} / {today_target} commits completed ({round(today_done / max(1, today_target) * 100)}% ✓)
- **Active Preset**: {preset_name}
- **Sessions Completed**: {state.get('runs_completed_today', 0)} / {config.get('runs_per_day', 4)}
- **Recipient**: `{email}`
- **Engine Status**: Healthy & Synced in Cloud (IST Cadence)

*Sent automatically by GitBot Cloud Engine (Daily Digest Mode).*
"""
    else:
        title = f"⚡ GitBot Session Alert — {date_str}"
        body = f"""### {title}

- **Commits in This Session**: {commits_this_run}
- **Today's Progress**: {today_done} / {today_target} commits
- **Sessions Completed**: {state.get('runs_completed_today', 0)} / {config.get('runs_per_day', 4)}
- **Recipient**: `{email}`

*Sent automatically by GitBot Cloud Engine (Per-Run Alert Mode).*
"""

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")

    if not token or not repo:
        print(f"[Notification] {title} recorded locally; no remote notification attempt was made.")
        return

    try:
        import urllib.request
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "GitBot-Engine",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        # 1. Search for existing GitBot Notification Feed issue
        list_url = f"https://api.github.com/repos/{repo}/issues?state=all&per_page=30"
        req = urllib.request.Request(list_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            issues = json.loads(resp.read().decode("utf-8"))

        feed_issue_num = None
        for iss in issues:
            if "GitBot Activity & Notification Feed" in iss.get("title", ""):
                feed_issue_num = iss.get("number")
                break

        if feed_issue_num:
            # Post comment
            comment_url = f"https://api.github.com/repos/{repo}/issues/{feed_issue_num}/comments"
            data = json.dumps({"body": body}).encode("utf-8")
            c_req = urllib.request.Request(comment_url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(c_req):
                print(f"[Notification] GitHub Issue comment posted to #{feed_issue_num}; delivery is unverified.")
        else:
            # Create new issue thread
            create_url = f"https://api.github.com/repos/{repo}/issues"
            data = json.dumps({
                "title": "🤖 GitBot Activity & Notification Feed",
                "body": body
            }).encode("utf-8")
            c_req = urllib.request.Request(create_url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(c_req) as new_iss_resp:
                new_iss = json.loads(new_iss_resp.read().decode("utf-8"))
                print(f"[Notification] GitHub Issue feed created (#{new_iss.get('number')}); delivery is unverified.")
    except Exception as e:
        print(f"[Notification] GitHub Issue notification attempt failed ({e}). Continuing.")

def main():
    batch_size, state, config = engine.get_run_batch_size()
    today_target = state.get("today_target", 0)
    today_done = state.get("today_done", 0)
    
    print(f"=== GitBot Scheduled Run ===")
    print(f"Date: {state.get('date')} | Target for today: {today_target} commits")
    print(f"Already done today: {today_done} | Commits for this run: {batch_size}")

    if batch_size <= 0:
        if config.get("is_paused", False):
            print("GitBot is currently PAUSED. Exiting cleanly with 0 commits.")
        else:
            print("Daily target already completed. Exiting cleanly.")
        return 0

    data = load_data()
    successful = 0

    for i in range(batch_size):
        if i == batch_size - 1:
            state["runs_completed_today"] = state.get("runs_completed_today", 0) + 1
        success, msg = make_commit(data, state)
        if success:
            successful += 1
            if (i + 1) % 10 == 0 or i == batch_size - 1:
                print(f"Progress: [{i + 1}/{batch_size}] {msg}")
        time.sleep(0.05)  # Tiny delay for distinct microsecond ordering

    # Final guarantee: persist state and ensure clean git status
    save_data(data)
    engine.save_state(state)
    run_cmd('git add data/activity.json data/state.json data/provenance.json')
    code, diff_out, _ = run_cmd('git diff --cached --name-only')
    if diff_out:
        run_cmd('git commit -m "chore(sync): finalize run checkpoint"')

    print(f"Successfully committed {successful}/{batch_size} in this run.")
    print(f"Today's progress: {state['today_done']}/{today_target} commits completed.")

    # Check notification dispatch
    notif_mode = config.get("notification_mode", "every-batch")
    runs_done = state.get("runs_completed_today", 0)
    runs_total = config.get("runs_per_day", 4)
    is_last_run = (runs_done >= runs_total or state["today_done"] >= today_target)

    if notif_mode == "every-batch":
        dispatch_notification("batch", state, config, successful)
    elif notif_mode == "morning-night" and runs_done in (1, runs_total):
        dispatch_notification("morning" if runs_done == 1 else "night", state, config, successful)
    elif notif_mode == "morning-only" and runs_done == 1:
        dispatch_notification("morning", state, config, successful)
    elif notif_mode == "night-only" and is_last_run:
        dispatch_notification("night", state, config, successful)

    return 0

if __name__ == "__main__":
    sys.exit(main())
