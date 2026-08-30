# foonathan-memory 0.7 适配笔记

## 编译环境
- 构建系统：CMake
- 编译日期：2026-08-29（HarmonyOS HongMeng Kernel 1.12.0，aarch64）
- 编译器：HNP clang/clang++ 15.0.4
- Conan：2.29.1，host/build 均使用 `ci/conan/profiles/ohos-aarch64`
- 状态：built（本地 W3 已通过；registry 发布状态受远端策略限制，未宣称 published）

## 编译步骤
源码来自官方 v0.7 tarball，SHA256 为
`01a7cc5a5ebddbd71bec69c89562a4a2ecd7c29334c0a29d38d83e7f7f66eb53`。

```bash
export PATH="/data/service/hnp/bin:$HOME/.local/bin:$HOME/.harmonybrew/bin:$PATH"
export DEFAULT_PREFIX="$HOME/usr/local"
export TMPDIR="$HOME/tmp"
PROFILE=/storage/Users/currentUser/ws/foonathan-memory-0.7/ci/conan/profiles/ohos-aarch64
conan create archives/f/foonathan-memory/0.7 \
  -pr:h="$PROFILE" -pr:b="$PROFILE"
```

配方通过 `CMakeToolchain` 设置 C++11、静态库、关闭 examples、打开 upstream tests/tools，并在 `build()` 中执行 `cmake.test()`。补丁通过 `apply_conandata_patches()` 应用。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报 `Could not set install folders for this platform!` | 上游只把 `UNIX`/`VXWORKS`/`WIN32` 作为安装平台，未识别 OHOS 系统名 | 扩展 CMake 平台判断，锚定匹配 `OHOS`、`HarmonyOS`、`OpenHarmony` |
| 2 | `heap_allocator`、`malloc_allocator`、`new_allocator` 对齐测试失败 | OHOS 小对象默认分配可能只有 8 字节对齐，而本机 `max_align_t` 为 16 字节 | POSIX hosted 路径使用 `posix_memalign`，请求大小为 0 时按 1 字节分配，并用 `free` 释放；Windows 保留原生分配路径 |
| 3 | 显式 `CMAKE_SYSTEM_NAME=HarmonyOS` 被 CMake 标记为 cross-compiling | Conan OHOS toolchain 会设置系统名，即使 host 与 target 都是 HarmonyOS，CMake 仍设置 `CMAKE_CROSSCOMPILING=TRUE` | 原生 host/target 均为 HarmonyOS 时允许 `nodesize_dbg` 执行；真正 Linux→OHOS 交叉构建仍不执行目标工具 |
| 4 | 相对路径传给 `-pr:h/-pr:b` 未加载仓库 profile | 当前 Conan 设备环境对该相对 profile 形式解析为默认 profile | W3 使用已验证的仓库 profile 绝对路径；没有修改共享 profile |

## 源码修改

- `0001-CMakeLists.txt.patch`：识别 OHOS/HarmonyOS/OpenHarmony 的 GNUInstallDirs 分支。
- `0002-include-foonathan-memory-malloc_allocator.hpp.patch`：POSIX hosted `malloc_allocator` 用 `posix_memalign`，零大小按 1 处理；Windows 保留原路径。
- `0003-src-CMakeLists.txt.patch`：原生 HarmonyOS host/target 允许节点大小工具运行。
- `0004-src-heap_allocator.cpp.patch`：POSIX hosted `heap_alloc` 用最大对齐的 `posix_memalign`，零大小按 1 处理；Windows 保留原路径。
- `0005-src-new_allocator.cpp.patch`：POSIX hosted `new_allocator` 用 `posix_memalign`/`free`，零大小按 1 处理；Windows 保留原路径。

## 依赖版本

- Conan recipe 声明依赖：0 个。
- 上游测试在配置阶段下载其固定 Catch2 v2.12.1 单头文件；该文件由上游测试 CMake 逻辑获取，不是 Conan package dependency。

## 验证结果

设备端 Conan W3：

```text
Package foonathan-memory/0.7 created
upstream CTest: 39 test cases, 140870 assertions, all passed
consumer test_package: test_foonathan_memory exited with rc=0
```

独立运行缓存中的上游测试得到：

```text
Passed all 39 test cases with 140870 assertions.
```

`test_package` 调用了 `heap_allocator`、`malloc_allocator`、`new_allocator` 的真实分配接口，检查 `max_align_t` 对齐，并通过 `memory_pool`/`std_allocator` 构造并使用 `std::vector`。`nodesize_dbg --version` 输出 `nodesize_dbg version 0.7`。

## 交付物

- Conan recipe：`conanfile.py`、`conandata.yml`
- Conan consumer test：`test_package/` 及 `test_package/MANIFEST.yml`
- 5 个平台可移植性 patches（其中 allocator 补丁使用标准 `__unix__` POSIX 守卫）
- 软件级 README、manifest 和 `commands.json`（声明 `nodesize_dbg`）
- 知识草稿：`knowledge/drafts/E321-draft-333C.{kv,md}`

## 发现与知识

- ✅ E267：CMake 平台分支同时识别 OHOS、HarmonyOS 和 OpenHarmony。
- ✅ E321（draft）：OHOS 小对象默认分配可能只有 8 字节对齐，POSIX hosted 路径需用 `posix_memalign` 覆盖默认、malloc 和 new 分配器，并处理零字节请求。
- ✅ 显式 `CMAKE_SYSTEM_NAME=HarmonyOS` 会令 CMake 标记 cross-compiling；原生 HarmonyOS worker 需允许 `nodesize_dbg` 生成节点大小头文件。

## 对话记录

### 对话 #1 — 2026-08-29
**操作**：完成 Conan 配方、OHOS 补丁、上游 CTest、消费者测试与归档验证。
**结果**：✅ Conan W3 与本地 CI 模拟通过；39 个上游 Catch2 用例和 1 个消费者测试通过。
**遗留问题**：通用 `clean-verify` 对 CMake-only 项目仍错误执行 `./configure`；SUMMARY 生成器存在全局 `'str' object has no attribute 'append'` 错误，均未修改框架文件。

### 对话 #2 — 2026-08-29
**操作**：按独立审计意见恢复官方源码 URL，补全 recipe homepage/url，扩展 OpenHarmony 节点工具条件，并清理 PR 候选中的本地生成二进制与日志。
**结果**：✅ 定向 Conan CI rebuild 通过（L0/L1/L2/L4/L5 全部 PASS）；等待 W4 复审和 PR 创建。
**遗留问题**：无代码级阻塞；PR 创建后需触发远端 `/rebuild` 并核对平台 CI 评论。

### 对话 #3 — 2026-08-29
**操作**：处理 PR #7099 的 R8 review 意见；将 allocator 的平台分支由私有 `__OHOS__` 宏改为标准 `__unix__` 守卫，POSIX hosted 构建统一使用 `posix_memalign`，Windows 保留原生分配路径。
**结果**：等待本地复验、更新审计并推送修复提交。

## 注意事项

- 本地设备已验证的 Conan profile 必须使用绝对路径；使用默认 profile 会缺少 `os.version` 并导致 invalid package。
- 当前远端 `ohpcd` 查询返回 `error:system acceleration policy not enabled`，因此不能据此确认 registry 已发布。
- 构建输出曾出现 `$TMPDIR` 下 GNU make jobserver FIFO 的 `Operation not permitted` 警告；后续目标仍成功完成，最终验证按 `--parallel 1` 独立重跑并保留日志。
---

**编译结束**: 2026-08-29 00:23
**最终状态**: built
