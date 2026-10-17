# jansson 2.14 适配笔记

## 编译环境
- 构建系统: cmake（GitHub archive 源码包无预生成 configure；本机/CI 无 automake，与 2.15.x 系列先例一致走 CMake）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4（aarch64-linux-ohos musl 交叉）
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/akheron/jansson/archive/refs/tags/v2.14.tar.gz
   sha256: c739578bf6b764aa0752db9a2fdadcfe921c78f1228c7ec0bb47fa804c55d17b
2. CMake 配置: `cmake <src> -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_C_FLAGS="--target=aarch64-linux-ohos -D__MUSL__"`
3. 编译: `make -j4`
4. 测试: `ctest --output-on-failure` — 全部 213 个测试通过 (100%)
5. 安装: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 报 "Compatibility with CMake < 3.5 has been removed" | jansson 2.14 的 CMakeLists.txt 声明 cmake_minimum_required(VERSION 2.8)，CMake 4.x 移除兼容 | CMakeToolchain 设 CMAKE_POLICY_VERSION_MINIMUM=3.5（上游 2.15.1 已自行提升最低版本） |
| 2 | libjansson.so 无 DT_SONAME | CMake 默认不设 SONAME（无版本化实体时） | package() 用 patchelf 补 SONAME + 剥 .codesign + binary-sign-tool 自签（复用 2.15.1.1 修复方案，防下游 DT_NEEDED 写入构建机绝对路径） |
| 3 | 手动探索时 sysroot 报错 Scrt1.o not found | 手动 --sysroot=/data/service/hnp/sysroot 指错路径（真实 sysroot 在 ohos-sdk 下） | 不需要显式 sysroot：/data/service/hnp/bin/clang wrapper 自带正确解析，conan profile 的 tools.build:compiler_executables 即正确 |

## 依赖版本

- cmake 4.1.2
- clang 15.0.4
- 无外部运行时依赖（仅需 libc）

## 验证结果

```bash
$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 213
Total Test time (real) = 4.72 sec
```

上游测试构成：
- api: 17 个可执行测试（test_array/test_chaos/test_copy/test_dump/test_dump_callback/test_equal/test_fixed_size/test_load/test_load_callback/test_loadb/test_memory_funcs/test_number/test_object/test_pack/test_simple/test_sprintf/test_unpack）
- suites 数据驱动: encoding-flags 12 + valid 34(+strip 变体) + invalid 50(+strip 变体) + invalid-unicode 18

## 注意事项

- jansson 2.14 同时支持 autotools 和 CMake；GitHub archive 包（codeload 生成）只含 configure.ac 不含 configure，需要 automake/aclocal/libtoolize 才能 bootstrap，CI 环境无这些工具时用 CMake 路径
- CMake 4.x 对老 policy 声明的兼容移除是通用坑（所有声明 <3.5 的老项目都会遇到），CMAKE_POLICY_VERSION_MINIMUM=3.5 是标准解法
- shared 库 SONAME 缺失问题与 2.15.1 相同，修复方案已固化在 conanfile.py 的 _set_soname_and_resign()
---

**编译结束**: 2026-09-04 02:09
**最终状态**: built（conan-verify 8 道门禁通过；CI 合并 upload 后由平台升级）
