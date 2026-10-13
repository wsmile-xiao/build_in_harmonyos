# test_snek.py -- consumer test for the packaged snek interpreter.
#
# Each check() prints exactly one "CHECK-OK: <name>" line on success and
# exits 1 on the first failure. Only language constructs covered by the
# upstream suite are used (print % formatting, assert-free explicit
# checks, def, for/range, list/dict literals, from math import *).


def check(cond, name):
    if not cond:
        print("FAIL %s" % name)
        exit(1)
    print("CHECK-OK: %s" % name)


check(2 + 3 * 4 == 14 and 10 - 4 == 6, "arith")
check("hello" + " " + "world" == "hello world" and str(42) == "42", "str")

a = [1, 2]
check(a + [3] == [1, 2, 3] and a[0] == 1, "list")

d = {"a": 1, "b": 2}
check(d["a"] + d["b"] == 3, "dict")


def fact(n):
    total = 1
    for i in range(1, n + 1):
        total *= i
    return total


check(fact(9) == 362880, "func-loop")

from math import *

check(sqrt(4) == 2, "math")
