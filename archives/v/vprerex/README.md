# vprerex

vprerex（visual prerex）是 prerex 先修课图表体系的 Qt-5 图形前端与 PDF
预览器：读取/编辑以 prerex 格式（`\begin{chart}` 环境）描述的课程图表，
并可把图表中课程框、箭头中点、背景点的坐标经剪贴板回传给 `prerex`
命令行编辑器，实现"点图即取坐标"的可视化编辑。

- 上游: <http://www.ctan.org/tex-archive/graphics/prerex>（CTAN prerex 宏包）
- 组件源码: `prerex/doc/vprerex-6.5.1.tar.gz`（同一宏包还含 prerex.sty / prerex）
- 版本: 6.5.1（ChangeLog: "modified for qt5 and poppler-qt5"，2017-11-26）
- 许可证: GPL-2.0-or-later
- 唯一构建描述: qmake 工程 `vprerex.pro`

## HarmonyOS PC 适配（aarch64 / musl / clang 15）

| 项 | 说明 |
|----|------|
| Qt5 | conan 包 `qt5-qtbase/5.15.2.2`（Core/Gui/Widgets） |
| Poppler | conan 包 `poppler/25.12.0.1`（**core** 库 `libpoppler.so` + `include/poppler` 头） |
| poppler-qt5 绑定 | 制品仓 poppler 全版本 `ENABLE_QT5=OFF`（无 Qt 绑定），也无独立 `poppler-qt5` 包 → 本适配新增 **poppler-qt5 兼容 shim**（`patches/0002`），在 poppler core 之上重实现 vprerex 用到的 `Poppler::Document / Page / Link / LinkBrowse` 子集（文档加载、Splash 渲染、链接注记提取），上游 3 个 `.cpp` / 2 个 `.h` 源文件零修改 |
| 构建 | 自研 CMakeLists（`patches/0001`）替换上游 qmake 工程；moc/uic 由 `qt5-qtbase/bin` 显式调用；shim 以 C++23 编译（poppler core 头需 C++20+） |
| 依赖冲突 | `qt5-qtbase` 链 `zlib/1.3.1`、`poppler` 链 `zlib/1.3.1.1` → consumer 侧 override 统一到 `1.3.1.1` |
| 测试 | 上游无测试套件（见 `6.5.1/test_package/MANIFEST.yml` 清点）；OHOS 侧新增 headless 测试：`--version` / `--help` 冒烟 + `--check-pdf <pdf>` 经 shim 加载/渲染/提取链接 |

## 用法

```sh
vprerex                       # 打开文件选择对话框
vprerex basefile [chartfile]  # 编辑 LaTeX 先修课图表
vprerex file.pdf              # 以最简 PDF 查看器方式打开
vprerex --version | --help    # 无 GUI 入口（OHOS 无显示环境验证用）
vprerex --check-pdf file.pdf  # 无 GUI 入口：经 poppler-qt5 shim 加载/渲染/取链接
```

> 运行时调用 `xterm` 与 `prerex` 编辑器；OHOS 上若无 xterm，可单独启动
> `prerex`（两者均为独立组件，不属于本包）。
