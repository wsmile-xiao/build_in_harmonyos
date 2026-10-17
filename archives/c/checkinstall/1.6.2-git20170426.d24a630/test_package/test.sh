#!/usr/bin/env bash
# test_package smoke tests for checkinstall 1.6.2-git20170426.d24a630
# Verifies: main script --version, installwatch wrapper --version,
# installwatch.so loads via dlopen (LD_PRELOAD core component).
set -euo pipefail

fail=0

# 1) checkinstall 主脚本（bash 脚本工具）
if command -v checkinstall >/dev/null 2>&1; then
    # --version 在部分环境可能返回非零退出码，此处仅校验输出内容，容忍非零（set -e 下需 || true）
    out=$(checkinstall --version 2>&1 || true)
    echo "checkinstall --version =>"
    echo "$out" | head -3
    if echo "$out" | grep -q "checkinstall"; then
        echo "PASS: checkinstall --version"
    else
        echo "FAIL: checkinstall --version output unexpected"
        fail=1
    fi
else
    echo "FAIL: checkinstall not on PATH"
    fail=1
fi

# 2) installwatch 包装脚本
if command -v installwatch >/dev/null 2>&1; then
    # --version 可能返回非零，同上容忍（仅校验输出含 Copyright）
    out=$(installwatch --version 2>&1 || true)
    echo "installwatch --version =>"
    echo "$out" | head -4
    if echo "$out" | grep -q "Copyright"; then
        echo "PASS: installwatch --version"
    else
        echo "FAIL: installwatch --version output unexpected"
        fail=1
    fi
else
    echo "FAIL: installwatch not on PATH"
    fail=1
fi

# 3) installwatch.so 真实 dlopen/dlsym 验证（LD_PRELOAD 拦截库核心组件）
#    写临时 C 探针：dlopen installwatch.so 并 dlsym 其导出符号
SO_FILE=''
if command -v checkinstall >/dev/null 2>&1; then
    ci_path=$(command -v checkinstall)
    pfx=$(cd "$(dirname "$ci_path")/.." && pwd)
    if [ -f "$pfx/lib/installwatch.so" ]; then
        SO_FILE="$pfx/lib/installwatch.so"
    fi
fi
if [ -n "$SO_FILE" ]; then
    # 临时目录用 $HOME/tmp 回退（OHOS /tmp 只读，E002）；编译器优先取 $CC，缺省 clang
    probe_dir="${TMPDIR:-$HOME/tmp}"
    probe_c="$probe_dir/iw_dlprobe_$$.c"
    probe_bin="$probe_dir/iw_dlprobe_$$"
    cat > "$probe_c" <<'EOF'
#include <stdio.h>
#include <dlfcn.h>
int main(int argc, char **argv) {
    if (argc < 2) return 2;
    void *h = dlopen(argv[1], RTLD_LAZY);
    if (!h) { fprintf(stderr, "dlopen failed: %s\n", dlerror()); return 1; }
    dlerror();
    void *s = dlsym(h, "__installwatch_timecount");
    if (dlerror()) { fprintf(stderr, "dlsym failed\n"); return 1; }
    printf("dlopen+dlsym OK: %s\n", argv[1]);
    dlclose(h);
    return 0;
}
EOF
    cc_bin="${CC:-clang}"
    if "$cc_bin" "$probe_c" -o "$probe_bin" -ldl >/dev/null 2>&1 \
        && "$probe_bin" "$SO_FILE" >/dev/null 2>&1; then
        echo "PASS: installwatch.so dlopen/dlsym OK"
    else
        echo "FAIL: installwatch.so dlopen/dlsym failed"
        fail=1
    fi
    rm -f "$probe_c" "$probe_bin"
else
    echo "FAIL: installwatch.so not found"
    fail=1
fi

if [ "$fail" = "0" ]; then
    echo "ALL TESTS PASSED"
else
    echo "SOME TESTS FAILED"
    exit 1
fi
exit 0
