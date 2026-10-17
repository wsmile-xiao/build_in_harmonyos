# libtiff 4.7.0 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包，支持两种消费形态。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译（CI 同款 profile）
conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## 编解码后端（8 个全开）

zlib、libdeflate、JPEG(libjpeg-turbo)、Zstd、WebP、LERC、JBIG、LZMA 均由 conan 依赖提供
（`requirements()`），不依赖设备预装系统库。test_package 对 8 后端做写读回环断言
（WEBP 走 RGB + `TIFFTAG_WEBP_LOSSLESS` 无损）。

## 4.7.0 与 4.7.2 的差异

- C++ 库开关名：4.7.0 是 `cxx`（4.7.2 改名 `tiff-cxx`），本配方 `-Dcxx=OFF` 纯 C 库。
- 其余构建选项与 4.7.2 同口径（工具/测试/文档/contrib 全关，8 后端全开）。

## .so 签名

`package()` 内对产物 `.so` 做 `llvm-objcopy --remove-section .codesign` +
`binary-sign-tool sign -selfSign 1` 显式重签（见 conanfile `_sign_shared_libs`）。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
conan install --requires=libtiff/4.7.0 -pr:h ohos-aarch64
```

生成 `TiffConfig.cmake` / `libtiff-4.pc`；`find_package(TIFF)` → `TIFF::tiff` 消费，运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=libtiff/4.7.0 -pr:h ohos-aarch64 \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "libtiff/4.7.0:*" --file libtiff.tgz   # 出包机导出（recipe + 二进制）
conan cache restore libtiff.tgz                               # 目标机导入
```
