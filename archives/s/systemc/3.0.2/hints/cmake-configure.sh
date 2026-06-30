#!/bin/sh
# CMake configure hints for systemc on HarmonyOS
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release
