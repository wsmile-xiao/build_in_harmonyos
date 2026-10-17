# 上游 tests/cxx 22 程序实跑记录（libgmpxx 6.3.0）

> **覆盖范围声明**：本记录只覆盖上游 N=200（GMP 6.3.0 tarball `tests/**` 的
> `check_PROGRAMS` 注册项，含审方口径 `t-*` 190）中的 `tests/cxx` **22** 项——即本包
> 交付面（C++ 绑定）对应的上游测试。其余 178 项（tests/ 根 8、misc 3、mpf 28、mpn 53、
> mpq 15、mpz 64、rand 7）的测试对象是 **libgmp C API**，不在本包 install 面
> （`package()` 裁剪 `libgmp.a`/`gmp.h`/`gmp.pc`，C 库由 `gmp/6.3.0` 交付），已按
> **NOT_RUN 记账、不写 PASS**；逐目录分解、取数命令与替代验证见
> `reports/test-report.md` §1.1 与 `notes.md`「上游测试（R51 三步法）」节。

- 日期：2026-09-19；环境：HarmonyOS PC 设备（aarch64，OHOS 6.0，clang 15.0.4，libc++）
- 被测产物：本轮 `conan create` 配方构建的 `libgmpxx.a`（46468 字节）与依赖 `libgmp.a`
  （1105512 字节），测试辅助库 `libtests.a`（172116 字节），均为 gmp 6.3.0 同源
  `--enable-cxx --disable-shared --enable-static --with-pic ABI=64` 配置产物
- 结果：**22/22 通过**（每程序独立编译链接并运行，退出码 0 计 PASS）

## 为什么不用 `make -C tests/cxx check`

设备 HMDFS 的 `getcwd(2)` 间歇返回 EFAULT/ENOTSUP（同一目录 bash 内建 pwd 可用、外部
pwd/libtool 失败，深浅路径均复现），libtool 生成测试可执行文件时的绝对路径解析
（`cannot determine absolute directory name of '../../.libs'`）随之确定性失败——
`make -C tests/cxx check` 在 t-binary 链接处 Error 1（`make t-binary` 单独重放亦复现）。
该故障属设备文件系统缺陷，与配方逻辑无关。故测试改用下述直接链接 harness 实跑，
编译器/宏与 configure 生成的一致，链接对象就是同一构建树的 `make` 产物。

## 实跑命令（harness 原件见文末哈希）

对 tests/cxx/Makefile.am `check_PROGRAMS` 全部 22 个程序逐一执行（t-locale 额外编译
clocale.c，与其 Makefile.am 的 `_SOURCES` 一致）：

```sh
/data/service/hnp/bin/clang++ -DNDEBUG -O3 -stdlib=libc++ -std=c++17 \
    -I<build> -I<src> -I<src>/tests -I<src>/tests/cxx \
    <src>/tests/cxx/<t>.cc [clocale.c] \
    <build>/tests/.libs/libtests.a <build>/.libs/libgmpxx.a <build>/.libs/libgmp.a -lm \
    -o <out>/<t> && <out>/<t>
```

## 实跑结果（逐字转录自原件 result.txt）

```
PASS t-assign
PASS t-binary
PASS t-cast
PASS t-constr
PASS t-cxx11
PASS t-do-exceptions-work-at-all-with-this-compiler
PASS t-headers
PASS t-iostream
PASS t-istream
PASS t-locale
PASS t-misc
PASS t-mix
PASS t-ops
PASS t-ops2z
PASS t-ops2qf
PASS t-ops2f
PASS t-ops3
PASS t-ostream
PASS t-prec
PASS t-rand
PASS t-ternary
PASS t-unary
SUMMARY pass=22 fail=0 build_fail=0 total=22
```

注：GMP 测试程序通过时静默退出 0（run.log 为 0 字节属预期）；build-errors.log 仅 1 行
clang 对 clocale.c 的 `-Wdeprecated` 提示（C 文件在 C++ 模式下编译的告警，与上游
Makefile.am 将 clocale.c 计入 C++ 目标的行为一致，不影响结果）。

## 原件指纹（上一轮任务目录的 task-data/libgmpxx-6.3.0/upstream-tests-evidence/）

| 文件 | SHA256 | 字节数 | 行数 |
| --- | --- | --- | --- |
| result.txt | 66a549e8b31fa52773b81a27135bd54156cdd31114c417526aba4156c158b95f | 1158 | 28 |
| run.log | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | 0 |
| build-errors.log | 6d958b0a6bbf3dca510e008d982ed30111e76af7da54929b0adab2f64a3c5a16 | 108 | 1 |
| run-upstream-tests-direct.sh（harness 原件） | f590d1d04f03aa2b5278a734e9ece0b9d2ad97de71d44b46714c85241860659f | 1970 | 36 |

**可核性说明（如实披露）**：上述四份原件位于**上一轮任务**的 task-data 目录（仓库外），
本轮任务目录中已不存在，因此**无法再按这些哈希复核逐字转录**；哈希与行列数为当时记录，
保留在此仅作审计线索。另有一处差额：`result.txt` 记录 28 行，而本文件的转录块是
22 个 `PASS` 行 + 1 个 `SUMMARY` 行 = 23 行；其余 5 行的内容未随原件留存，
差额无法解释——这一点在 W4 审计中已被列为「未覆盖项」，不作为通过证据。
