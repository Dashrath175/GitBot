import unittest
import os
import tempfile
import json
import subprocess
import shutil
from datetime import datetime, timezone
from unittest.mock import patch

import engine
import bot
import cli
import installer

class TestGitBotEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_config_file = engine.CONFIG_FILE
        self.original_state_file = engine.STATE_FILE

        engine.CONFIG_FILE = os.path.join(self.temp_dir.name, "config.json")
        engine.STATE_FILE = os.path.join(self.temp_dir.name, "data", "state.json")

    def tearDown(self):
        engine.CONFIG_FILE = self.original_config_file
        engine.STATE_FILE = self.original_state_file
        self.temp_dir.cleanup()

    def test_default_config(self):
        cfg = engine.load_config()
        self.assertIn("author_name", cfg)
        self.assertIn("author_email", cfg)
        self.assertEqual(cfg["min_daily_commits"], 50)
        self.assertEqual(cfg["max_daily_commits"], 250)
        self.assertEqual(cfg["runs_per_day"], 4)
        self.assertEqual(cfg["weekend_mode"], "normal")
        self.assertFalse(cfg["is_paused"])

    def test_custom_config(self):
        custom = {
            "author_name": "TestUser",
            "author_email": "test@example.com",
            "min_daily_commits": 60,
            "max_daily_commits": 200
        }
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(custom, f)

        cfg = engine.load_config()
        self.assertEqual(cfg["author_name"], "TestUser")
        self.assertEqual(cfg["author_email"], "test@example.com")
        self.assertEqual(cfg["min_daily_commits"], 60)
        self.assertEqual(cfg["runs_per_day"], 4)

    def test_presets_application(self):
        # Consistent
        cfg = engine.apply_preset("consistent")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["preset"], "consistent")
        self.assertEqual(cfg["min_daily_commits"], 40)
        self.assertEqual(cfg["normal_max_commits"], 90)

        # Hardcore
        cfg = engine.apply_preset("hardcore")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["preset"], "hardcore")
        self.assertEqual(cfg["min_daily_commits"], 80)
        self.assertEqual(cfg["max_daily_commits"], 250)

        # Active
        cfg = engine.apply_preset("active")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["preset"], "active")
        self.assertEqual(cfg["min_daily_commits"], 50)

        # Invalid
        self.assertIsNone(engine.apply_preset("unknown_preset"))

    def test_state_load_and_save(self):
        st = engine.load_state()
        self.assertIsNone(st["date"])
        self.assertEqual(st["today_done"], 0)

        st["date"] = "2026-09-06"
        st["today_done"] = 25
        st["today_target"] = 100
        engine.save_state(st)

        reloaded = engine.load_state()
        self.assertEqual(reloaded["date"], "2026-09-06")
        self.assertEqual(reloaded["today_done"], 25)
        self.assertEqual(reloaded["today_target"], 100)

    def test_calculate_next_target_bounds(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        state = {
            "date": "2026-09-05",
            "yesterday_target": 80,
            "current_month": "2026-09",
            "spikes_this_month": 4,
            "last_spike_date": "2026-09-01",
        }

        # 2026-09-02 was Wednesday (weekday)
        for _ in range(50):
            target, is_spike = engine.calculate_next_target(state, cfg, "2026-09-02")
            self.assertFalse(is_spike)
            self.assertGreaterEqual(target, cfg["min_daily_commits"])
            self.assertLessEqual(target, cfg["normal_max_commits"])

    def test_weekend_modes(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        state = {
            "yesterday_target": 80,
            "current_month": "2026-09",
            "spikes_this_month": 0,
        }
        sunday_str = "2026-09-06"

        # Weekend mode: off -> strictly 3 to 4 maintenance commits (never 0!)
        cfg["weekend_mode"] = "off"
        tgt_off, _ = engine.calculate_next_target(state, cfg, sunday_str)
        self.assertIn(tgt_off, [3, 4])

        # Weekend mode: light -> reduced
        cfg["weekend_mode"] = "light"
        tgt_light, _ = engine.calculate_next_target(state, cfg, sunday_str)
        self.assertGreater(tgt_light, 0)
        self.assertLessEqual(tgt_light, 80)

    def test_pause_and_resume(self):
        engine.set_paused(True)
        cfg = engine.load_config()
        self.assertTrue(cfg["is_paused"])

        batch, _, _ = engine.get_run_batch_size()
        self.assertEqual(batch, 0)

        engine.set_paused(False)
        cfg = engine.load_config()
        self.assertFalse(cfg["is_paused"])

    def test_post_spike_taper(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        state = {
            "yesterday_target": 220,
            "current_month": "2026-09",
            "spikes_this_month": 1,
            "last_spike_date": "2026-09-05",
        }
        target, is_spike = engine.calculate_next_target(state, cfg, "2026-09-02")
        self.assertLess(target, 200)
        self.assertGreaterEqual(target, cfg["min_daily_commits"])

    def test_get_run_batch_size_distribution(self):
        cfg = {
            "min_daily_commits": 50,
            "max_daily_commits": 250,
            "normal_max_commits": 145,
            "runs_per_day": 4,
            "is_paused": False
        }
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = {
            "date": today_str,
            "today_target": 100,
            "today_done": 0,
            "runs_completed_today": 0,
            "yesterday_target": 80,
            "current_month": today_str[:7],
            "spikes_this_month": 0,
            "history": []
        }
        engine.save_state(state)

        batch1, state1, _ = engine.get_run_batch_size()
        self.assertGreater(batch1, 0)
        self.assertLessEqual(batch1, 100)

        state1["today_done"] = 100
        engine.save_state(state1)

        batch_done, _, _ = engine.get_run_batch_size()
        self.assertEqual(batch_done, 0)

    def test_random_entry_generation(self):
        entry = bot.generate_random_entry()
        self.assertIn("id", entry)
        self.assertIn("timestamp", entry)
        self.assertIn("event", entry)
        self.assertIn("latency_ms", entry)
        self.assertEqual(entry["status"], "HEALTHY")

    def test_daily_roadmap(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = {
            "date": today_str,
            "today_target": 80,
            "today_done": 20,
            "runs_completed_today": 1,
            "yesterday_target": 75,
            "history": []
        }
        engine.save_state(state)

        rm = engine.get_daily_roadmap()
        self.assertIn("date", rm)
        self.assertEqual(rm["today_target"], 80)
        self.assertEqual(rm["today_done"], 20)
        self.assertEqual(len(rm["sessions"]), 4)
        self.assertEqual(rm["sessions"][0]["status"], "completed")
        self.assertEqual(rm["sessions"][1]["status"], "next_up")
        self.assertEqual(rm["sessions"][2]["status"], "scheduled")
        self.assertEqual(rm["sessions"][3]["status"], "scheduled")
        self.assertIn("countdown", rm)
        self.assertEqual(len(rm["lookahead"]), 3)

    def test_notification_mode(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        mode = engine.get_notification_mode()
        self.assertEqual(mode, "every-batch")

        updated = engine.set_notification_mode("morning-night")
        self.assertIsNotNone(updated)
        self.assertEqual(engine.get_notification_mode(), "morning-night")

        updated = engine.set_notification_mode("off")
        self.assertIsNotNone(updated)
        self.assertEqual(engine.get_notification_mode(), "off")

        invalid = engine.set_notification_mode("invalid_mode")
        self.assertIsNone(invalid)
        self.assertEqual(engine.get_notification_mode(), "off")

    def test_pause_and_resume_state(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        engine.set_paused(True)
        reloaded = engine.load_config()
        self.assertTrue(reloaded["is_paused"])

        batch, _, _ = engine.get_run_batch_size()
        self.assertEqual(batch, 0)

        engine.set_paused(False)
        reloaded = engine.load_config()
        self.assertFalse(reloaded["is_paused"])

    def test_weekend_mode_set_get(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        self.assertEqual(engine.get_weekend_mode(), "normal")
        engine.set_weekend_mode("light")
        self.assertEqual(engine.get_weekend_mode(), "light")
        engine.set_weekend_mode("off")
        self.assertEqual(engine.get_weekend_mode(), "off")
        self.assertIsNone(engine.set_weekend_mode("invalid"))
        self.assertEqual(engine.get_weekend_mode(), "off")


    def test_vacation_mode(self):
        engine.enable_vacation(days=7)
        st = engine.get_vacation_status()
        self.assertTrue(st["active"])
        self.assertIsNotNone(st["days_left"])

        cfg = engine.load_config()
        state = {"yesterday_target": 80, "current_month": "2026-09", "spikes_this_month": 0}
        tgt, is_spike = engine.calculate_next_target(state, cfg, "2026-09-07")
        self.assertGreaterEqual(tgt, 20)
        self.assertLessEqual(tgt, 40)
        self.assertFalse(is_spike)

        engine.disable_vacation()
        st_off = engine.get_vacation_status()
        self.assertFalse(st_off["active"])

    def test_ist_timezone_and_roadmap(self):
        now_ist = engine.get_ist_now()
        self.assertEqual(now_ist.tzinfo.utcoffset(None).total_seconds(), 5.5 * 3600)

        rm = engine.get_daily_roadmap(now_ist)
        self.assertEqual(len(rm["sessions"]), 4)
        expected_times = ["09:45 AM IST", "02:45 PM IST", "06:45 PM IST", "10:45 PM IST"]
        actual_times = [s["time_str"] for s in rm["sessions"]]
        self.assertEqual(actual_times, expected_times)

    def test_strategic_roadmap(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = {
            "date": today_str,
            "today_target": 80,
            "today_done": 30,
            "runs_completed_today": 2,
            "yesterday_target": 75,
            "history": [
                {"date": "2026-09-05", "commits": 20},
                {"date": "2026-09-06", "commits": 40}
            ]
        }
        engine.save_state(state)

        srm = engine.get_strategic_roadmap()
        self.assertIn("date", srm)
        self.assertEqual(len(srm["week_days"]), 7)
        self.assertEqual(len(srm["lookahead_7d"]), 7)
        self.assertGreaterEqual(srm["streak"], 1)
        self.assertGreater(srm["next_milestone"], 0)
        self.assertGreaterEqual(srm["milestone_pct"], 0)
        self.assertIn("vacation_status", srm)

    def test_reconcile_today_state_synchronization(self):
        rm = engine.get_daily_roadmap()
        srm = engine.get_strategic_roadmap()
        self.assertEqual(rm["today_done"], srm["today_done"])
        self.assertEqual(rm["today_target"], srm["today_target"])
        today_in_srm = next((d for d in srm["week_days"] if d["is_today"]), None)
        self.assertIsNotNone(today_in_srm)
        self.assertEqual(today_in_srm["commits"], rm["today_done"])

    def test_zero_state_fresh_install_initialization(self):
        # Empty zero-state template in isolated sandbox
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
        engine.save_state(clean_state)

        # On fresh install, batch size must be distributed across runs (NOT 100% in one go)
        batch, state, _ = engine.get_run_batch_size()
        self.assertGreater(state["today_target"], 0)
        self.assertGreater(batch, 0)
        self.assertLess(batch, state["today_target"])
        self.assertEqual(state["runs_completed_today"], 0)


class TestGitBotCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_config_file = engine.CONFIG_FILE
        self.original_state_file = engine.STATE_FILE

        engine.CONFIG_FILE = os.path.join(self.temp_dir.name, "config.json")
        engine.STATE_FILE = os.path.join(self.temp_dir.name, "data", "state.json")

    def tearDown(self):
        engine.CONFIG_FILE = self.original_config_file
        engine.STATE_FILE = self.original_state_file
        self.temp_dir.cleanup()

    def test_strip_ansi_and_vis_len(self):
        colored = "\033[96mHello \033[1mWorld\033[0m"
        self.assertEqual(cli.strip_ansi(colored), "Hello World")
        self.assertEqual(cli.vis_len(colored), 11)

    def test_render_row_alignment(self):
        w = 76
        r1 = cli.render_row("\033[92mShort\033[0m", width=w)
        r2 = cli.render_row("Some longer text that has more characters here", width=w)
        r3 = cli.render_row("📅 Unicode emoji line with details", width=w)
        
        self.assertEqual(cli.vis_len(r1), w)
        self.assertEqual(cli.vis_len(r2), w)
        self.assertEqual(cli.vis_len(r3), w)

    def test_render_row_overflow_safe(self):
        w = 76
        huge_text = "X" * 150
        r = cli.render_row(huge_text, width=w)
        self.assertEqual(cli.vis_len(r), w)
        self.assertTrue("..." in r)

    def test_uninstall_upstream_protection(self):
        with patch("cli.run_cmd", side_effect=[
            (0, "https://github.com/Dashrath175/GitBot.git", ""),
            (0, "", "")
        ]):
            with patch("cli.select_menu", return_value="keep"):
                with patch("builtins.input", return_value="y"):
                    with patch("subprocess.run") as mock_sub:
                        cli.cmd_uninstall()
                        for call in mock_sub.call_args_list:
                            args = str(call)
                            self.assertNotIn("gh repo delete", args)

    def test_select_menu_interactive(self):
        options = [
            {"key": "opt1", "title": "Option 1", "desc": "Desc 1"},
            {"key": "opt2", "title": "Option 2", "desc": "Desc 2"},
            {"key": "opt3", "title": "Option 3", "desc": "Desc 3"}
        ]
        with patch("sys.stdin.isatty", return_value=True):
            with patch("cli.read_single_key", side_effect=["down", "enter"]):
                chosen = cli.select_menu("Test", options, default_index=0)
                self.assertEqual(chosen, "opt2")

            with patch("cli.read_single_key", side_effect=["esc"]):
                chosen = cli.select_menu("Test", options, default_index=0)
                self.assertIsNone(chosen)

    def test_select_menu_non_interactive(self):
        options = [
            {"key": "opt1", "title": "Option 1"},
            {"key": "opt2", "title": "Option 2"}
        ]
        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.input", return_value="2"):
                chosen = cli.select_menu("Test", options, default_index=0)
                self.assertEqual(chosen, "opt2")

    def test_cmd_today_and_cmd_roadmap_independent(self):
        with patch("cli.sync_cloud_state"):
            try:
                cli.cmd_today()
                cli.cmd_roadmap()
            except Exception as e:
                self.fail(f"cmd_today or cmd_roadmap raised exception: {e}")

    def test_cmd_logs_and_cmd_doctor_execution(self):
        with patch("cli.run_cmd", return_value=(0, "[]", "")):
            try:
                cli.cmd_logs()
                cli.cmd_doctor()
            except Exception as e:
                self.fail(f"cmd_logs or cmd_doctor raised exception: {e}")

    def test_deterministic_target_generation(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        state = {"yesterday_target": 85, "spikes_this_month": 0, "last_spike_date": None}
        t1, is_spike1 = engine.calculate_next_target(state.copy(), cfg, "2026-09-08")
        t2, is_spike2 = engine.calculate_next_target(state.copy(), cfg, "2026-09-08")
        self.assertEqual(t1, t2)
        self.assertEqual(is_spike1, is_spike2)
        # Different date produces different deterministic target
        t3, _ = engine.calculate_next_target(state.copy(), cfg, "2026-09-09")
        self.assertIsInstance(t3, int)
        self.assertGreaterEqual(t3, 3)

    def test_system_snapshot_ssot_synchronization(self):
        snap = engine.get_live_system_snapshot()
        rm = engine.get_daily_roadmap()
        srm = engine.get_strategic_roadmap()
        self.assertEqual(snap["today_target"], rm["today_target"])
        self.assertEqual(snap["today_target"], srm["today_target"])
        self.assertEqual(snap["today_done"], rm["today_done"])
        self.assertEqual(snap["today_done"], srm["today_done"])
        self.assertEqual(snap["total_commits"], rm["total_commits"])
        self.assertEqual(snap["total_commits"], srm["total_commits"])

    def test_ist_timezone_commit_bucketing(self):
        # 2026-09-07 20:00:00 UTC is 2026-09-08 01:30:00 IST
        utc_ts = "2026-09-07T20:00:00Z"
        dt_ist = datetime.fromisoformat(utc_ts.replace("Z", "+00:00")).astimezone(engine.IST)
        self.assertEqual(dt_ist.strftime("%Y-%m-%d"), "2026-09-08")
        self.assertEqual(dt_ist.strftime("%I:%M %p"), "01:30 AM")

    def test_parse_gh_auth_status_multi_account(self):
        sample_output = """github.com
  ✓ Logged in to github.com account example-user (keyring)
  - Active account: true
  - Git operations protocol: https
  - Token: gho_****

  ✓ Logged in to github.com account Dashrath175 (keyring)
  - Active account: false
  - Git operations protocol: https
  - Token: gho_****

  ✓ Logged in to github.com account Ghostt-175 (keyring)
  - Active account: false
  - Git operations protocol: https
  - Token: gho_****
"""
        accounts = installer.parse_gh_auth_status(sample_output)
        self.assertEqual(len(accounts), 3)
        self.assertEqual(accounts[0]["username"], "example-user")
        self.assertTrue(accounts[0]["is_active"])
        self.assertEqual(accounts[1]["username"], "Dashrath175")
        self.assertFalse(accounts[1]["is_active"])
        self.assertEqual(accounts[2]["username"], "Ghostt-175")
        self.assertFalse(accounts[2]["is_active"])

    def test_classify_commit(self):
        self.assertEqual(engine.classify_commit("123", "feat: initialize GitBot [INITIALIZATION]"), "INITIALIZATION")
        # Conventional subjects and file choices are intentionally not proof.
        self.assertEqual(engine.classify_commit("124", "chore(sync): update automated activity checkpoint"), "MANUAL")
        self.assertEqual(engine.classify_commit("125", "perf(metrics): record performance latency snapshot"), "MANUAL")
        self.assertEqual(engine.classify_commit("126", "fix(logger): align timestamp drift in event sequence"), "MANUAL")
        self.assertEqual(engine.classify_commit("127", "chore(sync): finalize run checkpoint"), "MANUAL")
        self.assertEqual(engine.classify_commit("128", "Add custom login frontend component"), "MANUAL")
        self.assertEqual(engine.classify_commit("129", "Update README.md for production"), "MANUAL")

    def test_target_immutability(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = {
            "date": today_str,
            "today_target": 80,
            "today_done": 10,
            "runs_completed_today": 1,
            "history": []
        }
        engine.save_state(state)

        # First snapshot
        snap1 = engine.get_live_system_snapshot()
        self.assertEqual(snap1["today_target"], 80)

        # Simulate more commits done
        state["today_done"] = 95
        engine.save_state(state)

        # Second snapshot: target MUST NOT inflate or change
        snap2 = engine.get_live_system_snapshot()
        self.assertEqual(snap2["today_target"], 80)

    def test_roadmap_plan_becomes_next_day_target(self):
        cfg = engine.DEFAULT_CONFIG.copy()
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        today = engine.get_ist_now().date()
        state = {"date": today.isoformat(), "today_target": 80, "today_done": 0,
                 "runs_completed_today": 0, "yesterday_target": 80, "history": []}
        engine.save_state(state)
        first = engine.get_live_system_snapshot(now_dt=engine.get_ist_now())
        tomorrow = (today + __import__("datetime").timedelta(days=1)).isoformat()
        planned = engine.load_state()["planned_targets"][tomorrow]["target"]
        next_day = engine.get_live_system_snapshot(
            now_dt=engine.get_ist_now() + __import__("datetime").timedelta(days=1))
        self.assertEqual(next_day["today_target"], planned)

    def test_downward_correction(self):
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = {
            "date": today_str,
            "today_target": 80,
            "today_done": 40,
            "runs_completed_today": 2,
            "history": []
        }
        engine.save_state(state)

        # If live telemetry reports 15 (e.g. downward correction or rollback)
        mock_telemetry = {
            "total_commits": 15,
            "lifetime_bot_commits": 15,
            "lifetime_manual_commits": 0,
            "initialization_commits": 0,
            "today_commits": 15,
            "today_manual_commits": 0,
            "commits_by_date": {today_str: 15},
            "recent_commits": []
        }
        with patch("engine.get_live_git_telemetry", return_value=mock_telemetry):
            snap = engine.get_live_system_snapshot()
            # Must reflect 15, NOT locked at 40!
            self.assertEqual(snap["today_done"], 15)

    def test_version_alignment(self):
        self.assertEqual(cli.VERSION, "7.0.3")
        readme_path = os.path.join(os.path.dirname(__file__), "README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()
        self.assertIn("version-7.0.3-purple.svg", readme)
        self.assertIn("v7.0.3", readme)
        self.assertNotIn("5.12.1", readme)

    def _verify_session(self, ledger, remote_messages, session_id="2026-09-09-run-1"):
        records = "".join(f"{i:040x}\x1f{message}\x1e" for i, message in enumerate(remote_messages, 1))
        def remote_git(command, **kwargs):
            output = json.dumps(ledger) if "show" in command else records
            return subprocess.CompletedProcess(command, 0, output, "")
        with patch("engine.is_git_repo", return_value=True), patch("engine.subprocess.run", side_effect=remote_git):
            return engine.verify_session_remote(session_id, self.temp_dir.name)

    def test_session_verification_expected_remote_events_is_idempotent(self):
        sid = "2026-09-09-run-1"
        events = ["event-a", "event-b"]
        ledger = {"schema": 1, "events": {e: {"session_id": sid, "status": "committed"} for e in events},
                  "sessions": {sid: {"status": "EXECUTING", "events": events}}}
        messages = [f"work\n\nGitBot-Event-Id: {e}\nGitBot-Session-Id: {sid}\nGitBot-Schema: 1" for e in events]
        first = self._verify_session(ledger, messages)
        second = self._verify_session(ledger, messages)
        self.assertEqual(first["status"], "VERIFIED")
        self.assertEqual(second, first)

    def test_session_verification_rejects_missing_wrong_or_mismatched_provenance(self):
        sid, event = "2026-09-09-run-1", "event-a"
        good = f"work\n\nGitBot-Event-Id: {event}\nGitBot-Session-Id: {sid}\nGitBot-Schema: 1"
        ledger = {"schema": 1, "events": {event: {"session_id": sid}}, "sessions": {sid: {"events": [event]}}}
        self.assertEqual(self._verify_session(ledger, [])["status"], "NOT VERIFIED")
        self.assertEqual(self._verify_session(ledger, [good.replace(sid, "wrong-session")])["status"], "NOT VERIFIED")
        bad_ledger = {"schema": 1, "events": {event: {"session_id": "wrong-session"}}, "sessions": {sid: {"events": [event]}}}
        self.assertEqual(self._verify_session(bad_ledger, [good])["status"], "NOT VERIFIED")

    def test_session_verification_rejects_adversarial_duplicate_and_initialization(self):
        sid, event = "2026-09-09-run-1", "event-a"
        good = f"work\n\nGitBot-Event-Id: {event}\nGitBot-Session-Id: {sid}\nGitBot-Schema: 1"
        ledger = {"schema": 1, "events": {event: {"session_id": sid}}, "sessions": {sid: {"events": [event]}}}
        result = self._verify_session(ledger, ["feat: initialize GitBot [INITIALIZATION]", good, good])
        self.assertEqual(result["status"], "NOT VERIFIED")
        self.assertEqual(result["reason"], "duplicate remote event trailers")

    def test_session_verification_reconciles_delayed_remote_visibility(self):
        sid, event = "2026-09-09-run-1", "event-a"
        ledger = {"schema": 1, "events": {event: {"session_id": sid}}, "sessions": {sid: {"events": [event]}}}
        self.assertEqual(self._verify_session(ledger, [])["status"], "NOT VERIFIED")
        message = f"work\n\nGitBot-Event-Id: {event}\nGitBot-Session-Id: {sid}\nGitBot-Schema: 1"
        self.assertEqual(self._verify_session(ledger, [message])["status"], "VERIFIED")

    def test_session_reconciliation_persists_only_remote_verified_state(self):
        sid, event = "2026-09-09-run-1", "event-a"
        ledger = {"schema": 1, "events": {event: {"session_id": sid}}, "sessions": {sid: {"status": "EXECUTING", "events": [event]}}}
        engine.save_provenance(ledger, self.temp_dir.name)
        message = f"work\n\nGitBot-Event-Id: {event}\nGitBot-Session-Id: {sid}\nGitBot-Schema: 1"
        def remote_git(command, **kwargs):
            output = json.dumps(ledger) if "show" in command else f"{'a' * 40}\x1f{message}\x1e"
            return subprocess.CompletedProcess(command, 0, output, "")
        with patch("engine.is_git_repo", return_value=True), patch("engine.subprocess.run", side_effect=remote_git):
            results, changed = engine.reconcile_verified_sessions(self.temp_dir.name)
        self.assertTrue(changed)
        self.assertEqual(results[0]["status"], "VERIFIED")
        self.assertEqual(engine.load_provenance(self.temp_dir.name)["sessions"][sid]["status"], "VERIFIED")

    def test_get_connected_repo_priority(self):
        # 1. When config.json specifies connected_repo
        custom_cfg = {"connected_repo": "custom-owner/custom-repo"}
        with open(engine.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(custom_cfg, f)
        target_dir = os.path.dirname(engine.CONFIG_FILE)
        repo = cli.get_connected_repo(target_dir)
        self.assertEqual(repo, "custom-owner/custom-repo")

        # 2. When empty directory with no config and no remote
        empty_dir = self.temp_dir.name
        cfg_empty = os.path.join(empty_dir, "config.json")
        if os.path.exists(cfg_empty):
            os.remove(cfg_empty)
        with patch("cli.run_cmd", return_value=(1, "", "")):
            repo_none = cli.get_connected_repo(empty_dir)
            self.assertIsNone(repo_none)

    def test_fresh_install_e2e_simulation(self):
        # 1. Create clean-slate repository staging
        user_cfg = {
            "author_name": "TestDev",
            "author_email": "testdev@example.com",
            "connected_repo": "TestUser/GitBot",
            "preset": "active",
            "min_daily_commits": 50,
            "max_daily_commits": 250,
            "runs_per_day": 4,
            "weekend_mode": "normal",
            "is_paused": False,
            "notification_mode": "digest"
        }
        staging_dir = installer.create_clean_slate_staging("TestUser", "TestDev", "testdev@example.com", user_cfg)
        self.assertTrue(os.path.exists(staging_dir))
        self.assertTrue(os.path.exists(os.path.join(staging_dir, "install.ps1")))
        self.assertTrue(os.path.exists(os.path.join(staging_dir, "install.sh")))
        self.assertTrue(os.path.exists(os.path.join(staging_dir, ".gitignore")))

        try:
            # 2. Verify git history has EXACTLY 1 commit
            res_tot = subprocess.run(f'git -C "{staging_dir}" rev-list --count HEAD', shell=True, capture_output=True, text=True)
            self.assertEqual(int(res_tot.stdout.strip()), 1)

            # 3. Verify telemetry on clean repository
            telemetry = engine.get_live_git_telemetry(staging_dir)
            self.assertEqual(telemetry["total_commits"], 1)
            self.assertEqual(telemetry["lifetime_bot_commits"], 0)
            self.assertEqual(telemetry["initialization_commits"], 1)
            self.assertEqual(telemetry["today_commits"], 0)
            self.assertEqual(telemetry["today_manual_commits"], 0)

            # 4. Verify snapshot on clean repository
            engine.STATE_FILE = os.path.join(staging_dir, "data", "state.json")
            engine.CONFIG_FILE = os.path.join(staging_dir, "config.json")
            snap = engine.get_live_system_snapshot(target_dir=staging_dir)
            self.assertEqual(snap["total_commits"], 1)
            self.assertEqual(snap["today_done"], 0)
            self.assertEqual(snap["lifetime_bot_commits"], 0)
            self.assertEqual(snap["lineage"]["bot"], 0)
            self.assertEqual(snap["lineage"]["initialization"], 1)

            # 5. Simulate commits in this repository
            act_path = os.path.join(staging_dir, "data", "activity.json")
            with open(act_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = engine.load_state()

            # Temporarily point bot DATA_FILE and REPO_DIR to staging_dir
            orig_data_file = bot.DATA_FILE
            orig_repo_dir = bot.REPO_DIR
            bot.DATA_FILE = act_path
            bot.REPO_DIR = staging_dir
            try:
                # Make 2 bot commits
                ok1, _ = bot.make_commit(data, state)
                ok2, _ = bot.make_commit(data, state)
                self.assertTrue(ok1)
                self.assertTrue(ok2)

                # Verify telemetry after 2 commits
                t_after = engine.get_live_git_telemetry(staging_dir)
                self.assertEqual(t_after["total_commits"], 3)
                self.assertEqual(t_after["lifetime_bot_commits"], 2)
                self.assertEqual(t_after["today_commits"], 2)

                # Verify snapshot reflects 2 commits
                snap_after = engine.get_live_system_snapshot(target_dir=staging_dir)
                self.assertEqual(snap_after["today_done"], 2)
                self.assertEqual(snap_after["total_commits"], 3)

                # 6. Simulate downward correction (e.g. 1 commit rolled back in git)
                subprocess.run(f'git -C "{staging_dir}" reset --hard HEAD~1', shell=True, capture_output=True)
                snap_down = engine.get_live_system_snapshot(target_dir=staging_dir)
                # Must decrease to 1 without any max() lock!
                self.assertEqual(snap_down["today_done"], 1)
                self.assertEqual(snap_down["total_commits"], 2)
            finally:
                bot.DATA_FILE = orig_data_file
                bot.REPO_DIR = orig_repo_dir

        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
