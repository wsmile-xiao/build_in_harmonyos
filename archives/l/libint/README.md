# Libint (1.x / Libint1)

Libint 是用于计算高斯函数上两算符分子积分的 C/C++ 库（量子化学电子积分库），
由 Edward F. Valeev 开发。本归档适配的是 **Libint1 系列 1.2.1**（`libint`），
上游仓库：<https://github.com/evaleev/libint>。

> 与同仓库另一归档 `libint2`（Libint2 系列，v2.7.2）是**不同代码库**：
> Libint1 的源码树通过构建期 `libint_compiler`（纯 C 生成器）生成积分核，
> 而 libint2 的 release 资产是预生成库 tarball。

## 特性

- 1/2/3/4 中心两电子排斥积分（ERI），最大角动量由 `MAX_AM_ERI` 控制
  （默认 4 → `LIBINT_MAX_AM=5`，覆盖到 d 壳层）
- C API（`libint.h`）：`init_libint_base` / `init_libint` / `free_libint` /
  `libint_storage_required` / `build_eri` kernel 分发表
- 导数积分库 `libderiv.a`（随包安装到 `lib/`，默认目标不暴露）
- CMake package config（`LibintConfig.cmake`，`Libint::int` 目标）

## 依赖

**无外部 Conan 依赖**。`libint.a` 的 `extern "C"` 入口纯 C 可链接，不需要
GMP/MPFR/Boost/Eigen（那些属于 libint2 / libint 编译器高级路径），也不需要
`-static-libstdc++` / `-lm`。

## 构建要点（OHOS / HarmonyOS PC）

- 选用上游 **CMake（Psi4 移植）路径**，而不是 autotools：CMake 路径不需要
  perl/autotools（`configure.ac`/`objectdir.pl` 仅 autotools 路径需要）。
- `src/CMakeLists.txt` 用 `ExternalProject` 链：
  `libint_compiler`（C 生成器）→ 生成 `libint_library` 源码 → 编译
  `libint.a`/`libderiv.a`。生产静态库（`BUILD_SHARED_LIBS=OFF`）。
- `ENABLE_XHOST=OFF` 去平台相关 `-march=native`，保证可复现。
- `generate()` 显式设 `CMAKE_INSTALL_PREFIX` 到自包含 staging 前缀
  `${build_folder}/_install`（上游把 install DESTINATION 固化为绝对路径，
  conan 默认 `--prefix` 覆盖不了），`package()` 里 `cmake --install .` 后整目录
  拷入 `package_folder`。
- `cpp_info.libs=["int"]`（产物 `libint.a`），cmake 目标 `Libint::int`。

## 上游测试

libint 1.2.1（Libint1 源码树）**没有自动化测试套件**（审计见
`1.2.1/test_package/MANIFEST.yml` 的 `upstream_test_audit`），按 no_tests 口径
上报。功能正确性由 `test_package` 的 C 消费者测试（10 条真实 API 断言，ctest
注册 1 个用例）覆盖。

## 构建规模（供超时预算参考）

`MAX_AM_ERI=4`（LIBINT_MAX_AM=5）下构建量适中（数百个生成 kernel 源文件）；
更高 `MAX_AM_ERI` 会显著增长（约与 AM^4 成正比）。可通过
`-o libint/*:max_am_eri=N` 调整（不同值产生不同 Conan 包 ID）。
