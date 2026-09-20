# libheif-tools 1.23.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4
- 依赖: 无（`BUILD_SHARED_LIBS=OFF`，产物只依赖 libc）
- 状态: built

## 本包与库包的分工

| 归档 | 交付物 |
|------|--------|
| archives/l/libheif/1.22.2 | libheif.a/.so、`libheif/*.h`、libheif.pc、lib/cmake/libheif |
| archives/l/libheif-tools/1.23.0 | bin/heif-info、heif-dec、heif-convert（符号链接）、heif-enc 与对应 man1 |

`cmake.install()` 会把库侧产物一起铺出来，`package()` 删掉 `include/`、`lib/`，
保留 `bin/` 与 `share/man/man1/`。

## 编译步骤

1. `source()`: `get()` 下载 `v1.23.0.tar.gz`
   （sha256 `50ea4fbd1e19c7b8820271d6d0c73f2623fec5d659ce9fae57e48dbeb94fab9a`），
   打补丁 0001
2. `cmake` 配置（关键开关见下）
3. `cmake --build`
4. `cmake --install` 后裁剪安装树，ELF 自签名

```python
tc.variables["BUILD_SHARED_LIBS"] = "OFF"
tc.variables["WITH_EXAMPLES"] = "ON"          # 命令行工具挂在这个开关下
tc.variables["WITH_EXAMPLE_HEIF_VIEW"] = "OFF"    # 需要 SDL2
tc.variables["WITH_EXAMPLE_HEIF_THUMB"] = "OFF"   # 需要 libpng，且不是 CLI
for opt in CODEC_OPTIONS:  tc.variables[opt] = "OFF"
for pkg in ("JPEG", "PNG", "WEBP", "TIFF"):
    tc.variables[f"CMAKE_DISABLE_FIND_PACKAGE_{pkg}"] = "ON"
tc.variables["WITH_LIBSHARPYUV"] = "OFF"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 处理 |
|---|------|------|------|
| 1 | `libheif/box.cc` 编译失败：`no member named 'all_of' / 'find' in namespace 'std::ranges'` | OHOS SDK 的 libc++（clang 15.0.4）只有 `std::ranges` 命名空间，没有 ranges 算法；上游用 `std::ranges::all_of` / `std::ranges::find` | 补丁 0001 换成 `std::all_of` / `std::find`（`<algorithm>` 同文件已包含） |
| 2 | configure 失败：`The imported target "WebP::sharpyuv" references the file ".../libsharpyuv.so.0.1.2" but this file does not exist` | `heifio/CMakeLists.txt` 用的是 `find_package(WEBP)`（全大写），配方里禁的是 `CMAKE_DISABLE_FIND_PACKAGE_WebP`，大小写不匹配；设备 `/usr/local` 的 `WEBPConfig.cmake` 被拉进来 | 开关名改成 `WEBP`，与上游逐字一致 |
| 3 | 同上，`libsharpyuv` 一族被探测 | 上游 `WITH_LIBSHARPYUV` 默认 ON，探测的是同一批 `/usr/local` 配置 | `WITH_LIBSHARPYUV=OFF`（本构建无编解码器，不需要它做色彩空间转换） |
| 4 | 新二进制无法执行 | 鸿蒙要求 ELF 带 `.codesign` | `package()` 内 `llvm-objcopy` + `binary-sign-tool` 自签名；`heif-convert` 是符号链接，跳过、随目标一起生效 |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0001-libheif-box-cc-ranges-algorithms.patch` | `libheif/box.cc` 三处 `std::ranges::all_of` / `std::ranges::find` 换成迭代器版 `std::all_of` / `std::find` |

## 验证结果

```bash
ohc-run.py conan-verify libheif-tools 1.23.0   # G0-G4 / L2 / L4 / L5 全绿
```

`test_package/test.sh` 的输出（夹具 `examples/example.avif` 以 base64 随包携带）：

```
[test] heif-info --version
[test] heif-dec --version
[test] heif-convert --version
[test] heif-enc --version
        [ok] all four tools report version 1.23.0
        [ok] heif-convert is a symlink
[test] fixture ready: example.avif (113604 bytes)
[test] heif-info example.avif
        [ok] container parsed (25 lines)
[test] heif-info missing.avif (expected failure)
        [ok] missing input rejected
All tests passed.
```

## 注意事项

- `heif-info` 1.23.0 的 25 行输出里有 `MIME type: image/avif`、`main brand: avif`、
  `image: 800x533 (id=1), primary`、`colorspace: YCbCr, 4:2:0`、`bit depth: 8`；
  断言直接对这几行做，不要凭印象写 `num images:` 之类的字段名。
- 库里已有的是 1.22.2（`archives/l/libheif`），本包用 1.23.0，两者同源但版本不同，
  拆包边界（`include/`、`lib/` 归库包）必须保持，避免同一文件两个属主。
- 编解码器全部关闭是刻意的取舍：`heif-enc` 因此不能真正编码，只能做容器层面的操作；
  如果后续需要编码能力，要先把对应的编解码器依赖引入制品仓。
