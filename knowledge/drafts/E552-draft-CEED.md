# E552: meson+wrap 网络拉取型上游测试的直编执行方案

## 基本信息
- **严重度**: 2
- **类别**: build-system, testing, network, portability
- **作者**: wanderlust_0823
- **来源 PR**: 8557
- **来源提交**: b94f7ed（svector 1.4.0）

## 错误特征
```
Dependency "doctest" not found|Dependency "fmt" not found|Subproject .* does not exist and cannot be downloaded|Failed to download|subprojects/[a-z]+\.wrap
```

## 根因分析
上游测试套件由 meson 驱动，测试依赖（doctest、fmt 等）经 `subprojects/*.wrap`
在 meson 配置期从网络拉取。离线或网络受限的 CI/设备无法完成 wrap 下载，
`meson test` 整体不可执行，容易被误判为"上游无法测试"而放弃上游用例执行
（R51 违规的常见根源）。

## 推荐方案
**方法**: direct-compile-upstream-tests（免 meson 直编）

**说明**: 用与 wrap 锁定版本一致的官方依赖 tarball 头文件，加上游自带辅助
TU，逐翻译单元直接编译并运行上游测试，完全绕开 meson 与网络拉取；不修改
上游任何测试源码。

**验证/命令**:
```
# svector 1.4.0 实证（wrap 锁定 doctest 2.5.3 / fmt 11.2.0）
clang++ -std=c++17 -DDOCTEST_CONFIG_IMPLEMENT_WITH_MAIN \
    -I include -I <doctest-2.5.3解包>/doctest -I <fmt-11.2.0解包>/include \
    -I test test/unit/<TU>.cpp \
    Counter.o fmt_format.o fmt_os.o api.o -o t.bin && ./t.bin
# 30/30 TU 全部编译运行，doctest 全部 SUCCESS（133/133 用例）
```

### 关键路径细节（svector 实证）
- doctest 2.5.3 tarball 的头在 `<解包>/doctest/doctest.h`（无 include/ 前缀），
  而测试源码写 `#include <doctest.h>` —— `-I` 要指到 doctest 目录本身
- fmt 11 的 `fmt::v11::vprint` 符号不在 format.cc（print 类符号在 print.cc），
  直接预编译 format.cc + os.cc 目标文件即可满足大部分 TU
- 测试引用 `<app/Counter.h>` 等辅助头需 `-I test`，并预编译链接对应辅助 TU
  （test/app/Counter.cpp、test/fuzz/api.cpp、test/app/ui/*.cpp）
- 断言统计用每个 TU 的 doctest 汇总行（Status: SUCCESS）逐项留证

### 边界/反例/风险
- 适用于：header-only 测试依赖（doctest/gtest/catch2 系）或可独立编译的
  wrap 依赖；上游测试不依赖 meson 代码生成
- 反例：测试需要 meson configure 时生成的代码（如 config.h 模板）时，直编
  需要补齐等价生成物，复杂度上升需评估
- 风险：直编使用的依赖版本必须与 wrap 锁定版本一致，否则统计口径与上游
  官方结果不可比；禁止修改上游测试源码来迁就直编

### 回退方案
`tool_requires("meson/1.11.0")` + MesonToolchain/Meson 助手在 CI 内走原生
meson test（c-list 3.1.0 先例），要求制品仓已发布 meson 包且 CI 可达 wrap 源。

## 关键词
meson, wrap, subprojects, doctest, fmt, upstream test, direct compile,
DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN, network fetch, per-TU

---
*由 svector 1.4.0 适配实战沉淀（2026-09-06，PR 8557）*
