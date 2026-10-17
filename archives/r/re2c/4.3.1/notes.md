# re2c 4.3.1 编译进度

**日期**: 2026-08-08
**状态**: ✅ 已完成 (built)

## 基本信息
- 软件: re2c
- 版本: 4.3.1
- 构建系统: CMake (项目同时支持 autotools, 但 autotools 在 OHOS 上有 config.status 权限问题)
- 目标: ohos-aarch64
- 上游源码: https://github.com/skvadrik/re2c/releases/download/4.3.1/re2c-4.3.1.tar.xz

## 编译步骤

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 源码下载、解压、环境检查 |
| Step 2 configure | ✅ | CMake 配置成功 (HarmonyOS 平台警告为非致命) |
| Step 3 make | ✅ | 12 个可执行文件 + 5 个测试工具编译成功 |
| Step 4 install | ✅ | 24 个文件安装到 staging 目录 |
| Step 5 verify | ✅ | re2c --version 返回 4.3.1 |
| Step 6 conan-init | ✅ | 生成 conanfile.py + conandata.yml + test_package/ |
| Step 7 conan-verify | ✅ | G1/G0/G2/G3/G4 全部通过 |
| Step 8 finish | ✅ | W3 本地 CI 模拟通过 |
| Step 9 submit | 🔄 | 提交 PR |

## 发现与知识

### 构建系统选择
re2c 同时支持 autotools 和 CMake。在 OHOS 平台上:
- Autotools: config.guess/config.sub 需要打补丁识别 HarmonyOS (E007/E072); config.status 创建临时子目录时遇到权限问题
- CMake: Conan CMakeToolchain 自动适配 OHOS 平台, 无需额外补丁

选择 CMake 作为构建系统, 同时保留 autotools 补丁 (config.guess/config.sub) 供未来 autotools 用户使用。

### 补丁说明
- 0001-build-aux-config.guess.patch: 添加 HarmonyOS 系统识别
- 0002-build-aux-config.sub.patch: 添加 linux-ohos 三元组验证

### 上游测试套件限制
re2c 的 `run_tests.py` 测试套件在 OHOS 上因 Python `posix_spawn` 无法找到 `chmod` 命令而无法运行。这是 Python 平台限制, 非 re2c 问题。conan test_package 通过自定义测试验证了 re2c 功能。

### 续跑记录 (2026-09-17, 第 2 次尝试)
- CI 失败根因: 远端 CI worker 应用 PR diff 时失败 ("No packages to build" — conanfile.py 未落地), 属 worker 侧 patch 应用/下载闪失败; main 分支从未修改过 re2c 文件, 本地 `git apply` + toybox `patch -p1` 干跑均验证 diff 可干净应用。
- 修复动作: merge origin/main (2026-09-17, 8f1ebb5b4f) 刷新 PR diff; .gitignore 冲突取 main 侧 (消除重复条目噪音)。
- 本地复验: `conan create` (ohos-aarch64 profile) 通过; `CI_PACKAGES="archives/r/re2c/4.3.1" zsh ci/conan/build_and_test.sh` 完整本地 CI 复现通过 (L0/L1/L1e/L2/L5 全绿, 12 个 re2c* 二进制冒烟通过)。
- 检视闭环: 2 条 High (YYCURSOR const) 已修复并 resolved; P2 (config.guess __OHOS__) 属 R8 豁免的 LIBC 探针场景, 已在讨论串回复 + PR 描述补充例外申报。

---

**编译结束**: 2026-08-08
**最终状态**: built
