#!/data/service/hnp/bin/bash
# test_package/test_nift.sh — nift 3.0.3 消费者功能测试
#
# 设计说明（code-style 二.7 豁免记录）：
#   本脚本为「计数型测试」，需在单个断言失败后继续执行以累计 passed/failed
#   并输出 HMBS_TEST_PACKAGE_RESULT 汇总。为兼容 set -euo pipefail，所有可能
#   失败的命令（nift/nsm --version、nift init-html/init/build/run、nift track、
#   grep）均以 `if cmd` 守卫放入 if/elif 条件中——条件内的失败不会触发
#   errexit，从而既满足 shell 安全模式，又不打断断言计数。
#
# 断言（R34：真实执行打包的 nift / nsm 二进制；上游 v3.0.3 无测试套件，
#   以下用例按 nift 官方文档的典型站点/脚本工作流设计，覆盖其核心引擎）:
#   1.  nift --version 退出码 0 且输出包含 3.0.3
#   2.  nsm  --version 退出码 0 且输出包含 3.0.3
#   3.  nift init-html 初始化并构建最小静态网站，output/index.html 真实产出
#   4.  init-html 项目静态资源 (assets/css, assets/js) 被镜像到 output/
#   5.  track 自定义模板页面：模板被选中（模板头部标记出现在输出中）
#   6.  模板变量 $[title] 被替换为页面标题（<title>Nift Alpha</title>）
#   7.  @content 注入：页面内容真实出现在输出 HTML 中
#   8.  多页面构建：第二张 tracked 页面 beta 独立产出 output/beta.html
#   9.  增量构建（hash 模式）：修改内容后重构建，新内容出现、旧内容被替换
#   10. 内嵌 Lua 引擎：nift run 执行 Lua 脚本并输出预期文本
#   11. nift init 通用项目初始化并构建成功，output/index.html 真实产出
set -euo pipefail

BASE="$(pwd)"
WORK="$BASE/.nift-tests-$$"
passes=0
fails=0

note_pass() { passes=$((passes + 1)); echo "[OK] $1"; }
note_fail() { fails=$((fails + 1)); echo "[FAIL] $1"; }

echo "[test] nift --version"
if VOUT=$(nift --version 2>&1); then
    if echo "$VOUT" | grep -q "3.0.3"; then
        note_pass "nift --version prints v3.0.3"
    else
        note_fail "nift --version output missing '3.0.3': $VOUT"
    fi
else
    note_fail "nift --version failed: $VOUT"
fi

echo "[test] nsm --version"
if NOUT=$(nsm --version 2>&1); then
    if echo "$NOUT" | grep -q "3.0.3"; then
        note_pass "nsm --version prints v3.0.3"
    else
        note_fail "nsm --version output missing '3.0.3': $NOUT"
    fi
else
    note_fail "nsm --version failed: $NOUT"
fi

if mkdir -p "$WORK/site" && cd "$WORK/site"; then
    echo "[test] nift init-html builds minimal site"
    if IOUT=$(nift init-html 2>&1); then
        if [ -s output/index.html ]; then
            note_pass "init-html built output/index.html ($(wc -c < output/index.html) bytes)"
        else
            note_fail "init-html rc=0 but output/index.html missing or empty"
        fi
    else
        note_fail "init-html failed: $IOUT"
    fi

    echo "[test] init-html mirrors static assets to output/"
    if [ -f output/assets/css/style.css ] && [ -f output/assets/js/script.js ]; then
        note_pass "static assets (css/js) mirrored into output/"
    else
        note_fail "static assets missing from output/ (css/js)"
    fi

    echo "[test] custom template selected for tracked page"
    cat > templates/page.html <<'TPL_EOF'
