# lerc 4.0.4 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包，支持两种消费形态。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 源码

- 上游 tag: `js_v4.0.4`（GitHub 上无 `v4.0.4` tag，js_v4.0.4 包含完整 C++ 库源码）
- URL: `https://github.com/Esri/lerc/archive/js_v4.0.4.tar.gz`
- SHA256: `1dc090218387ab8ca615eefd844207be64454e37868b396f3e965ed0dcf83947`

## 补丁

| 补丁 | 说明 |
|------|------|
| `0001-src-LercLib-fpl_Compression.cpp.patch` | 添加 `#include <climits>` 修复 UINT_MAX 未声明 |

> 注：conan-center 的 `4.0.0-include-algorithm.patch` 不需要，js_v4.0.4 源码已自带 `#include <algorithm>`。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐使用 OpenHarmonyPCDeveloper 分发的 OHOS 适配版 conan。

## .so 签名

`package()` 中 `_sign_shared_libs()` 使用 `llvm-objcopy` 剥离旧 `.codesign` + `binary-sign-tool -selfSign` 重签。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
conan install --requires=lerc/4.0.4 -pr ohos-aarch64
```

生成 `lerc-config.cmake` / `Lerc.pc`；`find_package(LERC)` 消费，运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=lerc/4.0.4 -pr ohos-aarch64 \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "lerc/4.0.4:*" --file lerc.tgz   # 出包机导出
conan cache restore lerc.tgz                       # 目标机导入
```
