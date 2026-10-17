# dmc_unrar 1.8.0 适配笔记

## 编译环境
- 构建系统: custom（stb 风格单文件 C 库，上游无 configure/make/CMake/meson）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK /data/service/hnp/bin)
- 状态: built（conan-verify 全部门禁通过，可标 published）

## 编译步骤
1. `git worktree add -b feat/dmc_unrar-1.8.0`（稀疏检出规避 HMDFS inode 耗尽，见问题表）
2. 官方源核验：tag v1.8.0，tarball SHA-256 `9800526d85f0ec03a345879b0d4ca3f1e87169ddb8be518b858b31faf60ab7ae`
   （两次独立下载一致，确定性产物；github.com 主站超时，经 codeload 官方归档 CDN 获取）
3. W0 依赖预检：`bash ci/scripts/preflight_check.sh dmc_unrar/1.8.0` → 通过（无依赖声明，首次适配正常）
4. lang-preflight（R47）：detected=c，task=cpp，c↔cpp 兼容族 → 通过
5. Step 2 手工编译：`clang -c dmc_unrar.c -O2` + `ar rcs libdmc_unrar.a` → 通过，零源码修改
6. 功能验证：example 程序对真实 RAR5 样例（rarfile 测试套件 rar5-crc.rar）list/extract 均成功，
   2 个 2048 字节文件解压字节数精确一致
7. conan-init 生成配方 → 重写为单文件库直编配方（生成模板是 autotools 型，不适用）
8. conan-verify：G0-G4 + L2/L4/L5 全部门禁 PASS，test_package 消费者测试 1/1 通过

## 上游测试申报表（R51 三步法：清点 → 运行 → 回填）

上游 tag v1.8.0 完整清单（tar tzf 枚举结果）：
```
dmc_unrar-1.8.0/COPYING
dmc_unrar-1.8.0/README.md
dmc_unrar-1.8.0/dmc_unrar.c
dmc_unrar-1.8.0/example.c
```

台账（覆盖用户测试源/框架头/样例/基准/fixture/脚本/构建目标，逐项分类）：

| 类别 | 条目 | 是否独立上游用例 | 实际运行 | 结果/原因 |
|------|------|-----------------|----------|-----------|
| 用户测试源 | （无 tests/ 目录，无 *test*.c 文件） | 否 | - | 上游无任何测试源文件 |
| 框架头/源码 | （无） | 否 | - | 无测试框架 |
| 样例 | example.c | 否（使用示例，非测试用例） | 是 | list/extract 真实 RAR5 成功（见验证结果节） |
| 基准 | （无） | 否 | - | 无 |
| fixture | （无，上游不含样例 RAR） | 否 | - | 适配过程自行引入 rarfile 测试夹具（BSD-3-Clause） |
| 测试脚本 | （无） | 否 | - | 无 make check / ctest / meson test 入口 |
| 构建目标 | （无，无构建系统） | 否 | - | tar 包无 configure/CMakeLists/Makefile/meson.build |

枚举命令与证据（原始日志见 $HOME/oh-logs/dmc_unrar-r01/upstream-enum.log）：
- `tar tzf dmc_unrar-1.8.0.tar.gz`：仅 4 个文件，无 tests/
- grep test/CTestTestfile/Makefile/CMakeLists/meson/configure：无任何命中
- 源码 grep TEST_CASE/TEST(/doctest/catch/UnitTest：无框架注册

**双口径统计**：
- `source_declared_total` = **0**（官方 tag 源码中无可复制枚举的测试声明）
- `configured_executable_total` = **0**（无测试入口可实例化）
- `executed_passed_total` = **0**（上游无测试可运行）
- 全量通过率：0/0 —— 上游确无测试套件，此结论附上述清点证据（R51）
- 本库自增测试不计入上游口径：test_package 消费者用例 1 个（1/1 通过，见下节）、
  HarmonyOS 专项消费者用例 1 个（真实 RAR 解压验证）
- 说明：example.c 为上游使用示例而非测试注册项，未误计入上游用例（台账已标注）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 完整 worktree 检出失败 "No space left on device" | HMDFS 文件系统 inode 耗尽（48.45M inodes 100%，并发执行端共享），77,768 文件全量检出超出剩余配额 | 稀疏检出（sparse-checkout cone 模式 12 个顶层目录，6,663 文件），释放自身残留后收敛成功；inode 恢复至可用水平 |
| 2 | github.com 主站下载超时（urllib/curl 均 000） | 网络环境对 github.com 主站不可达；codeload/api/jsdelivr 均可达 | 经官方 codeload 归档 CDN 获取 tarball；conan 侧预置源下载缓存（sha256 键控）+ E017 ghfast.top 镜像注入 |
| 3 | conan-init 生成 autotools 模板 | 生成器按 URL 猜测 build_system=autotools，实际上游无构建系统 | 重写 conanfile.py 为单文件 C 库直编配方（conf 取编译器，R33） |
| 4 | conan create G2 失败 "no such file or directory: 'dmc_unrar.c'" | basic_layout 下 source_folder=build/src，build() 须用绝对路径 | build() 改用 os.path.join(self.source_folder, ...) |
| 5 | make jobserver mkfifo "Operation not permitted" | HMDFS 不支持 fifo（/storage/.../tmp/GMfifo*） | 非致命（cmake 并发降级），构建照常完成 |

## 源码修改

无（上游零修改；无补丁，patches/ 为空）

## 依赖版本

无第三方依赖（dependency-free 单文件库）；开发依赖：conan 2.29.1、clang 15.0.4 OHOS SDK

## 验证结果

```bash
# 1) OHOS 工具链直编（Step 2）
clang -c dmc_unrar.c -O2 -o dmc_unrar.o        # rc=0
ar rcs libdmc_unrar.a dmc_unrar.o              # rc=0

# 2) 功能验证（真实 RAR5 样例，codeload/json deliver 下载）
./example l rar5-crc.rar
# 1/2: "stest1.txt" - 2048 bytes
# 2/2: "stest2.txt" - 2048 bytes                rc=0
./example e rar5-crc.rar                        # 解压后 stest1/stest2.txt 各 2048 字节 rc=0

# 3) conan-verify（G0-G4, L2/L4/L5 全 PASS；test_package 消费者用例 1/1 Passed）
python3 scripts/ohc-run.py conan-verify dmc_unrar 1.8.0   # rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/d/dmc_unrar/1.8.0/conanfile.py | 单文件 C 库直编配方（静态库 libdmc_unrar.a + 头文件 + 包装头） |
| archives/d/dmc_unrar/1.8.0/conandata.yml | 官方源 URL + SHA-256 |
| archives/d/dmc_unrar/1.8.0/test_package/ | 消费者验证（test.c 内嵌 RAR5 夹具，真实 API 调用+解压校验） |
| archives/d/dmc_unrar/1.8.0/reports/ | conan-verify 报告 + conan-create 日志 |

## 注意事项

- 库类型（无 CLI），无 commands.json（R38 不适用）
- licenses: GPL-2.0-or-later（上游 README 声明）
- 消费者用法两种：`#include <dmc_unrar.h>` + 链 libdmc_unrar，或上游 stb 风格 `#include "dmc_unrar.c"`
- 夹具 rar5-crc.rar 来自 rarfile 测试套件（BSD-3-Clause），仅作验证用途
---

**编译结束**: 2026-09-21 16:12
**最终状态**: built
