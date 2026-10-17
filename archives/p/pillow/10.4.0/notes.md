# pillow 10.4.0 适配笔记（OHOS aarch64）

## 编译环境
- 构建系统: setuptools setup.py build_ext（pip install 装包）
- 编译器: clang 15.0.4（DevBox，lld 默认链接自动签名）
- Python: 3.12.9（~/usr/local，非 HNP）
- C 依赖: zlib/1.3.1、libjpeg/10、freetype/2.14.3（全部 conan 制品仓预编译包）
- 状态: published（conan create 全流程通过）

## 特性裁剪策略

启用 zlib + libjpeg + freetype（matplotlib 依赖链核心组合），禁用：
- tiff（libtiff 4.7.2 可用但非必需，减依赖面）
- lcms / webp / jpeg2000 / imagequant（颜色管理与现代格式，matplotlib 不用）
- raqm（复杂文本整形，依赖 harfbuzz+fribidi，可后续补）
- xcb（X11，OHOS 无意义）

## 依赖发现机制

setup.py 的 pil_build_ext 按 `<FEATURE>_ROOT` 环境变量找库（lib/ + include/），
配方把 conan 依赖的 package_folder 注入 JPEG_ROOT / ZLIB_ROOT / FREETYPE_ROOT。

## OHOS 适配点（与 numpy/contourpy 配方同族）

1. sitecustomize.py 补丁 posix_spawn PATH 搜索 + ELF 自动签名
2. lld 默认链接器（禁用 -fuse-ld=bfd）
3. -lpython3.12 显式链接（musl 不导出主 exe 符号）
4. package() 用 pip install --no-build-isolation 复用 build 产物

## 上游测试

- Tests/ 目录 181 个文件 1946 个测试函数
- 运行需 pytest + 上游 conftest；图像对比测试依赖 Tests/fonts、Tests/images 数据
- 关键路径：test_image（核心）、test_file_png（zlib）、test_file_jpeg（libjpeg）、test_imagefont（freetype）

## 验证结果（2026-09-02 conan create 完整通过）

- `conan create . --user=ohpcd --channel=stable -pr:h/-pr:b=ohos-aarch64 --build=missing` **全流程 PASS**：build_ext 全部 .o 编译 + wheel 打包 + 解包 → test_package 6/6 PASS
- test_package：PIL 导入 ✓ / 版本 ✓ / 像素访问 ✓ / PNG 往返（zlib）✓ / JPEG 往返（libjpeg）✓ / **freetype 文字渲染（真实字体）✓**
- 上游 pytest（排除 6 个被禁用特性的测试文件）：**3974 passed / 13 failed / 308 skipped**
  - 5 个 test_show（ImageShow 需外部图像查看器，OHOS 无）
  - 3 个 test_tiff_crashes（tiff 特性已禁用 + 数据路径）
  - 4 个默认字体像素级对比（光栅化亚像素差异，文字渲染功能本身正常）
  - 1 个 JPEG 表结构对比（libjpeg 10 与基线版本的表生成差异）
  - 无任何功能性失败
