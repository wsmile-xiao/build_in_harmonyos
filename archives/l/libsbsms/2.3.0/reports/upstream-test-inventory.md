# 上游测试清点报告 — libsbsms 2.3.0

> 结论: **上游 2.3.0 不随源码提供任何测试。N(上游) = 0。**
> 日期: 2026-09-15
> 依据: R51 上游测试三步法；device-facts §二.20（`TOTAL = PASS + FAIL + SKIP + NOT_RUN`，
> 「上游确无测试」须附清点证据，不得用「没环境」当理由）
> 清点对象: `libsbsms-2.3.0.tar.gz`
> sha256 `4f88d152bc06fedbda9d5d65517d40254a7310c9050601a93122309d45afd2c9`（450111 字节）

## 一、清点证据（逐条可复现）

源码树: `$TMPDIR/builds/libsbsms-2.3.0.work`（GitHub tag 归档解压，顶层 `libsbsms-2.3.0/`）

| # | 口径 | 命令 | 结果 |
|---|------|------|------|
| 1 | 归档条目总数 | `tar tzf libsbsms-2.3.0.tar.gz \| wc -l` | `72` |
| 2 | 是否存在测试目录 | `tar tzf libsbsms-2.3.0.tar.gz \| grep -iE '/(test\|tests\|testing\|check)'` | 零命中 |
| 3 | 文件名含 test | `find . -iname '*test*'` | 零命中 |
| 4 | 文件名含 check | `find . -iname '*check*'` | 仅 `./m4/ax_check_compiler_flags.m4`（autoconf 宏，不是测试） |
| 5 | 源码宏口径 | `grep -rn "int main" src include` | 零命中（11 个 `.cpp` 无任何可执行入口） |
| 6 | autotools 注册口径 | `grep -nE "SUBDIRS\|TESTS\|check-local\|check_PROGRAMS" Makefile.am src/Makefile.am` | 仅 `Makefile.am:1:SUBDIRS = src`，无 `TESTS`/`check-local`/`check_PROGRAMS` |
| 7 | CTest 注册口径 | `grep -nE "enable_testing\|add_test\|include\(CTest\)" CMakeLists.txt` | 零命中 |
| 8 | 其他测试框架 | `find . -name 'pytest.ini' -o -name 'tox.ini' -o -name 'meson.build' -o -name 'test_*.py'` | 零命中 |

四种口径（源码宏数 / 框架注册数 / assertion 数 / 消费者断言数）中，本例可用的是
**源码宏数 = 0** 与 **框架注册数 = 0**，两者一致，不存在"用错口径把 N 压小"的问题。

## 二、为什么 README 提到的 `test.cpp` 不算数

上游 `README.md` 写有 "The simplest method for doing so is found in test.cpp."，
但 **`test.cpp` 不在仓库里**（口径 3 零命中，口径 5 无 `main()`）。
该文件直到 main 分支新增 `example/` 目录后才出现（`example/src/sbsms-convert.cpp`
等），而 `2.3.0` tag 早于这次新增。因此：

- 不能按 main 分支的 `example/` 去申报上游测试数——那不是 2.3.0 的内容；
- 也不能把 `example/` 的代码搬进 `test_package/` 充数（它按可选开关引用
  `libsndfile`/`libmad`/`libportaudio` 等解码器，见 `example/src/config.h` 的
  `HAVE_SNDFILE`/`HAVE_MAD`/`HAVE_PORTAUDIO`，且 main 分支的
  `SBSMSQualityStandard` 参数表在 2.3.0 的 `src/` 上会崩溃，见 `notes.md` 问题 4）。

## 三、测试统计（上游为 0，鸿蒙特有分栏）

| 分类 | 总数 | PASS | FAIL | SKIP | NOT_RUN |
|------|:----:|:----:|:----:|:----:|:-------:|
| 上游测试 | 0 | 0 | 0 | 0 | 0 |
| 鸿蒙特有测试（`test_package` 消费者断言） | 26 | 26 | 0 | 0 | 0 |
| 合计 | 26 | 26 | 0 | 0 | 0 |

- 上游测试通过率 0/0（上游未提供任何测试入口）
- 鸿蒙特有测试通过率 26/26（100%）
- 适配后合计通过率 26/26（100%）

「鸿蒙特有测试」行的取数命令（设备实测）:

```console
$ cd archives/l/libsbsms/2.3.0/test_package && ./test_sbsms | tail -2
checks=26 failed=0
RESULT: PASS
```

该 26 条断言全部来自 `test_package/test_sbsms.cpp` 的 `check*()` 调用点，不包含任何
上游用例（上游没有用例可包含），因此不存在把上游用例混入鸿蒙行的口径问题。

## 四、未运行项

无。上游没有测试，故不存在"未运行的上游用例"。
