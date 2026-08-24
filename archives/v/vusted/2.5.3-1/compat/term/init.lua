local term = {}

function term.isatty()
  return false
end

function term.maketermfunc(sequence_fmt)
  return function(handle, ...)
    local first = handle
    local args = { ... }
    if type(handle) ~= "userdata" then
      handle = io.stdout
      if first ~= nil then
        table.insert(args, 1, first)
      end
    end
    local unpack_fn = table.unpack or unpack
    handle:write(string.format(sequence_fmt, unpack_fn(args)))
    return true
  end
end

term.colors = require("term.colors")
term.cursor = {}

return term
