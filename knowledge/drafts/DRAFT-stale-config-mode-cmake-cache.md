# DRAFT: CI Worker stale config-mode cmake package (absolute path) breaks downstream find_package

## 现象

CI Worker 上 conan create 的 cmake.configure() 阶段直接报错：

```
CMake Error at /storage/Users/currentUser/usr/local/lib/cmake/freetype/freetype-config.cmake:91 (message):
  The imported target "freetype" references the file

     "/storage/Users/currentUser/usr/local/lib/libfreetype.a"

  but this file does not exist.
Call Stack (most recent call first):
  CMakeLists.txt:741 (FIND_PACKAGE)
```

## 根因

已发布 freetype 包的 cmake 配置带打包者本机绝对路径（IMPORTED_LOCATION → /storage/Users/currentUser/usr/local/lib/libfreetype.a）。CI Worker 存在 <prefix>/lib/cmake/freetype/freetype-config.cmake（坏包残留，libX11-xcb.la 悬空路径同款），find_package(Freetype) 走 config-mode 加载它即炸。

配方旧方案仅置 FREETYPE_LIBRARY/FREETYPE_INCLUDE_DIR_* 为 NOTFOUND——只覆盖 module-mode 结果变量，config-mode 搜索仍会加载坏 config。

## 修复

`CMAKE_DISABLE_FIND_PACKAGE_<Pkg>=TRUE` 短路所有可选依赖的 find_package（31 个包 + X11）：

```python
for pkg in ("Freetype", "ilmbase", "Inventor", "Jasper", "OpenEXR",
            "OpenCascade", "COLLADA", "FBX", "ZLIB", "GDAL", "GTA",
            "CURL", "LibVNCServer", "DCMTK", "FFmpeg", "GStreamer",
            "GLIB", "DirectShow", "SDL2", "SDL", "Poppler-glib",
            "RSVG", "GtkGl", "DirectInput", "NVTT", "Asio",
            "ZeroConf", "LIBLAS", "Lua52", "Lua51", "GIFLIB",
            "JPEG", "PNG", "TIFF"):
    tc.cache_variables[f"CMAKE_DISABLE_FIND_PACKAGE_{pkg}"] = True
tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_X11"] = True
```

CMake 官方语义：视为 not found、不做任何搜索、不加载任何 config——坏 config 永不被读取。上游 CMakeLists 735 行注释自荐同款用法。<Pkg> 大小写必须与 find_package() 调用完全一致。

## 验证

- 本地 CMake 级对照实验：伪造坏 config（FATAL_ERROR 模拟）+ CMAKE_FIND_PACKAGE_PREFER_CONFIG → 无 DISABLE 变量复现报错；加 DISABLE 变量 configure 成功
- conan create 全量 + test_package 通过（本地）
- CI #44186 全绿（CI-018 Worker，同一台曾失败的机器）

## Fallback

必需依赖不能 disable 时：改写坏 config 的 IMPORTED_LOCATION 为 deps.package_folder 实际路径（libxfixes shadow/discard 手法变体），或向制品仓申请重发坏包。
