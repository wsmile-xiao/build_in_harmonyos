# timewarrior 1.9.1 适配笔记

## 构建配置

- 构建系统：CMake
- 编译器：OHOS Clang/Clang++
- 测试选项：`BUILD_TESTING=ON`
- 外部 Conan 依赖：无

## 适配处理

- 将 CMake 平台判断扩展到 OHOS/HarmonyOS。
- 部署上游 TAP 测试脚本、测试数据目录及辅助程序。
- 上游 `test/problems` 是由 `run_all` 调用的可执行 Python 文件；配方显式检查其文件类型、复制结果并设置执行权限。
- 为测试环境提供 `man` 查询 shim，并将上游 `doc/man1`、`doc/man7` 手册页复制到构建目录，通过 `MANPATH` 指向该目录，使 `help.t` 在 OHOS 上能执行真实帮助页对比；单独运行 `AtomicFileTest`。

## 验证结果

- 上游 TAP 测试：1505/1505（100%），另有 7 项由上游条件判断跳过。
- 上游 C++ `AtomicFileTest`：1/1（100%）。
- 新增安装制品消费测试：1/1（100%）。

## 源码信息

- URL：`https://github.com/GothenburgBitFactory/timewarrior/releases/download/v1.9.1/timew-1.9.1.tar.gz`
- SHA-256：`7ad34f95c0d61d356df55149f9479f8d9aaec417e5f57f2a1cc76ae2f8a3171b`
