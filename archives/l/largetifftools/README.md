# LargeTIFFTools

## 简介

LargeTIFFTools 是一套用于处理大型 TIFF 图像文件的命令行工具集，专门针对超大尺寸 TIFF 文件进行了优化。该工具集适用于医学影像、卫星图像、地理信息系统等领域的大规模图像处理场景。

## 功能组件

- **tifffastcrop**: 快速裁剪大型 TIFF 文件，支持按区域提取
- **tiffmakemosaic**: 将多个 TIFF 图块拼接成大型马赛克图像
- **tiffsplittiles**: 将大型 TIFF 文件分割成多个小图块

## OHOS 适配

### 构建特点
- 构建系统：autotools（标准流程）/ 手动 Makefile
- 编译器：clang/clang++
- 编译难度：🟡 中等

### 特殊说明
1. **config.status 权限问题**：在鸿蒙环境下，autotools 的 config.status 脚本在创建临时目录时可能遇到权限问题（"Permission denied"），需要采用手动 Makefile 方式编译
2. **手动编译流程**：
   ```bash
   # 设置环境变量
   export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib
   export CFLAGS="-I/storage/Users/currentUser/usr/local/include"
   export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib -Wl,-rpath,/storage/Users/currentUser/usr/local/lib"

   # 手动创建 config.h（见 patches/0002-config.h.in.patch）
   # 手动创建 Makefile

   make -j1
   make install DESTDIR=/path/to/install
   ```
3. **libpng 静态库**：系统中的 libpng 为静态库（libpng16.a），需要额外链接 zlib

## 依赖

| 依赖库 | 版本要求 | 用途 |
|--------|----------|------|
| libtiff | >= 4.0 | TIFF 文件读写 |
| libjpeg | any | JPEG 压缩支持 |
| libpng | >= 1.6 | PNG 压缩支持 |
| zlib | >= 1.2 | 压缩库 |

## 使用示例

```bash
# 裁剪 TIFF 文件（提取区域）
tifffastcrop -x 100 -y 100 -w 1000 -h 1000 input.tif output.tif

# 创建马赛克图像
tiffmakemosaic -i tile_*.tif -o mosaic.tif

# 分割大型 TIFF 为图块
tiffsplittiles -i large.tif -s 512x512 -o tiles/
```

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.4.1 | built | 2026-06-11 | 首个 OHOS 适配版本 |

## 许可证

GNU GPL v3 或更高版本

## 参考链接

- 官网: https://github.com/gn-nhc/largetifftools
- 源码: https://github.com/gn-nhc/largetifftools
- 作者: Christophe Deroueners (2013-2021)

## 注意事项

1. **构建系统兼容性**：由于 autotools 在鸿蒙环境下存在权限问题，建议后续版本考虑：
   - 使用 CMake 替代 autotools
   - 或创建补丁修复 config.status 权限问题

2. **动态库路径**：运行时需要设置 `LD_LIBRARY_PATH` 或使用 `-Wl,-rpath` 链接选项

3. **格式警告**：存在少量类型格式化警告（uint64_t vs unsigned long long），不影响功能