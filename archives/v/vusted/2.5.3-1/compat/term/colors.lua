local colors = {}
local names = {
  "reset",
  "default",
  "bright",
  "dim",
  "underscore",
  "blink",
  "reverse",
  "hidden",
  "black",
  "red",
  "green",
  "yellow",
  "blue",
  "magenta",
  "cyan",
  "white",
  "onblack",
  "onred",
  "ongreen",
  "onyellow",
  "onblue",
  "onmagenta",
  "oncyan",
  "onwhite",
}

local mt = {}

function mt:__tostring()
  return ""
end

function mt.__concat(left, right)
  return tostring(left) .. tostring(right)
end

function mt:__call(text)
  return tostring(text)
end

local function color()
  return setmetatable({}, mt)
end

for _, name in ipairs(names) do
  colors[name] = color()
end

return colors
