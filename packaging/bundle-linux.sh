#!/usr/bin/env bash
set -euo pipefail
package="$PWD/build/package/funny-furries"
cp build/release/funny-furries "$package/"
mkdir -p "$package/lib" "$package/licenses"
cp -L build/media/lib/libSDL2*.so* "$package/lib/"
for item in python3.11 libpython3.11-minimal libssl3 tcl8.6 tk8.6 libtcl8.6 libtk8.6; do
    if [[ -f "/usr/share/doc/$item/copyright" ]]; then
        cp "/usr/share/doc/$item/copyright" "$package/licenses/$item.txt"
        dpkg-query -W -f='${binary:Package} ${Version}\n' "$item" >> "$package/licenses/packages.txt"
    fi
done
cp packaging/play.sh packaging/install.sh "$package/"
cp packaging/licenses/libwarpzone-LICENSE-*.txt "$package/licenses/"  # kept in the repo: the Windows libwarpzone zip has none
chmod +x "$package/"*.sh

for library in "$package/_internal/"*.so*; do
    name=$(basename "$library")
    original=$(ldconfig -p | awk -v name="$name" '$1==name && !found {print $NF; found=1}')
    [[ -z "$original" ]] && continue
    owner=$(dpkg-query -S "$original" 2>/dev/null | head -1 | cut -d: -f1 || true)
    if [[ -z "$owner" ]]; then owner=$(dpkg-query -S "/usr$original" 2>/dev/null | head -1 | cut -d: -f1 || true); fi
    [[ -z "$owner" ]] && continue
    if [[ -f "/usr/share/doc/$owner/copyright" ]]; then cp "/usr/share/doc/$owner/copyright" "$package/licenses/$owner.txt"; fi
done
