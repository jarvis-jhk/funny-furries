#!/usr/bin/env bash
set -euo pipefail
package="$PWD/build/package/funny-furries"
cp build/release/funny-furries.exe "$package/"
cp build/media/bin/*.dll "$package/"
# Resolve the executable and SDL DLL imports recursively. Never depend on MSYS2 on the player's PC.
queue=("$package/funny-furries.exe" "$package/"*.dll)
for ((i=0; i<${#queue[@]}; i++)); do
    while read -r name; do
        source="$(find /ucrt64/bin -maxdepth 1 -iname "$name" -print -quit)"
        [[ -z "$source" ]] && continue  # Windows system DLL.
        if [[ ! -f "$package/$(basename "$source")" ]]; then
            cp "$source" "$package/"
            queue+=("$package/$(basename "$source")")
        fi
    done < <(objdump -p "${queue[i]}" | awk '/DLL Name:/ {print $3}')
done
cp -r /ucrt64/share/licenses "$package/licenses/UCRT64"
pacman -Q > "$package/licenses/UCRT64-packages.txt"
for notice in build/release/_deps/libwarpzone-*/LICENSE-*; do cp "$notice" "$package/licenses/libwarpzone-$(basename "$notice").txt"; done
