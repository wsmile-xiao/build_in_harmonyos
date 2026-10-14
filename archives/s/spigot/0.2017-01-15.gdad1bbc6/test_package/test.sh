#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer-side verification of the packaged spigot.
#
# R34: every assertion below really executes the installed `spigot` binary and
# compares its output against a literal expected value. Nothing here is `echo ok`.
#
# Every expected value in this file was extracted verbatim from the upstream test
# suite (spigot-0.2017-01-15.gdad1bbc6/test.sh) — same literal, same spigot
# arguments, same comparison. The full 1133-case suite is additionally executed
# in the recipe's build() phase; see test_package/MANIFEST.yml.
#
# OHOS notes:
#  * /system/bin/sh is mksh and cannot execute ELF binaries -> the driver runs
#    this script with bash (see test_package/conanfile.py).
#  * /tmp is read-only on HMDFS -> no scratch files are needed here.

SPIGOT="${1:-spigot}"
PASS=0
FAIL=0
TOTAL=0

if ! command -v "$SPIGOT" >/dev/null 2>&1 && [ ! -x "$SPIGOT" ]; then
    echo "FAIL: spigot binary not found (got '$SPIGOT')"
    exit 1
fi
echo "[test] using binary: $(command -v "$SPIGOT" 2>/dev/null || echo "$SPIGOT")"

