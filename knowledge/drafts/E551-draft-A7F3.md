# Windows Conan OHOS 验证的双 profile 与环境文件边界

## 场景

Windows 主机为 OHOS/arm64 交叉编译时，Conan 的 host profile 描述目标编译器、
sysroot 和 ABI，而 build profile 必须描述实际运行 CMake/Make/Ninja 的 Windows
执行器。Conan 2 在 OHOS host 下还可能生成 POSIX `conanbuild.sh`，不能直接交给
Windows `cmd.exe`。

## 根因

把同一个 OHOS profile 同时传给 `-pr:h` 和 `-pr:b` 会让 CMake try-compile 使用
目标 linker 处理 Windows 生成器参数；直接运行环境文件又会触发
`'.' is not recognized`。在 MSYS 中把预下载文件写成 `file://F:/...` 还可能丢失
盘符，导致 Conan 读取不存在的路径。

## 修复步骤

1. 建立任务自有 Windows build profile，使用 launcher 仅替换 `conan create` 的
   `-pr:b`，setup、remote 和其他 Conan 命令原样透传。
2. 配方和 test_package 在 Windows 上以参数列表、`env=None`、`shell=False`
   调用 CMake，避免 Conan POSIX 环境文件包装器；从任务环境补齐 target triple、
   DevEco LLVM 和 sysroot。
3. 本地 CI 使用隔离执行副本；当 MSYS 盘符转换不可靠时跳过预下载改写，保留
   官方 URL，并把完整命令日志与候选身份绑定。

## 验证方式

先回读 `conan profile show`，确认 host=OHOS/armv8/libc++、build=Windows/x86_64；
再运行真实 `conan create` 和 `test_package`，检查 CMake 使用 DevEco clang、
target/sysroot 正确且消费者真实链接公共 API。CI 结果必须由 finish 写入并校验，
不能手工创建 `.ci-result.json`。

## 适用范围与安全边界

适用于 Windows 上所有目标 profile 与执行器 profile 不同的 Conan 交叉构建。任务
launcher、overlay 和预下载开关只能位于任务目录，不得修改共享 skill/CI 或污染
提交树；跳过预下载只解决本机路径转换问题，不替代官方源码 URL、SHA-256、依赖
发布检查或目标机验证。若无法证明双 profile 和输入闭包，应停止在本地验证并转为
目标 worker 流程。
