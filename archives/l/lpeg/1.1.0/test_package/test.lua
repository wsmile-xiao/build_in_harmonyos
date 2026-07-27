-- test.lua — L1 test for lpeg 1.1.0
-- R34: Calls lpeg's actual API (P, R, S, match, version, etc.)

local lpeg = require("lpeg")

-- Verify lpeg version
assert(type(lpeg) == "table", "lpeg should be a table")
assert(lpeg.version == "LPeg 1.1.0", "lpeg version should be LPeg 1.1.0, got: " .. tostring(lpeg.version))

local P = lpeg.P
local R = lpeg.R
local S = lpeg.S
local C = lpeg.C
local Ct = lpeg.Ct

-- Test 1: Match a literal string
local p1 = P("hello")
assert(p1:match("hello world") == 6, "P('hello') should match at position 6")
assert(p1:match("world") == nil, "P('hello') should not match 'world'")

-- Test 2: Match character ranges
local digit = R("09")
assert(digit:match("5") == 2, "R('09') should match digit '5'")
assert(digit:match("a") == nil, "R('09') should not match 'a'")

-- Test 3: Match one or more digits
local number = digit^1
assert(number:match("12345abc") == 6, "digit^1 should match '12345' consuming 5 chars")
assert(number:match("abc") == nil, "digit^1 should not match 'abc'")

-- Test 4: Capture groups
local word = C(R("AZ","az")^1)
local result = word:match("hello")
assert(result == "hello", "C(R('AZ','az')^1) should capture 'hello', got: " .. tostring(result))

-- Test 5: Pattern composition with sequences
local greeting = P("hello") * P(" ") * C(R("AZ","az")^1)
local name = greeting:match("hello world")
assert(name == "world", "Should capture 'world' from 'hello world', got: " .. tostring(name))

-- Test 6: Choice operator
local yesno = P("yes") + P("no")
assert(yesno:match("yes") == 4, "Should match 'yes'")
assert(yesno:match("no") == 3, "Should match 'no'")
assert(yesno:match("maybe") == nil, "Should not match 'maybe'")

-- Test 7: Set matching
local hexdigit = S("0123456789abcdefABCDEF")
assert(hexdigit:match("a") == 2, "Should match hex digit 'a'")
assert(hexdigit:match("g") == nil, "Should not match 'g'")

print("lpeg test: all assertions passed OK")
