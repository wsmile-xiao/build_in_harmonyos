local builtin_assert = assert

local total = 0
local passed = 0
local failed = 0
local hooks = {}

local function fail(message)
  error(message or 'assertion failed', 2)
end

local function same(left, right, seen)
  if left == right then
    return true
  end
  if type(left) ~= type(right) then
    return false
  end
  if type(left) ~= 'table' then
    return false
  end

  seen = seen or {}
  if seen[left] == right then
    return true
  end
  seen[left] = right

  for key, value in pairs(left) do
    if not same(value, right[key], seen) then
      return false
    end
  end
  for key, value in pairs(right) do
    if not same(value, left[key], seen) then
      return false
    end
  end
  return true
end

local assertions = {}
assertions.are_same = function(expected, actual)
  if not same(expected, actual) then
    fail('values are not deeply equal')
  end
end
assertions.is_nil = function(value)
  if value ~= nil then
    fail('expected nil')
  end
end
assertions.is_true = function(value)
  if value ~= true then
    fail('expected true')
  end
end
assertions.has_error = function(callback)
  local ok = pcall(callback)
  if ok then
    fail('expected callback to raise an error')
  end
end
assertions.has_errors = assertions.has_error
assertions.are = {
  equals = function(expected, actual)
    if expected ~= actual then
      fail('values are not equal')
    end
  end,
}
setmetatable(assertions, {
  __call = function(_, condition, message)
    return builtin_assert(condition, message)
  end,
})
assert = assertions

function before_each(callback)
  hooks[#hooks + 1] = callback
end

function describe(_, callback)
  local hook_count = #hooks
  callback()
  while #hooks > hook_count do
    hooks[#hooks] = nil
  end
end

function it(name, callback)
  total = total + 1
  local ok, message = pcall(function()
    for index = 1, #hooks do
      hooks[index]()
    end
    callback()
  end)
  if ok then
    passed = passed + 1
    io.write('ok ', total, ' - ', name, '\n')
  else
    failed = failed + 1
    io.stderr:write('not ok ', total, ' - ', name, ': ', tostring(message), '\n')
  end
end

local executable = assert(LMPACK_RUNNER_EXECUTABLE)
local module = assert(LMPACK_MODULE)
local source = assert(LMPACK_UPSTREAM_SOURCE)
arg = arg or {}
arg[0] = 'libmpack-lua-upstream-runner'
arg[-1] = string.format('%q --upstream-child %q', executable, module)

local chunk, load_error = loadfile(source)
if not chunk then
  error(load_error)
end
local loaded, runtime_error = pcall(chunk)
if not loaded then
  failed = failed + 1
  io.stderr:write('not ok - upstream test file: ', tostring(runtime_error), '\n')
end

print(string.format(
  'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"upstream-test.lua-mini-busted","discovered":%d,"executed":%d,"passed":%d,"failed":%d}',
  failed == 0 and 'passed' or 'failed', total, total, passed, failed))
if failed ~= 0 or total == 0 then
  os.exit(1)
end
