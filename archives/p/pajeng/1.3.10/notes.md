# pajeng 1.3.10 适配笔记

## 编译环境
- 构建系统: cmake（>=3.20，CI/设备 cmake 4.1.2）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，profile ohos-aarch64）
- 状态: built（conan-verify 全门禁通过）

## 编译步骤

conan create 全自动流程（-pr:h/-pr:b ohos-aarch64，--build=missing）：

1. source()：官方 tarball（sha256 校验）
2. generate()：CMakeDeps + CMakeToolchain；FL_LIBRARY 预置 flex 包内 libfl.a 绝对路径；记录 bison 包 share/bison 数据目录
3. build()：cmake.configure（PAJE_LIBRARY=ON, PAJE_TOOLS=ON, PAJE_DOC=OFF, PAJE_USE_FMT=ON, STATIC_LINKING=OFF）→ cmake.build（flex/bison 生成 scanner/parser）→ BISON_PKGDATADIR 环境注入 → 构建树补 libpaje.so.2 符号链接 → 拷贝 traces 到构建目录上一级 → LD_LIBRARY_PATH shell 前缀注入后 ctest（上游测试）
4. test_package：消费者程序链接 pajeng::pajeng，断言 PajeColor API + 运行包内 pj_dump

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | FIND_PACKAGE(FMT 5.0.0) 拒绝 conan fmt 11.1.3 | config-mode 版本文件按 SameMajorVersion 语义判定，上游写法只适配 module-mode | 补丁放宽为无版本 REQUIRED（配方钉版 fmt/11.1.3） |
| 2 | bison 报 /share/bison/m4sugar/m4sugar.m4 cannot open | conan bison 包数据目录不在默认前缀 | build() 内按包路径注入 BISON_PKGDATADIR |
| 3 | PajeTraceEvent.cc/PajeEntity.cc 无条件包含 boost/spirit/qi.hpp | 上游默认环境预装 boost，qi 解析路径与 PAJE_USE_FMT 无关 | 补丁加 FIND_PACKAGE(boost CONFIG) + boost::boost 链接（boost/1.85.0） |
| 4 | pj_dump.cc/pj_equals.cc 无条件包含 argp.h | OHOS musl 无 argp | 补丁接 argp-standalone::argp-standalone（1.4.1 提供头+库） |
| 5 | FL_LIBRARY NOTFOUND | CMake FindFLEX 的内部缓存变量与 tool_requires 的 libdir 不通 | CMakeToolchain 预置 FL_LIBRARY=flex 包内 libfl.a 绝对路径 |
| 6 | 工具运行报 Error loading shared library ../libpaje/libpaje.so | OHOS 交叉平台 CMake 不判定 soname 支持，DT_NEEDED 退化为链接期相对路径 | 补丁显式 -Wl,-soname,libpaje.so.2；构建树/包内补 libpaje.so.2 符号链接；运行期 LD_LIBRARY_PATH 指向库目录 |
| 7 | ctest 12 套件全挂（加载不到 libpaje.so.2） | conanbuild env 覆盖进程级 LD_LIBRARY_PATH | 改 shell 前缀式注入（LD_LIBRARY_PATH="..." ctest），贯通 ctest→perl tesh→pj_dump |
| 8 | tesh 报 Could not open ../traces/*.trace | tesh 的 --cd 为 CMAKE_BINARY_DIR，traces 需在其上一级 | 拷贝上游 traces 到构建目录的上一级（build/traces） |

## 上游测试五维账本（诚实口径）

- `N_static = 50`：tests/*.tesh 共 12 个套件、50 条命令级断言（1+1+1+2+1+1+28+7+2+2+2+2），经 src/tools/CMakeLists.txt 的 ADD_TESH/ADD_TEST 全部注册为 CTest 测试
- `N_registered = 12`（CTest 套件数，承载上述 50 条命令）
- `N_executed = 12/12 套件全过` ⇒ tesh 命令级 50/50（tesh 任一命令失败即整套 NOK，0 NOK = 0 失败）
- 未执行 = 0；失败 = 0；跳过 = 0
- `N_consumer = 1`（test_pajeng）：链接 libpaje 断言 PajeColor 公开 API 字段 + 运行包内 pj_dump 解析随包 containers.trace 断言退出码与 Container 输出行

测试命令（build() 内真实执行）：`LD_LIBRARY_PATH=<构建树库路径> ctest -V --output-on-failure`
日志汇总：`100% tests passed, 0 tests failed out of 12`（build/Release/ctest.log）

## 源码修改（补丁）

- `patches/0001-src-libpaje-CMakeLists.txt.patch`：①paje_library 显式 soname；②放宽 FMT 版本请求；③补 boost find/链接
- `patches/0002-src-tools-CMakeLists.txt.patch`：④补 argp-standalone find 并给 pj_dump/pj_equals 链接
- 均为构建接线适配，无测试修改、无平台宏

## 依赖版本

- fmt/11.1.3（格式化输出，PAJE_USE_FMT=ON）
- boost/1.85.0（spirit qi 解析，头文件使用）
- argp-standalone/1.4.1（工具参数解析）
- 工具依赖：flex/2.6.4、bison/3.8.2（scanner/parser 生成）

## 验证结果

```bash
ohc-run.py conan-verify pajeng 1.3.10   # G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS
ohc-run.py finish pajeng 1.3.10 built   # W3 本地 CI 模拟通过，.ci-result.json exit_code=0
```

## 路径 A/B 判断

- 路径 A 主体如上。
- 路径 B 判断：不成立。候选主题「CMake 交叉平台 SONAME 缺失 → DT_NEEDED 相对路径退化」——现有知识库 E 系列未见同类条目，但该问题属单构建系统接线类，复用面窄（需同时满足 CMake+OHOS 交叉+共享库+CTest 四条件），不足以支撑跨仓库知识条目；其余均为单库特性（tesh 目录布局、bison 数据目录）。按纯路径 A 交付，此判断留痕。

## 对话记录

- 2026-09-18 01:46 GLM-54 relay 领坑（pajeng 1.3.10，任务 9283，主赛 409 后走小号中转）；建 worktree feat/pajeng-1.3.10
- 01:5x W0（fmt/flex/bison 已发布核验）、init-build、lang-preflight cpp
- 02:1x-04:3x 配方编写与迭代 16 轮 conan-verify（问题 1-8 依次定位修复）
- 04:3x conan-verify 全 PASS

---
**编译结束**: 2026-09-18 04:40
**最终状态**: built
---

**编译结束**: 2026-09-18 04:50
**最终状态**: built
