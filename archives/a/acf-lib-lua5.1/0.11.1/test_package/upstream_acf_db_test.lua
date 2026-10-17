local pkg = arg[1]
local harness = arg[2]
assert(pkg and pkg ~= "", "missing package folder")
assert(harness and harness ~= "", "missing test harness folder")

local base = pkg .. "/share/lua/5.1"
local stub = harness .. "/share/lua/5.1"
package.path = table.concat({
  base .. "/?.lua",
  base .. "/?/init.lua",
  base .. "/acf/?.lua",
  stub .. "/?.lua",
  stub .. "/?/init.lua",
  package.path,
}, ";")

local sites = {
  "L35/L41 databaseconnect keeps environment and connection distinct",
  "L69 runsqlcommand SAVEPOINT assert",
  "L82 runsqlcommand configured-table recovery ROLLBACK TO assert",
  "L86 runsqlcommand assert(res,err) error branch",
  "L90 runsqlcommand RELEASE assert",
  "L100 getselectresponse SAVEPOINT assert",
  "L102 getselectresponse execute assert",
  "L130 getselectresponse configured-table recovery ROLLBACK TO assert",
  "L134 getselectresponse assert(res,err) error branch",
  "L137 getselectresponse RELEASE assert",
}
local results = {}

local loaded, db = pcall(require, "acf.db")
if loaded then
  local function stat(object, name)
    if not object.env or not object.env.stats then return 0 end
    return object.env.stats[name] or 0
  end

  local function trace_matches(object, start_index, expected)
    local trace = object.env and object.env.trace or {}
    if #trace ~= start_index + #expected then return false end
    for index, statement in ipairs(expected) do
      if trace[start_index + index] ~= statement then
        return false
      end
    end
    return true
  end

  local function fresh()
    local object = db.create(db.engine.sqlite3, ":memory:", "", "", "", "")
    object.table_creation_scripts = {}
    object.databaseconnect()
    object.runsqlcommand("CREATE TABLE t (id INT)", false)
    object.runsqlcommand("INSERT INTO t (id) VALUES (1)", false)
    return object
  end

  local object = db.create(db.engine.sqlite3, ":memory:", "", "", "", "")
  object.table_creation_scripts = {}
  local connected = pcall(function() object.databaseconnect() end)
  results[1] = connected and
    object.env ~= nil and object.con ~= nil and object.env ~= object.con and
    type(object.env.connect) == "function" and
    type(object.con.execute) == "function" and
    object.env.trace ~= nil and object.env.stats ~= nil

  object = fresh()
  local savepoint_before = stat(object, "savepoint")
  local release_before = stat(object, "release")
  local transaction_ok = pcall(function()
    object.runsqlcommand("CREATE TABLE t2 (id INT)", true)
  end)
  results[2] = transaction_ok and
    stat(object, "savepoint") == savepoint_before + 1
  results[5] = transaction_ok and
    stat(object, "release") == release_before + 1

  object = fresh()
  object.table_creation_scripts = {
    missing_tbl = {"CREATE TABLE missing_tbl (id INT)"}
  }
  local rollback_before = stat(object, "rollback_to")
  local select_before = stat(object, "select")
  local trace_before = #object.env.trace
  -- Configured missing tables recover at db.lua L81-L84 and never reach L86.
  local command_recovered = pcall(function()
    object.runsqlcommand("SELECT * FROM missing_tbl", true)
  end)
  results[3] = command_recovered and
    stat(object, "rollback_to") == rollback_before + 1 and
    stat(object, "select") == select_before + 2 and
    object.env.tables.missing_tbl ~= nil and
    trace_matches(object, trace_before, {
      "SAVEPOINT before_command",
      "SELECT * FROM missing_tbl",
      "ROLLBACK TO before_command",
      "SAVEPOINT before_command",
      "CREATE TABLE missing_tbl (id INT)",
      "RELEASE SAVEPOINT before_command",
      "SAVEPOINT before_command",
      "SELECT * FROM missing_tbl",
      "RELEASE SAVEPOINT before_command",
    })

  object = fresh()
  local error_ok, error_message = pcall(function()
    object.runsqlcommand("UNSUPPORTED STATEMENT", false)
  end)
  results[4] = not error_ok and tostring(error_message):find("unsupported", 1, true) ~= nil

  object = fresh()
  savepoint_before = stat(object, "savepoint")
  release_before = stat(object, "release")
  select_before = stat(object, "select")
  local select_ok = pcall(function()
    object.getselectresponse("SELECT * FROM t", true)
  end)
  results[6] = select_ok and
    stat(object, "savepoint") == savepoint_before + 1
  results[7] = select_ok and
    stat(object, "select") == select_before + 1
  results[10] = select_ok and
    stat(object, "release") == release_before + 1

  object = fresh()
  object.table_creation_scripts = {
    missing_tbl = {"CREATE TABLE missing_tbl (id INT)"}
  }
  rollback_before = stat(object, "rollback_to")
  select_before = stat(object, "select")
  trace_before = #object.env.trace
  -- L132 returns the recursive retry, so both SELECT attempts are observable.
  local select_recovered = pcall(function()
    object.getselectresponse("SELECT * FROM missing_tbl", true)
  end)
  results[8] = select_recovered and
    stat(object, "rollback_to") == rollback_before + 1 and
    stat(object, "select") == select_before + 2 and
    object.env.tables.missing_tbl ~= nil and
    trace_matches(object, trace_before, {
      "SAVEPOINT before_select",
      "SELECT * FROM missing_tbl",
      "ROLLBACK TO before_select",
      "SAVEPOINT before_command",
      "CREATE TABLE missing_tbl (id INT)",
      "RELEASE SAVEPOINT before_command",
      "SAVEPOINT before_select",
      "SELECT * FROM missing_tbl",
      "RELEASE SAVEPOINT before_select",
    })

  object = fresh()
  rollback_before = stat(object, "rollback_to")
  trace_before = #object.env.trace
  -- Unrecognized errors bypass recovery and reach L134 without a rollback.
  error_ok, error_message = pcall(function()
    object.getselectresponse("UNSUPPORTED STATEMENT", true)
  end)
  results[9] = not error_ok and
    tostring(error_message):find("unsupported", 1, true) ~= nil and
    stat(object, "rollback_to") == rollback_before and
    trace_matches(object, trace_before, {
      "SAVEPOINT before_select",
      "UNSUPPORTED STATEMENT",
    })
