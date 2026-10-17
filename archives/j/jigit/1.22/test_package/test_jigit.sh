#!/bin/sh
# jigit/1.22 consumer + command-line assertions.
# Runs under toybox ash (/bin/sh); deliberately avoids /bin/bash and
# /usr/bin/python3, neither of which exists on HarmonyOS PC.
#
# $CC / $CPPFLAGS / $CFLAGS / $LDFLAGS come from conanbuild (AutotoolsToolchain
# + AutotoolsDeps), $PATH / $LD_LIBRARY_PATH from conanrun of the packaged
# libjte.so.2 + bin/.

checks=0
failures=0
# The script is run from the build folder but each assertion works inside its
# own scratch directory below, so the C source has to be addressed absolutely
# (create13 measured: compiling it by bare name after the cd dies with
# "no such file or directory: jte_consumer.c", which then cascades into the two
# consumer assertions).
src_dir=$(cd "$(dirname "$0")" && pwd)
work=$(pwd)/jigit-selftest.$$

ok()  { checks=$((checks + 1)); echo "ok $checks - $1"; }
bad() { checks=$((checks + 1)); failures=$((failures + 1)); echo "NOT OK $checks - $1"; }

mkdir -p "$work" || { echo "cannot create $work"; exit 70; }
cd "$work" || exit 70

# ---------------------------------------------------------------- 1. tools --
for t in jigsum jigsum-sha256 jigdump jigit-mkimage parallel-sums extract-data \
         rsyncsum mkjigsnap jigdo-gen-checksum-list jte-demo; do
    if command -v "$t" >/dev/null 2>&1; then
        ok "packaged command '$t' resolves on PATH"
    else
        bad "packaged command '$t' missing from PATH"
    fi
done

# ------------------------------------------------- 2. libjte C consumer ----
cc=${CC:-clang}
$cc -o jte_consumer "$src_dir/jte_consumer.c" $CPPFLAGS $CFLAGS $LDFLAGS -ljte >cc.log 2>&1
if [ $? -eq 0 ]; then
    ok "consumer compiles and links against packaged libjte ($cc)"
else
    bad "consumer failed to link against libjte"; sed -n '1,20p' cc.log
fi

if [ -x ./jte_consumer ]; then
    ./jte_consumer >consumer.log 2>&1
    rc=$?
    if [ $rc -eq 0 ] && grep -q '^LIBJTE-VERSION 2\.' consumer.log \
       && grep -q '^CONSUMER-OK$' consumer.log; then
        ok "consumer runs libjte_new/set_verbose/destroy round trip: $(tr '\n' ' ' < consumer.log)"
    else
        bad "consumer run failed rc=$rc: $(tr '\n' ' ' < consumer.log)"
    fi
    # HarmonyOS PC ships no ldd(1) (measured: `command -v ldd` -> not found), so
    # the shared-object binding is read straight out of the ELF dynamic section
    # with readelf(1) from the HNP toolchain: DT_NEEDED must name the versioned
    # soname that libtool installed, i.e. libjte.so.2.
    if readelf -d ./jte_consumer 2>/dev/null | grep -q 'NEEDED.*libjte\.so\.2'; then
        ok "consumer is bound to the packaged shared object libjte.so.2"
    else
        bad "readelf does not show NEEDED libjte.so.2 behind the consumer"
    fi
else
    bad "consumer binary absent, cannot run API round trip"
fi

# -------------------------------------------------- 3. jigsum base64 form --
printf 'jigit selftest payload A\n' > f1.bin
printf 'jigit selftest payload B line two\n' > f2.bin

jigsum f1.bin f2.bin > sums.md5 2>/dev/null
rc=$?
if [ $rc -eq 0 ] && [ "$(wc -l < sums.md5)" -eq 2 ]; then
    ok "jigsum emits one record per input file"
else
    bad "jigsum produced no per-file records (rc=$rc)"
fi
if [ "$(awk 'NR==1{print length($1)}' sums.md5)" -eq 22 ]; then
    ok "jigsum MD5 digest is the 22-character jigdo base64 form"
