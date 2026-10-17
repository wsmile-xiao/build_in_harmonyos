#!/usr/bin/env bash
# wx-upstream-tests.sh — wxwidgets-gtk3 3.2.10 上游测试套件真机运行脚本
# 用法: bash wx-upstream-tests.sh <RUN_ID>
# 前提: wxWidgets-3.2.10.tar.bz2 已放置于 $BASE（sha256 见 conandata.yml）
set -u

RUN_ID="${1:-r1}"
BASE="$HOME/validation/wx3210-$RUN_ID"
SRC_SHA="d66e929569947a4a5920699539089a9bda83a93e5f4917fb313a61f0c344b896"
CC="$HOME/usr/local/bin/clang"
CXX="$HOME/usr/local/bin/clang++"

export PATH="/data/service/hnp/bin:$HOME/.local/bin:$HOME/usr/local/bin:/system/bin"
export HOME=/storage/Users/currentUser
export USER=currentUser LOGNAME=currentUser CI=1
export TMPDIR="$HOME/tmp"
mkdir -p "$TMPDIR" "$BASE" "$BASE/bin"

# mktemp shim: toybox mktemp -d (mode 0700) maps on HMDFS to an ACL denying
# owner writes, breaking autoconf config.status — create dirs via mkdir.
cat > "$BASE/bin/mktemp" <<'SHIM_EOF'
#!/bin/sh
if [ "${1:-}" != "-d" ] && [ "${1:-}" != "--directory" ]; then
  exec /usr/bin/mktemp "$@"
fi
tpl="${2:-./tmp.XXXXXXXXXX}"
pre="${tpl%%X*}"
i=0
while [ "$i" -lt 200 ]; do
  rnd="$(head -c 4 /dev/urandom 2>/dev/null | od -An -tu4 | tr -d ' \t')"
  [ -n "$rnd" ] || rnd="${i}${RANDOM}${RANDOM}"
  cand="${pre}${rnd}"
  if mkdir "$cand" 2>/dev/null; then
    chmod 755 "$cand" 2>/dev/null
    printf '%s\n' "$cand"
    exit 0
  fi
  i=$((i + 1))
done
exit 1
SHIM_EOF
chmod +x "$BASE/bin/mktemp"
export PATH="$BASE/bin:$PATH"
LOG="$BASE/run-$(date +%Y%m%d-%H%M%S).log"
exec > "$LOG" 2>&1

step() { echo "=== [$(date '+%F %T')] $* ==="; }
die() { echo "!!! FATAL: $*" >&2; exit 1; }

step "env snapshot"
uname -srm
"$CC" --version | head -1
"$CXX" --version | head -1
make --version | head -1
pkg-config --version
echo "TMPDIR=$TMPDIR"

step "S1 verify source tarball"
cd "$BASE" || die "no BASE"
ls -l wxWidgets-3.2.10.tar.bz2 || die "tarball missing"
echo "$SRC_SHA  wxWidgets-3.2.10.tar.bz2" | sha256sum -c - || die "sha256 mismatch"
if [ ! -d wxWidgets-3.2.10 ]; then
  step "S2 extract (python tarfile — toybox tar lacks bz2)"
  python3 - <<'PYEOF' || die "extract failed"
import tarfile
with tarfile.open("wxWidgets-3.2.10.tar.bz2", "r:bz2") as t:
    t.extractall(filter="data")
print("extracted OK")
PYEOF
  [ -d wxWidgets-3.2.10 ] || die "srcdir missing after extract"
fi

cd wxWidgets-3.2.10 || die "no srcdir"

step "S3 config.sub accepts linux-ohos"
if ! grep -q 'linux-ohos' config.sub; then
  # 1) OS case list: accept 'ohos' as a known OS suffix
  sed -i 's/| nsk\* | powerunix\* | genode\* | zvmoe\* | qnx\* | emx\*)/| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | ohos*)/' config.sub
  # 2) kernel-os combination: accept linux-ohos*
  sed -i 's/| linux-uclibc\* )/| linux-uclibc* | linux-ohos* )/' config.sub
  grep -n "ohos" config.sub
fi
sh config.sub aarch64-unknown-linux-ohos || die "config.sub rejects ohos triplet"
# bundled subconfigures (3rdparty/pcre, src/expat/expat, ...) carry old-style
# config.sub — replace them all with the patched top-level copy
find . -name config.sub  -not -path ./config.sub  -exec cp config.sub {} \;
find . -name config.guess -not -path ./config.guess -exec cp config.guess {} \;

