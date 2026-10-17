# sfizz 1.2.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-26
- 编译器: clang/clang++（OHOS SDK 15.0.4）
- 状态: built（conan-verify 全通过，待 submit 后 CI 发布）

## 编译步骤

```bash
# 1. 依赖注入（制品仓拉取，均为 vendored 内部依赖，实际主库编译不依赖外部 conan 包）
conan install -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -of=. \
  -g CMakeToolchain -g CMakeDeps

# 2. 配置（SFIZZ_SHARED=ON 使库安装规则生效；BUILD_SHARED_LIBS=OFF 由补丁强制）
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_CXX_STANDARD=20 \
  -DCMAKE_CXX_STANDARD_REQUIRED=ON -DSFIZZ_TESTS=ON -DBUILD_TESTING=ON -DSFIZZ_SHARED=ON

# 3. 编译
make -j2

# 4. 测试（本地全量）
ctest  # 566/566 通过

# 5. staging 安装验证
make install DESTDIR=$TEST_PREFIX  # libsfizz.so + 3 头文件 + pkgconfig + sfizz_render
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub tarball 中 external/abseil-cpp、filesystem、simde、st_audiofile/thirdparty/* 为空 | git submodule 未随 tarball 分发 | conanfile.py source() 按 sfizz 1.2.3 锁定 commit 单独下载 6 个 submodule |
| 2 | C++20 编译失败：`u8"♯"` 无法构造 `std::string_view` | C++20 中 u8"" 是 `const char8_t[]`，无法隐式转 `basic_string_view<char>` | 去掉 u8 前缀（源文件 UTF-8 编码），Opcode.cpp/OpcodeT.cpp 共 10 处 |
| 3 | `std::result_of` 编译失败 | C++20 移除 `std::result_of` | 改用 `std::invoke_result_t`（ThreadPool.h） |
| 4 | `fs::path::u8string()` 赋值失败 | C++20 返回 `std::u8string` 无法赋给 `std::string` | 改用 `.string()`（Synth.cpp、AudioFile.cpp、DecentSampler.cpp、sfizz_render.cpp） |
| 5 | conan create 报 `BadZipFile` | codeload URL `.../tar.gz/refs/tags/1.2.3` 不以 .tar.gz 结尾，conan get() 无法推断压缩格式 | conandata.yml sources 显式 `filename: "sfizz-1.2.3.tar.gz"` |
| 6 | test_package 找不到 libsfizz | default shared=False 时 SFIZZ_SHARED=OFF，库/头文件/pkgconfig 不安装 | default_options shared=True |
| 7 | 运行时找不到 libwavpack.so | conan CMakeToolchain SharedLibBock 强制注入 BUILD_SHARED_LIBS=ON（CACHE 变量，tc.variables 无法覆盖），wavpack 等 vendored 子库变共享且 sfizz 不安装 | 顶层 CMakeLists 补丁 `set(BUILD_SHARED_LIBS OFF)`（必须放在 include(SfizzDeps) 之前，普通变量遮蔽 CACHE，子目录继承静态） |
| 8 | test_package region 数为 0 | test.c 引用 kick.wav 外部音频文件，测试环境无此文件 | 改为纯控制 region（无 sample），聚焦 API 实质调用 |
| 9 | [Files] Case sentitiveness 测试失败 | OHOS HMDFS 大小写不敏感（实测同 inode），上游测试在非 Win/mac 平台硬编码 caseSensitiveFs=true | 改为运行时探测（fs::exists 检查文件大小写变体） |

## 源码修改

9 个补丁（见 patches/）：
- 0001-CMakeLists.txt.patch：`set(BUILD_SHARED_LIBS OFF)`（vendored 子库静态）
- 0002-clients-sfizz_render.cpp.patch：u8string→string
- 0003-external-threadpool-ThreadPool.h.patch：result_of→invoke_result_t
- 0004-src-sfizz-Opcode.cpp.patch：u8 字面量去前缀
- 0005-src-sfizz-Synth.cpp.patch：u8string→string
- 0006-src-sfizz-import-foreign_instruments-AudioFile.cpp.patch：u8string→string×2
- 0007-src-sfizz-import-foreign_instruments-DecentSampler.cpp.patch：u8string→string
- 0008-tests-FilesT.cpp.patch：Case sentitiveness 运行时探测
- 0009-tests-OpcodeT.cpp.patch：u8 字面量去前缀×8

## 依赖版本

- 主库编译依赖全部为 vendored（abseil-cpp c2435f8、ghc-filesystem 8a2edd6、simde 2bf459d、st_audiofile thirdparty：dr_libs 4b3d078/libaiff 78864a4/wavpack 07ffb33）
- conan-verify 注入验证包（不参与主库链接）：absl/20260526.0、simde/0.8.2、ghc-filesystem/1.5.14、pugixml/1.16、cxxopts/3.3.1、kissfft/131、libsndfile/1.2.2、jack/1.9.22、libsamplerate/0.2.2、catch2/3.16.0、benchmark/1.9.5

## 验证结果

```bash
# 本地编译
make -j2  # 100% 成功（sfizz_static/shared/import/render/tests）

# 本地测试（W3）
ctest  # 566/566 通过（100%）

# Conan 配方验证（G2 conan create 从干净源码构建 + test_package 消费者测试）
conan-verify sfizz 1.2.3  # G0-G4 + L2/L4/L5 全通过
```

## 交付物

- conanfile.py（CMake 配方 + submodule 获取）
- conandata.yml（官方 codeload 源 + sha256 + 9 补丁引用）
- test_package/（test.c 实质调用 sfizz C API）
- patches/（9 个）
- commands.json（sfizz_render CLI 声明）
- 产物：libsfizz.so + sfizz.h/sfizz.hpp/sfizz_message.h + pkgconfig/sfizz.pc + sfizz_render

## 注意事项

- 本地 cmake 运行需 `LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos`（OHOS SDK libc++）
- conan-verify/conan create 同样需要该 LD_LIBRARY_PATH 环境
---

**编译结束**: 2026-09-26 03:41
**最终状态**: built