else
    bad "jigsum digest length wrong: $(awk 'NR==1{print length($1)}' sums.md5)"
fi

jigsum -c < sums.md5 >check.log 2>&1
if [ $? -eq 0 ]; then
    ok "jigsum -c verifies untouched files"
else
    bad "jigsum -c rejected its own output: $(tr '\n' ' ' < check.log)"
fi

printf 'x' >> f2.bin
jigsum -c < sums.md5 >corrupt.log 2>&1
rc=$?
printf 'jigit selftest payload B line two\n' > f2.bin
if [ $rc -ne 0 ] && grep -qi 'FAILED' corrupt.log; then
    ok "destructive check: jigsum -c detects the flipped byte"
else
    bad "destructive check inconclusive (rc=$rc): $(tr '\n' ' ' < corrupt.log)"
fi

jigsum-sha256 f1.bin f2.bin > sums.sha256 2>/dev/null
if [ $? -eq 0 ] && [ "$(awk 'NR==1{print length($1)}' sums.sha256)" -eq 43 ]; then
    ok "jigsum-sha256 emits the 43-character base64 SHA-256 digest"
else
    bad "jigsum-sha256 digest length wrong: $(awk 'NR==1{print length($1)}' sums.sha256)"
fi
jigsum-sha256 -c < sums.sha256 >check256.log 2>&1
if [ $? -eq 0 ]; then
    ok "jigsum-sha256 -c verifies untouched files"
else
    bad "jigsum-sha256 -c rejected its own output"
fi

# ------------------------------------- 4. parallel-sums cross verification --
parallel-sums --md5sum=ps.md5 --sha256sum=ps.sha256 f1.bin >ps.log 2>&1
rc=$?
if [ $rc -eq 0 ] && [ -s ps.md5 ] && [ -s ps.sha256 ]; then
    ok "parallel-sums writes the requested digest files"
else
    bad "parallel-sums failed rc=$rc: $(tr '\n' ' ' < ps.log)"
fi
ref_md5=$(md5sum f1.bin | awk '{print $1}')
got_md5=$(awk '{print $1}' ps.md5)
if [ -n "$ref_md5" ] && [ "$ref_md5" = "$got_md5" ]; then
    ok "parallel-sums MD5 matches the platform md5sum ($ref_md5)"
else
    bad "parallel-sums MD5 mismatch: ours=$got_md5 system=$ref_md5"
fi
ref_sha=$(sha256sum f1.bin | awk '{print $1}')
got_sha=$(awk '{print $1}' ps.sha256)
if [ -n "$ref_sha" ] && [ "$ref_sha" = "$got_sha" ]; then
    ok "parallel-sums SHA-256 matches the platform sha256sum"
else
    bad "parallel-sums SHA-256 mismatch: ours=$got_sha system=$ref_sha"
fi

# -------------------------------------------- 5. jigdo round trip (E2E) ----
# jte-demo is upstream libjte/test/demo: the only shipped driver of the
# template-creation API. Template + .jigdo in, byte-identical image out.
#
# libjte's list parser (jte.c) requires *hexadecimal* digests -- it validates
# every character with isxdigit() -- so jigsum's 22-character jigdo base64 form
# is rejected outright ("invalid checksum list file ... wrong checksum type?",
# measured in create13).  The hex list comes from the packaged
# jigdo-gen-checksum-list, which is exactly the tool patch 0003 had to teach
# about `uname -s` == HarmonyOS, so its output is asserted on its own before
# the round trip depends on it.
jigdo-gen-checksum-list --keep-literal f1.bin f2.bin > sums.hex 2>genhex.log
rc=$?
if [ $rc -eq 0 ] && [ "$(awk 'NR==1{print length($1)}' sums.hex)" -eq 32 ]; then
    ok "jigdo-gen-checksum-list emits a 32-hex-digit md5 list under HarmonyOS"
else
    bad "jigdo-gen-checksum-list produced no hex list (rc=$rc): $(tr '\n' ' ' < genhex.log)"
fi

jte-demo -outfile image.out -template round.template -jigdo round.jigdo \
         -md5 sums.hex f1.bin f2.bin >demo.log 2>&1
