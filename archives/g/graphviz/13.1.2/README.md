# graphviz 13.1.2 — 鸿蒙 PC conan 制品

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

原因：签名是内容哈希（存在 ELF 的 `.codesign` 节），**链接之后任何改字节的步骤都会让它失效**——meson install 抹除 RUNPATH（把字符串原地涂成 X）、libtool relink、strip/objcopy/patchelf 都是。复制本身不破坏签名。cmake 走 SDK `ohos.toolchain` 产的 `.so` 自签也无效。
**产可执行文件的包 `bin/` 必须一起签**——只签 `.so` 会让 `bin/xxx` 被 exec 时报 `Operation not permitted`。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
# 鸿蒙 PC：显式给 profile
conan install --requires=graphviz/13.1.2 -pr ohos-native
```

生成 `graphviz-config.cmake` / `libgvc.pc`（指向 cache）；`find_package(graphviz)` 消费，运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=graphviz/13.1.2 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "graphviz/13.1.2:*" --file graphviz.tgz   # 出包机导出（recipe + 二进制）
conan cache restore graphviz.tgz                               # 目标机导入
```
