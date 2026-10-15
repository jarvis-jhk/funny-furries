#!/usr/bin/env bash
# Local install only: no sudo, downloads, shell profiles or Steam database edits.
set -euo pipefail
folder=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
base="${XDG_DATA_HOME:-$HOME/.local/share}"
install_root="$base/funny-furries-app"
mkdir -p "$install_root" "$base/applications"
stage=$(mktemp -d "$install_root/.install-XXXXXX")
trap 'rm -rf -- "$stage"' EXIT
cp -a "$folder/." "$stage/"
version="$(cat "$folder/VERSION")-$(date +%s)-$$"
mv -- "$stage" "$install_root/$version"
ln -s "$version" "$install_root/.current-$$"
mv -Tf -- "$install_root/.current-$$" "$install_root/current"
# Escape reserved desktop-entry Exec characters, including user paths with spaces.
entry="$base/applications/funny-furries.desktop"
launch="$install_root/current/play.sh"
escaped=${launch//\\/\\\\}
escaped=${escaped//\"/\\\"}
escaped=${escaped//\$/\\\$}
escaped=${escaped//\`/\\\`}
escaped=${escaped//%/%%}
cat > "$entry" <<EOF
[Desktop Entry]
Type=Application
Name=Funny Furries
Comment=Two-player FF2 Xmas test release
Exec="$escaped" --fullscreen
Icon=input-gaming
Terminal=false
Categories=Game;
EOF
chmod +x "$entry"
if command -v xdg-user-dir >/dev/null; then
    desktop=$(xdg-user-dir DESKTOP)
    if [[ -d "$desktop" ]]; then cp "$entry" "$desktop/Funny Furries.desktop"; fi
fi
printf 'Installed. Start Funny Furries from the application menu. On Deck, add it to Steam as a non-Steam game.\n'
