# libminc 2.5.0 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包，`shared=True`（默认）产出 `lib/libminc2.so`。

## 出包（鸿蒙 PC CI）

```bash
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认
> 不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，
> 不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## ELF 签名（与本仓其他包的差异）

本 recipe **不重签**：用 `CMAKE_SKIP_RPATH=ON` 让 build 与 install 阶段都不写 RPATH，
CMake 的 install RPATH 改写被整体旁路，安装副本与 build 副本**字节全等**
（sha256 实测一致），原生 `.codesign` 链接器签名完好，无需重签。
代价是产物不带 RUNPATH——依赖解析（libhdf5/libnetcdf）由消费方的 conanrun 环境
或 `-Wl,-rpath` 提供，与仓库其他包的下游用法一致。

背景：上游 CMakeLists 给 minc2 设了 `INSTALL_RPATH`，CMake install 的 RPATH 改写
（含 SKIP_INSTALL_RPATH 的"清零"形态，实测仍有 143 字节 .dynstr 改动）会破坏
hnp 产物签名，加载器报 `Error loading shared library ... Permission denied`。
判据：打包副本与 build-tree 副本 sha256 对比。

## 消费

```bash
conan install --requires=libminc/2.5.0 -pr ohos-native
```

CMake 消费：`find_package(libminc CONFIG REQUIRED)` + `minc2` target
（cpp_info `cmake_target_name=minc2`）。公开头直接 include `<hdf5.h>`/`<netcdf.h>`，
消费方需同时依赖 hdf5/netcdf（cpp_info 已把两者 includedirs 合入）。

## 上游测试

上游 ctest 套件（`testdir/`，56 个注册用例）随配方 `build()` 的 `cmake.test()` 真跑；
`test_package/` 另做 MINC2+MINC1 双链路消费者断言（`H5Fis_hdf5`/`nc_inq_format`
底层指纹）。测试统计见 PR 正文与版本级 reports/test-report.md。

## 已知取舍（本版）

- `LIBMINC_MINC1_SUPPORT=ON`（MINC1 全功能，Debian 同开）。
- `LIBMINC_BUILD_EZMINC=OFF`：C++ 便利封装层（非核心格式能力）首版不启用。
- `LIBMINC_USE_NIFTI=OFF`：上游 ON 时走 ExternalProject 构建期外网拉取 nifti 源码，
  不可复现。
- 1 个测试补丁（`patches/0001-testdir-mincapi.c.patch`）：musl 未播种 `rand()`
  首值恒为 0，上游 mincapi 测试的「非法 id 应被拒绝」用例会命中合法 ICV id 0；
  补丁强制 id 落在 ≥2^30（恒高于 1000 槽位上限），平台无关地保持测试意图。
