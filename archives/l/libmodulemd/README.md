# libmodulemd

libmodulemd 是 Fedora Modularity 项目的 C 语言库，用于读写与校验模块元数据
（modulemd）YAML 文档：模块流（ModuleStream v1/v2）、模块索引（ModuleIndex）、
默认值（Defaults）、翻译（Translation）、废弃信息（Obsoletes），并随包提供
`modulemd-validator` 命令行校验工具。

## OHOS 适配

- **构建系统**: Meson；原生构建（build = target = OHOS/aarch64），clang 15，C11。
- **依赖链**: 仅 glib2（glib/gobject）+ libyaml；`rpmio=disabled` 免除 rpm
  整条依赖链（popt/sqlite/openssl/lua 等），压缩格式探测使用上游内置实现。
- **禁用项**: gobject-introspection、gtk-doc 文档、man 页、Python 2/3 绑定
 （OHOS 工具链缺失，均为上游官方 meson 选项）。
- **已知限制**: Python 绑定测试 34 项未运行（需 pygobject）；G_DEBUG
  fatal-warnings 的 debug 套件在新平台偏严格，失败时按日志逐项处理。
  详见各版本 `notes.md`。

## 依赖

- glib2 2.88.0
- libyaml 0.2.5

## 功能验证

```bash
pkg-config --modversion modulemd-2.0  # 期望输出: 2.15.3
modulemd-validator --version
```

## 参考

- 上游仓库: https://github.com/fedora-modularity/libmodulemd
- 发布包: https://github.com/fedora-modularity/libmodulemd/releases/tag/2.15.3
