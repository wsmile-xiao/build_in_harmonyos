# kdoctools5 5.116.0 HarmonyOS 移植记录

## 编译环境
- 构建系统：CMake
- 目标平台：HarmonyOS PC 6.0 aarch64（armv8）
- 编译器：Clang 15.0.4
- Conan：2.29.1（HarmonyOS 适配版）
- 上游：KDE Frameworks 5.116.0
- 状态：built（已在设备本机创建 Conan 包；未发布到 Conan 制品仓）

## 移植目标

打包 `meinproc5`、`checkXML5` 和 KDE DocBook 自定义资源，保留真实的 KF5Archive 支持；在 HarmonyOS 设备上运行 DocBook XML 到 HTML 的转换集成测试。

## 验证结果

- HarmonyOS aarch64 原生 `conan create`：通过，目标程序、共享库和资源已打包。
- Conan `test_package`：通过；真实运行打包后的 `meinproc5`，将 XML fixture 转换为非空 HTML，并校验输出标记。
- CMake 启用了 `BUILD_TESTING`。首次配置时缺少系统 DocBook XML 4.5 DTD 和 XSL，两个条件上游测试未注册；补装官方测试数据并重新配置后，按上游测试项逐项运行：`meinproc_template` 与 `kdoctools_install` 均在 HarmonyOS aarch64 真机通过（2/2）。其中 `kdoctools_install` 配置、构建并安装下游 CMake 消费者，检查 9 个生成/安装文件。
- HarmonyOS 设备补充运行测试：在用户级测试目录安装官方 DocBook XML 4.5 DTD 和 DocBook XSL 1.79.2 后，`checkXML5` 接受带内嵌 DTD 的有效 XML，并拒绝格式错误 XML；使用 `html/docbook.xsl` 完成转换，检查输出含预期文本。测试数据只用于设备验证，不随 Conan 配方打包。
- 设备上的 `meinproc5` 与 `checkXML5` 均由 `readelf` 确认为 AArch64 ELF。
- `zlib/1.3.1.1` 以 `force=True` 固定为 PIC 构建，避免 Qt5 传递依赖将 KArchive 拉回非 PIC `zlib/1.3.1`，导致 AArch64 共享库链接失败。
- 设备的 CMake 系统名为 `HarmonyOS`，因此手册生成目标的跳过条件同时覆盖 `HarmonyOS` 与 `OHOS`。
- 当前包仅在设备 Conan 本地缓存中，未发布到 Conan 制品仓。

## 发现与知识

✅ Conan OHOS profile 使用 `CMAKE_SYSTEM_NAME=HarmonyOS`；仅匹配 `OHOS` 的上游 CMake 条件可能漏掉 HarmonyOS 主机目标。

✅ Qt5 依赖图默认选择 `zlib/1.3.1`，但审核通过的 KArchive 二进制依赖 PIC 版 `zlib/1.3.1.1`；在本配方固定后，Conan 可复用匹配的 KArchive 二进制。

✅ 系统 DocBook DTD/XSL 缺失时，依赖它们的上游转换测试不会注册；设备用户级测试目录补齐官方 XML 4.5 DTD 和 XSL 1.79.2 后，两个上游测试项均通过，并完成 `checkXML5` 正反输入及标准 DocBook 转换验证。测试数据不作为 Conan 配方依赖。

✅ HarmonyOS SSH 用户对 `/data/local/tmp` 无写权限；消费者测试优先选择可写的 `TMPDIR` 或用户目录临时路径。

## 对话记录

### 对话 #1：HarmonyOS PC 移植与设备验证

- 按用户授权复用仓库中已审查的 `karchive5/5.116.0` 包；未发布依赖到 Conan 制品仓。
- 按用户授权跳过 W0/R36 依赖发布门禁；设备构建和 Conan 消费者测试仍实际运行。
- 在 HarmonyOS 6.0 aarch64 真机安装设备级 DocBook XSL 测试数据，运行 checkXML5 正反输入和真实 DocBook HTML 转换。
- 后续按用户要求补装 DocBook XML 4.5 DTD 与 XSL 1.79.2，重新配置后逐项运行上游 `meinproc_template`、`kdoctools_install`，两项均通过；上游测试统计按这两个测试项计算。
