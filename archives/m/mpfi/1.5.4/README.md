# mpfi 1.5.4 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64)的 conan 包。1.5.4 相对 1.5.2 的适配要点
完全一致（同为 autotools + libtool + gmp/mpfr 依赖），配方沿用 1.5.2 实战
验证过的全部鸿蒙补丁性配置。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译（显式传 profile）
conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。
> 上游 159 个 `make check` 测试程序（tests/t*.c）在 build() 内真跑。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## ELF 签名

**签名默认关**：本 recipe 的 `package()` 不重签，靠链接器自签（autotools/libtool 的 `make install` 会用 hnp-clang/lld 重新链接，当场产出有效自签 ELF）。见 ML-0043。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
conan install --requires=mpfi/1.5.4 -pr ci/conan/profiles/ohos-aarch64
```

生成 `mpfi-config.cmake` / `mpfi.pc`（指向 cache）；`find_package(mpfi)` 消费，运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=mpfi/1.5.4 -pr ci/conan/profiles/ohos-aarch64 \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 依赖

- gmp/6.3.0.1（force，压过 mpfr 钉的 6.3.0）
- mpfr/4.2.2.1
- 上游要求：GMP ≥ 4.1.0、MPFR ≥ 4.0.1（configure.ac 内编译期断言）