<!doctype html>
<html>
<head><title>$[title]</title></head>
<body>
<header>NIFT-TPL-HEADER</header>
<main>
@content
</main>
</body>
</html>
TPL_EOF
    mkdir -p content
    printf '<h1>Alpha page</h1>\n<p>NIFT-ALPHA-MARK-7788</p>\n' > content/alpha.html
    printf '<h1>Beta page</h1>\n<p>NIFT-BETA-MARK-7788</p>\n' > content/beta.html
    if nift track alpha "Nift Alpha" templates/page.html >/dev/null 2>&1 &&
       nift track beta "Nift Beta" templates/page.html >/dev/null 2>&1 &&
       nift build >/dev/null 2>&1; then
        if grep -q "NIFT-TPL-HEADER" output/alpha.html; then
            note_pass "custom template templates/page.html applied to alpha"
        else
            note_fail "output/alpha.html lacks custom template header"
        fi

        echo "[test] template variable \$[title] substitution"
        if grep -q "<title>Nift Alpha</title>" output/alpha.html; then
            note_pass "\$[title] substituted with tracked page title"
        else
            note_fail "output/alpha.html lacks '<title>Nift Alpha</title>'"
        fi

        echo "[test] @content injection"
        if grep -q "NIFT-ALPHA-MARK-7788" output/alpha.html; then
            note_pass "page content injected via @content"
        else
            note_fail "output/alpha.html lacks content marker NIFT-ALPHA-MARK-7788"
        fi

        echo "[test] multi-page build (beta)"
        if [ -f output/beta.html ] && grep -q "NIFT-BETA-MARK-7788" output/beta.html; then
            note_pass "second tracked page beta built to output/beta.html"
        else
            note_fail "output/beta.html missing or lacks content marker"
        fi

        echo "[test] incremental rebuild (hash mode) after content change"
        if nift incr-mode hash >/dev/null 2>&1; then
            printf '<h1>Alpha page v2</h1>\n<p>NIFT-ALPHA-MARK-8899</p>\n' > content/alpha.html
            if nift build >/dev/null 2>&1 &&
               grep -q "NIFT-ALPHA-MARK-8899" output/alpha.html &&
               ! grep -q "NIFT-ALPHA-MARK-7788" output/alpha.html; then
                note_pass "incremental rebuild picked up content change (old marker gone)"
            else
                note_fail "output/alpha.html not refreshed after content change"
            fi
        else
            note_fail "nift incr-mode hash failed"
        fi
    else
        note_fail "track/build pipeline failed"
    fi
    cd "$BASE"
else
    note_fail "cannot create site work dir $WORK/site"
fi

echo "[test] nift run executes embedded Lua script"
if mkdir -p "$WORK/lua" && cd "$WORK/lua"; then
    printf 'print("NIFT-LUA-OK-2468")\n' > t.lua
    if LOUT=$(nift run t.lua 2>&1); then
        if echo "$LOUT" | grep -q "NIFT-LUA-OK-2468"; then
            note_pass "embedded Lua (5.3) executed via 'nift run'"
        else
            note_fail "'nift run' output missing marker: $LOUT"
        fi
    else
        note_fail "'nift run t.lua' failed: $LOUT"
    fi
    cd "$BASE"
else
    note_fail "cannot create lua work dir $WORK/lua"
fi

echo "[test] nift init (generic project) builds output"
if mkdir -p "$WORK/gen" && cd "$WORK/gen"; then
    if nift init >/dev/null 2>&1; then
        if [ -s output/index.html ]; then
            note_pass "nift init created project and built output/index.html"
        else
            note_fail "nift init rc=0 but output/index.html missing or empty"
        fi
    else
        note_fail "nift init failed"
    fi
    cd "$BASE"
else
    note_fail "cannot create gen work dir $WORK/gen"
fi

rm -rf "$WORK"

if [ "$fails" -ne 0 ]; then
    echo "FAIL: $fails checks failed ($passes passed)"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_nift.sh","discovered":11,"passedCount":%d}\n' \
        "$passes"
    exit 1
fi

echo "OK: all 11 checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_nift.sh","discovered":11,"passedCount":%d}\n' \
    "$passes"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"makefile","command":"make check (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"nift 3.0.3 上游无测试套件：官方 tag v3.0.3 源码包内 Makefile 无 check/test 目标，仓库无 tests/ 目录；功能验证以 init-html/init 真实构建 + 自定义模板/增量/Lua 共 11 项用例代替"}\n'
exit 0
