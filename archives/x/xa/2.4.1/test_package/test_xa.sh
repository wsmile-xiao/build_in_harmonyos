#!/bin/sh
# test_package/test_xa.sh — functional test for the packaged xa toolchain.
# Runs under the conanrun environment (PATH includes the installed bin/ dir).
# Real assertions on the assembler, linker, relocator, archiver and dumper;
# any failure makes `conan test` fail (CI L1e verifies the test really needs
# the package by sabotaging bin/).
#
# NOTE: deliberately not `set -e`: several assertions inspect commands that
# return non-zero on purpose (bad source -> exit 1), and check() evaluates
# them as conditions; errexit would abort the suite instead of recording.
set -u

DIR="xa-test.$$"
mkdir -p "$DIR" || exit 1
cd "$DIR" || exit 1

n_ok=0
n_fail=0
check() {
  msg="$1"
  shift
  if eval "$@" >/dev/null 2>&1; then
    echo "ok - $msg"
    n_ok=$((n_ok + 1))
  else
    echo "not ok - $msg"
    n_fail=$((n_fail + 1))
  fi
}

echo "1..12"

cat > raw.a65 <<'EOF'
* = $1000
        .byte $41, $42, $43
EOF

cat > obj.a65 <<'EOF'
* = $1000
start:  lda #$01
        rts
EOF

cat > obj2.a65 <<'EOF'
* = $2000
        .byte $03, $04
EOF

cat > bad.a65 <<'EOF'
* = $1000
        jmp nowhere
EOF

# 1) every packaged binary answers --version
check "all six binaries answer --version" \
  'for b in xa file65 ldo65 reloc65 uncpk printcbm; do "$b" --version >/dev/null 2>&1 || exit 1; done'

# 2) xa --version reports the adapted version
check "xa --version reports 2.4.1" \
  'xa --version </dev/null 2>&1 | grep -q "xa (xa65) 2.4.1"'

# 3) no-argument usage text
check "xa prints usage without input files" \
  'xa </dev/null 2>&1 | grep -q "Usage: xa"'

# 4) raw assembly: exact output bytes
check "assembles a raw binary with exact bytes" \
  'xa raw.a65 -o raw.bin </dev/null && [ "$(od -An -tx1 raw.bin | tr -d " \n")" = "414243" ]'

# 5) diagnostics + non-zero exit for an undefined label
check "reports an undefined label with non-zero exit" \
  'rc=0; xa bad.a65 -o bad.o65 </dev/null 2>err.txt || rc=$?; [ $rc -ne 0 ] && grep -q "not defined" err.txt'

# 6) o65 object creation + file65 inspection
check "creates an o65 object and file65 reports it" \
  'xa -c -R obj.a65 -o obj.o65 </dev/null && file65 obj.o65 </dev/null | grep -q "o65 version 0 object file" && file65 obj.o65 </dev/null | grep -qF "text segment @ \$1000"'

# 7) label list (-l) contains the defined label
check "xa -l writes the label list" \
  'xa -l labels.txt -c -R obj.a65 -o obj.o65 </dev/null && grep -q "start" labels.txt'

# 8) ldo65 links two objects into an executable
check "ldo65 links two o65 objects" \
  'xa -c -R obj2.a65 -o obj2.o65 </dev/null && ldo65 -o linked.o65 obj.o65 obj2.o65 </dev/null && file65 linked.o65 </dev/null | grep -q "o65 version 0 executable file" && file65 linked.o65 </dev/null | grep -qF "text segment @ \$0400"'

# 9) reloc65 relocates a text segment
check "reloc65 relocates the text segment to \$2000" \
  'reloc65 -bt 8192 -o rel.o65 obj.o65 </dev/null && file65 rel.o65 </dev/null | grep -qF "text segment @ \$2000"'

# 10) uncpk creates an archive and lists the member
check "uncpk creates and lists a cpk archive" \
  'printf "hello world" > data.bin; uncpk c archive.cpk data.bin </dev/null && uncpk l archive.cpk </dev/null | grep -q data.bin'

# 11) uncpk extraction round-trips the payload
check "uncpk extracts the archive byte-identically" \
  'mkdir -p extracted && ( cd extracted && uncpk x ../archive.cpk </dev/null ) && cmp -s data.bin extracted/data.bin'

# 12) printcbm dumps a BASIC program
check "printcbm dumps a Commodore BASIC line" \
  'printf "\001\010\013\010\012\000\231\"HI\"\000\000\000" > prg.bin && printcbm prg.bin </dev/null 2>&1 | grep -q "print\"HI\""'

cd ..
rm -rf "$DIR"
echo "# xa functional assertions: pass=$n_ok fail=$n_fail"
[ "$n_fail" -eq 0 ]
