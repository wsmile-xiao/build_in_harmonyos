# 【积分赛】feat(cado): 0.9.6 适配 HarmonyOS PC

## PR 信息
- **三方库名称**：cado（不含版本号）
- **上游版本**：0.9.6
- **上游仓库地址**：https://github.com/rd235/cado
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

> 源码包 URL（conandata.yml）: https://github.com/rd235/cado/archive/refs/tags/v0.9.6.tar.gz （SHA-256 见 conandata.yml：35195ac4c7634b397a8d68325aac5d63a501ce507fc6406ada99a292c07dc8ef）

## 软件描述

CADO（Capability Ambient DO）是「能力授权」工具：让普通用户以受限的 Linux capabilities 环境执行命令，支持 scado 预授权机制，可作 sudo 的轻量替代（Unix 安全工具链 capsh 体系重要一环）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无测试（rule4 清点证据见「上游测试清点」节：顶层 CMakeLists.txt 仅 `add_subdirectory(man/src)` + uninstall 目标，src/CMakeLists.txt 仅 4 个可执行目标，无 tests/ 目录、无 make check/ctest/meson test） |
| 集成测试 | 0 | 上游无集成测试 |
| 其他测试 | 0 | 上游无任何测试框架/脚本 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无 |
| 集成测试 | 0 | 不变 | 上游无 |
| **鸿蒙特有测试** | **8** | 新增 | test_package 消费者级验证（rule12）：cado/cadrop/scado/caprint 4 二进制 × 存在性+输出断言 = 8 断言点（cado/caprint 校验 usage 帮助、cadrop 校验非法参数 parsing capabilities 分支、scado 校验运行时 UID/passwd 检查分支非空输出） |
| **合计** | **8** | **+8** | |

## 上游测试清点（rule4：N=0 实测证据）

上游 cado v0.9.6 源码树无任何测试设施（实测清点）：

- 顶层 `CMakeLists.txt`：仅 `include(GNUInstallDirs)` + `find_library` 依赖探测 + `add_subdirectory(man)` + `add_subdirectory(src)` + `add_custom_target(uninstall)`，**无 `enable_testing()`/`add_test()`/`make check` 目标**；
- `src/CMakeLists.txt`：仅 4 个可执行目标（cado/cadrop/scado/caprint）+ install 规则，**无任何测试目标**；
- 源码树无 `tests/`、`test/` 目录，无测试框架/测试脚本。

结论：上游测试注册数 N=0，适配后按 rule8 补全消费者级鸿蒙特有测试（下节）。

## 上游测试用例修改说明
- [x] **否**，未修改上游任何测试用例（上游无测试用例可修改）
- [ ] **是**，存在对上游测试用例的修改（逐条：文件路径+修改原因+修改内容）

## 补全测试用例说明
- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试
  - **补全的测试范围**：test_package 消费者级鸿蒙特有测试 8 断言点（rule12/rule8）
  - **补全原因**：上游 cado 为纯 C CLI 应用，无测试基础设施；需在 HarmonyOS PC 目标平台验证 4 个交付二进制的可执行性与关键分支行为
  - **新增测试文件清单**：
    1. `test_package/conanfile.py` — 4 二进制存在性 + 差异化输出断言（cado/caprint usage、cadrop parsing capabilities、scado 运行时检查分支），8 断言点
    2. `test_package/probe.sh` — 独立可运行的二进制冒烟脚本（与 conanfile.py test() 断言一致，供本地/CI 直接调用）
    3. `test_package/MANIFEST.yml` — 测试清单（assertion_count=8，与 PR 正文口径一致）

## 验证结果
- 编译状态：通过（`conan create archives/c/cado/0.9.6 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` → RC=0，Package created；4 个可执行文件 cado/cadrop/scado/caprint 产出）
- 上游测试用例通过率：0/0（上游无测试，rule4 清点 N=0）
- 新增测试用例通过率：8/8（100%）

### 编译验证
- 编译器: clang（OHOS SDK 26.0.0.18, aarch64-linux-ohos）
- 构建系统: CMake（bare cmake，上游 cmake_minimum_required 3.13；CMakeToolchain 设 `CMAKE_POLICY_DEFAULT_CMP0077=NEW`）
- 配置选项: `-DCMAKE_INSTALL_LIBDIR=lib`

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | cado/cadrop/scado/caprint 4 个可执行文件 |
| 产物存在性 | ✅ | conan create 验证（bin/ 完整） |
| ELF 格式 | ✅ | aarch64-linux-ohos |
| 运行测试 | ✅ | 新增消费者测试 8/8 通过 |

## 适配要点
- **依赖头文件目录注入**：cado 顶层 CMakeLists 用 `find_library` 定位依赖库（cap/execs/mhash/pam/pam_misc 均 FATAL_ERROR），但未把依赖 include 目录加入编译搜索路径，导致 `<sys/capability.h>`、`<security/pam_appl.h>`、`<mhash.h>`、`<execs.h>` 找不到。补丁 `0001-add-dep-include-dirs.patch` 增加 `find_path` + `include_directories` 注入 4 个依赖头文件目录。
- **依赖链完整性**：libexecs 为 cado 唯一在 ohpcd 缺失的硬依赖，已按 PF4 依赖闸单独适配（前置 PR #9175 已合入）。

## 补丁说明
- `patches/0001-add-dep-include-dirs.patch`：CMakeLists.txt 增补 4 个依赖头文件 `find_path` + `include_directories` 注入（依赖 include 目录未入编译搜索路径的修复，仅加依赖注入不改通用逻辑）

## 依赖
- libcap/2.73（已发布）
- linux-pam/1.7.2（已发布）
- mhash/0.9.9.9（已发布）
- libexecs/1.4（已发布，前置适配 PR #9175）

## 制品文件
- `archives/c/cado/0.9.6/conanfile.py`
- `archives/c/cado/0.9.6/conandata.yml`
- `archives/c/cado/0.9.6/manifest.yaml`
- `archives/c/cado/0.9.6/patches/0001-add-dep-include-dirs.patch`
- `archives/c/cado/0.9.6/test_package/`（conanfile.py + MANIFEST.yml + probe.sh）

## 补充说明
- 版本号策略：0.9.6 为上游正式版本号（tag v0.9.6 精确对应）
- 已知限制：scado 在无 passwd 条目环境下触发 UID/passwd 检查分支（沙箱实测输出 `Your UID isn't in the passwd file.`），属上游设计行为；cadrop 无 `-h`，以非法参数报错分支作为验证入口
