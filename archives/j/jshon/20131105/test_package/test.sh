#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for the installed jshon binary.
#
# Runs in the conanrun environment (PATH includes the installed bin/,
# LD_LIBRARY_PATH includes jansson's lib dir).
# Every expected value below was verified against a real jshon 20131105
# binary built and run natively on aarch64-linux-ohos (see notes.md "W4").
# Notes: jshon 20131105 has no -c compact flag (added in later upstream
# commits); default output is 1-space-indented JSON. Top-level input must
# be an object or an array — scalar documents are a parse error.
set -u

# /system/bin (mksh) cannot execute ELF binaries; ensure coreutils are reachable.
export PATH="$PATH:/system/bin"

fail=0
check() { # check <label> <expected> <actual>
    if [ "$2" = "$3" ]; then
        echo "PASS: $1"
    else
        echo "FAIL: $1 (expected [$2], got [$3])"
        fail=$((fail + 1))
    fi
}

echo "--- jshon consumer verification ---"

# ===== object key 读取 =====
# 1. 顶层 object 按 key 提取，-t 报告类型。
check "object key type" "number" "$(echo '{"a":1}' | jshon -e a -t)"
# 2. 嵌套 object 逐层提取字符串，-u 去引号输出。
check "nested key unstring" "str" "$(echo '{"b":{"c":"str"}}' | jshon -e b -e c -u)"
# 3. object 长度。
check "object length" "2" "$(echo '{"a":1,"b":2}' | jshon -l)"
# 4. key 列表按插入序输出（jansson 2.14+ 对象默认有序）。
check "object keys in insertion order" "b
a" "$(echo '{"b":2,"a":1}' | jshon -k)"

# ===== array 读取 =====
# 5. 数组按下标提取。
check "array index" "20" "$(echo '[10,20,30]' | jshon -e 1 -u)"
# 6. 数组长度。
check "array length" "3" "$(echo '[10,20,30]' | jshon -l)"
# 7. -a 迭代数组逐元素 -u。
check "array iterate" "1
2
3" "$(echo '[1,2,3]' | jshon -a -u)"

# ===== string / number / bool / null =====
# 8-9. string 的类型与去引号值（顶层标量被拒，字符串需包在 object 里）。
check "string type" "string" "$(echo '{"s":"hi"}' | jshon -e s -t)"
check "string value" "hi" "$(echo '{"s":"hi"}' | jshon -e s -u)"
# 10. 转义引号经 -u 还原为字面量。
check "escaped string value" 'a"b' "$(echo '{"s":"a\"b"}' | jshon -e s -u)"
# 11. number 值。
check "number value" "42" "$(echo '{"n":42}' | jshon -e n -u)"
# 12-13. bool 的类型与值。
check "bool type" "bool" "$(echo '{"x":true}' | jshon -e x -t)"
check "bool value" "true" "$(echo '{"x":true}' | jshon -e x -u)"
# 14-15. null 的类型与值。
check "null type" "null" "$(echo '{"x":null}' | jshon -e x -t)"
check "null value" "null" "$(echo '{"x":null}' | jshon -e x -u)"

# ===== 创建 / 修改 JSON =====
# 16. -s 插入字符串 key（默认 1 空格缩进的多行输出）。
check "create string key" '{
 "greeting": "hello"
}' "$(echo '{}' | jshon -s hello -i greeting)"
# 17. -n 插入非字符串 JSON 字面量。
check "create nonstring value" '{
 "num": 42
}' "$(echo '{}' | jshon -n 42 -i num)"
# 18. -s -i 覆盖已有 key（修改）。
check "modify existing key" '{
 "a": "two"
}' "$(echo '{"a":1}' | jshon -s two -i a)"
# 19. -d 删除 key。
check "delete key" '{
 "b": 2
}' "$(echo '{"a":1,"b":2}' | jshon -d a)"
# 20. 向空数组下标 0 插入元素（数组创建）。
check "array insert" '[
 "x"
]' "$(echo '[]' | jshon -s x -i 0)"

# ===== invalid JSON / 输入错误路径 =====
# 21. 语法错误的 JSON 必须返回非 0。
if echo '{bad' | jshon -t >/dev/null 2>&1; then
    echo "FAIL: invalid JSON returned 0"
    fail=$((fail + 1))
else
    echo "PASS: invalid JSON non-zero exit"
fi
# 22. 顶层标量输入被拒绝（jshon 顶层只接受 object/array）。
if echo '"hi"' | jshon -t >/dev/null 2>&1; then
    echo "FAIL: top-level scalar accepted"
    fail=$((fail + 1))
else
    echo "PASS: top-level scalar rejected"
fi
# 23. 空输入返回非 0。
if printf '' | jshon -t >/dev/null 2>&1; then
    echo "FAIL: empty input returned 0"
    fail=$((fail + 1))
else
    echo "PASS: empty input non-zero exit"
fi

# ===== 版本 =====
# 24. --version 原生支持（E503 判例对 jshon 不适用于 --version；--help 未注册，
#     见 notes.md L2 说明）。
check "--version output" "20131105" "$(jshon --version 2>/dev/null)"

# ===== ELF 专项（ELF64 / AArch64 / PIE / musl / 无宿主 RPATH）=====
echo "--- ELF 专项 ---"
bin_path="$(command -v jshon)"
if [ -n "$bin_path" ]; then
    echo "PASS: jshon resolved on PATH"
else
    echo "FAIL: jshon not found on PATH"
    fail=$((fail + 1))
fi
hdr="$(readelf -h "$bin_path" 2>/dev/null)"
# 25. ELF64。
if printf '%s\n' "$hdr" | grep -q 'Class:.*ELF64'; then
    echo "PASS: ELF64"
else
    echo "FAIL: not ELF64"
    fail=$((fail + 1))
fi
# 26. AArch64。
if printf '%s\n' "$hdr" | grep -q 'Machine:.*AArch64'; then
    echo "PASS: AArch64"
else
    echo "FAIL: not AArch64"
    fail=$((fail + 1))
fi
# 27. ET_DYN（PIE）。
if printf '%s\n' "$hdr" | grep -q 'Type:.*DYN'; then
    echo "PASS: PIE (ET_DYN)"
else
    echo "FAIL: not PIE (ET_DYN)"
    fail=$((fail + 1))
fi
# 28. musl 程序解释器。
if readelf -l "$bin_path" 2>/dev/null | grep -q 'interpreter: /lib/ld-musl-aarch64.so.1'; then
    echo "PASS: musl interpreter"
else
    echo "FAIL: musl interpreter not found"
    fail=$((fail + 1))
fi
# 29. 无宿主 RPATH/RUNPATH（动态段不得含任何 rpath 条目）。
if readelf -d "$bin_path" 2>/dev/null | grep -qE 'RPATH|RUNPATH'; then
    echo "FAIL: RPATH/RUNPATH present"
    fail=$((fail + 1))
else
    echo "PASS: no RPATH/RUNPATH"
fi
# 30. NEEDED 含 libjansson.so（复用制品仓 jansson，动态链接）。
if readelf -d "$bin_path" 2>/dev/null | grep -q 'NEEDED.*libjansson.so'; then
    echo "PASS: NEEDED libjansson.so"
else
    echo "FAIL: libjansson.so not in NEEDED"
    fail=$((fail + 1))
fi

if [ "$fail" -ne 0 ]; then
    echo "jshon test_package: $fail assertion(s) FAILED"
    exit 1
fi
echo "jshon test_package: 31/31 assertions PASS"
exit 0
