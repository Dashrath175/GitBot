#!/usr/bin/env bash
# ====================================================================
# GitBot - One-Command Autonomous Cloud Installation Script (macOS/Linux)
# ====================================================================

set -e

echo ">>> Initializing GitBot Installer..."

# 1. Check Python
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "[!] Python 3 is required to run the automated setup."
    echo "[!] Please install Python from https://www.python.org/downloads/ or via your package manager."
    exit 1
fi

# 2. Check Git
if ! command -v git &>/dev/null; then
    echo "[!] Git is required to clone and operate GitBot."
    echo "[!] Please install Git via your package manager (e.g. brew install git or apt install git)."
    exit 1
fi

# 3. Setup ~/.gitbot directory
GITBOT_HOME="$HOME/.gitbot"
BIN_DIR="$GITBOT_HOME/bin"

echo ">>> Installing GitBot into $GITBOT_HOME..."

if [ -d "$GITBOT_HOME" ]; then
    echo ">>> Updating existing GitBot installation in-place..."
    git -C "$GITBOT_HOME" remote add upstream https://github.com/Dashrath175/GitBot.git 2>/dev/null || true
    if [ -n "$(git -C "$GITBOT_HOME" status --porcelain)" ]; then
        echo "[!] Existing installation has local changes; preserving them. Commit, stash, or resolve them before updating."
        exit 1
    fi
    git -C "$GITBOT_HOME" fetch upstream main
    git -C "$GITBOT_HOME" merge --ff-only upstream/main || {
        echo "[!] Update cannot fast-forward safely; no files were overwritten."
        exit 1
    }
else
    echo ">>> Cloning GitBot repository..."
    git clone https://github.com/Dashrath175/GitBot.git "$GITBOT_HOME"
fi

# 4. Create global command wrapper in ~/.gitbot/bin
mkdir -p "$BIN_DIR"
WRAPPER="$BIN_DIR/gitbot"
cat << 'EOF' > "$WRAPPER"
#!/usr/bin/env bash
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
    PYTHON_CMD="python"
fi
"$PYTHON_CMD" "$REPO_DIR/cli.py" "$@"
EOF
chmod +x "$WRAPPER"

# 5. Symlink to ~/.local/bin or append to shell RC
LOCAL_BIN="$HOME/.local/bin"
if [ -d "$LOCAL_BIN" ] && [[ ":$PATH:" == *":$LOCAL_BIN:"* ]]; then
    ln -sf "$WRAPPER" "$LOCAL_BIN/gitbot"
else
    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_RC" ] && ! grep -q ".gitbot/bin" "$SHELL_RC"; then
        echo "export PATH=\"\$HOME/.gitbot/bin:\$PATH\"" >> "$SHELL_RC"
        echo ">>> Added ~/.gitbot/bin to $SHELL_RC"
    fi
fi

# 6. Run onboarding installer wizard
echo ">>> Running GitBot setup wizard..."
"$PYTHON_BIN" "$GITBOT_HOME/installer.py"

echo ""
echo ">>> Installation Complete! You can now type 'gitbot' from any terminal."
echo ""
