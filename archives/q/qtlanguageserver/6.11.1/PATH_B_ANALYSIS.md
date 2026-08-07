# qtlanguageserver 6.11.1 路径 B 复核分析

更新日期：2026-08-07

- 路径 B 类型：不成立（Build #15413 上游测试 5/5 通过）
- 路径 B Issue：#929
- 对应 PR：#2732
- 当前结论：Builds #15413 和 #15584 已在官方 OHOS Worker 编译全部测试目标
  并通过完整上游测试（5/5）。剩余失败来自消费测试使用 CMakeDeps 生成的
  配置错误查找 `qtbaseConfig.cmake`，属于可修复的消费元数据问题，不能作为
  路径 B 证据。

## 根因与证据边界

`qtbase/6.11.1` 已可从官方 Conan remote 取得。Build #15413 完成
`Qt6JsonRpc` 和 `Qt6LanguageServer` 静态库以及全部测试目标的编译、
链接，CTest 随后显示：

- `test_qtjsonrpc_module`：通过；
- `tst_qjsonrpcprotocol`：通过；
- `tst_typedjson`：通过；
- `tst_qlanguageserver`：通过；
- `tst_generated_lsp_types`：通过。

Build #15341 中四个失败项均在约 0.03 秒内报告
`execution failed with exit code no such file or directory`。启用
`QT_BUILD_TESTS_BY_DEFAULT` 后，Build #15413 生成了对应的 `tst_*`
可执行文件，并在官方 Worker 全部运行通过，证实旧结果并非平台不兼容。

## 已尝试方案与结果

1. 补齐并发布前置 `qtbase/6.11.1`：依赖解析成功，两个私有库完成编译链接。
2. 开启 `QT_BUILD_TESTS`：CTest 注册五项，但四个 `tst_*` 未进入默认构建。
3. 生成 Conan `VirtualRunEnv`：运行环境不能补齐未构建的测试文件。
4. 补充 `QT_BUILD_TESTS_BY_DEFAULT=ON` 后，Build #15413 完整五项
   CTest 全部通过。
5. Build #15413 的 L1 消费测试在 CMake 配置阶段报告
   `Library 'Qt6LanguageServerPrivate' not found in package`；实际安装文件为
   `libQt6LanguageServer.a` 和 `libQt6JsonRpc.a`，已将 `package_info()`
   导出名修正为 `Qt6LanguageServer` 和 `Qt6JsonRpc`。
6. Build #15584 再次完成构建、5/5 CTest 和安装，但 CMakeDeps 生成的
   `qtlanguageserver-config.cmake` 错误调用 `find_dependency(qtbase)`；而
   `qtbase` 包按约定只提供原生 `Qt6Config.cmake`。当前修复改为复用安装目录
   中的 `Qt6LanguageServerPrivateConfig.cmake` 和 `Qt6::LanguageServerPrivate`。
7. 未排除或跳过任何测试。

## 障碍与影响

- 官方 Worker 已执行完整 QtTest 测试集并全部通过，不存在可用于
  路径 B 的平台失败证据。
- 当前仅需新 CI 确认原生 Qt CMake target 可被 L1 消费测试链接。

## 解除条件

路径 B 解除条件已经触发：完整测试已通过。该库应按路径 A 继续；
待 L1 消费测试通过后，将 CI 状态更新为成功。
