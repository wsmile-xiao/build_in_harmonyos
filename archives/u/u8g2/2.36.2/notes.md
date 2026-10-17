# u8g2 2.36.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-08
- 编译器: clang/clang++ 15.0.4
- 状态: built（conan-verify G0-G4 全部 PASS，本地验证通过；制品发布以 CI release 为准）

## 编译步骤

```bash
# init-build 下载官方 tag 2.36.2 源码
python3 scripts/ohc-run.py init-build u8g2 2.36.2 --auto --url=https://github.com/olikraus/u8g2/archive/refs/tags/2.36.2.tar.gz
# lang-preflight 语言预检: detected=cpp, 568 源文件 (c:503, cpp:64, bash:19, lua:1), 主体占比 89%
python3 scripts/ohc-run.py lang-preflight u8g2 2.36.2 --src $BUILD_SRC_DIR
# conan-init 生成配方后修正为 CMake 模板（上游为 CMake 项目，非 autotools）
python3 scripts/ohc-run.py conan-init u8g2 2.36.2
# conan-verify 验证（G0-G4 全部 PASS）
python3 scripts/ohc-run.py conan-verify u8g2 2.36.2
```

上游 CMakeLists.txt 将 csrc/*.c glob 编译为 libu8g2，头文件安装到 `include/u8g2/`，并导出
CMake package config（`lib/cmake/u8g2/u8g2-config.cmake`）。配方设置 `BUILD_SHARED_LIBS=OFF`（R26 静态）。

## 上游测试清点（R51 申报表）

| 项目 | 结果 |
|------|------|
| tests/ 或 test/ 目录 | 无 |
| ctest 注册（add_test/enable_testing） | 无（CMakeLists.txt 无任何测试注册） |
| make check / Makefile 测试目标 | 无（上游无 Makefile） |
| pytest 等其他测试框架 | 无 |
| tools/ 目录 | 开发工具（font/ugl/maze 等），非测试套件 |
| sys/ 目录 | 14 个平台示例（arduino/arm/avr 等），非自动化测试 |

结论：u8g2 为嵌入式单色图形库，上游**无自动化测试套件**（无 ctest/无 test 目录/无 make check）。
按 R51 如实清点，不做任何伪造申报。

## 验证结果（test_package，消费者视角）

```bash
1/1 Test #1: test_u8g2 ........................   Passed    0.10 sec
100% tests passed, 0 tests failed out of 1
```

test.c 实质调用 u8g2 API：`u8g2_Setup_null` + `u8g2_InitDisplay` + `u8g2_ClearBuffer` +
`u8g2_DrawStr` + `u8g2_SendBuffer` + `FirstPage/NextPage` 帧循环，非空壳测试（R34）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build `_create_dual_track` 复制失败 | 上游 tarball 自带失效符号链接 `sys/arm-linux/drivers -> ./c-periphery/src`（链接目标不在包内），copytree 跟随链接失败 | 删除不完整 `.work`，用 `cp -a`（保留符号链接）重建 `.work` 后重跑 init-build |
| 2 | conan-init 生成 autotools 模板 | 模板自动识别偏差，u8g2 实为 CMake 项目 | 改写 conanfile.py 为 CMake 模板（CMakeToolchain + CMake） |
| 3 | conan-verify G2: test.c 找不到 u8g2.h | 上游头文件安装到 `include/u8g2/` 子目录 | test.c 改为 `#include "u8g2/u8g2.h"`（与上游 CMake 导出目标的 INSTALL_INTERFACE=include 一致） |

## 源码修改

无补丁（patches/ 为空）。未修改上游源码。

## 依赖版本

无第三方依赖（u8g2 为纯 C 库，W0 预检通过）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 模板配方（静态库，R26） |
| conandata.yml | 官方源 URL + sha256（aaeff28ff2d341bcef1cb9bc6a1ca390d31b29f3dfc147c43e3088cc355b3096） |
| test_package/ | 消费者测试（1/1 通过） |
| MANIFEST.yml | 测试声明（上游无自动化测试，如实申报） |

## 注意事项

- 上游 tag 2.36.2 已核验（commit f2e188003eb39d31ca87c46af16a0eaaaedce161）
- 头文件在 `include/u8g2/` 子目录，消费者需 `#include "u8g2/u8g2.h"`

## 知识路径判定（executor_local，快照查重）

知识快照: `/storage/Users/currentUser/tianyi/.ohc-knowledge-snapshots/u8g2-2.36.2-r01-pc2-9-20260908T131419Z`
（repo: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git, ref: main,
HEAD: 7285d042840352f4caa18ccf5f3a3ebc443e60c8, sparse: knowledge, read-only）

扫描范围: 正式 `knowledge/graph/E*.kv`（542 条）+ `knowledge/doc/E*.md` +
`knowledge/drafts/*.{md,kv}`（659 条），根目录无 DRAFT-* 配对。

| 候选经验 | error signature | 查重结果 | 判定 |
|----------|----------------|----------|------|
| test_package G2 找不到 u8g2.h（上游 CMake 装头到 include/u8g2 子目录） | `fatal error: 'u8g2.h' file not found` | **等价命中 E217**（check-cmake-header-install-subdir，error_signature/root_cause/trigger_tool 逐字段一致；本次实现：test_package 按上游导出接口 `#include "u8g2/u8g2.h"`） | reuse_existing → 路径 A |
| init-build _create_dual_track 失效符号链接 copytree 失败 | `shutil.Error: Operation not permitted / No such file or directory` | E255(E018/E073/E037 均不匹配)；属 init-build 框架脚本行为 + 上游 tarball 数据特性，非库适配知识；草稿 DRAFT-gnustep-gui-0.31.1-hmdfs-copyfile-symlink 为 HMDFS copyfile 不同场景 | 不沉淀（共享框架/工具行为） |
| conan-init 误识别为 autotools 而实为 CMake | 模板构建系统偏差 | 无等价；conan-init 构建系统识别属工具行为 | 不沉淀（共享框架/工具行为） |

**knowledge_decision: reuse_existing（E217），路径 A**，无新增草稿，不创建 DRAFT。
基线知识条目 E219/E253/E305 root_cause 为空为知识图谱历史存量，非本库引入，未改动。
---

**编译结束**: 2026-09-08 21:47
**最终状态**: built
