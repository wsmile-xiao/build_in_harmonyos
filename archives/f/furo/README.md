# furo

干净、可定制的 Sphinx 文档主题(A clean customisable Sphinx documentation theme)。

- 平台任务:`furo/2024.8.30`(自导入,积分赛-依赖 5 火种)
- 上游:https://github.com/pradyunsg/furo ;任务号 2024.8.30 无上游对应发布,
  基线取同时间线实际发布 **2024.8.6**(官方 PyPI wheel,溯源见 manifest.yaml / notes.md)
- 形态:**纯 Python/纯资产**(Sphinx 主题,85 文件,零编译),按数据/源码包豁免模式
  conan 化:noarch,build() 以 85 文件 size+sha256 钉死校验替代构建
- 消费:Sphinx `html_theme = "furo"`;配方导出 PYTHONPATH 与 FURO_THEME_DIR
- 许可:MIT
