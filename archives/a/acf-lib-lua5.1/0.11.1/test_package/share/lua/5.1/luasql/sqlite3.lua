local module = {}

function module.sqlite3()
  -- LuaSQL factories return an environment; acf.db stores it in dbobject.env.
  local environment = {
    trace = {},
    stats = {
      release = 0,
      rollback_to = 0,
      savepoint = 0,
      select = 0,
    },
  }

  function environment:connect()
    environment.tables = {}
    environment.savepoints = {}
    -- connect() returns a distinct connection, stored by acf.db in dbobject.con.
    local connection = {}

    function connection:escape(value)
      return tostring(value):gsub("'", "''")
    end

    function connection:execute(sql)
      if type(sql) ~= "string" then return nil, "unsupported non-string statement" end
      local statement = sql:match("^%s*(.-)%s*$")
      environment.trace[#environment.trace + 1] = statement
      if statement:match("^SAVEPOINT%s+") then
        environment.stats.savepoint = environment.stats.savepoint + 1
        environment.savepoints[#environment.savepoints + 1] = true
        return 0
      end
      if statement:match("^ROLLBACK%s+TO%s+") then
        environment.stats.rollback_to = environment.stats.rollback_to + 1
        return 0
      end
      if statement:match("^RELEASE%s+") then
        environment.stats.release = environment.stats.release + 1
        environment.savepoints[#environment.savepoints] = nil
        return 0
      end

      local table_name = statement:match("^CREATE%s+TABLE%s+([%w_]+)")
      if table_name then
        environment.tables[table_name] = environment.tables[table_name] or {}
        return 0
      end

      table_name = statement:match("^INSERT%s+INTO%s+([%w_]+)")
      if table_name then
        if not environment.tables[table_name] then
          return nil, "LuaSQL: no such table: " .. table_name
        end
        environment.tables[table_name][#environment.tables[table_name] + 1] = {id = 1}
        return 1
      end

      table_name = statement:match("^SELECT%s+.+%s+FROM%s+([%w_]+)")
      if table_name then
        environment.stats.select = environment.stats.select + 1
        if not environment.tables[table_name] then
          return nil, "LuaSQL: no such table: " .. table_name
        end
        local rows = environment.tables[table_name]
        local cursor = {index = 0}
        function cursor:fetch(row)
          self.index = self.index + 1
          if not rows[self.index] then return nil end
          row = row or {}
          for key, value in pairs(rows[self.index]) do row[key] = value end
          return row
        end
        function cursor:close() end
        return cursor
      end

      return nil, "unsupported statement"
    end

    function connection:close() end
    return connection
  end

  function environment:close() end
  return environment
end

return module