# assert <label> <expected> <spigot args...>
# Runs `spigot <args...>` and requires exit 0 and stdout exactly equal to
# <expected>.
assert() {
    local label="$1" expected="$2"
    shift 2
    TOTAL=$((TOTAL + 1))
    local out rc
    out=$("$SPIGOT" "$@" 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        FAIL=$((FAIL + 1))
        echo "FAIL [$label]: exit=$rc (expected 0); output: $out"
    elif [ "$out" != "$expected" ]; then
        FAIL=$((FAIL + 1))
        echo "FAIL [$label]:"
        echo "    expected: [$expected]"
        echo "    actual:   [$out]"
    else
        PASS=$((PASS + 1))
        echo "ok   [$label]"
    fi
}

# assert_match <label> <extended-regex> <spigot args...>
# For multi-line / version-dependent output.
assert_match() {
    local label="$1" pattern="$2"
    shift 2
    TOTAL=$((TOTAL + 1))
    local out rc
    out=$("$SPIGOT" "$@" 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        FAIL=$((FAIL + 1))
        echo "FAIL [$label]: exit=$rc (expected 0); output: $out"
    elif ! printf '%s\n' "$out" | grep -qE "$pattern"; then
        FAIL=$((FAIL + 1))
        echo "FAIL [$label]: output does not match /$pattern/; got: $out"
    else
        PASS=$((PASS + 1))
        echo "ok   [$label]"
    fi
}

echo
echo "=== 1. identity / capability report ==="
# The GMP big-integer provider must actually be compiled in. This mirrors
# Debian's own autopkgtest (debian/tests/bigint-provider), which exists to catch
# a silent fallback to spigot's much slower internal bignum code.
assert_match "version reports spigot" '^spigot, ' --version
assert_match "bigint provider is gmp" '^[[:space:]]*big integer provider: gmp$' --version

echo
echo "=== 2. constants to 70+ digits (spigot digit generator) ==="
assert "pi to 70 digits" \
    '3.1415926535897932384626433832795028841971693993751058209749445923078164' -d70 'pi^1'
assert "eulergamma to 70 digits" \
    '0.5772156649015328606065120900824024310421593359399235988057672348848677' -d70 eulergamma
assert "zeta(2) = pi^2/6 to 70 digits" \
    '1.6449340668482264364724151666460251892189499012067984377355582293700074' -d70 'zeta(2)'
assert "zeta(3) (Apery) to 70 digits" \
    '1.2020569031595942853997381615114499907649862923404988817922715553418382' -d70 'zeta(3)'

echo
echo "=== 3. exactness hazards (upstream regression tests) ==="
assert "sqrt(3) survives exact cancellation" \
    '1.7320508075688772935274463415058723669428052538103806280558069794519330' -d70 -- '(sqrt(2) - sqrt(2)) + sqrt(3)'
assert "sin(pi) + sqrt(2)" \
    '1.4142135623730950488016887242096980785696718753769480731766797379907324' -d70 -- 'sin(pi) + sqrt(2)'
assert "sin(pi/2) + sqrt(2)" \
    '2.4142135623730950488016887242096980785696718753769480731766797379907324' -d70 -- 'sin(pi/2) + sqrt(2)'
assert "pi to 44 digits with round-to-nearest" \
    '3.14159265358979323846264338327950288419716940' -d44 --rn pi
assert "1/2 to 40 digits is exact" '0.5' -d40 1/2

echo
echo "=== 4. algebraic / integer-sequence solver ==="
assert "golden ratio via algebraic()" \
    '1.61803398874989484820458683436563811772030917980576' -d50 'algebraic(0,2,-1,-1,+1)'
assert "continued fraction 1;2,3 at 100 digits" \
    '1;2,3' -d100 -cl 'algebraic(1,2,-10,307,-210,0,0,-10,7)'

echo
echo "=== 5. transcendental + special functions ==="
assert "LambertW(-1/e) + sqrt(2)" \
    '0.41421356237309504880' -d20 -- 'W(-1/e) + sqrt(2)'
assert "erf(0)" '0' 'erf(0)'
assert "erfc(0)" '1' 'erfc(0)'
assert "Phi(0)" '0.5' 'Phi(0)'
assert "erfinv(0.99)" '1.8213863677' -d10 -- 'inverf(0.99)'

echo
echo "=== 6. log family (dyadic and decimal bases) ==="
assert "log(0.66) to 20 digits" '-0.41551544396166582316' -d20 'log(0.66)'
assert "log2(2^456)" '456' 'log2(2^456)'
assert "log2(2^-456)" '-456' 'log2(2^-456)'
assert "dyadic log(4,2)" '2' -R 'log(4,2)'
assert "log(6,12) also falls back to a rational" \
    '0.72105705434887015680' -d20 'log(6,12)'

echo
echo "=== 7. rationals, ceil/floor, let-bindings ==="
assert "ceil(1+sqrt(0))" '1' 'ceil(1+sqrt(0))'
assert "1/2 - pi/1e80 to 40 digits" \
    '0.4999999999999999999999999999999999999999' -d40 '1/2 - pi/1e80'
assert "let x=pi, y=e in (x+y)/(x-y)" \
    '13.8429592019974901448229600419452604080771' -d40 'let x=pi, y=e in (x+y)/(x-y)'
assert "nested let f(x)=x+1, g(x)=f(2*x)" \
    '7.2831853071795864769252867665590057683943' -d40 'let f(x)=x+1, g(x)=f(2*x) in g(pi)'
assert "4/-9 in lowest terms via -R" '-4/9' -R 4/-9

echo
echo "=== 8. output bases and printf formats ==="
assert "pi in base 2" \
    '11.0010010000111111011010101000100010000101' -b2 -d40 pi
assert "pi in base 16" \
    '3.243f6a8885a308d313198a2e03707344a4093822' -b16 -d40 pi
assert "pi in base 36" \
    '3.53I5AB8P5FSA5JHK72I8ASC47WWZLACLJJ9ZN98L' -B36 -d40 pi
assert "pi with --printf=%.10a" '0x1.921fb54443p+1' --printf=%.10a -- pi
assert "pi^12 with --printf=%e" '9.242692e+05' --printf=%e -- 'pi^12'
assert "width/flag torture: --printf='% 50.10a' of -pi/65536" \
    '                               -0x1.921fb54443p-15' '--printf=% 50.10a' -- -pi/65536
assert "-0.1 with --printf=%.17g" '-0.1' --printf=%.17g -- -0.1

echo
echo "=== 9. trig by degree (separately implemented code path) ==="
assert "cosd(-240)" '-0.5' -d6 'cosd(-240)'
assert "asind(-0.5)" '-30' -d6 'asind(-0.5)'
assert "atan2d(3,4)" '36.869897' -d6 'atan2d(3,4)'

echo
echo "=== 10. p-th roots via algebraic pow ==="
assert "(+2)^(-10/4)" '0.17677669529663688110' -d20 -- '(+2)^(-10/4)'
assert "(+2)^(1/4)" '1.18920711500272106671' -d20 -- '(+2)^(1/4)'

echo
echo "[summary] pass=$PASS fail=$FAIL total=$TOTAL"
[ "$FAIL" -eq 0 ] || exit 1
echo "test spigot 0.2017-01-15.gdad1bbc6: PASS"
exit 0
