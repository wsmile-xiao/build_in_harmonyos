#!/bin/bash
# console-setup 1.248 — OHOS 冒烟测试（自写，上游 0 测试用例）
#
# 断言依据（脚本全文核对 + 完整包布局实测）：
# - setupcon 分支顺序（参数解析段）：--help（exit 0 + Usage）→ 未知选项
#   （exit 1 + Unrecognised option）→ 无参/配置缺失（exit 1 + "None of
#   /etc/default/keyboard"）——均在 loadkeys/setfont 等外部命令之前触发；
#   真实加载路径需 Linux VT + root，非 root CI 不触达
# - ckbcomp 为 perl 键图编译器：-help（exit 0 + Usage）/ us（142 行键图
#   含 108 行 keycode）/ -charmap ISO-8859-1 us（acm 原始文件路径）——
#   installdir=${0%/*} 去尾 /bin 自解析到 $pkg，数据读
#   $pkg/share/console-setup/ckb + $pkg/share/consoletrans
# - 字体 744 psf.gz（构建期 make -C Fonts gzipped-linux-fonts -j4 产物）
#   落位 + gzip 魔数（解压前 2 字节 04 36 = PSF1 magic）
# - compose/dkey 27+27 + remap.inc 落位（构建期 make compose-files
#   dkey-files 产物）
#
# 环境适配：perl 由 hnp 提供（test conanfile PATH 前缀注入）；/tmp 只读，
# 工作产物落 $PKG_ROOT 内（conan 包目录）

set -uo pipefail

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo "  [PASS] $1"; }
fail() { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }

SC="$(command -v setupcon 2>/dev/null || true)"

echo "=== console-setup 1.248 — OHOS 冒烟测试 ==="
echo

PKG_ROOT=""
if [ -n "$SC" ]; then
    PKG_ROOT="$(cd "$(dirname "$SC")/.." && pwd)"
fi
WORK_DIR="${PKG_ROOT}/.cs_test_work"
mkdir -p "$WORK_DIR" 2>/dev/null || WORK_DIR="."

# T00 — setupcon 在 env PATH（runenv bindirs 注入）
if [ -z "$SC" ]; then
    fail "setupcon 不在 PATH（conan runenv 未注入）"
else
    pass "setupcon 在 PATH: $SC"
fi

# T01 — setupcon --help：exit 0 + Usage（参数解析前分支，确定性行为）
if [ -n "$SC" ]; then
    OUT="$(bash "$SC" --help 2>&1)"; RC=$?
    if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q "Usage: setupcon"; then
        pass "setupcon --help exit 0 + Usage"
    else
        fail "--help 断言不符: RC=$RC OUT=$(echo "$OUT" | head -2)"
    fi
else
    fail "setupcon 缺失，跳过 --help"
fi

# T02 — setupcon 无参：exit 1 + 确定性早退分支（先于 loadkeys/setfont
#      外部命令）：OHOS 内核非 Linux → "Unknown kernel (only Linux is
#      supported)"（Linux 上则为 "None of /etc/default/keyboard"）
if [ -n "$SC" ]; then
    OUT="$(bash "$SC" 2>&1)"; RC=$?
    if [ "$RC" -eq 1 ] && echo "$OUT" | grep -qE "Unknown kernel|None of /etc/default/keyboard"; then
        pass "setupcon 无参 exit 1 + 确定性早退分支（$(echo "$OUT" | head -1)）"
    else
        fail "无参断言不符: RC=$RC OUT=$(echo "$OUT" | head -2)"
    fi
else
    fail "setupcon 缺失，跳过错参"
fi

# T03 — setupcon 未知选项：exit 1 + Unrecognised option（实测 RC=1）
if [ -n "$SC" ]; then
    OUT="$(bash "$SC" --frobnicate 2>&1)"; RC=$?
    if [ "$RC" -eq 1 ] && echo "$OUT" | grep -qi "Unrecognised option"; then
        pass "setupcon 未知选项 exit 1 + Unrecognised option"
    else
        fail "未知选项断言不符: RC=$RC OUT=$(echo "$OUT" | head -2)"
    fi
