#!/bin/sh
set -eu

wrapper=$1
tmp=${TMPDIR:-/tmp}/abuild-meson-test-$$
mkdir -p "$tmp/share" "$tmp/bin" "$tmp/native" "$tmp/cross"
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
: >"$tmp/share/functions.sh"

cat >"$tmp/bin/meson" <<'EOF'
#!/bin/sh
if [ "${MESON_FAIL:-0}" = 1 ]; then
    exit 42
fi
printf '%s\n' "$@" >"$MESON_ARGS_LOG"
EOF
chmod +x "$tmp/bin/meson"

(
    cd "$tmp/native"
    ABUILD_SHAREDIR="$tmp/share" \
    CHOST=x86_64-alpine-linux-musl CBUILD=x86_64-alpine-linux-musl \
    CARCH=x86_64 PATH="$tmp/bin:$PATH" MESON_ARGS_LOG="$tmp/native.args" \
        sh "$wrapper" build-native -Dfeature=enabled
)
test ! -e "$tmp/native/abuild-meson.cross"
grep -Fx -- '--prefix=/usr' "$tmp/native.args"
grep -Fx -- '--wrap-mode=nodownload' "$tmp/native.args"
grep -Fx -- 'build-native' "$tmp/native.args"
grep -Fx -- '-Dfeature=enabled' "$tmp/native.args"
if grep -F -- '--cross-file=' "$tmp/native.args" >/dev/null; then
    echo "FAIL: native invocation unexpectedly used a cross file" >&2
    exit 1
fi

(
    cd "$tmp/cross"
    ABUILD_SHAREDIR="$tmp/share" \
    CHOST=aarch64-alpine-linux-musl CBUILD=x86_64-alpine-linux-musl \
    CARCH=aarch64 CROSS_COMPILE=aarch64-alpine-linux-musl- \
    CBUILDROOT=/ohos/sysroot PATH="$tmp/bin:$PATH" \
    MESON_ARGS_LOG="$tmp/cross.args" \
        sh "$wrapper" build-cross -Dtests=true
)
grep -Fq "strip = 'aarch64-alpine-linux-musl-strip'" "$tmp/cross/abuild-meson.cross"
grep -Fq "cpu_family = 'aarch64'" "$tmp/cross/abuild-meson.cross"
grep -Fq "cpu = 'aarch64'" "$tmp/cross/abuild-meson.cross"
grep -Fq "endian = 'little'" "$tmp/cross/abuild-meson.cross"
grep -Fq "sys_root = '/ohos/sysroot'" "$tmp/cross/abuild-meson.cross"
grep -Fq "sys_root = '/'" "$tmp/cross/abuild-meson.native"
grep -Fx -- '--cross-file=abuild-meson.cross' "$tmp/cross.args"
grep -Fx -- '--native-file=abuild-meson.native' "$tmp/cross.args"
grep -Fx -- 'build-cross' "$tmp/cross.args"
grep -Fx -- '-Dtests=true' "$tmp/cross.args"

if (
    cd "$tmp/native"
    ABUILD_SHAREDIR="$tmp/share" \
    CHOST=x86_64-alpine-linux-musl CBUILD=x86_64-alpine-linux-musl \
    CARCH=x86_64 PATH="$tmp/bin:$PATH" MESON_FAIL=1 \
    MESON_ARGS_LOG="$tmp/failure.args" \
        sh "$wrapper" build-failure
); then
    echo "FAIL: abuild-meson ignored the Meson failure" >&2
    exit 1
else
    status=$?
fi
test "$status" -eq 42

echo "PASS: abuild-meson native and cross configuration checks"