rc=$?
if [ $rc -eq 0 ] && [ -s round.template ] && [ -s round.jigdo ] && [ -s image.out ]; then
    ok "jte-demo produces .template/.jigdo/payload image via libjte"
else
    bad "jte-demo round trip setup failed rc=$rc: $(tr '\n' ' ' < demo.log)"
fi

jigdump round.template >dump.log 2>&1
rc=$?
if [ $rc -eq 0 ] && grep -qi 'DESC block found' dump.log; then
    ok "jigdump parses the generated binary template"
else
    bad "jigdump could not parse the template rc=$rc: $(tr '\n' ' ' < dump.log)"
fi

jigit-mkimage -t round.template -j round.jigdo -o rebuilt.out >mkimage.log 2>&1
rc=$?
if [ $rc -eq 0 ] && [ -s rebuilt.out ] && cmp -s image.out rebuilt.out; then
    ok "jigit-mkimage reconstructs a byte-identical image from .jigdo + .template"
else
    bad "jigit-mkimage reconstruction differs rc=$rc: $(tr '\n' ' ' < mkimage.log)"
fi

# --- destructive control for the round trip (rewritten after create14) -----
# Measured premise: with both payload files below libjte MIN_JIGDO_FILE_SIZE
# (1024 bytes, libjte/jte.h:105) jte-demo writes an EMPTY [Parts] section - the
# whole image rides inside the template compressed data block - and
# jigit-mkimage resolves mirror entries by name only (find_file_in_mirror()
# calls file_exists(), mkimage.c:259-297; the digest carried by the .jigdo is
# never recomputed).  Probing the packaged binaries (probe27.sh) measured that
# appending a byte, truncating, and even renaming f1.bin away each still gave
# rc=0 with a byte-identical image, so "mutate the mirror" is not a usable
# destructive check for this shape; the artefact mkimage really consumes is the
# template.  probe27c.sh: one flipped byte mid-template aborts rc=5 with
# "ungzip_data_block: failed to decompress", one in the footer rc=22 with
# "Failed to find desc start", both ending in "Unable to recreate image from
# template file", and the output image is truncated to 0 bytes.
toff=$(wc -c < round.template | tr -d " ")
cp round.template corrupt.template
printf "Z" | dd bs=1 seek=$((toff / 2)) count=1 conv=notrunc of=corrupt.template 2>/dev/null
jigit-mkimage -t corrupt.template -j round.jigdo -o rebuilt2.out >mkimage2.log 2>&1
rc=$?
if [ $rc -ne 0 ] && grep -qi "Unable to recreate image from template file" mkimage2.log && ! cmp -s image.out rebuilt2.out; then
    ok "destructive check: mkimage aborts (rc=$rc) instead of reproducing the image from a mutated template"
else
    bad "destructive check inconclusive (rc=$rc): $(tr "\n" " " < mkimage2.log)"
fi

# -------------------------------------------- 6. interpreter-side checks ----
jigdo-gen-checksum-list --help >sh.out 2>&1
rc=$?
if [ $rc -ne 127 ] && ! grep -qi 'No such file' sh.out; then
    ok "jigdo-gen-checksum-list runs under the platform /bin/sh (rc=$rc)"
else
    bad "jigdo-gen-checksum-list cannot start under /bin/sh (rc=$rc)"
fi
mkjigsnap --help >pl.out 2>&1
rc=$?
if [ $rc -ne 127 ] && ! grep -qi 'No such file' pl.out; then
    ok "mkjigsnap resolves its Perl interpreter after the shebang fix (rc=$rc)"
else
    bad "mkjigsnap still points at a missing interpreter (rc=$rc): $(tr '\n' ' ' < pl.out)"
fi

cd ..
rm -rf "$work"
# Repo consumer-summary convention (same shape as lutok/plod): one machine
# readable line whose denominator is every assertion site the script can
# reach, so the number declared in the PR body is checkable statically.
total=$checks
failed=$failures
passed=$((total - failed))
echo "SUMMARY jigit consumer: total=$total passed=$passed failed=$failed"
[ $failures -eq 0 ] || exit 1
exit 0