else
    fail "setupcon 缺失，跳过未知选项"
fi

CKB="$(command -v ckbcomp 2>/dev/null || true)"

# T04 — ckbcomp -help：exit 0 + "Usage: ckbcomp"（实测 RC=0）
if [ -n "$CKB" ]; then
    OUT="$(perl "$CKB" -help 2>&1)"; RC=$?
    if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q "Usage: ckbcomp"; then
        pass "ckbcomp -help exit 0 + Usage"
    else
        fail "ckbcomp -help 断言不符: RC=$RC OUT=$(echo "$OUT" | head -2)"
    fi
else
    fail "ckbcomp 不在 PATH（runenv 未注入 bin/）"
fi

# T05 — ckbcomp us 生成键图：142 行含 108 行 keycode（运行期 perl 解析
#      $pkg/share/console-setup/ckb 数据——installdir 自解析验证）
if [ -n "$CKB" ]; then
    MAP="$WORK_DIR/us.map"
    OUT="$(perl "$CKB" us >"$MAP" 2>&1)"; RC=$?
    LINES=0; KC=0
    [ -f "$MAP" ] && LINES=$(wc -l < "$MAP")
    [ -f "$MAP" ] && KC=$(grep -c "^keycode" "$MAP" || true)
    if [ "$RC" -eq 0 ] && [ "$LINES" -ge 140 ] && [ "$KC" -ge 100 ]; then
        pass "ckbcomp us 生成键图（$LINES 行，$KC 行 keycode，installdir 自解析）"
    else
        fail "ckbcomp us 断言不符: RC=$RC LINES=$LINES KC=$KC OUT=$(echo "$OUT" | head -2)"
    fi
else
    fail "ckbcomp 缺失，跳过 us 键图生成"
fi

# T06 — ckbcomp -charmap ISO-8859-1 us：RC=0（share/consoletrans/ 的 acm
#      原始文件路径命中——搜索顺序第 3 项）
if [ -n "$CKB" ]; then
    MAP="$WORK_DIR/us8859.map"
    OUT="$(perl "$CKB" -charmap ISO-8859-1 us >"$MAP" 2>&1)"; RC=$?
    KC=0
    [ -f "$MAP" ] && KC=$(grep -c "^keycode" "$MAP" || true)
    if [ "$RC" -eq 0 ] && [ "$KC" -ge 100 ]; then
        pass "ckbcomp -charmap ISO-8859-1 us RC=0（acm 原始文件路径，$KC 行 keycode）"
    else
        fail "charmap 断言不符: RC=$RC KC=$KC OUT=$(echo "$OUT" | head -2)"
    fi
else
    fail "ckbcomp 缺失，跳过 charmap"
fi

