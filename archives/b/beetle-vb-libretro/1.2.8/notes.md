# beetle-vb-libretro 1.2.8 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure；libretro 核心插件库）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（OHOS aarch64 profile）
- 状态: built

## 编译步骤

```bash
# 官方源码固定于 master HEAD 提交 83ed42608601fb7b01d41e4f8fb2007a37b8c84e
# 上游仓库无 release tag（GitHub 确认 "There aren't any releases here"），
# 版本 1.2.8 由分析端指定，源码固定该提交以可复现。
make CC=clang CXX=clang++ -j1   # 在源码目录执行，产出 mednafen_vb_libretro.so
```

产物：`mednafen_vb_libretro.so`（64-bit LSB arm64 共享库，导出 25 个 `retro_*` 公开符号）。

## 上游测试完整枚举台账（双口径）

枚举范围：官方 tag 固定提交的完整源码树（`.orig` 基线），覆盖用户测试源、
框架头/源码、样例、基准、fixture、测试脚本和构建目标。

| 枚举项 | 结果 | 证据 |
|--------|------|------|
| tests/ 等测试目录 | 无 | `find . -iname "*test*"` 仅命中 `mednafen/hw_cpu/v810/fpu-new/softfloat-specialize.h`（普通头文件，非测试） |
| Makefile check/test 目标 | 无 | 目标仅 `all/clean/install/uninstall` |
| ctest / meson test / GTest 注册 | 无 | 全树无 `add_test`/`TEST_CASE`/`ctest`/`doctest`/`catch2`/`gtest` 命中 |
| 测试脚本（sh/py/pl） | 无 | 全树无脚本文件 |
| 样例/基准/fixture | 无 | 全树仅 43 h + 10 c + 3 cpp + 4 inc + 2 yml + 2 mk 源文件 |
| libretro-common 测试目录 | 无 | 仅 compat/ 与 include/ |

结论：上游**无独立测试套件**。该库是 libretro 模拟器核心（插件 .so），
由前端（RetroArch 等）dlopen 消费，上游不提供 check/test 入口。

双口径统计：

- `source_declared_total` = 0（官方固定提交源码中按可复制枚举规则未发现任何独立上游测试声明）
- `configured_executable_total` = 0（当前 OHOS 配置实例化的独立可执行用例数）
- `executed_passed_total` = 0，失败数 = 0，未运行/未实例化数 = 0
- 通过率口径：`0/0`（无上游用例可运行；不存在未实例化项）
- 逐项映射：无「源码声明/宏或注册项 → 预处理/构建条件 → 构建目标 → 注册项 → 执行日志」链（无声明项）

说明：上游测试存在性已按 R51 三步法清点；「上游确无测试」附上述枚举证据。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时（`<urlopen error [Errno 110] Operation timed out>`） | 本机无法直连 github.com | 经 gh-proxy.com 镜像下载官方提交归档；conandata.yml 保留官方 URL，CI/E017 自动注入 ghfast.top 镜像 |
| 2 | 上游无 release tag | 仓库无 Releases/Tags | 固定 master HEAD 提交 `83ed42608601fb7b01d41e4f8fb2007a37b8c84e`，sha256=02630caca19b3e5ba4a1132c78cca7c2ac7238169f7014d8f345b86540ce4fc7 |
| 3 | conan-verify G2 首次失败：`Package type is 'library', but no 'shared' option declared` | package_type=library 必须声明 shared 选项 | 补 `options = {"shared": [True, False]}`，default True |
| 4 | conan-verify G2 二次失败：`make: *** No targets specified and no makefile found` | basic_layout 使构建目录在 build-release，Makefile 在源码目录 | `self.run(..., cwd=self.source_folder)` 在源码目录执行 make |

## 源码修改

无补丁（上游源码零修改，纯 Makefile 构建直接成功）。

## 依赖版本

无第三方 Conan 依赖（requirements 为空）；仅依赖系统 libc/工具链（clang 15 / llvm-ar / make）。

## 验证结果

```bash
# 本地原生编译（工作区）
make -j4  → exit 0，产物 mednafen_vb_libretro.so (arm64, 182720 bytes)

# conan-verify 全门禁（OHOS aarch64 profile）
python3 scripts/ohc-run.py conan-verify beetle-vb-libretro 1.2.8
→ G1/G2/G3/G4 + L2/L4/L5 全 PASS，exit 0

# 消费者验证（test_package，dlopen 核心调用 retro_* 公开 ABI）
./test_beetle-vb-libretro <mednafen_vb_libretro.so>
→ consumer ok: library_name=Beetle VB library_version=v1.31.0 valid_extensions=vb|vboy|bin retro_api_version=1
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Makefile 构建配方（library，shared 插件） |
| conandata.yml | 官方提交归档 URL + sha256 |
| test_package/ | 消费者 dlopen 测试（retro_api_version/retro_get_system_info 断言） |
| reports/conan-verify-report.md | G1-G4 + L2/L4/L5 验证报告 |

## 注意事项

- 该库为 libretro 核心插件（非 CLI）：无 commands.json（R38 仅 tool 类型需要）。
- 上游无独立测试套件；消费者可用性验证由 test_package dlopen 测试承担（见上）。
- 版本 1.2.8 为分析端指定；源码固定提交以避免分支漂移（无 tag 可钉）。
---

**编译结束**: 2026-09-25 07:01
**最终状态**: built
