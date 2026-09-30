# libmdbx 0.14.4 适配笔记

## 基本信息

- 软件：libmdbx
- 版本：0.14.4
- 上游（任务声明官方源）：https://github.com/Mithril-mine/libmdbx
- 许可证：Apache-2.0
- 归档：`v0.14.4.tar.gz`
- SHA-256：`fb53f23ae6d9ed219b09792b1687b2f48598b95cfd12afb437d9d5e953052c21`
- 上游 VERSION.json：`v0.14.4-0-g716ce9d5`（2026-09-18）

## 适配决策

- 复用 0.14.3 已验证的 CMake 共享库构建策略，同时启用 C++ API；关闭上游工具、man page 和库内测试，避免把可执行文件/测试带入包产物。
- Conan 包名保持任务权威名 `libmdbx`；上游库文件/CMake 目标对应 `mdbx`，包目标导出为 `libmdbx::mdbx`。
- OHOS 的 CMake 系统名显式设为 `OHOS`，固定安装库目录 `lib`，匹配设备 CMake 平台模块与 Conan OHOS profile。
- 单个合并补丁 `0001-mdbx.c.patch` 承载两处 OHOS 语义修改（相对 0.14.3 的两个补丁按 0.14.4 源码重新生成，行号/上下文与 0.14.4 精确匹配）：
  1. `mdbx_env_create()` 中 Linux `uname()` 内核版本门槛（<3.16 拒绝）：HarmonyOS 兼容层报告 `1.12.0.0` 但实际提供目标 API，仅对 `__OHOS__` 跳过该门槛。
  2. `osal_fseek_shut()` 中约 4 TiB `lseek` 回退探测：HarmonyOS 对失败候选返回 `EINVAL`，上游把失败候选写回共享停车偏移导致后续锁文件 `lseek` 失败；只保留最后一次成功候选。
- OHOS 构建显式关闭 `MDBX_USE_FALLOCATE`：HMDFS 上 `posix_fallocate()` 返回 `EACCES`，`pwrite()`/`ftruncate()` 可用，让 `osal_fsetsize()` 走可用的截断扩展路径。
- 仅声明 `pthread` 系统库；额外原子库由设备链接结果决定，不预先硬编码。

## 上游测试边界

`v0.14.4` 发布归档是精简 amalgamated 源码包，不含完整上游测试目录；上游 `examples/` 提供 C 与 C++ API 示例（CTest 注册为 `c_api`/`c++_api`），作为上游用例入口。test_package 以消费者视角补充 C API、C++ API 与 OHOS 专项用例。

## 验证结果

- conan-verify（ohos-aarch64 profile，clang 15，Conan 2.29.1）全部门禁通过：G0/G1/G2(conan create)/G3(系统同名库隔离)/G4(产物完整)/L2/L4/L5。
- 补丁经 `refresh-patch --auto` 从 orig/work 差异精确生成，conan create 中 `apply_conandata_patches` 干净应用（无 hunk 偏移警告）。
- 纯库包，无 `bin/` 产物，不涉及 commands.json（R38 库类型豁免）。

## 尚未闭环

- W3 本地 CI 模拟已通过（.ci-result.json exit_code=0，L0/L1/L4/L5 全 pass）；W4 审计、远端 CI 与 Review 闭环待 submit 后推进。
---

**编译结束**: 2026-09-28 11:30
**最终状态**: built
