-- test_stringy.lua — verification for lua-stringy 0.7
-- Adapted from upstream stringy_test.lua
-- Tests: split, strip, startswith, endswith, find, count, join

local stringy = require("stringy")

-- ── split ──────────────────────────────────────
local parts = stringy.split("asdfsk", "s")
assert(#parts == 3, "split: expected 3 parts, got " .. #parts)

assert(
  "a|b|c" == table.concat(stringy.split("a\tb\tc", "\t"), "|"),
  "split: tab delimiter"
)
assert(stringy.split("asdf", "s")[1] == "a", "split: first element")

assert(
  "a||b||c" == table.concat(stringy.split("aXXbXXc", "XX"), "|"),
  "split: multi-char delimiter"
)

-- ── strip ───────────────────────────────────────
assert(stringy.strip(" asdf ") == "asdf", "strip: both sides")
assert(stringy.strip("asdf ") == "asdf", "strip: trailing only")
assert(stringy.strip(" asdf  ") == "asdf", "strip: uneven")
assert(stringy.strip("asdf") == "asdf", "strip: no whitespace")
assert(stringy.strip("\nasdf\r\n") == "asdf", "strip: newlines")

-- ── startswith ──────────────────────────────────
assert(stringy.startswith("asdf", "a"), "startswith: single char")
assert(stringy.startswith("asdf", "asd"), "startswith: prefix")
assert(stringy.startswith("asdf", "asdf"), "startswith: full match")
assert(stringy.startswith("asdf", ""), "startswith: empty")
assert(not stringy.startswith("asdf", "asdfg"), "startswith: too long")
assert(not stringy.startswith("asdf", "b"), "startswith: no match")

-- ── endswith ────────────────────────────────────
assert(stringy.endswith("asdf", "f"), "endswith: single char")
assert(stringy.endswith("asdf", "asdf"), "endswith: full match")
assert(stringy.endswith("asdf", ""), "endswith: empty")
assert(not stringy.endswith("asdf", "xasdf"), "endswith: too long")
assert(not stringy.endswith("asdf", "x"), "endswith: no match")

-- ── find ────────────────────────────────────────
assert(stringy.find("baaaa", "a") == 2, "find: basic")
assert(stringy.find("baaaa", "baaaa") == 1, "find: full match")
assert(stringy.find("baaaa", "baaaa", 1) == 1, "find: with start")
assert(stringy.find("baaaa", "baaaa", 2) == nil, "find: not found with start")
assert(stringy.find("abcdef", "b", 3) == nil, "find: not found")
assert(stringy.find("abcdef", "c", 3) == 3, "find: with start=3")
assert(stringy.find("abcdef", "c", 4) == nil, "find: not found from 4")
assert(stringy.find("abcdef", "c", -1) == nil, "find: negative start")

-- ── count ───────────────────────────────────────
assert(stringy.count("aaa", "a") == 3, "count: single char")
assert(stringy.count("aaa", "aa") == 1, "count: non-overlapping")
assert(stringy.count("aaa", "") == 0, "count: empty token")
assert(stringy.count("aaa", "b") == 0, "count: not found")
assert(stringy.count("aaa", "aaa") == 1, "count: full match")
assert(stringy.count("aaa", "aaaa") == 0, "count: token too long")
assert(stringy.count("", "aaaa") == 0, "count: empty string")

-- ── join ────────────────────────────────────────
assert(stringy.join("_", 1, 2, 3) == "1_2_3", "join: basic")
assert(stringy.join("_", 1, "ab", "cd") == "1_ab_cd", "join: mixed types")

print("All lua-stringy tests passed!")
