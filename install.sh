#!/usr/bin/env bash
# install.sh — one-step installer for hermes-research-plugin
#
# Usage:
#   bash install.sh                        # installs from default repo
#   bash install.sh your-fork/hermes-research-plugin   # installs from a fork
#
# What it does:
#   1. Installs the plugin from GitHub
#   2. Enables it so it loads on the next Hermes session
#   3. Prints a quick-start reminder

set -euo pipefail

REPO="${1:-YOUR_GITHUB_USERNAME/hermes-research-plugin}"
PLUGIN_NAME="deep-research"

echo "Installing hermes-research-plugin from ${REPO} ..."

if ! command -v hermes &>/dev/null; then
    echo "Error: 'hermes' command not found." >&2
    echo "Install Hermes first: https://hermes-agent.nousresearch.com/docs/getting-started" >&2
    exit 1
fi

hermes plugins install "${REPO}" --enable

echo ""
echo "Done! Plugin '${PLUGIN_NAME}' is installed and enabled."
echo ""
echo "Quick start:"
echo "  /deep-research what's the best toaster for home use under \$100"
echo "  /deep-research what car should I buy for a family of 4"
echo "  /deep-research <any topic>"
echo ""
echo "Need web search? Run: hermes setup"
