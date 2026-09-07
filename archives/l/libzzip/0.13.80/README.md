# libzzip 0.13.80 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包。libzzip 即 **zziplib**
(gdraheim/zziplib)：基于 zlib 的 ZIP 读取库（zzip_open/zzip_read POSIX 风格 API）。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## 依赖

- zlib/1.3.1.1（本仓 Conan 包，唯一真实依赖）

## 上游测试

官方测试 `test/zziptests.py`（230 项 python unittest）在 `build()` 内真跑：
`--downloads=OFF` 跳过 134 项联网 CVE 测试；SFX 用例 (test_81000) 因 OHOS
内核拒绝 exec "zip前缀+ELF尾部" 拼接文件（EPERM）被显式排除（pattern 枚举法）。
其余 229 项全部在本机真跑：**Ran 229 — OK (skipped=134), 0 fail / 0 error**。

## ELF 签名

**本 recipe 显式重签**：`package()` 调 `_sign_binaries()`，对 `lib/**/*.so*` 与 `bin/` 下
真实 ELF 逐个 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`。

原因：cmake 走 SDK `ohos.toolchain` 产的 `.so` 自签无效（dlopen `Permission denied`）；而 install 阶段若复制或 strip 已链接产物，也会破坏链接器自签。
**产可执行文件的包 `bin/` 必须一起签**——只签 `.so` 会让 `bin/xxx` 被 exec 时报 `Operation not permitted`。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
# 鸿蒙 PC：显式给 profile
conan install --requires=libzzip/0.13.80 -pr ohos-native
```

生成 `zziplib-config.cmake` / `zziplib.pc`（指向 cache）；`find_package(zziplib)` 消费，
target `zziplib::libzzip`，运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=libzzip/0.13.80 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "libzzip/0.13.80:*" --file libzzip.tgz   # 出包机导出（recipe + 二进制）
conan cache restore libzzip.tgz                               # 目标机导入
```
