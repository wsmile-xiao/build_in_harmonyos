# fsm-variant 1.0.0 适配记录

## W0/W0b

- 任务语言为 C++，源码主体为 C++，无 Conan 依赖；官方 tarball SHA-256：`86a660a281ba1656e9dabf47157d20a73e7d44c67f501c0ad71ab90ac0ab6deb`。
- 发布 tarball 含 CMakeLists，但缺少 `.gitmodules` 声明的 `cmake/common` 子模块内容。

## 构建与测试

- 官方根 CMake 配置会在 `include(tools)`、`include(compile_flags)` 和 `configure_and_install()` 处失败；失败日志保留在初始 HANDOFF 中。
- 该库是独立 header-only 库。recipe 不抓取未锁定的 SSH 子模块，而是用 OHOS profile 的 clang++ 直接编译并运行官方 `connection_fsm`、`tcp_fsm` 两个示例。
- test_package 通过 Conan CMakeDeps 消费 `mp::fsm`，真实验证 `dispatch()` 和 `get_state()` 的三态转换。

## 路径判断

- 本任务走路径 A+B：header-only 适配完成；发布归档缺失 CMake 子模块的证据、边界和处理原则抽取为 `DRAFT-release-tarball-missing-cmake-submodule`。

## 对话记录

### 对话 #1（2026-09-03）

- 首轮构建确认根因是发布 tarball 缺少 `cmake/common`，不是 OHOS 语言或编译器不兼容。
- 采用不下载不受 recipe 锁定的 SSH 子模块的最小方案；上游两个示例和 Conan consumer 均由真实命令验证。

## 结束

最终状态: built
---

**编译结束**: 2026-09-03 02:28
**最终状态**: built
