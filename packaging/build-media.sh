#!/usr/bin/env bash
# WAV/PNG are the only formats the local importer writes. Keep codec dependencies out.
set -euo pipefail
root=$(pwd)
prefix="$root/build/media"
mkdir -p build/media-source
fetch() {
    local name=$1 version=$2 checksum=$3
    local archive="build/media-source/$name-$version.tar.gz"
    if [[ ! -f "$archive" ]]; then
        curl -fLsS --retry 3 "https://github.com/libsdl-org/${name/SDL2/SDL}/releases/download/release-$version/$name-$version.tar.gz" -o "$archive"
    fi
    echo "$checksum  $archive" | sha256sum -c -
    tar -xzf "$archive" -C build/media-source
}
fetch SDL2 2.30.12 ac356ea55e8b9dd0b2d1fa27da40ef7e238267ccf9324704850d5d47375b48ea
cmake -S build/media-source/SDL2-2.30.12 -B build/media-sdl -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DSDL_TEST=OFF -DSDL_STATIC=OFF -DSDL_LIBSAMPLERATE=OFF
cmake --build build/media-sdl --parallel 2
cmake --install build/media-sdl
export PKG_CONFIG_PATH="$prefix/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export CMAKE_PREFIX_PATH="$prefix:${CMAKE_PREFIX_PATH:-}"
fetch SDL2_image 2.8.8 2213b56fdaff2220d0e38c8e420cbe1a83c87374190cba8c70af2156097ce30a
fetch SDL2_mixer 2.8.1 cb760211b056bfe44f4a1e180cc7cb201137e4d1572f2002cc1be728efd22660
cmake -S build/media-source/SDL2_image-2.8.8 -B build/media-image -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DSDL2_DIR="$prefix/lib/cmake/SDL2" -DSDL2IMAGE_SAMPLES=OFF -DSDL2IMAGE_BACKEND_STB=ON \
    -DSDL2IMAGE_AVIF=OFF -DSDL2IMAGE_TIF=OFF -DSDL2IMAGE_WEBP=OFF \
    -DSDL2IMAGE_JXL=OFF -DSDL2IMAGE_JPG_SAVE=OFF -DSDL2IMAGE_PNG_SAVE=OFF
cmake --build build/media-image --parallel 2
cmake --install build/media-image
cmake -S build/media-source/SDL2_mixer-2.8.1 -B build/media-mixer -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DSDL2_DIR="$prefix/lib/cmake/SDL2" -DSDL2MIXER_SAMPLES=OFF -DSDL2MIXER_FLAC=OFF -DSDL2MIXER_MOD=OFF \
    -DSDL2MIXER_MP3=OFF -DSDL2MIXER_MIDI=OFF -DSDL2MIXER_OPUS=OFF \
    -DSDL2MIXER_VORBIS=OFF -DSDL2MIXER_WAVPACK=OFF
cmake --build build/media-mixer --parallel 2
cmake --install build/media-mixer