step "S4 pkg-config wiring from conan cache"
# gtk build folder's conan-generated pc dir first (complete closure incl.
# libzstd via libtiff), package pc dirs as fallback
GTKC="$HOME/.conan2/p/b/gtk8a8e4bdc2d4ff/b/build-release/conan"
PC="$GTKC"
for d in "$HOME"/.conan2/p/b/*/p/lib/pkgconfig; do
  [ -d "$d" ] && PC="$PC:$d"
done
export PKG_CONFIG_PATH="$PC"
echo "PKG_CONFIG_PATH=$PKG_CONFIG_PATH" | tr ':' '\n' | head -10
pkg-config --modversion gtk+-3.0 || die "gtk+-3.0 not resolvable"
pkg-config --cflags gtk+-3.0 >/dev/null || die "gtk+-3.0 cflags broken"
echo "gtk+-3.0 = $(pkg-config --modversion gtk+-3.0)"
# gtk closure is shared (.so) — collect exact -L dirs for runtime resolution
LIBDIRS=$(pkg-config --libs gtk+-3.0 | tr ' ' '\n' | sed -n 's/^-L//p' | sort -u | tr '\n' ':')
export LD_LIBRARY_PATH="$HOME/usr/local/lib:${LIBDIRS}${LD_LIBRARY_PATH:-}"
echo "LD_LIBRARY_PATH dirs:"; echo "$LD_LIBRARY_PATH" | tr ':' '\n' | head -25

step "S5 configure (autoconf, mirrors conan recipe options)"
rm -rf build
mkdir -p build
cd build || die "no builddir"
../configure \
  --build=aarch64-unknown-linux-ohos \
  --prefix="$BASE/install" \
  --disable-shared \
  --with-gtk=3 \
  --with-libpng=builtin \
  --with-libjpeg=builtin \
  --without-libtiff \
  --with-expat=builtin \
  --with-zlib=builtin \
  --without-opengl \
  CC="$CC" CXX="$CXX" \
  > "$BASE/configure.log" 2>&1
RC=$?
tail -40 "$BASE/configure.log"
[ $RC -eq 0 ] || die "configure failed rc=$RC (see $BASE/configure.log)"
grep -E "Configured wxWidgets|which gui toolkit|gtk" "$BASE/configure.log" | tail -5

step "S6 build (make -j2)"
make -j2 > "$BASE/make.log" 2>&1
RC=$?
echo "make rc=$RC"
[ $RC -eq 0 ] || { tail -60 "$BASE/make.log"; die "make failed"; }

step "S7 build tests target"
make -C tests all > "$BASE/make-tests.log" 2>&1
RC=$?
echo "make tests rc=$RC"
if [ $RC -ne 0 ]; then
  # upstream configure unconditionally appends -lX11 for GTK on unix
  # (assumes GTK=X11); broadway-only gtk has no X11 — strip and rebuild
  if grep -q "unable to find library -lX11" "$BASE/make-tests.log"; then
    step "S7b strip spurious -lX11 from generated Makefiles, rebuild tests"
    sed -i "s/ -lX11 / /g" Makefile tests/Makefile
    make -C tests all > "$BASE/make-tests2.log" 2>&1
    RC=$?
    echo "make tests (post X11 fix) rc=$RC"
  fi
fi
tail -5 "$BASE/make-tests2.log" 2>/dev/null || tail -20 "$BASE/make-tests.log"

step "S7c ensure test data fixtures are in place (r1 lesson)"
# 'all' aborts at test_drawing before reaching the trailing data targets on
# first pass — request them explicitly and verify, otherwise horse.*-based
# cases (CopyFile/Eof/Error/FindFileNext/FileExists) fail as fixture-missing
make -C tests data data-image-sample data-images en_GB fr ja >> "$BASE/make-tests2.log" 2>&1 || true
for f in horse.xpm horse.png horse.bmp; do
  [ -f "tests/$f" ] || echo "WARN: fixture tests/$f missing"
done
[ -f tests/horse.bmp ] || die "horse.bmp fixture missing — aborting run (invalid)"
ls -l tests/test tests/test_gui tests/horse.bmp 2>/dev/null

step "S8 run upstream non-GUI test suite (tests/test)"
cd tests || die "no tests dir"
./test > "$BASE/test-output.log" 2>&1
TEST_RC=$?
echo "TEST_RC=$TEST_RC"
tail -25 "$BASE/test-output.log"

step "S9 attempt GUI test binary (expected: no display; capture exact failure)"
if [ -x ./test_gui ]; then
  ./test_gui > "$BASE/test-gui-run.log" 2>&1
  GUI_RC=$?
else
  echo "test_gui not built" > "$BASE/test-gui-run.log"
  GUI_RC=127
fi
echo "GUI_RC=$GUI_RC"
tail -5 "$BASE/test-gui-run.log"

step "S10 summary"
{
  echo "test binary rc=$TEST_RC"
  echo "test_gui binary rc=$GUI_RC (expected fail headless)"
  sha256sum "$BASE/test-output.log" "$BASE/test-gui-run.log" 2>/dev/null
} | tee "$BASE/summary.txt"

step "DONE run_id=$RUN_ID"
echo "ALL_LOGS_IN=$BASE"
