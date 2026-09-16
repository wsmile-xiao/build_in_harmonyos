# E543-draft-E6ED — macOS Objective-C “now playing” CLI 的可移植落点（__APPLE__ 双路径 + 诚实空结果）

> **Contributor**: E6ED | **Status**: DRAFT（未索引，待人工审核） | **Updated**: 2026-09-14
> **Source event**: nowplaying-cli 2.1.0 HarmonyOS PC 适配，上游 `kirtan-shah/nowplaying-cli` v2.1.0

## 适用场景

上游是 **macOS 专属 Objective-C(++) 命令行工具**，其核心能力建立在目标平台不存在的私有框架上：

- 读取 / 控制系统 “now playing”（本例：`Foundation`/`AppKit` + 私有 `MediaRemote`）；
- 或依赖其它 Apple 私有传输层（对照 `DRAFT-m1ddc-apple-ddc-transport-boundary`：`IOKit`/`IOAVService`）。

## 问题

OpenHarmony native SDK 与 macOS 的差异是**双重的**，两条都不能绕过：

1. **语言运行时缺失**：sysroot 无 `libobjc`/`libdispatch`/`Foundation`，clang 首个阻塞即
   `fatal error: 'Foundation/Foundation.h' file not found`。
2. **能力缺失**：native `libohavsession.so`（115 个导出符号）只有 **provider** 侧
   （`OH_AVSession_Create/Activate/SetAVMetadata/SetPlaybackState/SetPlaybackPosition/…`）
   + AVCast 投屏控制器；**没有** native 的 `OH_AVSessionManager` / `OH_AVSessionController` /
   `getAllSessionDescriptors`，`native_avmetadata.h` 也没有 getter —— 系统级 “查询正在播放”
   在 native 侧**无法实现**。

三种常见误判：整包标 unsupported 后删二进制（只证明没编译失败）；用硬编码 demo 数据冒充
查询（伪造副作用）；把另一个平台的私有栈（如 Linux DDC）拉进单包 PR（改变依赖边界）。

## 推荐方法

1. **源码边界拆分**：补丁把上游 Objective-C 源文件整体包进 `#if defined(__APPLE__)`，原版
   逐字保留；非 Apple 分支提供纯 C++ 实现。（`.mm` 文件在非 Apple 分支用 `-x c++` 编译，
   预处理排除掉全部 ObjC `#import` 后即为纯 C++17。）
2. **复刻 CLI 契约**：子命令、字段键、输出格式（每行一值 / `--json`）、退出码逐字对齐，
   让下游脚本可无感迁移。
3. **映射到真实存在的原生 API**：把能落地的动词映射到目标平台真正具备的接口
   （本例控制命令 → 原生 AVSession **provider** 会话；`OH_AVSession_Create` 在 HarmonyOS PC
   上实测 `rc=0`，是真实代码路径而非桩）。
4. **诚实失败 / 诚实空结果**：平台缺能力时，返回与上游“无数据”场景**逐字一致**的结果
   （每个键一行 ``；`get-raw` 输出 `{}`），或非零退出并给出诊断；**绝不伪造**。
5. **test_package 真实执行被测物**：运行已安装二进制，断言真实 stdout/stderr/退出码；
   AVSession 相关路径可接受“成功 or 诚实失败（含诊断）”双分支，但禁止静默假成功。

## 与已有知识的差异

- `DRAFT-m1ddc-apple-ddc-transport-boundary`：Apple 私有 **硬件传输层**（IOKit/IOAVService）
  缺失；本条目是 Apple 私有 **多媒体框架**（MediaRemote）+ 目标平台侧 **控制器 API 缺失**，
  是同一归类的第二实例。
- `E449`（GNUstep Objective-C 运行时）：讲的是**存在** libobjc2 时如何发布 ObjC 运行时
  flags；本条目是**运行时与 Foundation 均不存在**、且**能力本身缺失**的情形。

## 禁止做法

- 不要返回假成功，也不要用硬编码 demo 数据冒充真实查询。
- 不要删除二进制、丢弃上游源码或交付空包。
- 不要用桩 `libobjc`/shim 掩盖缺失运行时。
- 不要把未适配的其它平台私有栈混入同一个单包 PR。

## 已验证示例（nowplaying-cli 2.1.0）

- 归档：`archives/n/nowplaying-cli/2.1.0/`（补丁 `patches/0001-portable-nonapple.patch`）
- 复现入口：
  ```sh
  conan create archives/n/nowplaying-cli/2.1.0 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
  ```
- 结果：本地 CI 模拟（L0/L1/L2/L4/L5 + JC/KC + L1e 破坏性反向验证）全部 `pass`，
  test_package 10/10。

## 证据来源

- `archives/n/nowplaying-cli/2.1.0/conanfile.py` / `conandata.yml` / `notes.md`
- `archives/n/nowplaying-cli/2.1.0/patches/0001-portable-nonapple.patch`
- `archives/n/nowplaying-cli/2.1.0/test_package/test.sh` / `MANIFEST.yml`
- SDK 证据：`llvm-nm -D <sysroot>/usr/lib/aarch64-linux-ohos/libohavsession.so`（115 符号）
