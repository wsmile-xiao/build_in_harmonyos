# libstroke 0.5.1 HarmonyOS PC 适配笔记

## 源码与许可核验

- 上游主页：`https://www.etla.net/libstroke/`。
- 上游原始发布包名称：`libstroke-0.5.1.tar.gz`。
- 当前上游下载入口已失效，因此使用 Gentoo 公共镜像中的同名原始发布包；其 SHA-256 为 `0da9f5fde66feaf6697ba069baced8fb3772c3ddc609f39861f92788f5c7772d`，与 Debian 源码包元数据记录一致。
- 许可证按上游 `COPYING` 和 `COPYRIGHT` 标记为 `GPL-2.0-only`。

## 源码与构建审计

核心库只有 `libstroke/stroke.c` 和公开头文件 `libstroke/stroke.h`。上游还包含可选的 GTK 1.x 包装库 `libgstroke`、Java 绑定及三个交互式演示，它们不属于无图形依赖的核心识别库。

上游 Autotools 文件生成于 2001 年，`configure` 即使构建核心库也会强制探测 X11。核心实现仅在定义 `STROKE_MOUSE_FOOTPRINTS` 时才引用 X11；本配方不定义该宏，并直接使用 Conan 配置的 OHOS Clang 编译核心源码，从而不引入无关的 X11 依赖，也不使用任何 `--build`、`--host` 或 `--target` 参数。

现代 C99 编译器不允许隐式声明 `strcpy`。补丁 `0001-include-string-header.patch` 仅补充标准头文件 `<string.h>`，不包含 HarmonyOS 条件分支，也不改变库行为。

## 上游测试审计

上游源码不存在 `make check`、`make test`、CTest、Meson test 或其他自动化测试入口，正式自动化测试数为 **0**。`tests/` 下存在三个需要人工图形交互的演示：

1. `tests/stroke_test.c`：X11 鼠标绘制演示，会打开窗口并等待鼠标输入；
2. `tests/gnome_stroke_test.c`：GTK 1.x 交互演示；
3. `tests/stroke_test.tcl`：Tk 交互演示。

这些文件未注册为上游自动化测试，也没有可判定通过/失败的无人值守断言，因此不计入上游测试用例数。适配后新增消费者测试覆盖九个核心 API 功能场景，并用编译期 `__OHOS__` 守卫增加一个 HarmonyOS 特有平台验证，共 **10** 个测试用例、**20** 个运行时断言，不少于上游实测数量。

## 测试覆盖

- 公共常量及头文件可用性；
- 空笔画和点数不足笔画的拒绝行为；
- 水平正向、水平反向、垂直向下、垂直向上和对角线笔画的序列转换；
- 完成一次转换后复用识别器处理下一条笔画；
- HarmonyOS 编译宏验证、真实静态链接和真机执行。

## 依赖与产物

- 第三方依赖：无；
- 系统链接库：`libm`；
- 默认产物：`lib/libstroke.a`、`include/stroke.h` 及许可证文件；
- 不生成命令行工具，因此无需 `commands.json`。

## 最终状态

配方、补丁、包元数据和消费者测试均已完成；HarmonyOS PC arm64 真机上的 Conan 干净构建、真实链接和全部 20 个运行时断言通过。
