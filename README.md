<div align="center">

# 🤖 GitBot: Autonomous Cloud Contribution Engine

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated%20Cloud-blue?logo=github-actions)](https://github.com/features/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-brightgreen.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-7.0.3-purple.svg)](https://github.com/Dashrath175/GitBot)
[![Zero Server](https://img.shields.io/badge/Hosting-100%25%20Free%20Cloud-success)](https://github.com)

**GitBot** is a 100% cloud-native developer tool and aesthetic terminal control center that autonomously maintains an authentic, organic GitHub contribution graph — **without requiring your laptop or any server to stay on**.

<p align="center"><img src="assets/gitbot-slime.png" alt="GitBot green slime mascot" width="180"></p>

> **Safety model:** GitBot refuses to run its automation in `Dashrath175/GitBot`. Dashboard figures identify whether they are verified remote Git evidence, planned control state, prediction, or cached/offline data. Creating a GitHub issue/comment is a delivery attempt; GitBot does not claim that an email was delivered.

[Quick Install](#-1-command-quick-install) • [Interactive CLI Shell](#-antigravity-style-interactive-shell) • [Daily Roadmap (IST)](#-daily-cloud-roadmap) • [Vacation Mode](#-vacation-mode) • [GitHub Notifications](#-github-notification-attempts) • [Presets & Pacing](#-intensity-presets) • [FAQ](#-frequently-asked-questions)

</div>

---

```
   ____ _ _   ____        _   
  / ___(_) |_| __ )  ___ | |_ 
 | |  _| | __|  _ \ / _ \| __|
 | |_| | | |_| |_) | (_) | |_ 
  \____|_|\__|____/ \___/ \__|  v7.0.3
  Autonomous Cloud Contribution Engine
```

```
╭──────────────────────────────────────────────────────────────────────────╮
│ SYSTEM STATUS DASHBOARD                                       [ ACTIVE ] │
├──────────────────────────────────────────────────────────────────────────┤
│ Profile     : Developer <dev@example.com>                                │
│ Preset      : Active                 Pacing : Normal                     │
│ Notify Mode : EVERY-BATCH            Today  : 2026-09-07 (11:30 AM IST)  │
│                                                                          │
│ Today's Commits : 14 / 53 target (26% completed)                         │
│ [██████░░░░░░░░░░░░░░░░░░] 26%                                           │
│                                                                          │
│ Cloud Sessions  : 1 / 4 completed today                                  │
│ Schedule Times  : 09:45, 14:45, 18:45, 22:45 IST (Cloud)                 │
│ Monthly Spikes  : 0 / 4 (Occasional 170+ days)                           │
│ Commit Velocity : 50 – 250 commits / day                                 │
╰──────────────────────────────────────────────────────────────────────────╯
```

---

## ⚡ 1-Command Quick Install

Install and launch GitBot into your GitHub account with a single command in your terminal:

### 🪟 Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/Dashrath175/GitBot/main/install.ps1 | iex
```

### 🍎 macOS / 🐧 Linux (Terminal)
```bash
curl -fsSL https://raw.githubusercontent.com/Dashrath175/GitBot/main/install.sh | bash
```

**What the installer does automatically:**
1. 🔒 **Direct 100% Private Repository**: Creates a standalone, completely private repository under your GitHub account (`@username/GitBot`). No fork restrictions, no public lock, 100% stealth.
2. 👤 **Detects Profile Credentials**: Automatically pairs your verified GitHub name & email to credit all commits directly to your personal activity graph.
3. 🇮🇳 **Indian Standard Time (IST) Cadence**: Configures daily schedules aligned to real Indian working hours (09:45 AM, 02:45 PM, 06:45 PM, 10:45 PM IST).
4. ⚙️ **Enables Actions Write Permissions**: Sets up cloud execution permissions automatically via API.
5. 🌐 **Registers Global `gitbot` CLI**: Adds the interactive shell wrapper to your system PATH.
6. 🔔 **Creates a Welcome Issue**: Records a GitHub notification object; email delivery depends on the user’s GitHub notification settings.
7. 🚀 **Offers First Cloud Run**: Configures the workflow for the selected repository; activity remains subject to its repository guard and permissions.

> [!TIP]
> **Re-Running the Installer**:
> Re-running the installation command performs a safe, in-place update from upstream (`Dashrath175/GitBot`). It preserves your personalized settings and commit history.

---

## ✨ Why GitBot?

| Feature | GitBot | Traditional Scripts |
| :--- | :--- | :--- |
| **Execution** | **100% Cloud-Native** (GitHub Actions) | Requires laptop/PC on 24/7 |
| **Interface** | **Antigravity-Style REPL Shell** (`gitbot > `) | Confusing config files & raw scripts |
| **Privacy** | **Direct 100% Private Repo by Default** | Clunky public forks with visibility lock |
| **Timezone** | **Indian Standard Time (IST)** Native | Desynced UTC midnight date resets |
| **Graph Dynamics** | **Markov Random Walk** with natural flow | Artificial static blocks (e.g. exactly 5/day) |
| **Zero-Commit Days** | **Strictly 0 Blank Days** (Min 3-4 commits) | Broken streaks on weekends or holidays |
| **Repository Size** | **Rotates Telemetry** (< 5MB forever) | Bloats repo with megabytes of dummy files |
| **Maintenance** | **Zero-Maintenance Upstream Sync** | Constant rebase conflicts & token expirations |

---

## 🖥️ Antigravity-Style Interactive Shell

Running `gitbot` from any terminal launches a persistent, interactive command center with your live connected identity:

```text
PS C:\> gitbot

   ____ _ _   ____        _   
  / ___(_) |_| __ )  ___ | |_ 
 | |  _| | __|  _ \ / _ \| __|
 | |_| | | |_| |_) | (_) | |_ 
  \____|_|\__|____/ \___/ \__|  v7.0.3
  Autonomous Cloud Contribution Engine — Interactive Control Shell

╭──────────────────────────────────────────────────────────────────────────╮
│ ⚡ CONNECTED GITHUB IDENTITY                                  [ ACTIVE ] │
├──────────────────────────────────────────────────────────────────────────┤
│ Account  : @Dashrath175                                                  │
│ Email    : dev@example.com                                               │
│ Repo     : https://github.com/Dashrath175/GitBot [Private]               │
╰──────────────────────────────────────────────────────────────────────────╯

Type 'help' to view all commands, or 'exit' / 'q' to quit.

gitbot > 
```

Execute all commands directly inside the shell without repeatedly typing `gitbot`:

```bash
# Display live system dashboard & progress
status

# View today's 4-session cloud roadmap and countdown (or 'today')
roadmap

# Arrow-key notification settings (Every Batch, Morning + Night, Morning Only, Night Only, Off)
notify

# Arrow-key commit intensity preset (Active, Consistent, Hardcore)
intensity

# Arrow-key weekend pacing preference (Normal, Light, Off / Minimal)
weekend

# Arrow-key vacation maintenance mode (7 Days, 14 Days, Custom, Off)
vacation

# Pause or resume automated cloud commits
pause
resume

# Run 7-point system diagnostic health check
doctor

# Trigger an instant cloud or local run
trigger

# View recent cloud execution logs
logs

# Pull latest engine updates from upstream (Dashrath175/GitBot)
update

# Cleanly uninstall GitBot from system
uninstall

# Show command reference table
help

# Exit shell
exit / q
```

> [!TIP]
> One-shot terminal execution is also supported: `gitbot status`, `gitbot roadmap`, `gitbot doctor`, etc. can still be run directly from PowerShell or Bash.

---

## 📅 Daily Cloud Roadmap

Run `gitbot roadmap` (or `gitbot today`) anytime to view your exact daily schedule aligned to Indian Standard Time (IST):

```
╭──────────────────────────────────────────────────────────────────────────╮
│ 📅 TODAY'S CLOUD EXECUTION ROADMAP                      2026-09-07 (IST) │
├──────────────────────────────────────────────────────────────────────────┤
│ Profile  : Developer <dev@example.com>                                   │
│ Preset   : Active             │ Next Run: in 3h 15m (Afternoon Session)  │
│ Progress : 14 / 53 commits (26% completed)                               │
│ [██████░░░░░░░░░░░░░░░░░░] 26%                                           │
├──────────────────────────────────────────────────────────────────────────┤
│ DAILY CLOUD SESSION AGENDA                                               │
│ #  Session Name         Schedule       Target      Status                │
│ 1  Morning Session     09:45 AM IST   13 commits   ✓ Completed           │
│ 2  Afternoon Session   02:45 PM IST   13 commits   ⏳ Next Up            │
│ 3  Evening Session     06:45 PM IST   13 commits   ○ Scheduled           │
│ 4  Night Session       10:45 PM IST   14 commits   ○ Scheduled           │
├──────────────────────────────────────────────────────────────────────────┤
│ 📈 3-DAY LOOKAHEAD FORECAST                                              │
│ • Tomorrow  : 50 – 85 commits (Momentum Walk)                            │
│ • In 2 Days : 50 – 99 commits (Momentum Walk)                            │
│ • In 3 Days : 50 – 106 commits (Momentum Walk)                           │
╰──────────────────────────────────────────────────────────────────────────╯
```

---

## 🏖️ Vacation Mode

Planning to step away or take a holiday? Use `vacation` to keep your contribution streak green without burning high commit volumes:

- **Reduced 20–40 Commits Daily**: Generates a substantially lower vacation pace.
- **Unbroken Green Streak**: Ensures your GitHub contribution squares stay 100% active every single day.
- **Configurable Durations**:
  - `1 Week (7 Days)` — Automatically restores your normal preset after 7 days.
  - `2 Weeks (14 Days)` — 14-day light maintenance period.
  - `Ongoing / Indefinite` — Stays in vacation mode until manually disabled.
  - `Disable Vacation` — Resumes your standard preset immediately.
- **Dashboard Badge**: The status header displays `[ VACATION ]` with remaining days while active.

---

## 🔔 GitHub Notification Attempts

GitBot records notification attempts through GitHub issue activity. GitBot can verify an API object/comment was created, but cannot claim email delivery:

- **Every Batch**: one notification attempt after each completed batch.
- **Morning + Night**, **Morning Only**, and **Night Only**: scheduled start/end summaries.
- **Off**: no notification attempts.

---

## 🎯 Intensity Presets

Adjust your velocity anytime using arrow keys in `gitbot intensity`:

### 🟢 Consistent Dev (40 – 90 commits/day)
For developers who want a steady, continuous active green streak without excessive volume.
- Daily Target: 40–90 commits
- Spike Days: Occasional bump to 100–120 (max 3/mo)

### 🔵 Active Contributor (50 – 150 commits/day) *(Default)*
The optimal sweet spot. Replicates the rhythm of an active open-source contributor.
- Daily Target: 50–145 commits
- Spike Days: Burst days up to 200 commits (max 4/mo)

### 🟣 Hardcore Coder (80 – 250 commits/day)
For maximum velocity and high-density graphs.
- Daily Target: 80–180 commits
- Spike Days: High-velocity bursts up to 250 commits

### 🏖️ Weekend Modes (`gitbot weekend`)
- **Normal**: Full commit pace 7 days a week.
- **Light**: Relaxed weekend volume (~40% of weekday target).
- **Off / Minimal**: Strict maintenance mode (**3–4 commits/day**, never 0 commits, preserving green graph).

---

## 📈 Smooth Momentum Algorithm

GitBot rejects static commit counts (e.g., exactly 10 commits every day) which look visibly automated. Instead, it uses a **momentum-controlled random walk**:

```
Day 01:  79 commits
Day 02:  95 commits  (Smooth transition)
Day 03: 112 commits  (Natural progression)
Day 04:  98 commits  (Slight dip)
Day 05: 215 commits  ★ SPIKE DAY (170+, strictly capped 3-4x/mo)
Day 06: 138 commits  (Smooth decay down)
Day 07: 110 commits  (Return to regular rhythm)
```

Daily targets are distributed across **4 distinct sessions** in Indian Standard Time (09:45 AM, 02:45 PM, 06:45 PM, 10:45 PM IST) for authentic diurnal activity.

---

## ❓ Frequently Asked Questions

<details>
<summary><b>Does my computer need to stay on?</b></summary>
No! GitBot runs entirely inside GitHub Actions cloud servers. Once installed, you can shut down your computer or disconnect from the internet completely.
</details>

<details>
<summary><b>Why aren't private contributions showing on my graph?</b></summary>
Because GitBot creates a 100% Private repository for total stealth, you just need to enable private contributions in your profile once:
1. Go to your GitHub profile (`https://github.com/YOUR_USERNAME`).
2. Above your contribution graph, click **Contribution settings** (dropdown on the top right).
3. Check **"Include private contributions on my profile"**.
4. All your green squares will instantly illuminate!
</details>

<details>
<summary><b>How do I pause GitBot temporarily?</b></summary>
Run `pause` inside the interactive shell (or `gitbot pause` in terminal). When you're ready to resume, run `resume`.
</details>

<details>
<summary><b>Will this bloat my repository or consume lots of storage?</b></summary>
No. GitBot automatically rotates and prunes telemetry entries, keeping repository history lean. Your repository will remain under 5 MB permanently.
</details>

<details>
<summary><b>How does automatic upstream synchronization work?</b></summary>
Every scheduled cloud run safely synchronizes core engine updates directly from the parent repository (<code>Dashrath175/GitBot</code>) while strictly preserving your personalized <code>config.json</code> and commit data.
</details>

---

## 📄 License
Open-source under the [MIT License](LICENSE).

