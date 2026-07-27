-- test_luasql.lua — LuaSQL SQLite3 driver functional test
-- Tests: module loading, environment creation, database CRUD operations

local luasql = require("luasql.sqlite3")
assert(type(luasql) == "table", "require('luasql.sqlite3') should return a table")
assert(type(luasql.sqlite3) == "function", "luasql.sqlite3 should be a function")

-- Create environment
local env = luasql.sqlite3()
assert(type(env) == "userdata", "env should be userdata")

-- Connect to in-memory database
local conn = env:connect(":memory:")
assert(type(conn) == "userdata", "conn should be userdata")

-- Create table
local ok, err = conn:execute([[
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER
    )
]])
assert(ok == 0, "CREATE TABLE failed: " .. tostring(err))

-- Insert data
ok, err = conn:execute("INSERT INTO users (name, age) VALUES ('Alice', 30)")
assert(ok == 1, "INSERT failed: " .. tostring(err))

ok, err = conn:execute("INSERT INTO users (name, age) VALUES ('Bob', 25)")
assert(ok == 1, "INSERT failed: " .. tostring(err))

-- Query data
local cur = conn:execute("SELECT * FROM users ORDER BY age")
assert(type(cur) == "userdata", "cursor should be userdata")

-- Fetch rows
local row = cur:fetch({}, "a")
assert(row ~= nil, "first fetch should return a row")
assert(row.name == "Bob", "first row should be Bob, got: " .. tostring(row.name))
assert(row.age == 25, "Bob's age should be 25, got: " .. tostring(row.age))

row = cur:fetch({}, "a")
assert(row ~= nil, "second fetch should return a row")
assert(row.name == "Alice", "second row should be Alice, got: " .. tostring(row.name))
assert(row.age == 30, "Alice's age should be 30, got: " .. tostring(row.age))

-- No more rows
row = cur:fetch({}, "a")
assert(row == nil, "should be no more rows")

-- Close cursor
cur:close()

-- Update data
ok, err = conn:execute("UPDATE users SET age = 31 WHERE name = 'Alice'")
assert(ok == 1, "UPDATE failed: " .. tostring(err))

-- Verify update
cur = conn:execute("SELECT age FROM users WHERE name = 'Alice'")
row = cur:fetch({}, "a")
assert(row.age == 31, "Alice's age should be 31 after update, got: " .. tostring(row.age))
cur:close()

-- Delete data
ok, err = conn:execute("DELETE FROM users WHERE name = 'Bob'")
assert(ok == 1, "DELETE failed: " .. tostring(err))

-- Verify delete
cur = conn:execute("SELECT COUNT(*) as cnt FROM users")
row = cur:fetch({}, "a")
assert(row.cnt == 1, "should have 1 row after delete, got: " .. tostring(row.cnt))
cur:close()

-- Close connection and environment
conn:close()
env:close()

print("LuaSQL SQLite3 driver test PASSED")
