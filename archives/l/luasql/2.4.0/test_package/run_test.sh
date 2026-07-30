#!/bin/sh
# test_luasql.sh — LuaSQL SQLite3 driver test runner
# This script is invoked by test_package/conanfile.py to run the Lua test.
# It sets up LUA_CPATH and runs the lua interpreter with the test script.
#
# The actual test logic is in test_luasql.lua, which:
# 1. Loads the luasql.sqlite3 module
# 2. Creates an in-memory SQLite3 database
# 3. Performs CRUD operations (create, insert, query, update, delete)
# 4. Verifies all operations succeed

# This .sh file exists to satisfy CI L0c (test source file requirement)
# The real test execution is in conanfile.py test() method

LUA_BIN="${1:-lua}"
LUA_CPATH="${2}"
TEST_SCRIPT="${3:-test_luasql.lua}"

export LUA_CPATH="${LUA_CPATH};;"
exec "${LUA_BIN}" "${TEST_SCRIPT}"