# T07 — 744 字体落位 + PSF 魔数抽样（bdf2psf 双格式：PSF1 magic
#      36 04（0x0436 小端，Terminus 系）/ PSF2 magic 72 b5 4a 86
#      （0x864AB572 小端，DejaVu 系）——两魔数均合法）
if [ -n "$PKG_ROOT" ] && [ -d "$PKG_ROOT/share/consolefonts" ]; then
    FONTS=$(ls "$PKG_ROOT"/share/consolefonts/*.psf.gz 2>/dev/null | wc -l)
    if [ "$FONTS" -eq 744 ]; then
        BAD=0; BADF=""
        for f in Lat15-Terminus16.psf.gz Uni2-DejaVu30x16.psf.gz Arabic-DejaVu51x28.psf.gz; do
            if [ ! -f "$PKG_ROOT/share/consolefonts/$f" ]; then
                BAD=1; BADF="$f (缺失)"; break
            fi
            MAGIC=$(gzip -dc "$PKG_ROOT/share/consolefonts/$f" 2>/dev/null | head -c 4 | od -An -tx1 | tr -d " \n")
            case "$MAGIC" in
                3604*|72b54a86) : ;;
                *) BAD=1; BADF="$f (MAGIC=$MAGIC)"; break ;;
            esac
        done
        if [ "$BAD" -eq 0 ]; then
            pass "share/consolefonts 744 个 psf.gz 落位 + PSF 魔数抽样（36 04 / 72 b5 4a 86 双格式）"
        else
            fail "字体魔数/存在性校验失败: $BADF"
        fi
    else
        fail "字体数不符: $FONTS/744"
    fi
else
    fail "share/consolefonts 缺失"
fi

# T08 — share/consoletrans/ 27 个 .acm 落位
if [ -n "$PKG_ROOT" ] && [ -d "$PKG_ROOT/share/consoletrans" ]; then
    ACM=$(ls "$PKG_ROOT"/share/consoletrans/*.acm 2>/dev/null | wc -l)
    if [ "$ACM" -eq 27 ]; then
        pass "share/consoletrans 27 个 .acm 落位"
    else
        fail "acm 数不符: $ACM/27"
    fi
else
    fail "share/consoletrans 缺失"
fi

# T09 — etc/console-setup/ 55 个 .inc（27 compose + 27 dkey + 1 remap）落位
if [ -n "$PKG_ROOT" ] && [ -d "$PKG_ROOT/etc/console-setup" ]; then
    COMP=$(ls "$PKG_ROOT"/etc/console-setup/compose.*.inc 2>/dev/null | wc -l)
    DKEY=$(ls "$PKG_ROOT"/etc/console-setup/dkey.*.inc 2>/dev/null | wc -l)
    [ -f "$PKG_ROOT/etc/console-setup/remap.inc" ] && REMAP=1 || REMAP=0
    if [ "$COMP" -eq 27 ] && [ "$DKEY" -eq 27 ] && [ "$REMAP" -eq 1 ]; then
        pass "etc/console-setup 27 compose + 27 dkey + remap.inc 落位"
    else
        fail "inc 落位不符: compose=$COMP dkey=$DKEY remap=$REMAP"
    fi
else
    fail "etc/console-setup 缺失"
fi

# T10 — etc/console-setup/ckb/ 数据落位（ckbcomp @xdirs[0]/[1] 数据目录）
if [ -n "$PKG_ROOT" ] && [ -d "$PKG_ROOT/etc/console-setup/ckb" ]; then
    CKB_DIR="$PKG_ROOT/etc/console-setup/ckb"
    R=$(ls "$CKB_DIR"/rules/* 2>/dev/null | wc -l)
    S=$(ls "$CKB_DIR"/symbols/* 2>/dev/null | wc -l)
    if [ "$R" -ge 17 ] && [ "$S" -ge 135 ]; then
        pass "etc/console-setup/ckb 落位（rules $R + symbols $S + keycodes/types/geometry/compat）"
    else
        fail "ckb 数据不符: rules=$R symbols=$S"
    fi
else
    fail "etc/console-setup/ckb 缺失"
fi

# T11 — perl 脚本 shebang 已适配 + 默认配置落位
if [ -n "$PKG_ROOT" ]; then
    SB=$(head -1 "$PKG_ROOT/bin/ckbcomp" 2>/dev/null)
    if [ "$SB" = "#!/usr/bin/env perl" ]; then
        pass "bin/ckbcomp shebang 已适配（#!/usr/bin/env perl）"
    else
        fail "ckbcomp shebang 不符: $SB"
    fi
    if [ -f "$PKG_ROOT/etc/default/keyboard" ] && [ -f "$PKG_ROOT/etc/default/console-setup" ]; then
        pass "etc/default/keyboard + console-setup 配置落位"
    else
        fail "etc/default 配置缺失"
    fi
else
    fail "PKG_ROOT 未确定"
fi

# 清理工作产物
rm -rf "$WORK_DIR" 2>/dev/null || true

echo
echo "=== 结果: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
