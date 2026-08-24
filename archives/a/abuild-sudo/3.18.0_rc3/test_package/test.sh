#!/data/service/hnp/bin/bash
# test_package/test.sh — abuild-sudo 消费者功能测试
# 运行于 conanrun 环境（PATH 已包含安装后的 bin/）
# 三个真实用例:
#   TC1: abuild-sudo 二进制存在且可执行
#   TC2: 非白名单调用被受控拒绝（退出码 1 且 stderr 非空）
#        abuild-sudo 仅允许 abuild 组成员以白名单子命令(adduser/addgroup/apk)
#        提权;普通调用必然在组校验处受控失败(exit 1 "Group not found")。
#   TC3: abuild-adduser/abuild-addgroup/abuild-apk 符号链接存在且指向 abuild-sudo
set -u

discovered=3
passed=0
failed=0

# TC1
bin="$(command -v abuild-sudo 2>/dev/null)"
if [ -n "$bin" ] && [ -x "$bin" ]; then
    passed=$((passed + 1))
    echo "[ok] TC1: abuild-sudo binary present and executable ($bin)"
else
    failed=$((failed + 1))
    echo "[fail] TC1: abuild-sudo binary missing or not executable"
fi

# TC2
out="$(abuild-sudo 2>&1)"
rc=$?
if [ $rc -eq 1 ] && [ -n "$out" ]; then
    passed=$((passed + 1))
    echo "[ok] TC2: non-whitelisted invocation rejected (rc=1, stderr: $out)"
else
    failed=$((failed + 1))
    echo "[fail] TC2: invocation unexpectedly accepted (rc=$rc, stderr: $out)"
fi

# TC3
links_ok=0
for sub in adduser addgroup apk; do
    link="${bin%/*}/abuild-$sub"
    if [ -L "$link" ] && [ "$(readlink "$link")" = "abuild-sudo" ]; then
        links_ok=$((links_ok + 1))
        echo "[ok] TC3: symlink abuild-$sub -> abuild-sudo"
    else
        echo "[fail] TC3: symlink abuild-$sub missing or wrong target"
    fi
done
if [ "$links_ok" -eq 3 ]; then
    passed=$((passed + 1))
else
    failed=$((failed + 1))
fi

if [ $failed -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 1
fi
