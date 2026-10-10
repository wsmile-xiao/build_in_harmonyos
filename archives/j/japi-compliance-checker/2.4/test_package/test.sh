#!/usr/bin/env bash
# test_package/test.sh — consumer tests for japi-compliance-checker (R34/PF3/L0c).
#
# Invoked by test_package/conanfile.py with the conanrun env: PATH contains
# the installed bin/ (japi-compliance-checker wrapper) and the JDK bin dir
# (JAVA_HOME resolved by the conanfile).
#
# Assertions (8):
#   A1 CLI contract: --version prints "Java API Compliance Checker (JAPICC) 2.4"
#   A2 JDK toolchain reachable (javac / jar / java / javap)
#   A3 test jars compile+package (v1: two public methods; v2: removeMe removed
#      and NewApi added)
#   A4 jar-vs-jar comparison writes the HTML report (upstream exits 1 when
#      breaks are detected - the exit code is asserted in A5)
#   A5 break detected: console summary "Binary compatibility:" < 100% with
#      exactly 1 binary problem AND upstream exit-code contract (rc=1)
#   A6 HTML report names the removed method ("removeMe")
#   A7 negative control: v1 vs v1 -> "Binary compatibility: 100%", 0 problems
#   A8 -dump mode creates an API dump carrying API_DUMP_VERSION 2.4
set -u

CHECKS=0
FAILS=0

check() {
    # $1 = description, $2 = 0 (pass) / non-zero (fail)
    CHECKS=$((CHECKS + 1))
    if [ "$2" -eq 0 ]; then
        echo "  [PASS] $1"
    else
        echo "  [FAIL] $1" >&2
        FAILS=$((FAILS + 1))
    fi
}

command -v japi-compliance-checker >/dev/null 2>&1 || {
    echo "FATAL: japi-compliance-checker not on PATH (conanrun env broken)" >&2
    exit 1
}

# scratch dir via mktemp (leaves no residue next to the recipe; conan 2
# runs test() with the test_package folder as cwd)
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/src1/com/exapi" "$WORK/src2/com/exapi"
cd "$WORK"

# --- A1: --version ----------------------------------------------------------
V_OUT="$(japi-compliance-checker --version 2>&1 || true)"
case "$V_OUT" in
    *"Java API Compliance Checker (JAPICC) 2.4"*) RC=0 ;;
    *) RC=1 ;;
esac
check "A1 --version reports JAPICC 2.4 (got: $(echo "$V_OUT" | head -1))" $RC

# --- A2: JDK toolchain reachable --------------------------------------------
RC=0
for t in javac jar java javap; do
    command -v "$t" >/dev/null 2>&1 || { RC=1; echo "  missing: $t" >&2; }
done
check "A2 JDK toolchain reachable (javac/jar/java/javap)" $RC

# --- test sources -----------------------------------------------------------
cat > src1/com/exapi/Api.java <<'JAVA'
package com.exapi;
public class Api {
    public int stableMethod(int x) { return x + 1; }
    public int removeMe(int x) { return x * 2; }
}
JAVA
cat > src2/com/exapi/Api.java <<'JAVA'
package com.exapi;
public class Api {
    public int stableMethod(int x) { return x + 1; }
}
JAVA
cat > src2/com/exapi/NewApi.java <<'JAVA'
package com.exapi;
public class NewApi {
    public void hello() { }
}
JAVA

# --- A3: compile + package the two jars -------------------------------------
RC=0
javac -d cls1 src1/com/exapi/Api.java 2>javac1.log && \
    jar --create --file v1.jar -C cls1 . 2>>javac1.log || RC=1
javac -d cls2 src2/com/exapi/Api.java src2/com/exapi/NewApi.java 2>javac2.log && \
    jar --create --file v2.jar -C cls2 . 2>>javac2.log || RC=1
check "A3 test jars compiled and packaged (v1.jar, v2.jar)" $RC
[ $RC -ne 0 ] && { cat javac1.log javac2.log >&2 || true; }

# --- A4: comparison runs and writes the HTML report --------------------------
# (upstream contract: rc=1 when breaks are detected - checked in A5; rc=0 is
#  not required here, the report file is the evidence of a completed run)
CMP_OUT="$(japi-compliance-checker v1.jar v2.jar 2>&1)"; CMP_RC=$?
if [ -n "$CMP_OUT" ] && [ -f "compat_reports/v/1_to_2/compat_report.html" ]; then
    RC=0
else
    RC=1
fi
check "A4 comparison completed and report written (compat_reports/v/1_to_2/)" $RC

# --- A5: console summary flags the break -------------------------------------
PCT="$(echo "$CMP_OUT" | grep -o 'Binary compatibility: [0-9.]*%' | head -1)"
NPROB="$(echo "$CMP_OUT" | grep -o 'Total binary compatibility problems: [0-9]*' | head -1)"
case "$PCT|$NPROB" in
    *"100%"*) RC=1 ;;  # must NOT be fully compatible
    *"problems: 1") RC=0 ;;
    *) RC=1 ;;
esac
if [ $RC -eq 0 ] && [ $CMP_RC -ne 1 ]; then
    RC=1  # upstream exit-code contract: non-zero when breaks detected
fi
check "A5 break detected ('$PCT', '$NPROB') with exit code $CMP_RC" $RC

# --- A6: HTML report names the removed method --------------------------------
if grep -q "removeMe" "compat_reports/v/1_to_2/compat_report.html" 2>/dev/null; then
    RC=0
else
    RC=1
fi
check "A6 report HTML contains removed method 'removeMe'" $RC

# --- A7: negative control (v1 vs v1) -----------------------------------------
SELF_OUT="$(japi-compliance-checker v1.jar v1.jar 2>&1)"; SELF_RC=$?
SPCT="$(echo "$SELF_OUT" | grep -o 'Binary compatibility: [0-9.]*%' | head -1)"
SNPROB="$(echo "$SELF_OUT" | grep -o 'Total binary compatibility problems: [0-9]*' | head -1)"
if [ $SELF_RC -eq 0 ] && [ "$SPCT" = "Binary compatibility: 100%" ] && \
   [ "$SNPROB" = "Total binary compatibility problems: 0" ]; then
    RC=0
else
    RC=1
fi
check "A7 negative control v1-vs-v1: 100%, 0 problems" $RC

# --- A8: -dump mode ----------------------------------------------------------
RC=0
DUMP_OUT="$(japi-compliance-checker -dump v1.jar -dump-path api.dump 2>&1)" || RC=1
if [ $RC -eq 0 ] && [ -f api.dump ] && grep -q "API_DUMP_VERSION" api.dump && \
   grep -q "'2.4'" api.dump; then
    RC=0
else
    RC=1
fi
check "A8 -dump creates API dump with API_DUMP_VERSION 2.4" $RC

# ----------------------------------------------------------------------------
echo "assertions=$CHECKS failures=$FAILS"
if [ $FAILS -gt 0 ]; then
    exit 1
fi
exit 0
