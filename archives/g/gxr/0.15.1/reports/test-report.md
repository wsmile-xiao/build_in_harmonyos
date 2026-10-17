# gxr 0.15.1 测试报告

> 测试日期：2026-09-09  
> 目标环境：OHOS 6.0 / API 20 / Clang 15.0.4 / AArch64  
> 模拟环境：Linux x86_64 / Monado simulated HMD / Mesa llvmpipe  
> 测试类型：Conan 干净构建、共享/静态矩阵、上游 Meson 测试、C++ 消费者

## 一、测试摘要

| 测试集合 | 总数 | 通过 | 失败 | 通过率 |
|----------|------|------|------|--------|
| 上游测试 | 4 | 4 | 0 | 100% |
| 新增 C++ 消费者 | 1 | 1 | 0 | 100% |
| OHOS 共享构建 | 65 步 | 65 步 | 0 | 100% |
| OHOS 静态构建 | 64 步 | 64 步 | 0 | 100% |

## 二、上游测试明细

| 测试 | 类型 | 结果 |
|------|------|------|
| `test_io` | 资源写入与缓存路径单元测试 | PASS |
| `test_overlay` | OpenXR 上下文、Vulkan 纹理与覆盖层集成测试 | PASS |
| `test_context` | XR 上下文生命周期与退出事件集成测试 | PASS |
| `test_actions` | 动作清单和控制器绑定集成测试 | PASS |

四项均由上游 Meson 注册并在 Monado 模拟 HMD + llvmpipe 环境实际执行。适配补齐 OpenXR Vulkan 扩展协商及运行时物理设备校验后，结果为 4/4。

## 三、消费者测试

`test_package/gxr_test.cpp` 是真实 C++17 消费者，包含 19 个断言，覆盖：

- 时间差和 `timespec` 转换；
- `GxrDevice` 创建、类型、句柄、型号和 pose 状态；
- Graphene transformation 写入/读取；
- `GxrDeviceManager` 创建和初始设备列表；
- `gxr_io_get_cache_path` 路径后缀。

同一测试源码完成 OHOS AArch64 共享/静态配置、编译和链接，并在本地匹配运行构建中实际执行通过，结果 1/1。
OHOS 原生执行前在测试构建目录内复制并重新签名 JSON-GLib SONAME，运行路径优先使用该任务私有副本，不修改 Conan 依赖缓存。

## 四、正式构建证据

```text
OHOS shared: 65/65, PASS
gxr/0.15.1#658e6d850830e4a543411d7835b3389a:f98eae6a0c8bf7137fb87659f23bfe5cfd3801ec#1be88ac478368e6b4d6452c5b6858888

OHOS static: 64/64, PASS
gxr/0.15.1#658e6d850830e4a543411d7835b3389a:2cebf5736bb948ea5a3309ae22e1e0998da17948#5ca7fc1d4bda96f02a57dce199373e7e

Upstream Meson: 4/4, PASS
C++ consumer: 1/1, PASS
```

## 五、结论

gxr 0.15.1 的 OHOS AArch64 共享/静态核心库、公共头、pkg-config 元数据、可移植示例、四个上游测试目标和 C++ 消费者均完成验证；要求范围内测试全部通过。正式 Conan 制品因仓库尚无已发布的 OpenXR/OpenVR 依赖而明确不包含 XR 后端模块，不把模拟环境的后端验证表述为 OHOS 制品已交付的功能。