end

local discovered = #sites
local executed, passed, failed, skipped = 0, 0, 0, 0
for index, site in ipairs(sites) do
  if not loaded or results[index] == nil then
    skipped = skipped + 1
    io.write("[UPSTREAM-SKIP] " .. site .. "\n")
  elseif results[index] then
    executed = executed + 1
    passed = passed + 1
    io.write("[UPSTREAM-PASS] " .. site .. "\n")
  else
    executed = executed + 1
    failed = failed + 1
    io.write("[UPSTREAM-FAIL] " .. site .. "\n")
  end
end

local status = "failed"
if executed == discovered and passed == discovered and failed == 0 and skipped == 0 then
  status = "passed"
end
io.write(string.format(
  "UPSTREAM_ACF_DB_TEST: discovered=%d executed=%d passed=%d failed=%d skipped=%d\n",
  discovered, executed, passed, failed, skipped))
io.write(string.format(
  'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"acf.db-lua-assert-sites","command":"lua-runner upstream_acf_db_test.lua <pkg> <harness>","discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":%d,"reason":"upstream has no formal suite; real db.lua runtime assert sites executed with a test-only in-memory LuaSQL stub"}\n',
  status, discovered, executed, passed, failed, skipped))
io.stdout:flush()
if status ~= "passed" then error("db.lua assert-site execution failed", 0) end
