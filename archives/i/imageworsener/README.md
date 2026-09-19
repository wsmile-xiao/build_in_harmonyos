# imageworsener

ImageWorsener 是命令行图像处理工具与 C 语言库，支持 PNG/JPEG/BMP 读写、
实验性 WebP、只读 GIF 及 PNM/MIFF/TIFF 编码，提供缩放/重采样、抖动、
灰度化、背景合成等能力。

## OHOS 适配

- 构建系统: Autotools（configure + make），源码包自带预生成的 configure。
- 依赖: zlib、libpng、libjpeg、libwebp（制品仓已有版本，全启用）。
- 上游测试: `make check` 运行 `tests/runtest`，比对 196 个期望产物；
  补丁使脚本退出码真实反映比对结果。
- 产物: `libimageworsener` 静态库、`imagew` 命令行工具、`imagew.h` 头文件。

## 参考

- 官网: https://entropymine.com/imageworsener/
- 上游仓库: https://github.com/jsummers/imageworsener
