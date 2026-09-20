# vfit

Variable Font Instancing Tool — generate custom, static instances of a variable font defined in a configuration file.

- 上游: https://github.com/jonpalmisc/vfit
- 版本: 2.1.0
- 许可证: MIT
- 构建: 纯 Python (poetry), `pip --prefix` 安装, 无编译步骤
- 产物: `lib/pythonX.Y/site-packages/vfit` + `bin/vfit` (console_script `vfit.app:main`)
- 依赖: fonttools, tqdm, brotli (pip 运行时依赖, 构建阶段预装)
