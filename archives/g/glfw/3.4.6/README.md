# glfw 3.4.6 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包，支持两种消费形态。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

> **cmake 库须走 ohos.toolchain（recipe 已自包含，无需改 profile）**：本库经 cmake 构建，须让 cmake 走 `ohos.toolchain.cmake`（`CMAKE_SYSTEM_NAME=OHOS` → 正确出 SONAME/版本软链 `libglfw.so.3`；否则退化成裸 `libglfw.so`、bridge 的 `-l:libglfw.so.3` 链接失败，见 ML-0035）。**`build()` 会自发现 toolchain**（优先 profile `[conf]` 的 `tools.cmake.cmaketoolchain:user_toolchain`，其次 `OHOS_NDK_HOME`，最后 glob `/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake`），所以 **`conan create -pr ohos-native` 裸跑即可，不依赖 profile host 段有没有配**（CI 模拟：撤掉 host user_toolchain 仍通过）。若你的 SDK 布局特殊，设 `OHOS_NDK_HOME` 或在 profile 配 user_toolchain 即可覆盖。

## 两个 .so（libglfw + libglfw_bridge）

GLFW 鸿蒙后端产**两个互为 `DT_NEEDED` 的 .so**（循环依赖，musl BIND_NOW dlopen 必须双向可解析，ML-0023）：

- `libglfw.so.3.4`（soname `libglfw.so.3`）— GLFW 主库，桌面 GL + Vulkan。
- `libglfw_bridge.so` — host HAP NAPI-import 的桥接库，供原生后端反调 ArkTS。

`build()` 复刻源码 `build-ohos.sh` 的 **two-pass**（Pass1 各自 `-z undefs` 编出、Pass2 互指对方重链记 `DT_NEEDED`），两个 `.so` 都进包 `lib/`。

## .so 签名

**签名默认关**：本 recipe 的 `package()` 不自签 `.so`，靠链接器自签（构建时 clang 直接产出有效自签 ELF，无需事后重签）。见 ML-0043。

若构建过程有步骤在链接后改动 `.so` 二进制，需用 `--sign-so` 生成显式重签 recipe，或改用不改动 `.so` 的构建选项（推荐后者）。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
# 鸿蒙 PC：显式给 profile
conan install --requires=glfw/3.4.6 -pr ohos-native
```

生成 `glfw-config.cmake` / `glfw3.pc`（指向 cache）；`find_package(glfw)` 消费，运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=glfw/3.4.6 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "glfw/3.4.6:*" --file glfw.tgz   # 出包机导出（recipe + 二进制）
conan cache restore glfw.tgz                               # 目标机导入
```
