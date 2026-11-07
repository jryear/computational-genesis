#!/bin/bash
# machine-self birth read for macOS. Read-only: writes one file and changes nothing else.
# Uses only tools that ship with macOS (no python, no Homebrew, no installs).
# Deliberately avoids privacy-protected folders (Desktop, Documents, Downloads,
# Mail, Messages, Photos), so it triggers no permission prompts and reads no personal content.
#
#   bash birth.sh            -> /Users/Shared/machine-self/<user>-<timestamp>.txt
OUT_DIR="/Users/Shared/machine-self"
mkdir -p "$OUT_DIR" 2>/dev/null || OUT_DIR="$HOME"
OUT="$OUT_DIR/$(id -un)-$(date -u +%Y%m%dT%H%M%SZ).txt"
s() { printf '\n### %s\n' "$1"; }
{
s "read"; date -u "+%Y-%m-%dT%H:%M:%SZ"; echo "user=$(id -un) uid=$(id -u) groups=$(id -Gn)"
s "identity"; sw_vers 2>/dev/null; uname -m; sysctl -n hw.model 2>/dev/null; sysctl -n hw.memsize 2>/dev/null
echo "booted: $(sysctl -n kern.boottime 2>/dev/null)"
s "factory seal (system volume)"; csrutil authenticated-root status 2>/dev/null; csrutil status 2>/dev/null
diskutil info / 2>/dev/null | egrep -i 'Volume Name|Sealed|FileVault|APFS Snapshot'
s "this account"; echo "home created: $(stat -f '%SB' "$HOME" 2>/dev/null)"
dscl . -read "/Users/$(id -un)" RealName UserShell NFSHomeDirectory 2>/dev/null
s "other accounts"; dscl . -list /Users UniqueID 2>/dev/null | awk '$2>=500'
s "disks and shared"; df -h 2>/dev/null | egrep -v '^devfs|map '; ls -la /Volumes 2>/dev/null
echo "-- /Users/Shared:"; ls -laT /Users/Shared 2>/dev/null | head -40
s "OS install and package receipts (non-Apple, with install time)"
for p in $(pkgutil --pkgs 2>/dev/null | grep -v '^com\.apple\.'); do
  echo "$p  $(pkgutil --pkg-info "$p" 2>/dev/null | awk -F': ' '/install-time/{print $2}' | xargs -I{} date -r {} -u '+%F %T' 2>/dev/null)"; done
s "apps (/Applications, ~/Applications): name, added, signer, downloaded-by"
for a in /Applications/*.app "$HOME"/Applications/*.app; do
  [ -e "$a" ] || continue
  added=$(stat -f '%SB' "$a" 2>/dev/null)
  signer=$(codesign -dv "$a" 2>&1 | awk -F= '/TeamIdentifier/{print $2}')
  q=$(xattr -p com.apple.quarantine "$a" 2>/dev/null | awk -F';' '{print $3}')
  echo "$(basename "$a") | added $added | team ${signer:-none} | quarantine-agent ${q:--}"
done
s "launch agents and daemons (what starts automatically)"
for d in "$HOME/Library/LaunchAgents" /Library/LaunchAgents /Library/LaunchDaemons; do
  for f in "$d"/*.plist; do
    [ -e "$f" ] || continue
    prog=$(plutil -extract ProgramArguments json -o - "$f" 2>/dev/null || plutil -extract Program raw -o - "$f" 2>/dev/null)
    echo "$f | created $(stat -f '%SB' "$f") | $prog"
  done
done
echo "-- loaded (user domain, non-Apple):"; launchctl list 2>/dev/null | grep -v 'com\.apple\.' | head -60
s "listening network ports (own processes)"; lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR==1||1' | head -40
lsof -nP -iUDP 2>/dev/null | grep -v '\*:\*' | head -10
s "running processes (non-Apple paths)"
ps -axo pid,ppid,user,lstart,command 2>/dev/null | egrep -v ' /System/| /usr/libexec/| /usr/sbin/| /sbin/| /Library/Apple/' | head -80
s "developer and agent tooling present"
for t in brew git python3 node npm claude codex gh tailscale docker; do
  p=$(command -v "$t" 2>/dev/null); [ -n "$p" ] && echo "$t -> $p"; done
xcode-select -p 2>/dev/null && echo "(command line tools installed)"
s "home top level (name, created, modified)"; ls -laT "$HOME" 2>/dev/null | head -60
s "~/Library top level"; ls -laT "$HOME/Library" 2>/dev/null | head -80
s "~/Library/Application Support (which apps keep state)"; ls -laT "$HOME/Library/Application Support" 2>/dev/null | head -80
s "hidden config dirs in home"; ls -d "$HOME"/.[!.]* 2>/dev/null
s "recent installs (install.log)"; grep -i 'Installed\|installer\[' /var/log/install.log 2>/dev/null | tail -40
} > "$OUT" 2>&1
echo "birth read written: $OUT ($(wc -c < "$OUT") bytes)"
