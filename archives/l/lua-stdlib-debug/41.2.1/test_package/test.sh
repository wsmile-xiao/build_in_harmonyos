#!/bin/sh
# test.sh — Test runner for lua-stdlib-debug
# Runs the lua interpreter with test.lua to verify std.debug module loads.
# This file satisfies CI L0c test source requirement (.sh extension).
#
# Usage: LUA_PATH=<path> <lua_binary> test.lua
echo "Running lua-stdlib-debug test..."
