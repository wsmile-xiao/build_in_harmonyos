# XaoS 4.3.4 HarmonyOS PC 适配笔记

## 上游信息

- 上游仓库：<https://github.com/xaos-project/XaoS>
- 官方发布标签：`release-4.3.4`，提交 `9e1d900de70b7478a2dd8f8498a9a7285796d309`
- 源码归档 SHA-256：`4bb1c6bdc3a136e7bdceaa626ae48944ef289cdc092dc5e46b4f8e9e049c5b07`
- 应用类型：Qt 6 Widgets 桌面分形缩放器；上游 CMake 安装的可执行文件为 `bin/XaoS`
- 构建选项：保持上游默认 `DEEPZOOM=OFF`、`OPENGL=OFF`，不引入未预检的 OpenGL/GLUT 依赖

## 依赖检查

适配前执行 `ci/scripts/preflight_check.sh xaos/4.3.4`。该预检提示首次适配尚无依赖声明，属于正常状态。首次构建实证 `qtbase/6.11.1` 不含 `Qt6PrintSupportConfig.cmake`（其 `FEATURE_printsupport=OFF`），而官方 XaoS CMake 将 `PrintSupport` 标为必需组件；因此改用已发布的 `qtbase/6.11.1.3`。该包实际包含 PrintSupport、WaylandClient、offscreen/minimal/Wayland QPA。OHOS aarch64 Conan graph 可解析该变体及其依赖，并从 `ohpcd` 下载对应二进制。`qttools/6.11.1.1` 提供 LinguistTools 与 `lrelease`。

上游还调用 `qt6_add_translation` 生成翻译目录，因此配方为 `Qt6_DIR` 与 `Qt6LinguistTools_DIR` 指向 Conan Qt 包，并在构建时提供所有传递 Qt 库路径给 `lrelease`。真机构建发现 Conan 缓存中的 Qt `lrelease` 带有不可执行的旧 `.codesign`，设备返回 `Operation not permitted`。配方将其复制到 build folder，剥离旧签名并自签名，校验 `lrelease -version` 后再构建，不修改 Conan 依赖缓存。Qt 6.11.1.3 的 PrintSupport 是必要的上游 CMake 组件；保留该依赖以维持上游构建和功能配置。

## 上游测试清点

上游没有 `tests/` 或 `test/` 目录，也没有 CTest 注册用例。详细证据、清点命令和 `tools/nametest.sh` 的执行解释见 [`reports/upstream-tests.md`](reports/upstream-tests.md)。上游测试分母为 0；该目录内消费者测试不计入上游数量。

## 适配和验证

目标 profile：`ci/conan/profiles/ohos-aarch64`（OHOS 6.0、aarch64、Clang 15、C++17）。

消费者测试通过 XaoS 自带的 `-render` 自动化入口，在设备上运行包内 `bin/XaoS`，从最小 Mandelbrot `.xaf` 输入生成 PNG，再实际解码检查图像结构、160×120 尺寸和非均匀像素。该测试不依赖启动交互事件循环，也不把进程退出码作为唯一结果。第一次运行发现 CMake 安装后的 XaoS ELF 虽保留 `.codesign` 段仍被系统拒绝执行；`package()` 在安装完成后剥除旧签名并重签最终 ELF，修复后 Conan G2 与 W3 消费者渲染测试均通过。

## 验证结果

- Conan 验证报告：G0–G3 PASS；G4 未核验，因为验证器未能定位 package ID，产物完整性检查没有执行。Conan 验证器中的 L2/L4/L5 因无本机 cache 路径跳过；W3 `build_and_test.sh` 的 L1、L4、L5 PASS，通用 L2 探针跳过（上游参数拼写差异，见上）。
- `python3 scripts/ohc-run.py finish xaos 4.3.4 built` 的 W3 本地 CI：通过，`.ci-result.json` 由 finish 工具生成，日志 SHA-256 已记录。
- `test_package` 在 HarmonyOS HongMeng Kernel 1.12.0 aarch64 上真实执行 `XaoS -render`，成功生成并解码 160×120 PNG，至少 1009 种不同像素；Conan G2 与 W3 各执行并通过一次。
- 上游正式测试数为 0；清点命令和证据见 [`reports/upstream-tests.md`](reports/upstream-tests.md)。消费者渲染测试单独统计，不并入上游测试分母。
- W3 的通用 L2 探针尝试 `--version`/`--help` 并跳过；上游只接受单连字符 `-help`，该选项会打印帮助但进程返回 255，因此不能记为 L2 PASS。真实渲染测试通过。SSH 会话没有活动的图形显示会话，因此本次验证离屏渲染，不覆盖交互窗口显示。
- `finish` 的 Conan G2 和 W3 已通过。后续归档阶段报告了仓库框架中的历史打包/知识图谱检查警告；按 R19 不生成废弃的手工 tar.gz 包。

### 对话 #1

用户确认适配官方 `xaos-project/XaoS` 4.3.4，并选择 HarmonyOS PC NATIVE 桌面应用路线。验证在用户提供的 HarmonyOS 6.0 aarch64 真机上完成。
