#!/system/bin/sh
# End-to-end consumer test for the packaged rats binary.
#
# Validates the full chain: the rats executable loads, its expat-parsed
# vulnerability database (rats-*.xml) is found at DATADIR, and it actually
# audits a C source file and reports findings.
#
# Usage: test_rats.sh <path-to-rats-binary>

set -u

EXE="${1:-}"
if [ -z "$EXE" ]; then
    echo "usage: test_rats.sh <path-to-rats>" >&2
    exit 2
fi

WORK="$(mktemp -d)"
SAMPLE="$WORK/sample.c"
cat > "$SAMPLE" <<'EOF'
#include <string.h>
#include <stdio.h>
int main(int argc, char **argv) {
    char buf[16];
    char *src = argv[1];
    strcpy(buf, src);
    strcat(buf, "x");
    sprintf(buf, "%s", src);
    printf("%s\n", buf);
    return 0;
}
EOF

# 1) --help must load (libexpat resolvable) and print usage.
#    NOTE: upstream `rats --help` intentionally exits with status 1 (it calls
#    usage(); exit(1)), so we validate the *output*, not the exit code.
OUT_HELP="$("$EXE" --help 2>&1)"
echo "$OUT_HELP"
case "$OUT_HELP" in
    *RATS*|*usage*)
        echo "PASS: rats --help loaded and printed usage" ;;
    *)
        echo "FAIL: rats --help failed to load/print (libexpat or ELF issue?)" >&2
        exit 1 ;;
esac

# 2) Audit the sample; rats must report at least one vulnerability.
OUT="$("$EXE" "$SAMPLE" 2>&1)"
echo "$OUT"

case "$OUT" in
    *strcpy*|*strcat*|*sprintf*|*High*|*Medium*|*Low*)
        echo "PASS: rats reported vulnerabilities for the C sample" ;;
    *)
        echo "FAIL: rats produced no vulnerability findings (DB/parse issue?)" >&2
        exit 1 ;;
esac

# 3) A clean sample must produce no High/Medium findings.
CLEAN="$WORK/clean.c"
printf 'int main(void){return 0;}\n' > "$CLEAN"
CLEAN_OUT="$("$EXE" "$CLEAN" 2>&1)"
echo "$CLEAN_OUT"
case "$CLEAN_OUT" in
    *High*|*Medium*)
        echo "FAIL: rats reported findings for a trivially clean file" >&2
        exit 1 ;;
    *)
        echo "PASS: rats reported no High/Medium findings for a clean file" ;;
esac

rm -rf "$WORK"
echo "ALL TESTS PASSED"
