# coremark 1.01 适配笔记

## 编译环境
- 构建系统: makefile（无 configure；官方 Makefile + PORT_DIR 移植层）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（OHOS 交叉编译链 /data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

```bash
# 源码：官方 tag v1.01（https://github.com/eembc/coremark, tag v1.01, commit cfa9ab3778）
# tarball SHA-256: 99c5a6d63af85a281b4e4d6ccb522c446653c435dfec9455ad73ef9e71f28bde
make PORT_DIR=linux64 CC=clang XCFLAGS="-DITERATIONS=1000"   # 默认 make run：编译+性能运行+验证运行
make PORT_DIR=linux64 CC=clang XCFLAGS="-DITERATIONS=1000 -DPERFORMANCE_RUN=1" load run1.log
make PORT_DIR=linux64 CC=clang XCFLAGS="-DITERATIONS=1000 -DVALIDATION_RUN=1" load run2.log
make PORT_DIR=linux64 CC=clang XCFLAGS="-DITERATIONS=1000 -DPROFILE_RUN=1" load run3.log
```

coremark 是自验证基准程序（无 configure、无 tests/ 目录、无 ctest/GTest 注册）。构建产物是 `coremark.exe`（CLI 可执行文件，非库）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时（Errno 110） | 执行端到 github.com 主站连接超时 | 改用官方 GitHub codeload 域名（codeload.github.com，官方正式源）下载 tag v1.01 tarball，SHA-256 已核验 |
| 2 | `make check`（md5sum -c coremark.md5）失败 | 上游官方 tag 源码包**不随发布提供** coremark.md5 校验文件（`make check` 目标依赖该文件，仅 EEMBC 完整发行包内含） | 记录为上游发行物缺失：`check` 目标不可运行属上游固定行为，非适配缺陷；以 run 目标（自带 crcfinal 自校验 + "Correct operation validated"）作为权威验证入口 |
| 3 | PORT_DIR 缺省检测 | Makefile 依赖 `uname` 判定 PORT_DIR | 显式指定 `PORT_DIR=linux64` |

## 源码修改

无（纯原生编译验证；HarmonyOS 适配通过 conanfile.py 配方层完成，不打源码补丁）。

## 上游测试枚举台账（双口径，R51）

coremark 无独立测试文件，其"测试"即基准自验证运行。枚举结果：

| 入口 | 类型 | 分类理由 | 是否独立上游用例 | 实际运行 | 结果 |
|------|------|----------|------------------|----------|------|
| run1.log（PERFORMANCE_RUN） | 性能+正确性自校验 | Makefile run 目标之一，输出 crcfinal + 校验 | 是（验证入口） | ✅ 已运行 | PASS（Correct operation validated, 15551.29 it/s） |
| run2.log（VALIDATION_RUN） | 验证运行 | Makefile run 目标之一，同上 | 是（验证入口） | ✅ 已运行 | PASS（Correct operation validated, 15344.48 it/s） |
| run3.log（PROFILE_RUN） | profile 运行 | Makefile run 目标之一，同上 | 是（验证入口） | ✅ 已运行 | PASS（Correct operation validated, 65915.63 it/s） |
| `make check` | 源码完整性（md5sum -c coremark.md5） | 上游发行物缺 coremark.md5 | 否（非用户用例，发行缺失） | ❌ 不可运行 | 上游发行物缺失（官方 tag 不含 coremark.md5）；非适配缺陷 |
| tests/ 目录 | 不存在 | — | — | — | 无测试目录 |
| ctest/GTest 注册 | 不存在 | — | — | — | 无测试框架注册 |

统计口径：
- source_declared_total（源码中可枚举验证入口）: 3（run1/run2/run3.log）
- configured_executable_total（当前配置实际实例化）: 1（coremark.exe，三种运行参数）
- executed_passed_total: 3/3（100%）
- 未运行/未实例化: 0
- `make check` 归入"上游发行物缺失"，不计入独立用例分母（非框架注册的用户用例），已在台账列明原因

## 依赖版本

- 系统依赖: 无第三方库依赖（仅标准 C + librt，linux64 移植层）
- W0 依赖发布检查: coremark 无 conan requires 依赖，无预发布检查项

## 验证结果

```bash
# run1.log（性能运行）
CoreMark 1.0 : 15551.293349 / ... -O2 -DITERATIONS=1000 -DPERFORMANCE_RUN=1 -lrt / Heap
Correct operation validated.
# run2.log（验证运行）
Iterations/Sec : 15344.483658
Correct operation validated.
# run3.log（profile 运行）
Iterations/Sec : 65915.627996
Correct operation validated.
```

## 注意事项

1. coremark 是基准测试程序（CLI，非库），产物 `coremark.exe` 需按 R38 配套 `commands.json`。
2. `make check` 依赖上游发行物 coremark.md5，官方 GitHub tag 不含该文件，属上游固定行为。
3. 编译需 `PORT_DIR` 显式指定与 `-DITERATIONS`（默认 0 表示自动迭代）。
---

**编译结束**: 2026-09-20 23:33
**最终状态**: built
