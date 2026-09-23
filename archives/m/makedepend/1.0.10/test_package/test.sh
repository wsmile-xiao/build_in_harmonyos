#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer-side verification of the packaged makedepend.
# Runs inside the conanrun environment, so bin/makedepend is on PATH.
set -eu

echo "[test] makedepend is on PATH"
command -v makedepend

workdir="${TMPDIR:-$PWD}/makedepend-test-$$"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir"
cd "$workdir"

cat > dep.h <<'EOF'
#define ANSWER 42
EOF

cat > demo.c <<'EOF'
#include "dep.h"
int main(void) { return ANSWER; }
EOF

cat > Makefile <<'EOF'
demo: demo.o
	$(CC) -o demo demo.o
EOF

echo "[test] makedepend demo.c"
makedepend demo.c

grep -q '^# DO NOT DELETE' Makefile
echo "[test] ok: '# DO NOT DELETE' marker appended to Makefile"

grep -q '^demo\.o: dep\.h' Makefile
echo "[test] ok: '#include \"dep.h\"' turned into the 'demo.o: dep.h' dependency"

# Negative case: outside a Makefile directory makedepend must fail (exit 1).
mkdir -p no-makefile
cd no-makefile
printf 'int main(void) { return 0; }\n' > standalone.c
if makedepend standalone.c; then
    echo "❌ makedepend unexpectedly succeeded without a Makefile"
    exit 1
fi
echo "[test] ok: makedepend fails as expected when no Makefile is present"

echo "[test] makedepend consumer test passed"
