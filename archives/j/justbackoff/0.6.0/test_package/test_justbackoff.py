#!/usr/bin/env python3
"""justbackoff 0.6.0 consumer test (CI L0c + R34).

Standalone test source, executed via self.run from test_package/conanfile.py
with the package's conanrun PYTHONPATH applied.

R34: this test really calls the installed package API (Backoff / to_seconds /
to_ms); it is not a print-only stub.

Coverage (mirrors the upstream contract asserted by tests/test_backoff.py and
adds boundary/cap cases the upstream suite does not exercise):

  1. to_seconds / to_ms unit conversion
  2. default constructor values (min_ms=100, max_ms=10000, factor=2)
  3. duration() progression + attempt() counter + reset()
  4. for_attempt(n) direct lookup
  5. factor != 2.0 progression
  6. max_ms cap (dur > max_ms -> to_seconds(max_ms))
  7. int arguments behave like float arguments
  8. jitter=True stays inside [min_ms, min_ms*factor^attempt] (and is capped)
  9. jitter=False is fully deterministic

Usage: test_justbackoff.py <site-packages-dir>
"""
import os
import random
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isfile(os.path.join(site, "justbackoff", "__init__.py")):
        raise AssertionError(f"justbackoff package missing in {site}")
    sys.path.insert(0, site)

    from justbackoff import Backoff, to_ms, to_seconds

    n = 0

    # 1. unit conversion ---------------------------------------------------
    assert to_seconds(100.0) == 0.1, to_seconds(100.0)
    assert to_seconds(0) == 0.0
    assert to_ms(0.1) == 100.0
    assert to_ms(1000.0) == 1000000.0
    n += 4

    # 2. default constructor values ---------------------------------------
    d = Backoff()
    assert d.min_ms == 100.0 and d.max_ms == 10000.0 and d.factor == 2.0
    assert d.jitter is False
    assert d.duration() == to_seconds(100.0)
    n += 4

    # 3. duration() progression / attempt() / reset() ----------------------
    b = Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0)
    assert b.attempt() == 0
    assert b.duration() == to_seconds(100.0)
    assert b.duration() == to_seconds(200.0)
    assert b.duration() == to_seconds(400.0)
    assert b.attempt() == 3
    b.reset()
    assert b.attempt() == 0
    assert b.duration() == to_seconds(100.0)
    n += 8

    # 4. for_attempt() direct lookup --------------------------------------
    f = Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0)
    assert f.for_attempt(0) == to_seconds(100.0)
    assert f.for_attempt(1) == to_seconds(200.0)
    assert f.for_attempt(2) == to_seconds(400.0)
    # for_attempt() itself must not advance the counter
    assert f.attempt() == 0
    n += 4

    # 5. factor != 2.0 -----------------------------------------------------
    g = Backoff(min_ms=100.0, max_ms=10000.0, factor=1.5)
    assert g.duration() == to_seconds(100.0)
    assert g.duration() == to_seconds(150.0)
    assert g.duration() == to_seconds(225.0)
    g.reset()
    assert g.duration() == to_seconds(100.0)
    n += 4

    # 6. max_ms cap --------------------------------------------------------
    c = Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0)
    # 100 * 2^10 = 102400 ms > max_ms -> capped at max_ms (10.0 s)
    assert c.for_attempt(10) == to_seconds(10000.0)
    assert c.for_attempt(6) == to_seconds(6400.0)   # not yet capped
    assert c.for_attempt(7) == to_seconds(10000.0)  # 12800 ms -> capped
    n += 3

    # 7. int arguments behave like float arguments -------------------------
    i = Backoff(min_ms=100, max_ms=10000, factor=2)
    assert (i.min_ms, i.max_ms, i.factor) == (100.0, 10000.0, 2.0)
    assert i.duration() == to_seconds(100.0)
    assert i.duration() == to_seconds(200.0)
    assert i.duration() == to_seconds(400.0)
    i.reset()
    assert i.duration() == to_seconds(100.0)
    n += 6

    # 8. jitter=True stays within [min_ms, min_ms*factor^attempt] ----------
    j = Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0, jitter=True)
    assert j.duration() == to_seconds(100.0)   # attempt 0: dur == min_ms
    for attempt in (1, 2, 3):
        dur = j.duration()
        low, high = to_seconds(100.0), to_seconds(100.0 * 2 ** attempt)
        assert low <= dur <= high, (attempt, dur, low, high)
    n += 4
    # deterministic jitter for a fixed seed -> reproducible bounds
    random.seed(20261002)
    j2 = Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0, jitter=True)
    j2.duration()
    r1 = j2.duration()
    random.seed(20261002)
    j3 = Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0, jitter=True)
    j3.duration()
    r2 = j3.duration()
    assert r1 == r2, (r1, r2)
    assert to_seconds(100.0) <= r1 <= to_seconds(200.0), r1
    n += 2

    # 9. jitter=False is deterministic -------------------------------------
    k = Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0, jitter=False)
    assert [k.duration() for _ in range(3)] == [0.1, 0.2, 0.4]
    n += 1

    # module identity ------------------------------------------------------
    import justbackoff as mod
    assert os.path.realpath(mod.__file__).startswith(
        os.path.realpath(site)), mod.__file__
    assert callable(mod.Backoff) and callable(mod.to_seconds)
    n += 2

    print(f"OK: justbackoff 0.6.0 consumer test — {n} assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
