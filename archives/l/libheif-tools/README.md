# libheif-tools

`heif-info` / `heif-dec` / `heif-convert` / `heif-enc` —— libheif 自带的 HEIF/AVIF 容器命令行工具。

## Description

- `heif-info`：打印容器的结构信息（MIME type、brand、每张图的尺寸与色彩信息、
  metadata、属性等）。
- `heif-dec`：解出容器里的图像；`heif-convert` 是它历史上的名字，上游装成符号链接，
  本包保留了这个链接。
- `heif-enc`：把图像打包进 HEIF/AVIF 容器。

库本体（`libheif.a/.so`、头文件、`libheif.pc`、`lib/cmake/libheif`）属于
`archives/l/libheif`，本包只交付 `bin/` 下的可执行文件和它们对应的 man1。

## Project URL
https://github.com/strukturag/libheif

## License
LGPL-3.0-or-later

## HarmonyOS 适配说明

### 构建信息
- **版本**: 1.23.0（库里已有的是 `archives/l/libheif/1.22.2`，两者同源工程）
- **构建系统**: CMake
- **编译器**: clang 15.0.4
- **链接方式**: `BUILD_SHARED_LIBS=OFF`，静态链接，产物只依赖 libc

### 与库包的分工
`cmake.install()` 会把静态库、头文件、`libheif.pc` 和 `lib/cmake/libheif` 一并铺出来，
`package()` 里删掉 `include/` 与 `lib/`，只留 `bin/` 和 `share/man/man1/`，
保证同一个文件只有一个属主。

### 平台限制与补丁
| 问题 | 根因 | 处理 |
|------|------|------|
| `box.cc` 编译报 `no member named 'all_of' in namespace 'std::ranges'` | OHOS SDK 自带的 libc++（clang 15.0.4）只有 `std::ranges` 命名空间，**没有任何 ranges 算法**；上游用的正是 `std::ranges::all_of` / `std::ranges::find` | 补丁 `0001-libheif-box-cc-ranges-algorithms.patch` 换成等价的 `std::all_of` / `std::find`（同文件已含 `<algorithm>`） |
| `heifio` 的 WebP 探测把系统里坏的 CMake 配置拉进来 | `heifio/CMakeLists.txt` 写的是 `find_package(WEBP)`（全大写），而配方里禁的是 `CMAKE_DISABLE_FIND_PACKAGE_WebP`，大小写不匹配；设备 `/usr/local` 的 `WEBPConfig.cmake` 引用了不存在的 `libsharpyuv.so.0.1.2`，configure 直接失败 | 探测开关逐字对上上游的写法（`WEBP`），并额外关掉同样探测系统 libwebp 的 `WITH_LIBSHARPYUV` |
| 新二进制无法执行 | 鸿蒙安全机制要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名（`heif-convert` 符号链接跟随目标签名） |

### 构建取舍
上游没有 `tools` 开关，命令行工具挂在 `examples/CMakeLists.txt` 下、由
`WITH_EXAMPLES` 控制，所以整个构建图都会编出来，交付时才裁剪。编解码器全部关闭
（`WITH_LIBDE265` / `WITH_DAV1D` / `WITH_AOM_*` / `WITH_X265` …），
这是一份容器层面的构建：工具能解析、拆包容器，不做编码解码。

### 使用方式
```bash
heif-info image.avif
heif-info --version
heif-dec image.avif out.png
heif-enc -o out.avif in.png          # 需要本构建未启用的编解码器
```

### 验证结果
- `ohc-run.py conan-verify libheif-tools 1.23.0`: G0-G4 / L2 / L4 / L5 全绿
- `test_package/test.sh`: 四个工具的 `--version`、`heif-convert` 是符号链接、
  官方 AVIF 夹具解析（MIME type / main brand / primary 图像尺寸 / 色彩空间 / 位深）、
  以及"缺失输入必须非 0 退出"的反例
