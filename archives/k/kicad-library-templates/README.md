# kicad-library-templates

KiCad 官方工程模板和 worksheet 资源的 HarmonyOS Conan 归档。

## 内容

- 版本：10.0.5
- 上游：<https://gitlab.com/kicad/libraries/kicad-templates>
- 安装目录：`share/kicad/template`
- 资源：19 个工程模板、36 个 worksheet，以及上游模板工程中的全部资源文件
- 依赖：无编译依赖和运行时依赖

该包不提供链接库或命令行程序。下游 KiCad 工具通过 Conan 的资源目录元数据或
`KICAD_TEMPLATE_DIR` 运行环境变量定位模板。

## 许可证

上游模板资源使用 KiCad Libraries CC-BY-SA 4.0 许可证及其设计文件例外，
许可证文件随包安装到 `licenses/LICENSE.md`。
