-- json.lua — pure-Lua JSON encoder (subset used by acf-core: json.encode).
-- TEST-HARNESS equivalent of lua-json4's json module. NOT shipped with the
-- acf-core conan package.
local json = {}

local function esc(s)
  s = string.gsub(s, '\\', '\\\\')
  s = string.gsub(s, '"', '\\"')
  s = string.gsub(s, '\n', '\\n')
  s = string.gsub(s, '\r', '\\r')
  s = string.gsub(s, '\t', '\\t')
  return s
end

local function encode(val, stack)
  local t = type(val)
  if t == "nil" then return "null"
  elseif t == "boolean" then return tostring(val)
  elseif t == "number" then
    if val ~= val or val == math.huge or val == -math.huge then return "null" end
    return string.format("%.14g", val)
  elseif t == "string" then return '"' .. esc(val) .. '"'
  elseif t == "table" then
    if stack[val] then return "null" end
    stack[val] = true
    local is_array = true
    local n = 0
    for k in pairs(val) do
      if type(k) ~= "number" or k < 1 or k % 1 ~= 0 then is_array = false end
      if type(k) == "number" and k > n then n = k end
    end
    local parts = {}
    if is_array and n > 0 then
      for i = 1, n do parts[#parts+1] = encode(val[i], stack) end
    else
      local keys = {}
      for k in pairs(val) do keys[#keys+1] = k end
      table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
      for _, k in ipairs(keys) do
        if type(k) == "string" then
          parts[#parts+1] = '"' .. esc(k) .. '":' .. encode(val[k], stack)
        end
      end
    end
    stack[val] = nil
    if is_array and n > 0 then return "[" .. table.concat(parts, ",") .. "]" end
    if #parts == 0 then return "{}" end
    return "{" .. table.concat(parts, ",") .. "}"
  end
  return "null"
end

function json.encode(val)
  return encode(val, {})
end

return json
