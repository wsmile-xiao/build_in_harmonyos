# 上游测试枚举台账 — uchardet 0.0.7

## 注册方式

`test/CMakeLists.txt` 遍历 `test/<lang>/<charset>/` 语料目录，每个语料文件注册一项
ctest：`add_test(NAME "<lang>:<charset>" COMMAND uchardet-tests <file>)`。
上游跳过 5 项已知损坏组合（不注册）：ja:utf-16le、ja:utf-16be、es:iso-8859-15、
da:iso-8859-1、he:iso-8859-8。

## 语料组合清单（ctest 注册 116 项；另 5 项上游已知损坏由上游 CMakeLists 跳过未注册，以 * 标注）

ar:iso-8859-6, bg:iso-8859-5, bg:windows-1251, cs:iso-8859-2, da:iso-8859-1*,
de:iso-8859-1, de:iso-8859-15, de:windows-1252, el:iso-8859-7, en:iso-8859-1,
en:iso-8859-15, en:us-ascii, en:utf-16be, en:utf-16le, en:utf-32be, en:utf-32le,
en:utf-8, en:windows-1252, eo:iso-8859-3, es:iso-8859-15*, es:iso-8859-1,
es:windows-1252, et:iso-8859-15, et:iso-8859-4, fi:iso-8859-1, fi:iso-8859-15,
fr:iso-8859-1, fr:iso-8859-15, fr:us-ascii, fr:windows-1252, ga:iso-8859-15,
ga:windows-1252, he:iso-8859-8*, hu:iso-8859-2, it:iso-8859-1, it:iso-8859-15,
it:windows-1252, ja:euc-jp, ja:iso-2022-jp, ja:shift_jis, ja:utf-16be*,
ja:utf-16le*, ja:utf-8, lt:iso-8859-13, lv:iso-8859-13, mt:iso-8859-3,
nl:iso-8859-1, nl:iso-8859-15, no:iso-8859-1, no:iso-8859-15, pl:iso-8859-2,
pl:iso-8859-16, pt:iso-8859-1, pt:iso-8859-15, pt:windows-1252, ro:iso-8859-2,
ro:iso-8859-16, ru:iso-8859-5, ru:koi8-r, ru:windows-1251, ru:utf-8, sk:iso-8859-2,
sl:iso-8859-2, sv:iso-8859-1, sv:iso-8859-15, th:iso-8859-11, th:tis-620,
tr:iso-8859-9, zh:big5, zh:euc-tw, zh:gb18030, zh:utf-8 ...

（* 标记为上游已知损坏跳过项；以上为 ctest -N 枚举的主要组合，
完整清单见 `reports/w3-local-ci.log` 中 L1 段 ctest 输出）

## 执行结果

```
100% tests passed, 0 tests failed out of 116
Total Test time (real) = 2.99 sec
```

执行环境：conan create（profile ohos-aarch64）内 `cmake.test()`，2026-09-18。
