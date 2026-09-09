import json
import os
import random
import subprocess
from datetime import datetime, timezone, timedelta

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION = "7.0.3"

# Indian Standard Time (IST): UTC+05:30
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    return datetime.now(IST)

def get_current_date_ist():
    return get_ist_now().strftime("%Y-%m-%d")

def get_current_time_ist_str():
    return get_ist_now().strftime("%I:%M %p IST")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "state.json")
ACTIVITY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "activity.json")
PROVENANCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "provenance.json")
CONTROL_SCHEMA = 1

DEFAULT_CONFIG = {
    "author_name": "Developer",
    "author_email": "dev@example.com",
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
    "vacation_end_date": None
}

PRESETS = {
    "consistent": {
        "name": "Consistent Dev",
        "description": "Steady active presence with controlled volume (40-90 commits)",
        "min_daily_commits": 40,
        "max_daily_commits": 120,
        "normal_max_commits": 90,
        "spike_min_commits": 100,
        "spike_max_commits": 120,
        "max_spikes_per_month": 3,
        "runs_per_day": 4,
        "max_delta_per_day": 20
    },
    "active": {
        "name": "Active Contributor",
        "description": "Vibrant and natural open-source presence (50-150 commits)",
        "min_daily_commits": 50,
        "max_daily_commits": 200,
        "normal_max_commits": 145,
        "spike_min_commits": 160,
        "spike_max_commits": 200,
        "max_spikes_per_month": 4,
        "runs_per_day": 4,
        "max_delta_per_day": 30
    },
    "hardcore": {
        "name": "Hardcore Coder",
        "description": "High-intensity output with major contribution bursts (80-250 commits)",
        "min_daily_commits": 80,
        "max_daily_commits": 250,
        "normal_max_commits": 180,
        "spike_min_commits": 190,
        "spike_max_commits": 245,
        "max_spikes_per_month": 4,
        "runs_per_day": 4,
        "max_delta_per_day": 40
    }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            if "<<<<<<<" in content:
                lines = []
                in_conflict = False
                for line in content.splitlines():
                    if line.startswith("<<<<<<<") or line.startswith("======="):
                        in_conflict = True
                        continue
                    elif line.startswith(">>>>>>>"):
                        in_conflict = False
                        continue
                    if not in_conflict:
                        lines.append(line)
                content = "\n".join(lines)
            return json.loads(content)
        except Exception:
            pass
    return {
        "date": None,
        "today_target": 80,
        "today_done": 0,
        "runs_completed_today": 0,
        "yesterday_target": 75,
        "current_month": None,
        "spikes_this_month": 0,
        "last_spike_date": None,
        "history": []
    }

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def load_provenance(target_dir=None):
    """Read the committed GitBot event ledger.  Missing data is never guessed."""
    path = os.path.join(target_dir, "data", "provenance.json") if target_dir else PROVENANCE_FILE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("schema") == CONTROL_SCHEMA and isinstance(data.get("events"), dict):
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return {"schema": CONTROL_SCHEMA, "events": {}, "sessions": {}}

def save_provenance(data, target_dir=None):
    path = os.path.join(target_dir, "data", "provenance.json") if target_dir else PROVENANCE_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

def parse_gitbot_trailers(message):
    """Return GitBot trailers only when all required fields occur exactly once."""
    found = {}
    for line in (message or "").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in ("GitBot-Event-Id", "GitBot-Session-Id", "GitBot-Schema"):
            if key in found:
                return None
            found[key] = value.strip()
    if set(found) != {"GitBot-Event-Id", "GitBot-Session-Id", "GitBot-Schema"}:
        return None
    if found["GitBot-Schema"] != str(CONTROL_SCHEMA):
        return None
    return found

def verify_session_remote(session_id, target_dir=None, remote_ref="origin/main"):
    """Verify one session exclusively from the committed ledger and remote history.

    Workflow success, local counters, and author identity are deliberately not proof.
    A verified session has every ledger event exactly once on the selected remote ref,
    with its matching session trailer.  This makes reconciliation safe to repeat.
    """
    result = {"session_id": session_id, "status": "NOT VERIFIED", "reason": "unknown", "events": []}
    if not session_id or not target_dir or not is_git_repo(target_dir):
        result["reason"] = "repository unavailable"
        return result
    try:
        ledger_proc = subprocess.run(
            ["git", "-C", target_dir, "show", f"{remote_ref}:data/provenance.json"],
            capture_output=True, text=True, timeout=20
        )
        ledger = json.loads(ledger_proc.stdout) if ledger_proc.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        ledger = None
    if not isinstance(ledger, dict) or ledger.get("schema") != CONTROL_SCHEMA or not isinstance(ledger.get("events"), dict):
        result["reason"] = "remote provenance ledger unavailable"
        return result
    session = ledger.get("sessions", {}).get(session_id)
    if not isinstance(session, dict) or not isinstance(session.get("events"), list) or not session["events"]:
        result["reason"] = "session has no committed ledger events"
        return result
    expected = session["events"]
    if len(set(expected)) != len(expected):
        result["reason"] = "duplicate event in ledger"
        return result
    for event_id in expected:
        event = ledger.get("events", {}).get(event_id)
        if not isinstance(event, dict) or event.get("session_id") != session_id:
            result["reason"] = "ledger provenance mismatch"
            return result
    try:
        proc = subprocess.run(
            ["git", "-C", target_dir, "log", remote_ref, "--format=%H%x1f%B%x1e"],
            capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError):
        result["reason"] = "remote history unavailable"
        return result
    if proc.returncode != 0:
        result["reason"] = "remote ref unavailable"
        return result
    found = {}
    for record in proc.stdout.split("\x1e"):
        if "\x1f" not in record:
            continue
        sha, message = record.split("\x1f", 1)
        trailers = parse_gitbot_trailers(message)
        if not trailers or trailers["GitBot-Session-Id"] != session_id:
            continue
        event_id = trailers["GitBot-Event-Id"]
        found.setdefault(event_id, []).append(sha.strip())
    duplicates = sorted(event_id for event_id, shas in found.items() if len(shas) != 1)
    missing = sorted(set(expected) - set(found))
    unexpected = sorted(set(found) - set(expected))
    result["events"] = sorted((event_id, found[event_id][0]) for event_id in set(expected) & set(found) if len(found[event_id]) == 1)
    if duplicates:
        result["reason"] = "duplicate remote event trailers"
    elif missing:
        result["reason"] = "expected remote events missing"
    elif unexpected:
        result["reason"] = "unexpected remote event trailers"
    else:
        result["status"] = "VERIFIED"
        result["reason"] = "all ledger events verified on remote"
    return result

def reconcile_verified_sessions(target_dir=None, remote_ref="origin/main"):
    """Persist only session statuses proven by ``verify_session_remote``.

    This is idempotent: already verified sessions are untouched, and an
    unavailable/mismatched remote never changes the local ledger.
    """
    target_dir = target_dir or REPO_DIR
    ledger = load_provenance(target_dir)
    results, changed = [], False
    for session_id, session in ledger.get("sessions", {}).items():
        if not isinstance(session, dict) or session.get("status") != "EXECUTING":
            continue
        result = verify_session_remote(session_id, target_dir, remote_ref)
        results.append(result)
        if result["status"] == "VERIFIED":
            session["status"] = "VERIFIED"
            session["verified_remote_ref"] = remote_ref
            session["verified_event_count"] = len(result["events"])
            changed = True
    if changed:
        save_provenance(ledger, target_dir)
    return results, changed

def calculate_next_target(state, config, current_date_str, seed_key=None):
    """
    Calculates today's commit target using a momentum-controlled Markov random walk.
    Uses a deterministic pseudo-random generator seeded by (seed_key, preset, date)
    so that local and cloud execution always produce identical targets for the same day.
    """
    if seed_key is None:
        seed_key = config.get("author_email") or config.get("author_name") or "gitbot"
    preset_key = config.get("preset", "active")
    rng = random.Random(f"{seed_key}:{preset_key}:{current_date_str}")

    current_month_str = current_date_str[:7]
    
    # Month rollover check
    if state.get("current_month") != current_month_str:
        state["current_month"] = current_month_str
        state["spikes_this_month"] = 0

    yesterday_target = state.get("yesterday_target", 80)
    spikes_done = state.get("spikes_this_month", 0)
    max_spikes = config.get("max_spikes_per_month", 4)
    last_spike_date = state.get("last_spike_date")

    # Check days since last spike
    days_since_last_spike = 99
    if last_spike_date:
        try:
            d_last = datetime.fromisoformat(last_spike_date).date()
            d_curr = datetime.fromisoformat(current_date_str).date()
            days_since_last_spike = (d_curr - d_last).days
        except Exception:
            days_since_last_spike = 99

    # 0. Check Vacation / Maintenance Mode
    if config.get("vacation_mode", False):
        end_date = config.get("vacation_end_date")
        if end_date and current_date_str > end_date:
            # Vacation period expired, return to regular preset
            config["vacation_mode"] = False
            config["vacation_end_date"] = None
            save_config(config)
        else:
            # Vacation is intentionally a single effective reduced mode; weekend
            # reduction is not applied a second time below.
            target = rng.randint(20, 40)
            return target, False

    # Check weekend mode
    weekend_mode = config.get("weekend_mode", "normal")
    is_weekend = False
    try:
        d = datetime.fromisoformat(current_date_str).date()
        is_weekend = (d.weekday() >= 5)
    except Exception:
        pass

    if is_weekend and weekend_mode == "off":
        # Never 0 commits: maintain unbroken streak with light 3-4 maintenance commits
        return rng.choice([3, 4]), False

    # Determine if today is an occasional spike day (170+ commits, 3-4 times/month)
    is_spike = False
    if (not is_weekend or weekend_mode == "normal") and spikes_done < max_spikes and days_since_last_spike >= 6:
        # ~11% chance when eligible to hit 3-4 per month
        if rng.random() < 0.12:
            is_spike = True

    if is_spike:
        target = rng.randint(config.get("spike_min_commits", 170), config.get("spike_max_commits", 240))
        state["spikes_this_month"] = spikes_done + 1
        state["last_spike_date"] = current_date_str
        return target, True

    # Non-spike day: smooth transition from yesterday
    # If yesterday was a spike (> 160), smoothly taper down instead of a steep cliff drop
    if yesterday_target >= 160:
        base = int(yesterday_target * rng.uniform(0.60, 0.72))
        delta = rng.randint(-15, 15)
        target = base + delta
    else:
        # Standard smooth step: delta bounded by max_delta_per_day
        max_delta = config.get("max_delta_per_day", 32)
        # Add slight mean-reversion pull toward sweet spot (85-105)
        mean_pull = 0
        if yesterday_target > 120:
            mean_pull = -rng.randint(4, 12)
        elif yesterday_target < 65:
            mean_pull = rng.randint(4, 12)

        delta = rng.randint(-max_delta, max_delta) + mean_pull
        target = yesterday_target + delta

    # Clamp to normal range [min_daily_commits, normal_max_commits]
    min_limit = config.get("min_daily_commits", 50)
    max_limit = config.get("normal_max_commits", 145)
    target = max(min_limit, min(max_limit, target))

    # Apply weekend adjustments
    if is_weekend and weekend_mode == "light":
        target = max(15, int(target * 0.45))

    # Absolute safety guarantee: Never fewer than 3 commits in any mode
    target = max(3, target)
    return target, False

def ensure_planned_targets(state, config, start_date_str, days=8):
    """Persist a deterministic IST date plan so roadmap values cannot re-roll."""
    plans = state.setdefault("planned_targets", {})
    cursor = datetime.fromisoformat(start_date_str).date()
    simulated = dict(state)
    simulated["planned_targets"] = plans
    for _ in range(days):
        date_str = cursor.isoformat()
        if date_str not in plans:
            target, is_spike = calculate_next_target(simulated, config, date_str)
            plans[date_str] = {"target": target, "is_spike": is_spike, "status": "PLANNED"}
        target = plans[date_str]["target"]
        simulated["yesterday_target"] = target
        cursor += timedelta(days=1)
    return plans

def get_run_batch_size(now_dt=None):
    """
    Returns how many commits to make in this run, and updates the state.
    Uses Indian Standard Time (IST, UTC+05:30) for midnight date rollovers.
    """
    if now_dt is None:
        now_dt = get_ist_now()
    
    date_str = now_dt.strftime("%Y-%m-%d")
    config = load_config()
    state = load_state()

    # If paused, don't execute commits
    if config.get("is_paused", False):
        return 0, state, config

    # If it's a new day or uninitialized
    if state.get("date") != date_str or not state.get("today_target"):
        # Save yesterday's final tally to history
        if state.get("date") is not None and state.get("today_target", 0) > 0:
            state.setdefault("history", []).append({
                "date": state["date"],
                "commits": state.get("today_done", 0),
                "target": state.get("today_target", 0),
                "is_spike": state.get("today_target", 0) >= config.get("spike_min_commits", 170)
            })
            if len(state["history"]) > 90:
                state["history"] = state["history"][-90:]
            state["yesterday_target"] = state.get("today_target", 80)

        # Calculate new target for today
        plans = ensure_planned_targets(state, config, date_str)
        plan = plans[date_str]
        target, is_spike = plan["target"], plan.get("is_spike", False)
        plan["status"] = "LOCKED"
        state["date"] = date_str
        state["today_target"] = target
        state["today_done"] = 0
        state["runs_completed_today"] = 0

    # Ensure state matches actual commits in this repo
    live_stats = get_live_commit_stats()
    state["today_done"] = live_stats.get("today_commits", 0)

    runs_per_day = config.get("runs_per_day", 4)
    runs_done = min(runs_per_day, state.get("runs_completed_today", 0))
    runs_left = max(1, runs_per_day - runs_done)
    commits_left = max(0, state["today_target"] - state.get("today_done", 0))

    if commits_left == 0 or runs_done >= runs_per_day:
        return 0, state, config

    if runs_left == 1:
        # Last run of the day: complete all remaining commits
        batch_size = commits_left
    else:
        # Distribute with slight natural variance
        base = commits_left // runs_left
        variance = random.randint(-3, 4)
        batch_size = max(1, base + variance)
        # Ensure we don't overshoot or leave too few for final run
        batch_size = min(batch_size, commits_left - (runs_left - 1))

    return max(1, batch_size), state, config

def set_paused(paused: bool):
    config = load_config()
    config["is_paused"] = paused
    save_config(config)
    return config

def apply_preset(preset_key: str):
    if preset_key not in PRESETS:
        return None
    preset = PRESETS[preset_key]
    config = load_config()
    config["preset"] = preset_key
    for k in ["min_daily_commits", "max_daily_commits", "normal_max_commits", 
              "spike_min_commits", "spike_max_commits", "max_spikes_per_month", 
              "runs_per_day", "max_delta_per_day"]:
        if k in preset:
            config[k] = preset[k]
    save_config(config)
    return config

def get_notification_mode():
    config = load_config()
    return config.get("notification_mode", "every-batch")

def set_notification_mode(mode: str):
    valid_modes = ["every-batch", "morning-night", "morning-only", "night-only", "off"]
    mode_clean = mode.strip().lower()
    if mode_clean not in valid_modes:
        return None
    config = load_config()
    config["notification_mode"] = mode_clean
    save_config(config)
    return config

def get_weekend_mode():
    config = load_config()
    return config.get("weekend_mode", "normal")

def set_weekend_mode(mode: str):
    valid_modes = ["normal", "light", "off"]
    mode_clean = mode.strip().lower()
    if mode_clean not in valid_modes:
        return None
    config = load_config()
    config["weekend_mode"] = mode_clean
    save_config(config)
    return config

def get_vacation_status():
    config = load_config()
    active = config.get("vacation_mode", False)
    end_date = config.get("vacation_end_date")
    days_left = None
    if active and end_date:
        try:
            today_d = get_ist_now().date()
            end_d = datetime.fromisoformat(end_date).date()
            days_left = (end_d - today_d).days
            if days_left < 0:
                active = False
                config["vacation_mode"] = False
                config["vacation_end_date"] = None
                save_config(config)
                days_left = None
        except Exception:
            pass
    return {
        "active": active,
        "end_date": end_date,
        "days_left": days_left
    }

def enable_vacation(days=None, end_date_str=None):
    config = load_config()
    config["vacation_mode"] = True
    if days:
        end_d = get_ist_now().date() + timedelta(days=days)
        config["vacation_end_date"] = end_d.isoformat()
    elif end_date_str:
        config["vacation_end_date"] = end_date_str
    else:
        config["vacation_end_date"] = None
    save_config(config)
    return config

def disable_vacation():
    config = load_config()
    config["vacation_mode"] = False
    config["vacation_end_date"] = None
    save_config(config)
    return config

DEFAULT_STATE_FILE = os.path.join(REPO_DIR, "data", "state.json")

def classify_commit(c_hash, c_msg, target_dir=None, author_email=None):
    """
    Attribution intentionally does not trust author, subject, or changed files.
    A GitBot event must have all trailers and a matching committed ledger entry.
    """
    if not c_msg:
        return "UNKNOWN"
    clean_msg = c_msg.strip()
    if clean_msg.startswith("feat: initialize GitBot [INITIALIZATION]"):
        return "INITIALIZATION"
    trailers = parse_gitbot_trailers(clean_msg)
    if not trailers or not target_dir or not c_hash:
        return "MANUAL"
    ledger = load_provenance(target_dir)
    event = ledger["events"].get(trailers["GitBot-Event-Id"])
    if not event:
        return "MANUAL"
    if event.get("session_id") != trailers["GitBot-Session-Id"]:
        return "MANUAL"
    # The event is committed in the same tree as the trailer.  Event identifiers
    # are random UUIDs, so accidental message copying cannot create attribution.
    return "GITBOT"

def is_git_repo(target_dir):
    """Check if target_dir is a valid git repository work tree."""
    if not target_dir or not os.path.exists(target_dir):
        return False
    try:
        res = subprocess.run(
            f'git -C "{target_dir}" rev-parse --is-inside-work-tree',
            shell=True, capture_output=True, text=True
        )
        return res.returncode == 0 and res.stdout.strip() == "true"
    except Exception:
        return False

def get_live_git_telemetry(target_dir=None, author_email=None):
    """
    Retrieves complete ground-truth git telemetry using 3-tier attribution:
    - total_commits: Total physical count on origin/main (or HEAD)
    - lifetime_bot_commits: Verified commits generated by GitBot
    - lifetime_manual_commits: Verified manual user commits
    - initialization_commits: Setup/template initial commits
    - commits_by_date: Dict mapping YYYY-MM-DD -> verified bot commit count (IST)
    - today_commits: Verified bot commits made today in IST
    - today_manual_commits: Manual commits made today in IST
    - recent_commits: Last 5 commits with hash, message, attribution, and relative time
    """
    if target_dir is None:
        if os.path.abspath(STATE_FILE) != os.path.abspath(DEFAULT_STATE_FILE):
            target_dir = os.path.dirname(os.path.dirname(os.path.abspath(STATE_FILE)))
        else:
            gitbot_home = os.path.expanduser("~/.gitbot")
            target_dir = gitbot_home if os.path.exists(gitbot_home) else REPO_DIR

    if not is_git_repo(target_dir):
        state = load_state()
        today_commits = state.get("today_done", 0)
        commits_by_date = {}
        for h in state.get("history", []):
            if isinstance(h, dict) and "date" in h:
                commits_by_date[h["date"]] = h.get("commits", 0)
        today_str = get_ist_now().strftime("%Y-%m-%d")
        cur_date = state.get("date") or today_str
        if today_commits > 0:
            commits_by_date[cur_date] = today_commits
        tot = today_commits + sum(h.get("commits", 0) for h in state.get("history", []) if isinstance(h, dict))
        return {
            "total_commits": tot,
            "lifetime_bot_commits": tot,
            "lifetime_manual_commits": 0,
            "initialization_commits": 0,
            "today_commits": today_commits,
            "today_manual_commits": 0,
            "commits_by_date": commits_by_date,
            "recent_commits": []
        }

    ref = "HEAD"
    try:
        chk = subprocess.run(
            f'git -C "{target_dir}" rev-parse --verify origin/main',
            shell=True, capture_output=True, text=True
        )
        if chk.returncode == 0 and chk.stdout.strip():
            ref = "origin/main"
    except Exception:
        ref = "HEAD"

    total_count = 0
    try:
        res_tot = subprocess.run(
            f'git -C "{target_dir}" rev-list --count {ref}',
            shell=True, capture_output=True, text=True
        )
        if res_tot.returncode == 0 and res_tot.stdout.strip().isdigit():
            total_count = int(res_tot.stdout.strip())
    except Exception:
        pass

    commits_by_date = {}
    recent_commits = []
    lifetime_bot_commits = 0
    lifetime_manual_commits = 0
    initialization_commits = 0
    today_str = get_ist_now().strftime("%Y-%m-%d")
    today_bot_commits = 0
    today_manual_commits = 0

    try:
        res_log = subprocess.run(
            f'git -C "{target_dir}" log {ref} --format="%H%x1f%cI%x1f%B%x1f%cr%x1f%ae%x1e"',
            shell=True, capture_output=True, text=True
        )
        if res_log.returncode == 0 and res_log.stdout:
            for record in res_log.stdout.split("\x1e"):
                if not record.strip():
                    continue
                parts = record.strip("\n").split("\x1f")
                if len(parts) < 5:
                    continue
                c_hash = parts[0]
                iso_str = parts[1].replace("Z", "+00:00")
                c_msg = parts[2] if len(parts) > 2 else ""
                c_rel = parts[3] if len(parts) > 3 else ""
                c_author = parts[4] if len(parts) > 4 else ""

                c_class = classify_commit(c_hash, c_msg, target_dir, author_email or c_author)
                try:
                    dt_ist = datetime.fromisoformat(iso_str).astimezone(IST)
                    d_str = dt_ist.strftime("%Y-%m-%d")
                except Exception:
                    d_str = today_str
                    dt_ist = get_ist_now()

                if c_class == "GITBOT":
                    lifetime_bot_commits += 1
                    commits_by_date[d_str] = commits_by_date.get(d_str, 0) + 1
                    if d_str == today_str:
                        today_bot_commits += 1
                elif c_class == "INITIALIZATION":
                    initialization_commits += 1
                else:
                    lifetime_manual_commits += 1
                    if d_str == today_str:
                        today_manual_commits += 1

                if len(recent_commits) < 5:
                    recent_commits.append({
                        "hash": c_hash,
                        "date": d_str,
                        "time_ist": dt_ist.strftime("%I:%M %p"),
                        "message": c_msg,
                        "attribution": c_class,
                        "relative": c_rel
                    })
    except Exception:
        pass

    return {
        "total_commits": total_count,
        "lifetime_bot_commits": lifetime_bot_commits,
        "lifetime_manual_commits": lifetime_manual_commits,
        "initialization_commits": initialization_commits,
        "today_commits": today_bot_commits,
        "today_manual_commits": today_manual_commits,
        "commits_by_date": commits_by_date,
        "recent_commits": recent_commits
    }

def get_live_commit_stats(target_dir=None):
    """
    Retrieves ground-truth commit statistics directly from git (backward compatibility wrapper).
    """
    telemetry = get_live_git_telemetry(target_dir)
    return {
        "today_commits": telemetry["today_commits"],
        "total_commits": telemetry["total_commits"]
    }

def get_live_system_snapshot(target_dir=None, now_dt=None, force_sync=False):
    """
    Authoritative Central Tracking Layer and Single Source of Truth (SSOT).
    Produces a complete, consistent snapshot of the system state, git ground truth,
    today's agenda, and strategic lookahead across all 7 data domains.
    Used universally by status, today, roadmap, logs, and doctor.
    """
    if now_dt is None:
        now_dt = get_ist_now()

    config = load_config()
    state = load_state()
    vacation_info = get_vacation_status()
    date_str = now_dt.strftime("%Y-%m-%d")
    time_str = now_dt.strftime("%I:%M %p IST")

    if target_dir is None:
        if os.path.abspath(STATE_FILE) != os.path.abspath(DEFAULT_STATE_FILE):
            target_dir = os.path.dirname(os.path.dirname(os.path.abspath(STATE_FILE)))
        else:
            gitbot_home = os.path.expanduser("~/.gitbot")
            target_dir = gitbot_home if os.path.exists(gitbot_home) else REPO_DIR

    # 1. Evaluate Remote Freshness / Handshake
    freshness_state = "VERIFIED"
    if force_sync:
        try:
            chk_rem = subprocess.run(
                f'git -C "{target_dir}" remote get-url origin',
                shell=True, capture_output=True, text=True
            )
            if chk_rem.returncode == 0 and chk_rem.stdout.strip():
                fetch_res = subprocess.run(
                    f'git -C "{target_dir}" fetch origin main',
                    shell=True, capture_output=True, text=True, timeout=8
                )
                if fetch_res.returncode == 0:
                    freshness_state = "VERIFIED"
                else:
                    freshness_state = "STALE"
            else:
                freshness_state = "UNVERIFIED"
        except Exception:
            freshness_state = "OFFLINE"
    else:
        try:
            chk_rem = subprocess.run(
                f'git -C "{target_dir}" remote get-url origin',
                shell=True, capture_output=True, text=True
            )
            if chk_rem.returncode != 0 or not chk_rem.stdout.strip():
                freshness_state = "UNVERIFIED"
            else:
                freshness_state = "VERIFIED"
        except Exception:
            freshness_state = "UNVERIFIED"

    # 2. Query ground-truth git telemetry with 3-tier attribution
    telemetry = get_live_git_telemetry(target_dir, author_email=config.get("author_email"))
    live_today = telemetry["today_commits"]
    total_commits = telemetry["total_commits"]
    lifetime_bot_commits = telemetry.get("lifetime_bot_commits", live_today)
    lifetime_manual_commits = telemetry.get("lifetime_manual_commits", 0)
    initialization_commits = telemetry.get("initialization_commits", 0)
    today_manual_commits = telemetry.get("today_manual_commits", 0)
    commits_by_date = telemetry["commits_by_date"]
    recent_commits = telemetry["recent_commits"]

    # 3. Deterministic target generation & Immutability
    today_done = live_today  # Ground truth strictly governs completed count (Downward-correction supported!)

    if state.get("date") != date_str or not state.get("today_target"):
        plans = ensure_planned_targets(state, config, date_str)
        plan = plans[date_str]
        target, is_spike = plan["target"], plan.get("is_spike", False)
        plan["status"] = "LOCKED"
        state["date"] = date_str
        state["today_target"] = target
        state["today_done"] = today_done
        state["runs_completed_today"] = 0
        save_state(state)
        today_target = target
        runs_done = 0
    else:
        today_target = state.get("today_target", 80)
        runs_done = state.get("runs_completed_today", 0)
        # Today’s target is immutably locked and never inflated.

    if state.get("today_done") != today_done:
        state["today_done"] = today_done
        save_state(state)

    # 3. Session Windows in IST
    windows = [
        {"id": 1, "name": "Morning Session", "time_str": "09:45 AM IST", "hour": 9, "minute": 45},
        {"id": 2, "name": "Afternoon Session", "time_str": "02:45 PM IST", "hour": 14, "minute": 45},
        {"id": 3, "name": "Evening Session", "time_str": "06:45 PM IST", "hour": 18, "minute": 45},
        {"id": 4, "name": "Night Session", "time_str": "10:45 PM IST", "hour": 22, "minute": 45},
    ]

    runs_per_day = len(windows)
    base_commits = today_target // runs_per_day
    rem = today_target % runs_per_day

    current_minutes = now_dt.hour * 60 + now_dt.minute
    sessions = []
    next_window = None
    min_future_diff = 99999

    for w in windows:
        w_minutes = w["hour"] * 60 + w["minute"]
        diff = w_minutes - current_minutes
        if diff > 0 and diff < min_future_diff:
            min_future_diff = diff
            next_window = w

    for i, w in enumerate(windows):
        w_commits = base_commits + (rem if i == runs_per_day - 1 else 0)

        if i < runs_done:
            status = "completed"
        elif i == runs_done:
            status = "next_up"
        else:
            status = "scheduled"

        sessions.append({
            "id": w["id"],
            "name": w["name"],
            "time_str": w["time_str"],
            "planned_commits": w_commits,
            "status": status
        })

    # Countdown calculation
    if next_window is not None:
        hours = min_future_diff // 60
        mins = min_future_diff % 60
        countdown_str = f"in {hours}h {mins}m ({next_window['name']})" if hours > 0 else f"in {mins}m ({next_window['name']})"
        next_session_str = f"{next_window['time_str']} ({countdown_str})"
    else:
        tomorrow_diff = (24 * 60 - current_minutes) + (9 * 60 + 45)
        hours = tomorrow_diff // 60
        mins = tomorrow_diff % 60
        countdown_str = f"tomorrow in {hours}h {mins}m (Morning Session)"
        next_session_str = f"Tomorrow 09:45 AM IST ({countdown_str})"

    has_upcoming_today = any(s["status"] in ("next_up", "scheduled") for s in sessions)
    remaining_sessions = sum(1 for s in sessions if s["status"] in ("next_up", "scheduled"))
    remaining_commits = max(0, today_target - today_done)

    raw_pct = int(round((today_done / max(1, today_target)) * 100))
    if today_done < today_target or runs_done < runs_per_day or has_upcoming_today:
        pct = min(99, raw_pct)
    else:
        pct = 100

    # 4. Weekly Breakdown (Monday to Sunday) from Ground Truth
    monday_dt = (now_dt - timedelta(days=now_dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_days = []
    week_done = 0
    for i in range(7):
        day_dt = monday_dt + timedelta(days=i)
        d_str = day_dt.strftime("%Y-%m-%d")
        d_name = day_dt.strftime("%a")
        is_today = (d_str == date_str)
        is_past = (day_dt.date() < now_dt.date())
        is_future = (day_dt.date() > now_dt.date())

        if is_today:
            c_count = today_done
        elif is_past:
            c_count = commits_by_date.get(d_str, 0)
        else:
            c_count = None

        if c_count is not None:
            week_done += c_count

        week_days.append({
            "date": d_str,
            "day": d_name,
            "is_today": is_today,
            "is_past": is_past,
            "is_future": is_future,
            "commits": c_count
        })

    # Week target based on preset pacing
    est_weekly_target = today_target * 5
    if config.get("weekend_mode") == "off":
        est_weekly_target += 8
    elif config.get("weekend_mode") == "light":
        est_weekly_target += int(today_target * 0.8)
    else:
        est_weekly_target += today_target * 2
    week_pct = int(round((week_done / max(1, est_weekly_target)) * 100))

    # 5. Streak Calculation from real git dates
    streak = 0
    check_dt = now_dt.date()
    if commits_by_date.get(date_str, 0) > 0 or today_done > 0:
        streak += 1
        check_dt -= timedelta(days=1)
    else:
        check_dt -= timedelta(days=1)

    while True:
        d_str = check_dt.strftime("%Y-%m-%d")
        if commits_by_date.get(d_str, 0) > 0:
            streak += 1
            check_dt -= timedelta(days=1)
        else:
            break

    # 6. 7-Day Lookahead Calendar. Values shown here are committed plans, not
    # fresh predictions; a displayed date therefore becomes its locked target.
    lookahead_7d = []
    curr_t = today_target
    delta = config.get("max_delta_per_day", 30)
    norm_max = config.get("normal_max_commits", 145)
    min_commits = config.get("min_daily_commits", 50)
    weekend_mode = config.get("weekend_mode", "normal")

    plans = ensure_planned_targets(state, config, date_str)
    for day_offset in range(1, 8):
        future_dt = now_dt + timedelta(days=day_offset)
        f_day = future_dt.strftime("%a (%b %d)")
        is_wknd = future_dt.weekday() in (5, 6)

        planned = plans[future_dt.date().isoformat()]["target"]
        rng_str = f"{planned} commits"
        mode_lbl = "PLANNED"

        lookahead_7d.append({
            "day_label": f_day,
            "range": rng_str,
            "mode": mode_lbl
        })

    # 7. Milestone Progression
    milestone_targets = [100, 250, 500, 1000, 2500, 5000, 10000]
    next_milestone = next((m for m in milestone_targets if m > total_commits), 10000)
    prev_milestone = next((m for m in reversed(milestone_targets) if m <= total_commits), 0)
    ms_pct = min(100, int(round((total_commits / max(1, next_milestone)) * 100)))

    # 8. Spikes tracking
    spikes_done = state.get("spikes_this_month", 0)
    max_spikes = config.get("max_spikes_per_month", 4)

    # 9. Format labels
    if vacation_info["active"]:
        preset_name = "Vacation Mode"
        vac_sub = f"{vacation_info['days_left']}d left" if vacation_info.get("days_left") is not None else "Ongoing"
        pacing_name = f"20-40/day ({vac_sub})"
    else:
        preset_name = config.get("preset", "active").title()
        pacing_name = config.get("weekend_mode", "normal").title()

    notify_mode = config.get("notification_mode", "every-batch").upper()
    velocity_str = f"{config.get('min_daily_commits', 50)} – {config.get('max_daily_commits', 250)} commits / day"

    recent_days = []
    for d in sorted(commits_by_date.keys(), reverse=True)[:5]:
        recent_days.append({
            "date": d,
            "commits": commits_by_date[d]
        })
    recent_days.reverse()

    save_state(state)
    return {
        "author_name": config.get("author_name", "Developer"),
        "author_email": config.get("author_email", "dev@example.com"),
        "preset": config.get("preset", "active"),
        "preset_name": preset_name,
        "pacing_name": pacing_name,
        "notify_mode": notify_mode,
        "velocity_str": velocity_str,
        "is_paused": config.get("is_paused", False),
        "vacation_status": vacation_info,
        "date_str": date_str,
        "time_str": time_str,
        "now_dt": now_dt,
        "today_target": today_target,
        "today_done": today_done,
        "remaining_commits": remaining_commits,
        "raw_pct": raw_pct,
        "pct": pct,
        "total_commits": total_commits,
        "total_runs": runs_per_day,
        "runs_done": min(runs_done, runs_per_day),
        "sessions": sessions,
        "countdown": countdown_str,
        "next_session_str": next_session_str,
        "has_upcoming_today": has_upcoming_today,
        "remaining_sessions": remaining_sessions,
        "week_days": week_days,
        "week_done": week_done,
        "week_target": est_weekly_target,
        "week_pct": week_pct,
        "streak": streak,
        "lookahead_7d": lookahead_7d,
        "next_milestone": next_milestone,
        "prev_milestone": prev_milestone,
        "milestone_pct": ms_pct,
        "spikes_done": spikes_done,
        "max_spikes": max_spikes,
        "recent_commits": recent_commits,
        "recent_days": recent_days,
        "commits_by_date": commits_by_date,
        "freshness_state": freshness_state,
        "lifetime_bot_commits": lifetime_bot_commits,
        "lifetime_manual_commits": lifetime_manual_commits,
        "initialization_commits": initialization_commits,
        "today_manual_commits": today_manual_commits,
        "lineage": {
            "total": total_commits,
            "bot": lifetime_bot_commits,
            "manual": lifetime_manual_commits,
            "initialization": initialization_commits
        }
    }

def reconcile_today_state(state=None, config=None, target_dir=None, now_dt=None):
    """
    Authoritative single source of truth for today's commit statistics (backward compatibility).
    """
    snap = get_live_system_snapshot(target_dir=target_dir, now_dt=now_dt)
    return {
        "date_str": snap["date_str"],
        "today_target": snap["today_target"],
        "today_done": snap["today_done"],
        "runs_done": snap["runs_done"],
        "live_stats": {
            "today_commits": snap["today_done"],
            "total_commits": snap["total_commits"]
        }
    }

def get_daily_roadmap(now_dt=None, target_dir=None):
    """
    Computes today's detailed multi-session execution roadmap in Indian Standard Time (IST),
    derived directly from the authoritative system snapshot.
    """
    snap = get_live_system_snapshot(target_dir=target_dir, now_dt=now_dt)
    return {
        "date": snap["date_str"],
        "author_name": snap["author_name"],
        "author_email": snap["author_email"],
        "preset": snap["preset"],
        "today_target": snap["today_target"],
        "today_done": snap["today_done"],
        "runs_completed": snap["runs_done"],
        "total_runs": snap["total_runs"],
        "countdown": snap["countdown"],
        "sessions": snap["sessions"],
        "lookahead": snap["lookahead_7d"][:3],
        "is_paused": snap["is_paused"],
        "notification_mode": snap["notify_mode"].lower(),
        "vacation_status": snap["vacation_status"],
        "total_commits": snap["total_commits"]
    }

def get_strategic_roadmap(now_dt=None, target_dir=None):
    """
    Computes the strategic multi-day and multi-week horizon roadmap,
    derived directly from the authoritative system snapshot.
    """
    snap = get_live_system_snapshot(target_dir=target_dir, now_dt=now_dt)
    return {
        "date": snap["date_str"],
        "author_name": snap["author_name"],
        "author_email": snap["author_email"],
        "preset": snap["preset"],
        "today_target": snap["today_target"],
        "today_done": snap["today_done"],
        "week_days": snap["week_days"],
        "week_done": snap["week_done"],
        "week_target": snap["week_target"],
        "streak": snap["streak"],
        "lookahead_7d": snap["lookahead_7d"],
        "total_commits": snap["total_commits"],
        "next_milestone": snap["next_milestone"],
        "prev_milestone": snap["prev_milestone"],
        "milestone_pct": snap["milestone_pct"],
        "spikes_done": snap["spikes_done"],
        "max_spikes": snap["max_spikes"],
        "vacation_status": snap["vacation_status"],
        "is_paused": snap["is_paused"]
    }



