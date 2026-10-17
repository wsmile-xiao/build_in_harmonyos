# log4cpp 1.1.6 适配笔记

## 基本信息

- 上游版本：1.1.6
- 上游标签：`REL_1.1.6_Mar_12_2026`
- 构建系统：CMake
- 许可证：LGPL-2.1-or-later
- 源码 SHA256：`00a4c14e92bef300328c38405ac505f237bbd720cba69497305fd8a12d10c251`

## 适配策略

配方构建静态库并开启位置无关代码：

```text
BUILD_SHARED_LIBS=OFF
CMAKE_POSITION_INDEPENDENT_CODE=ON
LOG4CPP_BUILD_EXAMPLES=OFF
```

上游示例在静态库模式下仍链接仅共享库目标
`log4cpp::log4cpp_shared`，会在 CMake 生成阶段失败。因此关闭 examples。
上游 `tests/` 目录和全部 17 项 CTest 均保留并执行，没有修改或删除上游测试。

## 本地验证

验证环境为干净 Linux 容器、Conan 2.29.1、GCC 12.2 和 CMake
3.25.1。执行命令：

```bash
conan profile detect --force
conan create archives/l/log4cpp/1.1.6 --build=missing -s build_type=Release
```

结果：

- 源码下载和 SHA256 校验：通过
- CMake 配置、编译和安装：通过
- 上游 CTest：17/17 通过，100%
- 打包后消费者测试：17/17 断言通过，100%
- 补丁：无

消费者测试实际链接 Conan 包中的 `liblog4cpp.a`，覆盖优先级转换、
Category、NDC、StringQueueAppender、格式化 DEBUG/INFO/WARN/ERROR 消息
以及日志记录数量。

## OHOS AArch64 验证

使用 OpenHarmony 6.0 API 20 SDK 的官方 `ohos.toolchain.cmake`、
Clang 15.0.4 和 Conan 2.29.1 完成交叉编译：

- `liblog4cpp.a`：编译、链接和打包通过
- 17 个上游测试目标：全部编译并链接通过
- 消费者测试目标：编译并链接通过
- 消费者产物：ELF64、AArch64
- 动态依赖：`libc++_shared.so`、`libc.so`

交叉编译环境不能运行 AArch64 目标程序，因此 OHOS 运行测试为
`not_run`。本地没有在鸿蒙 PC 真机运行，赛事官方 CI 仍是平台最终
验证信号。
