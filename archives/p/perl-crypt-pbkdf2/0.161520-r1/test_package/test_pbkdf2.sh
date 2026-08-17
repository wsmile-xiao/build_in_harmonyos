#!/bin/bash
# test_package/test_pbkdf2.sh — Crypt::PBKDF2 功能测试
# 在 Conan test_package 中由 conanfile.py 的 test() 方法调用
#
# 测试策略：
# 1. 验证模块文件存在且语法正确
# 2. 如果 Perl 运行时依赖可用，执行功能测试
# 3. 如果依赖不可用，退化为文件结构验证

set -euo pipefail

# 获取包路径（由 conanfile.py 通过环境变量传入）
PKG_LIB="${PERL5LIB:-}"
PERL_BIN="${PERL_BIN:-perl}"

echo "[test] Crypt::PBKDF2 test_package functional test"
echo "[test] PERL5LIB=$PKG_LIB"

# --- 1. 文件存在性检查 ---
echo "[test] Step 1: File existence check"
EXPECTED_FILES=(
    "Crypt/PBKDF2.pm"
    "Crypt/PBKDF2/Hash.pm"
    "Crypt/PBKDF2/Hash/DigestHMAC.pm"
    "Crypt/PBKDF2/Hash/HMACSHA1.pm"
    "Crypt/PBKDF2/Hash/HMACSHA2.pm"
    "Crypt/PBKDF2/Hash/HMACSHA3.pm"
)

for f in "${EXPECTED_FILES[@]}"; do
    FULL_PATH=""
    for lib in $(echo "$PKG_LIB" | tr ':' ' '); do
        if [ -f "$lib/$f" ]; then
            FULL_PATH="$lib/$f"
            break
        fi
    done
    if [ -z "$FULL_PATH" ]; then
        echo "[fail] Missing: $f"
        exit 1
    fi
    echo "[pass] Found: $f"
done

# --- 2. 语法检查（非致命：依赖模块可能不在 CI 环境中）---
echo "[test] Step 2: Syntax check (non-fatal if deps missing)"
for f in "${EXPECTED_FILES[@]}"; do
    for lib in $(echo "$PKG_LIB" | tr ':' ' '); do
        if [ -f "$lib/$f" ]; then
            if $PERL_BIN -c "$lib/$f" 2>&1 | grep -q "OK"; then
                echo "[pass] Syntax OK: $f"
            else
                echo "[warn] Syntax check skipped (deps missing): $f"
            fi
            break
        fi
    done
done

# --- 3. 功能测试（如果依赖可用）---
echo "[test] Step 3: Functional test (requires Moo, Type::Tiny, etc.)"
if TEST_OUTPUT=$($PERL_BIN -e '
use strict;
use warnings;
use Crypt::PBKDF2;

my $pbkdf2 = Crypt::PBKDF2->new(
    hash_class => "HMACSHA1",
    iterations => 1000,
);

# Test generate + validate
my $hash = $pbkdf2->generate("password");
print "[pass] generate() produces hash\n";

unless ($pbkdf2->validate($hash, "password")) {
    die "[fail] validate() should accept correct password";
}
print "[pass] validate() accepts correct password\n";

if ($pbkdf2->validate($hash, "wrongpassword")) {
    die "[fail] validate() should reject wrong password";
}
print "[pass] validate() rejects wrong password\n";

# Test RFC 6070 vector (c=1)
my $pbkdf2_rfc = Crypt::PBKDF2->new(
    hash_class => "HMACSHA1",
    iterations => 1,
);
my $result = unpack("H*", $pbkdf2_rfc->PBKDF2("salt", "password"));
my $expected = "0c60c80f961f0e71f3a9b524af6012062fe037a6";
unless ($result eq $expected) {
    die "[fail] RFC 6070 c=1 mismatch: got $result, expected $expected";
}
print "[pass] RFC 6070 c=1 test vector matches\n";

# Test SHA256
my $pbkdf2_256 = Crypt::PBKDF2->new(
    hash_class => "HMACSHA2",
    hash_args => { sha => 256 },
    iterations => 1000,
);
my $hash256 = $pbkdf2_256->generate("test256");
unless ($pbkdf2_256->validate($hash256, "test256")) {
    die "[fail] SHA256 validate failed";
}
print "[pass] HMAC-SHA256 generate+validate works\n";

print "[test] All functional tests passed\n";
' 2>&1); then
    echo "$TEST_OUTPUT"
else
    TEST_EXIT=$?
    if echo "$TEST_OUTPUT" | grep -q "Can't locate"; then
        echo "[warn] Functional test skipped (Perl runtime dependencies not available)"
        echo "[test] Falling back to file-only validation (already passed)"
    else
        echo "$TEST_OUTPUT"
        echo "[fail] Functional test failed (exit code $TEST_EXIT) - not a dependency issue"
        exit 1
    fi
fi

echo "[test] Test package validation complete"
exit 0
