-- md5.lua — pure-Lua MD5 message-digest (RFC 1321), Lua 5.4 native bit ops.
-- Provides the `md5.sumhexa` API used by acf-core's authenticator.lua.
-- TEST-HARNESS module; NOT shipped with the acf-core conan package.
local string, table, math = string, table, math
local MASK32 = 0xFFFFFFFF

local function band(a, b) return (a & b) & MASK32 end
local function bor(a, b) return (a | b) & MASK32 end
local function bxor(a, b) return (a ~ b) & MASK32 end
local function bnot(a) return ((~a) & MASK32) end

local function f(x, y, z) return bxor(band(x, y), band(bnot(x), z)) end
local function g(x, y, z) return bxor(band(x, z), band(y, bnot(z))) end
local function h(x, y, z) return bxor(bxor(x, y), z) end
-- I(X,Y,Z) = Y ^ (X | ~Z)
local function i_(x, y, z) return bxor(y, bor(x, bnot(z))) end

local S = { {7,12,17,22}, {5,9,14,20}, {4,11,16,23}, {6,10,15,21} }
local K = {}
for k = 1, 64 do
  K[k] = math.floor(2^32 * math.abs(math.sin(k))) & MASK32
end

local function rol(x, n) return ((x << n) | (x >> (32 - n))) & MASK32 end

local function md5_process(state, block)
  local a, b, c, d = state[1], state[2], state[3], state[4]
  local M = {}
  for i = 1, 16 do
    local v = 0
    for j = 0, 3 do
      v = v | (block[(i-1)*4 + j + 1] << (8*j))
    end
    M[i] = v & MASK32
  end
  for k = 1, 64 do
    local fval, gidx, r
    if k <= 16 then fval = f(b, c, d); gidx = k; r = S[1][((k-1)%4)+1]
    elseif k <= 32 then fval = g(b, c, d); gidx = ((5*k - 4) % 16) + 1; r = S[2][((k-1)%4)+1]
    elseif k <= 48 then fval = h(b, c, d); gidx = ((3*k + 2) % 16) + 1; r = S[3][((k-1)%4)+1]
    else fval = i_(b, c, d); gidx = ((7*k - 7) % 16) + 1; r = S[4][((k-1)%4)+1]
    end
    local temp = (a + fval + K[k] + M[gidx]) & MASK32
    temp = rol(temp, r)
    temp = (temp + b) & MASK32
    a, b, c, d = d, temp, b, c
  end
  state[1] = (state[1] + a) & MASK32
  state[2] = (state[2] + b) & MASK32
  state[3] = (state[3] + c) & MASK32
  state[4] = (state[4] + d) & MASK32
end

local function md5_digest(s)
  local bytes = {}
  for i = 1, #s do bytes[i] = string.byte(s, i) end
  local len = #s
  local orig_len_bits = len * 8
  bytes[#bytes+1] = 0x80
  while (#bytes % 64) ~= 56 do bytes[#bytes+1] = 0 end
  for j = 0, 7 do
    bytes[#bytes+1] = math.floor(orig_len_bits / 2^(8*j)) % 256
  end
  local state = {0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476}
  for off = 1, #bytes, 64 do
    local block = {}
    for i = 1, 64 do block[i] = bytes[off + i - 1] end
    md5_process(state, block)
  end
  local digest = {}
  local function word_le(w)
    for j = 0, 3 do digest[#digest+1] = math.floor(w / 2^(8*j)) % 256 end
  end
  word_le(state[1]); word_le(state[2]); word_le(state[3]); word_le(state[4])
  return digest
end

local md5 = {}

function md5.sumhexa(s)
  local digest = md5_digest(s or "")
  local hex = {}
  for _, b in ipairs(digest) do hex[#hex+1] = string.format("%02x", b) end
  return table.concat(hex)
end

return md5
