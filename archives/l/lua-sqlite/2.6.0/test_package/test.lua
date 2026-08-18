-- Test script for lua-sqlite (LuaSQL SQLite3 driver)
-- R34: Calls actual luasql.sqlite3 API (connect, execute, fetch, close)
local luasql = require("luasql.sqlite3")
local env = luasql.sqlite3()
assert(env, "Failed to create luasql environment")

local con = env:connect(":memory:")
assert(con, "Failed to connect to in-memory database")

-- Create table and insert data
con:execute("CREATE TABLE test (id INTEGER, name TEXT)")
con:execute("INSERT INTO test VALUES (1, 'hello')")
con:execute("INSERT INTO test VALUES (2, 'world')")

-- Query and verify results
local cur = con:execute("SELECT * FROM test ORDER BY id")
local row = cur:fetch({}, "a")
assert(row.id == 1, "Expected id=1, got " .. tostring(row.id))
assert(row.name == "hello", "Expected name='hello', got " .. tostring(row.name))

row = cur:fetch({}, "a")
assert(row.id == 2, "Expected id=2, got " .. tostring(row.id))
assert(row.name == "world", "Expected name='world', got " .. tostring(row.name))

-- No more rows
row = cur:fetch({}, "a")
assert(row == nil, "Expected no more rows")

cur:close()
con:close()
env:close()
print("All tests passed!")
