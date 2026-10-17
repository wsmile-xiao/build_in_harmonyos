-- luasql/sqlite3.lua — in-memory SQLite3 stub for triggering db.lua assert paths.
-- acf-lib's db.lua declares a local `assert(v, m)` (lines 5-11) and calls it at
-- 9 sites (L41/69/82/86/90/100/130/134/137) inside databaseconnect /
-- runsqlcommand / getselectresponse. This stub provides a luasql.sqlite3()
-- environment whose :connect() returns a fake connection object. The
-- connection's :execute() understands SAVEPOINT / RELEASE / ROLLBACK TO /
-- CREATE TABLE / INSERT / SELECT so the 9 assert sites are genuinely reached
-- and the local assert's `error(m, 0)` fires when a SQL statement fails.
--
-- Test-harness only; not shipped with acf-lib-lua5.4.
local luasql_sqlite3 = {}

function luasql_sqlite3.sqlite3()
  local env = {}
  function env:connect(database, user, password, host, port)
    -- In-memory SQLite: tables stored in `env.tables[name] = {row, row, ...}`,
    -- a savepoint stack in `env.sp`, and a row-cursor factory for SELECT.
    env.tables = {}
    env.sp = {}
    local con = {}
    function con:execute(sql)
      if sql == nil then return nil, "nil sql" end
      if type(sql) ~= "string" then return nil, "non-string sql" end
      local s = sql:match("^%s*(.-)%s*$")
      -- SAVEPOINT / RELEASE / ROLLBACK TO — assert sites L69/L82/L90/L100/L130/L137
      if s:match("^SAVEPOINT%s+") then
        env.sp[#env.sp + 1] = s:match("SAVEPOINT%s+(%S+)")
        return 0
      end
      if s:match("^RELEASE%s+") then
        if #env.sp > 0 then env.sp[#env.sp] = nil end
        return 0
      end
      if s:match("^ROLLBACK%s+TO%s+") then
        -- keep the savepoint, just roll back logical state (no-op for in-memory)
        return 0
      end
      -- CREATE TABLE — triggers assert(res, err) path L86 when ok
      local tbl = s:match("^CREATE%s+TABLE%s+([%w_]+)")
      if tbl then
        env.tables[tbl] = env.tables[tbl] or {}
        return 0
      end
      -- INSERT — triggers assert(res, err) path L86 when ok
      local itbl = s:match("^INSERT%s+INTO%s+([%w_]+)")
      if itbl then
        if not env.tables[itbl] then return nil, "LuaSQL: no such table: " .. itbl end
        local vals = s:match("%((.-)%)%s*VALUES%s*%((.-)%)%s*$")
        if vals then
          local cols = {}
          for c in vals:gmatch("[%w_]+") do cols[#cols + 1] = c end
          local vstr = s:match("VALUES%s*%((.-)%)%s*$")
          local vals_arr = {}
          for v in (vstr or ""):gmatch("[^,%s]+") do vals_arr[#vals_arr + 1] = v end
          local row = {}
          for i, c in ipairs(cols) do row[c] = vals_arr[i] end
          env.tables[itbl][#env.tables[itbl] + 1] = row
        end
        return 1
      end
      -- SELECT — returns a cursor for getselectresponse (L102/L134)
      local stbl = s:match("^SELECT%s+.+%s+FROM%s+([%w_]+)")
      if stbl then
        if not env.tables[stbl] then return nil, "LuaSQL: no such table: " .. stbl end
        local cur = {}
        local rows = {}
        for _, r in ipairs(env.tables[stbl]) do rows[#rows + 1] = r end
        local idx = 0
        function cur:fetch(tbl, mode)
          idx = idx + 1
          if idx > #rows then return nil end
          if type(tbl) == "table" then
            for k, v in pairs(rows[idx]) do tbl[k] = v end
            return tbl
          end
          return rows[idx]
        end
        function cur:close() end
        return cur
      end
      -- Unknown statement → return failure so assert(res, err) sites fire honestly
      return nil, "LuaSQL: unsupported statement"
    end
    function con:close() end
    return con
  end
  function env:close() end
  return env
end

return luasql_sqlite3
