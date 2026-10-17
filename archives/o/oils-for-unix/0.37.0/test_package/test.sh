#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke/functional test for oils-for-unix binaries.
# Runs in the conanrun environment (PATH includes the installed bin/).
set -eu

fail() {
    echo "[test] FAIL: $1" >&2
    exit 1
}

# 1. The main binary must report the packaged version.
echo "[test] oils-for-unix --version"
version_out="$(oils-for-unix --version 2>&1)"
echo "       -> $version_out"
case "$version_out" in
    *"Oils 0.37.0"*) ;;
    *) fail "unexpected --version output: $version_out" ;;
esac

# 2. OSH behaves like a POSIX shell: simple echo + variable expansion.
echo "[test] osh -c 'echo hello from osh'"
osh_out="$(osh -c 'echo hello from osh' 2>&1)"
[ "$osh_out" = "hello from osh" ] || fail "osh echo mismatch: $osh_out"

# 3. OSH arithmetic expansion must evaluate correctly (real shell feature).
echo "[test] osh -c 'echo \$((1 + 2 * 3))'"
osh_arith="$(osh -c 'echo $((1 + 2 * 3))' 2>&1)"
[ "$osh_arith" = "7" ] || fail "osh arithmetic mismatch: $osh_arith"

# 4. YSH must also run as the same multi-call binary (symlink dispatch).
echo "[test] ysh -c 'echo hello from ysh'"
ysh_out="$(ysh -c 'echo hello from ysh' 2>&1)"
[ "$ysh_out" = "hello from ysh" ] || fail "ysh echo mismatch: $ysh_out"

# 5. YSH structured data (JSON) must work, proving the YSH runtime is intact.
echo "[test] ysh -c 'json write ({x: 42})'"
ysh_json="$(ysh -c 'json write ({x: 42})' 2>&1)"
case "$ysh_json" in
    *'"x": 42'*) ;;
    *) fail "ysh json write mismatch: $ysh_json" ;;
esac

# --- OSH (POSIX shell) core features ---

# 6. Variable assignment and expansion.
echo "[test] osh -c 'x=hello; echo \$x'"
osh_var="$(osh -c 'x=hello; echo $x' 2>&1)"
[ "$osh_var" = "hello" ] || fail "osh var expansion mismatch: $osh_var"

# 7. Command substitution.
echo "[test] osh -c 'echo \$(echo sub)'"
osh_sub="$(osh -c 'echo $(echo sub)' 2>&1)"
[ "$osh_sub" = "sub" ] || fail "osh command substitution mismatch: $osh_sub"

# 8. Pipe + read (OSH preserves read variable across a pipeline).
echo "[test] osh -c 'echo hi | read v; echo got:\$v'"
osh_read="$(osh -c 'echo hi | read v; echo got:$v' 2>&1)"
[ "$osh_read" = "got:hi" ] || fail "osh pipe/read mismatch: $osh_read"

# 9. if conditional.
echo "[test] osh -c 'if [ 1 -eq 1 ]; then echo ok; fi'"
osh_if="$(osh -c 'if [ 1 -eq 1 ]; then echo ok; fi' 2>&1)"
[ "$osh_if" = "ok" ] || fail "osh if mismatch: $osh_if"

# 10. for loop.
echo "[test] osh -c 'for i in a b c; do printf %s \$i; done'"
osh_for="$(osh -c 'for i in a b c; do printf %s $i; done' 2>&1)"
[ "$osh_for" = "abc" ] || fail "osh for loop mismatch: $osh_for"

# 11. Function definition and call.
echo "[test] osh -c 'f() { echo fn; }; f'"
osh_fn="$(osh -c 'f() { echo fn; }; f' 2>&1)"
[ "$osh_fn" = "fn" ] || fail "osh function mismatch: $osh_fn"

# 12. case pattern matching.
echo "[test] osh -c 'case x in x) echo m;; esac'"
osh_case="$(osh -c 'case x in x) echo m;; esac' 2>&1)"
[ "$osh_case" = "m" ] || fail "osh case mismatch: $osh_case"

# 13. Exit status propagation ($?).
echo "[test] osh -c 'false; echo rc=\$?'"
osh_rc="$(osh -c 'false; echo rc=$?' 2>&1)"
[ "$osh_rc" = "rc=1" ] || fail "osh exit code mismatch: $osh_rc"

# 14. Globbing (pathname expansion).
echo "[test] osh -c 'echo *.txt' (in a temp dir)"
tmpd="$(mktemp -d)"
(
    cd "$tmpd"
    touch t.txt
    osh_glob="$(osh -c 'echo *.txt' 2>&1)"
    [ "$osh_glob" = "t.txt" ] || { echo "osh glob mismatch: $osh_glob" >&2; exit 1; }
)
rm -rf "$tmpd"

# --- YSH (structured language) core features ---

# 15. List literal + len().
echo "[test] ysh -c 'var a = [1,2,3]; echo \$[len(a)]'"
ysh_len="$(ysh -c 'var a = [1,2,3]; echo $[len(a)]' 2>&1)"
[ "$ysh_len" = "3" ] || fail "ysh list/len mismatch: $ysh_len"

# 16. Dict literal + attribute access.
echo "[test] ysh -c 'var d = {name: \"oil\"}; echo \$[d.name]'"
ysh_dict="$(ysh -c 'var d = {name: "oil"}; echo $[d.name]' 2>&1)"
[ "$ysh_dict" = "oil" ] || fail "ysh dict mismatch: $ysh_dict"

# 17. JSON read from stdin into _reply.
echo "[test] ysh -c 'echo \"{\\\"k\\\": 42}\" | json read; echo \$[_reply.k]'"
ysh_json_read="$(ysh -c 'echo "{\"k\": 42}" | json read; echo $[_reply.k]' 2>&1)"
[ "$ysh_json_read" = "42" ] || fail "ysh json read mismatch: $ysh_json_read"

# 18. String method call (.upper()).
echo "[test] ysh -c 'echo \$[\"hello\".upper()]'"
ysh_upper="$(ysh -c 'echo $["hello".upper()]' 2>&1)"
[ "$ysh_upper" = "HELLO" ] || fail "ysh string method mismatch: $ysh_upper"

# --- Error paths (valid error input must return non-zero) ---

# 19. Unknown command must fail with a non-zero exit status.
echo "[test] osh -c 'this_cmd_definitely_not_exist_12345' (expect non-zero)"
set +e
osh -c 'this_cmd_definitely_not_exist_12345' >/dev/null 2>&1
osh_notfound_rc=$?
set -e
[ "$osh_notfound_rc" -ne 0 ] || fail "osh unknown command should fail, got rc=$osh_notfound_rc"

# 20. Syntax error must fail with a non-zero exit status.
echo "[test] osh -c 'if then fi' (expect non-zero)"
set +e
osh -c 'if then fi' >/dev/null 2>&1
osh_syntax_rc=$?
set -e
[ "$osh_syntax_rc" -ne 0 ] || fail "osh syntax error should fail, got rc=$osh_syntax_rc"

echo "[test] all oils-for-unix smoke tests PASSED ✅"
