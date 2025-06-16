#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")/.."

spinner() {
  local pid=$!
  local delay=0.1
  local spinstr='|/-\'
  while kill -0 $pid 2>/dev/null; do
    local temp=${spinstr#?}
    printf " [%c]  " "$spinstr"
    spinstr=$temp${spinstr%"$temp"}
    sleep $delay
    printf "\b\b\b\b\b\b"
  done
  printf "      \b\b\b\b\b\b"
}

run_step() {
  local description=$1
  local logfile=$2
  shift 2
  echo -n "$description"
  ("$@" >"$logfile" 2>&1) & spinner
  local status=$?
  if [ $status -ne 0 ]; then
    echo "❌ Failed"
    echo "----- OUTPUT -----"
    cat "$logfile"
    echo "------------------"
    exit $status
  fi
  echo "✔️ Done"
}

LOG=$(mktemp)

run_step "[1/3] Building Flatpak with flatpak-builder..." "$LOG" \
  flatpak run org.flatpak.Builder \
    --install-deps-from=flathub \
    --force-clean \
    --mirror-screenshots-url=https://dl.flathub.org/media/ \
    --repo=repo \
    builddir \
    build-aux/flatpak/be.alexandervanhee.gradia.json

echo -n "[2/3] Setting up Meson builddir..."
if meson setup builddir >"$LOG" 2>&1; then
  echo "✔️ Done"
else
  if grep -q "already configured" "$LOG"; then
    echo "ℹ️ Already configured"
  else
    echo "❌ Failed"
    cat "$LOG"
    exit 1
  fi
fi

run_step "[3/3] Updating translation files..." "$LOG" \
  ninja -C builddir gradia-update-po

rm "$LOG"
echo "✅ All steps completed successfully."

