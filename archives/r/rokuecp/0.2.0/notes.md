# rokuecp 0.2.0 HarmonyOS PC 适配笔记

## 适配范围

- 路径 A（基础适配）。
- 官方标签：`v0.2.0`（tag commit `de1f0d7fb5801a268f1c5014e428b26835a9b13a`）。
- 构建系统：CMake；语言主体：C（1/1 源文件，任务 C/C++ 家族预检通过）。
- 交付物：共享库 `librokuecp.so.0.2.0`、公共头 `rokuecp.h` 和 `rokuecp.pc`。

## W0 依赖核验

上游 `CMakeLists.txt` 的三个 REQUIRED 模块均在 `ohpcd` 制品仓实测可下载：

- `gssdp/1.6.6`
- `libsoup3/3.6.5-r1`
- `libxml2/2.15.3.1`
- `glib2/2.88.0`（只注入 GSSDP 公共头所需 include 目录，不重复链接静态 GObject）

`gssdp/1.6.6` 已按 `libsoup3/3.6.5-r1` 发布，根配方保持相同版本，避免改变依赖二进制的 package ID。

## 上游测试清点（R51）

- `N_static = 0`：官方 tarball 只有一个 C 源文件和公共头；无 `tests/`、`test/`、测试源文件或测试脚本。
- `N_registered = 0`：顶层 CMakeLists 无 `enable_testing()`、`include(CTest)` 或 `add_test()`。
- `N_executed = 0`：没有可执行的上游测试入口，因此不存在跳过或修改上游用例。
- `N_consumer = 11`：通用消费者用例 10 项断言，加 HarmonyOS 专有用例 1 项；全部真实链接并调用安装后的库。

## 适配方法

上游通过 `pkg_check_modules()` 查找 GSSDP、libsoup3 和 libxml2。目标依赖均为 Conan 包，配方在源码副本中将该依赖块替换为 CMakeDeps 的三个导入目标；GLib 只提供 GSSDP 公共头需要的 include 目录，不把静态 GObject 重复链入共享库。配方同时移除 CMake 目标中硬编码的 `SHARED`，使产物类型与 Conan `shared` 选项严格一致。没有修改库源码和平台行为。关闭文档构建，默认保留共享库发布形态。

## 测试范围

通用测试使用公开 API 的离线确定性分支，不依赖实际 Roku 设备：

1. TV 专用按键拒绝非 TV 设备。
2. Limited 模式拒绝按键输入。
3. 非 TV 设备拒绝频道列表。
4. Limited 模式拒绝频道列表。
5. 非 TV 设备拒绝当前电视频道查询。
6. Limited 模式拒绝当前电视频道查询。
7. 非 TV 设备拒绝直播频道启动。
8. Limited 模式拒绝应用列表。
9. 不支持搜索的设备拒绝搜索。
10. Limited 模式拒绝自定义输入。

鸿蒙特有测试单独编译并运行，验证消费者由 `__OHOS__` 编译、目标指针宽度为 64 位，并实际调用 `rokuSendKey()` 的确定性错误路径。上游网络交互 API 需要真实 Roku 设备，未伪造网络结果，也未删除或篡改上游测试。

## 已知限制

- 设备发现和 HTTP ECP 成功路径需要同一局域网内的 Roku 硬件；标准 CI 无此硬件，因此只验证无需硬件即可严格断言的公开 API 行为。
- 源码无需 HarmonyOS 条件补丁；依赖适配完全由 Conan/CMake 生成层完成。

## 结束标记

rokuecp 0.2.0 HarmonyOS PC 适配、打包与 11 项消费者断言均已完成。
