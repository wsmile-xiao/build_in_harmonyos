# termcap 1.3.1 适配笔记

## 编译环境
- 构建系统: 1996 年手写 configure + 手写 Makefile（非 automake）
- 编译日期: 2026-09-13
- 编译器: clang 15（OHOS aarch64 真机）
- 状态: built

## 编译步骤

1. W0 预检：`bash ci/scripts/preflight_check.sh termcap/1.3.1` 通过（无依赖声明，零外部依赖）。
2. W0b：归档树无 termcap 同名/同版本；recipe-search 无相似配方。
3. 探索编译（builds/termcap-1.3.1.work）：
   - `./configure --prefix=$DEFAULT_PREFIX`（CC=clang）一次通过——该 configure 不使用 config.guess/sub（tarball 内也没有），仅探测头文件并写 config.cache。
   - `make -j1`（ar rc libtermcap.a + ranlib）。
   - 上游 `make install` 无 DESTDIR 支持、且无条件向 /usr/include 写文件（错误被 ignore），探索产物已手工清理，配方 package() 直接拷贝 libtermcap.a + termcap.h。
4. conan-init → 人工定制配方（static-library 型，绕过 Autotools.configure 的标准目录参数）→ conan-verify（G0-G4 + L2/L4/L5 全 PASS）。

## 上游测试账本（四维）

- 上游源码静态声明总数 N_static = 0：源码树无 tests/ 目录、无测试源文件、无 dejagnu/ctest 注册；Makefile.in 为手写（非 automake），连 `check` 目标都不存在（grep "^check:" 计 0）。
- 实际执行数 N_executed = 0（上游无测试可执行）。
- 跳过数 = 0。
- 新增消费者测试 N_consumer = 1（test_package/test.c，7 项断言），经 CTest 执行：`1/1 Test #1: test_termcap Passed`，`100% tests passed, 0 tests failed out of 1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 时 `configure: error: --bindir=${prefix}/bin: invalid option` | 1996 年手写 configure 早于标准目录参数集（--bindir/--sbindir/--libdir/--includedir/--oldincludedir），Conan Autotools.configure() 默认全传 | build() 绕过 Autotools.configure()，直接 `sh configure --prefix=...`（sh 调用同时规避 HMDFS exec 位问题，E490） |
| 2 | 探索期 make install 向 /usr/include 写文件 | 上游 Makefile 无 DESTDIR，硬编码系统路径 | 配方 package() 直接拷贝 libtermcap.a 与 termcap.h，不跑 install；探索残留已清理 |

## 源码修改

无（conandata.yml `patches: {}`）。探索期曾向工作树拷入新版 config.guess/sub，但该 configure 不使用它们，未进补丁。

## 依赖版本

无外部依赖（零依赖库）。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh termcap/1.3.1   # PASS
python3 scripts/ohc-run.py conan-verify termcap 1.3.1
# G1/G2(conan create)/G3/G4/L2/L4/L5 全 PASS
# 消费者测试 CTest 1/1 Passed（7 项断言）
```

## 注意事项

- 纯静态库（ar 归档），无 shared 产物；TERMCAP_FILE 默认编译为 /etc/termcap，运行时可用 $TERMCAP/$TERM 环境变量覆盖（消费者测试即用内联 TERMCAP 条目验证）。
- 上游 `make install` 会向 /usr/include 写文件且报错被 ignore——配方已绕开；直接复用上游 install 目标的其他项目需注意。
- 路径 A，无跨仓库新知识增量（老 configure 参数集问题属 E 系既有模式覆盖范围），不走路径 B。
---

**编译结束**: 2026-09-14 00:23
**最终状态**: built
