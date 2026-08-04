# libxml2 2.15.3.1 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包，支持两种消费形态。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 上游测试（随构建启用）

配方以 `LIBXML2_WITH_TESTS=ON` + `LIBXML2_WITH_PROGRAMS=ON` 接入上游测试套件
（CMake 的 add_suite/catalog 测试需 xmllint/xmlcatalog 目标，故不能纯库模式）。
OHOS 真机实跑：runtest 3880 用例通过率 97.3%，testapi/testcatalog/testchar/
testdict/testparser/testrecurse 全过；scripts/catalogs 系列与 runsuite 因上游
tarball 未打包辅助 cmake 脚本/xmlconf 数据而无法运行（上游缺陷，与平台无关）。
详见 `notes.md`。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## .so 签名

`package()` 会显式重签 `.so`：先用 `llvm-objcopy --remove-section .codesign` 剥除旧签名段，
再用 `binary-sign-tool sign -selfSign 1` 重新自签（SDK 工具链产出的 `.so` 自签无效，需事后重签）。

若构建过程有步骤在链接后改动 `.so` 二进制，需用 `--sign-so` 生成显式重签 recipe，或改用不改动 `.so` 的构建选项（推荐后者）。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
# 鸿蒙 PC：显式给 profile
conan install --requires=libxml2/2.15.3.1 -pr ohos-native
```

生成 `LibXml2Config.cmake`（`find_package(LibXml2)` 消费）与 `libxml-2.0.pc`（指向 cache）；运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=libxml2/2.15.3.1 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "libxml2/2.15.3.1:*" --file libxml2.tgz   # 出包机导出（recipe + 二进制）
conan cache restore libxml2.tgz                               # 目标机导入
```
