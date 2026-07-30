# gsl 2.8 — 鸿蒙 PC conan 制品

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

**签名默认关**：本 recipe 的 `package()` 不重签，靠链接器自签（autotools/libtool 的 `make install` 会用 hnp-clang/lld 重新链接，当场产出有效自签 ELF）。见 ML-0043。

若构建过程有步骤在链接后改动二进制（复制/strip/尾拼），须改用 `--sign-so` 重新生成，或改用不改动产物的构建选项（推荐后者）。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
# 鸿蒙 PC：显式给 profile
conan install --requires=gsl/2.8 -pr ohos-native
```

生成 `gsl-config.cmake` / `gsl.pc`（指向 cache）；`find_package(gsl)` 消费，运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=gsl/2.8 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "gsl/2.8:*" --file gsl.tgz   # 出包机导出（recipe + 二进制）
conan cache restore gsl.tgz                               # 目标机导入
```
