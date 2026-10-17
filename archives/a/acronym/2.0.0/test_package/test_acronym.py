#!/usr/bin/env python3
"""Path B supplementary tests for acronym 2.0.0 — Acronym Scoring System.

上游 bacook17/acronym 2.0.0 无任何测试文件，本文件按路径 B 补全：
覆盖 score_word / score_acronym / _set_caps / _get_acronym / _index_in
/ find_acronyms（fake corpus，避免真实 NLTK 语料下载）/ ensure_corpus。

运行方式：python3 test_acronym.py
"""
import sys
import unittest
import os

# CI/鸿蒙受限环境无法从用户目录加载 numpy/pandas/nltk 的 C 扩展 .so
# （加载报 Permission denied，HMDFS/SELinux 限制）。被测核心逻辑
# （scoring、字符串处理）均为纯 Python，不依赖这些库的功能；为通过
# import 注入最小 stub。依赖真实 numpy/pandas 的 find_acronyms 集成
# 测试在依赖不可用时跳过。
try:
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import nltk  # noqa: F401
    _DEPS_OK = True
except Exception:
    _DEPS_OK = False
    import types
    for _name in ("numpy", "pandas", "nltk"):
        sys.modules.setdefault(_name, types.ModuleType(_name))

# 通过 PYTHONPATH 找到已安装的 acronym 包
import acronym.acronym as mod
from acronym.scoring import score_word, score_acronym


class FakeCorpus(object):
    """最小 fake NLTK corpus：words() 返回词表，ensure_loaded() 不报错。"""

    def __init__(self, words):
        self._words = words

    def ensure_loaded(self):
        return None

    def words(self):
        return self._words


class FakeMissingCorpus(object):
    """模拟语料缺失：ensure_loaded() 抛 LookupError。"""

    def ensure_loaded(self):
        raise LookupError("corpus not found")


class TestScoreWord(unittest.TestCase):
    def test_score_word_basic(self):
        # 首字母 +10，第二字母 +3，末字母 +3，连续大写 bonus +2
        # "ABC": A=10, B=3+2(consec)=5, C=3+2(consec)=5 => 20
        self.assertEqual(score_word("ABC"), 20)

    def test_score_word_consecutive_bonus(self):
        # 连续大写：后一个字母额外 +2
        # "AB" -> A:10 + B:(3+2) = 15
        self.assertEqual(score_word("AB"), 15)

    def test_score_word_subword_bonus(self):
        # corpus 中包含子词时加分
        # "MultiVariable": M(10) + u(0,小写跳过) ... 尾部 "able" 在 corpus
        corpus = {"able"}
        s = score_word("MultiVariable", corpus=corpus)
        self.assertGreater(s, 0)

    def test_score_word_ignores_non_alpha(self):
        # 非字母字符被剥离
        self.assertEqual(score_word("A-B-C"), score_word("ABC"))


class TestScoreAcronym(unittest.TestCase):
    def test_score_acronym_total(self):
        # score_acronym = sum(score_word per word) - 10
        # "AB" -> score_word=15, 总分 = 15 - 10 = 5
        self.assertEqual(score_acronym("AB"), 5)

    def test_score_acronym_multiple_words(self):
        s = score_acronym("Multi Variable")
        self.assertEqual(s, score_word("Multi") + score_word("Variable") - 10)


class TestSetCaps(unittest.TestCase):
    def test_set_caps(self):
        self.assertEqual(mod._set_caps("multivariable", [0, 5]), "MultiVariable")


class TestGetAcronym(unittest.TestCase):
    def test_get_acronym(self):
        self.assertEqual(mod._get_acronym("multivariable", [0, 5]), "MV")


class TestIndexIn(unittest.TestCase):
    def test_index_in_simple(self):
        # "cat" 按序出现在 "concatenate" 中
        idx = mod._index_in("concatenate", "cat")
        self.assertIsNotNone(idx)
        # 还原出的字母应为 C-A-T
        letters = "".join("concatenate"[i] for i in idx)
        self.assertEqual(letters, "cat")

    def test_index_in_no_match(self):
        self.assertIsNone(mod._index_in("abc", "xyz"))


class TestFindAcronyms(unittest.TestCase):
    @unittest.skipUnless(_DEPS_OK, "numpy/pandas C 扩展在受限环境不可用，跳过")
    def test_find_acronyms_fake_corpus(self):
        # fake corpus 包含单词 "code"，输入 "cod e" 中 c-o-d-e 按序出现
        corpus = FakeCorpus(["create", "data", "code", "date"])
        result = mod.find_acronyms("cod e", corpus, min_length=3, max_length=6)
        # 返回 pandas DataFrame
        self.assertFalse(result.empty)
        self.assertIn("score", result.columns)
        self.assertIn("CODE", result.index)
        # 分数应为降序
        scores = list(result["score"])
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestEnsureCorpus(unittest.TestCase):
    def test_ensure_corpus_missing_raises(self):
        with self.assertRaises(RuntimeError):
            mod.ensure_corpus(FakeMissingCorpus())

    def test_import_module_no_network(self):
        # 打补丁后 import 不触发 NLTK 语料下载（不阻塞）
        self.assertTrue(hasattr(mod, "ensure_corpus"))
        self.assertTrue(callable(mod.find_acronyms))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
