#!/usr/bin/env python3
"""Test script for rapidfuzz 3.12.2 — verifies core fuzzy matching functionality.

Exercises the C extension modules (fuzz_cpp, utils_cpp, process_cpp_impl,
metrics_cpp, _initialize_cpp) and the pure-Python fallback layer.
"""
import sys


def test_fuzz():
    from rapidfuzz import fuzz
    r = fuzz.ratio("this is a test", "this is a test!")
    assert r >= 95.0, f"fuzz.ratio expected >= 95, got {r}"
    pr = fuzz.partial_ratio("this is a test", "this is a test!")
    assert pr >= 99.0, f"fuzz.partial_ratio expected >= 99, got {pr}"
    ts = fuzz.token_set_ratio("fuzzy was a bear", "fuzzy fuzzy was a bear")
    assert ts >= 90.0, f"fuzz.token_set_ratio expected >= 90, got {ts}"
    return r, pr, ts


def test_distance():
    from rapidfuzz.distance import Levenshtein, Hamming, Jaro, JaroWinkler, Indel, LCSseq, OSA, DamerauLevenshtein
    lev = Levenshtein.distance("lewenstein", "levenshtein")
    assert lev == 2, f"Levenshtein.distance expected 2, got {lev}"
    ham = Hamming.distance("abcde", "abcde")
    assert ham == 0, f"Hamming.distance expected 0, got {ham}"
    jar = Jaro.similarity("MARTHA", "MARHTA")
    assert jar > 0.9, f"Jaro.similarity expected > 0.9, got {jar}"
    jw = JaroWinkler.similarity("MARTHA", "MARHTA")
    assert jw > 0.9, f"JaroWinkler.similarity expected > 0.9, got {jw}"
    ind = Indel.distance("lewenstein", "levenshtein")
    assert ind == 3, f"Indel.distance expected 3, got {ind}"
    lcs = LCSseq.distance("lewenstein", "levenshtein")
    assert lcs == 2, f"LCSseq.distance expected 2, got {lcs}"
    osa = OSA.distance("lewenstein", "levenshtein")
    assert osa == 2, f"OSA.distance expected 2, got {osa}"
    dl = DamerauLevenshtein.distance("lewenstein", "levenshtein")
    assert dl == 2, f"DamerauLevenshtein.distance expected 2, got {dl}"
    return lev, ham, jar, jw, ind, lcs, osa, dl


def test_process():
    from rapidfuzz import process
    results = process.extract("hello", ["hello", "world", "hello world"], limit=2)
    assert len(results) >= 1, f"process.extract returned empty: {results}"
    best = results[0]
    assert best[0] == "hello", f"process.extract best expected 'hello', got {best[0]}"
    assert best[1] >= 99.0, f"process.extract best score expected >= 99, got {best[1]}"
    return results


def test_utils():
    from rapidfuzz import utils
    # default_process only strips the ends, lowercases and drops punctuation;
    # it deliberately preserves interior whitespace.
    s = utils.default_process("  Hello, World!  ")
    assert isinstance(s, str), f"default_process should return str, got {type(s)}"
    assert s == "hello  world", f"default_process expected 'hello  world', got '{s}'"
    assert s == s.strip(), f"default_process should strip ends, got '{s}'"
    t = utils.default_process("Fuzzy  was A  bear")
    assert t == "fuzzy  was a  bear", f"default_process expected whitespace kept, got '{t}'"
    return s


def test_cpp_implementation():
    """断言真正跑的是 C++ 实现，而不是 import 失败后的纯 Python 兜底。

    `import rapidfuzz` 在扩展模块载入失败时会静默切到 *_py 实现，消费者测试
    照样全绿（CI #63465 的教训）。绑定函数的 __module__ 会暴露真实来源：
    编译版是 rapidfuzz.fuzz_cpp / .distance.metrics_cpp，纯 Python 版是 *_py。
    """
    from rapidfuzz import fuzz
    from rapidfuzz.distance import Levenshtein
    for fn, name in ((fuzz.ratio, "fuzz.ratio"),
                     (Levenshtein.distance, "distance.Levenshtein.distance")):
        mod = getattr(fn, "__module__", "") or ""
        assert "_cpp" in mod, (
            f"{name} 来自 {mod!r}，说明 C++ 扩展未生效（退化为纯 Python 实现）")
    print(f"OK cpp: fuzz.ratio from {fuzz.ratio.__module__}, "
          f"Levenshtein.distance from {Levenshtein.distance.__module__}")
    return fuzz.ratio.__module__


def main():
    print("=== rapidfuzz 3.12.2 consumer test ===")
    ver = sys.version_info
    print(f"Python: {ver.major}.{ver.minor}.{ver.micro}")

    test_cpp_implementation()

    r = test_fuzz()
    print(f"OK fuzz: ratio={r[0]:.2f} partial={r[1]:.2f} token_set={r[2]:.2f}")

    d = test_distance()
    print(f"OK distance: lev={d[0]} ham={d[1]} jaro={d[2]:.4f} jw={d[3]:.4f} "
          f"indel={d[4]} lcs={d[5]} osa={d[6]} dl={d[7]}")

    p = test_process()
    print(f"OK process: extract best={p[0][0]!r} score={p[0][1]:.2f}")

    u = test_utils()
    print(f"OK utils: default_process -> {u!r}")

    print("PASS: all rapidfuzz tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
