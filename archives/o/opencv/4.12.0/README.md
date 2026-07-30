# opencv 4.12.0 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包，支持两种消费形态。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## ELF 签名

**本 recipe 显式重签**：`package()` 调 `_sign_binaries()`，对 `lib/**/*.so*` 与 `bin/` 下
真实 ELF 逐个 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`。

原因：cmake 走 SDK `ohos.toolchain` 产的 `.so` 自签无效（dlopen `Permission denied`）；而 install 阶段若复制或 strip 已链接产物，也会破坏链接器自签。
**产可执行文件的包 `bin/` 必须一起签**——只签 `.so` 会让 `bin/xxx` 被 exec 时报 `Operation not permitted`。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
# 鸿蒙 PC：显式给 profile
conan install --requires=opencv/4.12.0 -pr ohos-native
```

用 **OpenCV 自带的** `OpenCVConfig.cmake`（装在 `lib/cmake/opencv4/`），本配方设了
`cmake_find_mode=none` 并把该目录放进 `builddirs`——因为上游的 config 定义了全部 `opencv_*`
target、并正确处理内链的 3rdparty 静态库（libtiff/protobuf/quirc/ade），比 conan 生成的完整：

```cmake
find_package(OpenCV REQUIRED)
target_link_libraries(app PRIVATE ${OpenCV_LIBS})
```

pkg-config 消费用 `opencv4`。运行期 `source conanrun.sh`。

> **头文件在 `include/opencv4/`**（`#include <opencv2/opencv.hpp>`），配方已声明进
> `cpp_info.includedirs`，消费方无需自己拼这一层。

## 消费 B：裸程序（设备 ~/usr/local）

```bash
conan install --requires=opencv/4.12.0 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`。

> ⚠️ 本包接了 ffmpeg，`libopencv_videoio.so` 会 `DT_NEEDED` 其 `libav*`，**产物不自包含**。
> 必须部署整个依赖图（deployer 会自动展开），单拷 opencv 会在加载期报
> `Error loading shared library`。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "opencv/4.12.0:*" --file opencv.tgz   # 出包机导出（recipe + 二进制）
conan cache restore opencv.tgz                               # 目标机导入
```
