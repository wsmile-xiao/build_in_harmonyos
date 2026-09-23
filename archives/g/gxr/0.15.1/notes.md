# gxr 0.15.1 适配笔记

## 编译环境

- 构建系统：Meson 1.11.0
- 编译日期：2026-09-09
- 目标编译器：OHOS Clang 15.0.4，`aarch64-unknown-linux-ohos`
- 本地运行基线：Linux x86_64、Monado 模拟 HMD、Mesa llvmpipe
- 状态：built

## 编译步骤

1. 从 GitLab 官方归档下载并校验 gxr 0.15.1 源码。
2. Conan 使用 OHOS AArch64 profile 解析已发布的 Gulkan、GTK、GLib、JSON-GLib、HarfBuzz 及其传递依赖。
3. `MesonToolchain` 关闭文档/内省和未发布的 OHOS OpenXR/OpenVR Conan 后端，构建核心库、可移植示例与全部四个上游测试程序。
4. Linux 交叉构建时验证 `pkgconf`、`glslangValidator` 的可执行架构，使用构建机工具生成 pkg-config 元数据和 SPIR-V。
5. 共享、静态两种 OHOS 包均由 `conan create` 从干净源码生成，C++17 `test_package` 实质调用安装后的公开 API。
6. 同源 OpenXR 构建在 Monado 模拟 HMD + llvmpipe 环境运行四项上游测试，并运行同一份 C++ 消费源码。

## R40 适配完整性边界

本次路径 A 制品交付 GXR 的后端无关核心库、公共头文件、pkg-config 元数据和可移植示例。OHOS Conan 制品仓当前没有已发布的 OpenXR/OpenVR 配方，依据 R36 不能把未发布依赖加入正式包，因此正式构建明确使用 `-Dbackends=[]`，不声明该制品包含 XR 运行时后端。OpenXR 源码适配由同源 Monado 模拟构建验证，待相应 OHOS 依赖发布后即可在正式制品中启用；当前降级不以 stub 或固定成功返回绕过功能。

## 问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Linux→OHOS 交叉配置误用 AArch64 `pkgconf`/`glslangValidator` | host/build profile 复用时 Conan 工具包与构建机架构不一致 | 配方逐个验证工具可执行性，优先选取构建机可运行工具，再回退到 Conan 工具包 |
| 2 | `x_keyboard_synthesis.c` 找不到 `X11/keysymdef.h` | OHOS GTK 元数据可传播 X11 名称，但 HarmonyOS 不提供 X11 开发头和 XTest 运行环境 | 以 `host_machine.system() == 'harmonyos'` 精确排除唯一 X11 专用示例 |
| 3 | OpenXR validation 拒绝 `xrCreateSession` | 上游未调用 `xrGetVulkanGraphicsDeviceKHR`，也未把运行时要求的 Vulkan 扩展传给 Gulkan | 实现实例/设备扩展查询、解析和传递，并验证运行时选择的物理设备 |
| 4 | OpenXR view 枚举输出结构无效 | 分配数组后未初始化每项 `type` | 零初始化数组并设置 `XR_TYPE_VIEW`/`XR_TYPE_VIEW_CONFIGURATION_VIEW` |
| 5 | `VkGraphicsPipelineCreateInfo.subpass` 类型错误 | 上游把指针型 `VK_NULL_HANDLE` 赋给整数索引 | 改用整数 `0` |
| 6 | OHOS 严格 C11 下无 `CLOCK_MONOTONIC` | musl 需要 POSIX feature-test macro | 定义 `_POSIX_C_SOURCE=200809L` |
| 7 | cube 链接缺少 Vulkan 符号 | 示例直接调用 Vulkan API，Gulkan元数据不替示例传播系统 loader | 示例显式查找并链接平台 `vulkan` 库 |
| 8 | C++ 消费者链接公共 C API 失败 | 三个公共函数头缺少 C linkage guards | 添加 `G_BEGIN_DECLS`/`G_END_DECLS` |
| 9 | `shared=False` 仍输出共享库 | 上游硬编码 `shared_library()` | 改用 `library()`，让 Meson `default_library` 生效 |
| 10 | OHOS 原生 CI 启动 `test_io` 或独立 C++ 消费者时拒载 JSON-GLib | 已发布的 `json-glib/1.10.6` 虽带旧 `.codesign`，从 Conan 缓存加载时签名不被当前执行环境接受；配方构建测试与 `test_package` 是两个隔离阶段 | 保持依赖缓存只读，在两个测试阶段各自的构建目录物化 SONAME 常规文件、移除旧签名并原子重签，仅将对应任务私有目录前置到测试运行路径 |

## 上游测试清点（R51）

| 测试 | 类型 | OHOS 目标构建 | Monado 模拟运行 |
|------|------|---------------|-----------------|
| `test_io` | 单元测试 | PASS | PASS |
| `test_overlay` | XR 集成测试 | PASS | PASS |
| `test_context` | XR 集成测试 | PASS | PASS |
| `test_actions` | XR 集成测试 | PASS | PASS |

上游恰有 4 个测试源文件和 4 个 Meson 注册项；适配未修改测试断言或测试源码。无后端的 OHOS 核心包只注册可运行的 `test_io`，但四个测试程序全部编译；带 OpenXR 的同源模拟构建实际运行 4/4，通过率 100%。

## 验证结果

- OHOS AArch64 共享 `conan create`：PASS，65/65 Ninja 步骤，消费者配置/编译/链接 PASS。
- OHOS AArch64 静态 `conan create`：PASS，64/64 Ninja 步骤，生成 `libgxr-0.15.a`，消费者配置/编译/链接 PASS。
- 上游 Meson 测试：PASS，4/4。
- C++17 消费者：PASS，1/1；覆盖时间、设备状态、矩阵、设备管理器和 IO API。
- 源码 URL、SHA-256、补丁 dry-run、共享/静态制品布局：PASS。

## 交付物

| 文件 | 说明 |
|------|------|
| `libgxr-0.15.so.0.15.1` / `libgxr-0.15.a` | 共享/静态核心库 |
| `gxr-0.15.pc` | pkg-config 消费元数据 |
| `include/gxr-0.15/` | 公共头文件 |

---

**编译结束**：2026-09-09  
**最终状态**：built
