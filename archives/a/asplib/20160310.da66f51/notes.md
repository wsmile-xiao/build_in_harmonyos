# asplib 20160310.da66f51 适配笔记

## 编译环境
- 构建系统: cmake (cmake_minimum_required 2.6; UseMultiArch.cmake + asplib_helpers.cmake)
- 编译日期: 2026-08-26
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos, /data/service/hnp/bin)
- 目标平台: OpenHarmony PC arm64 (OHOS, CMAKE_SYSTEM_NAME=HarmonyOS)
- 状态: built

## 编译步骤

1. init-build（本地 tarball 直供，无网络下载）：
   `python3 ohc-run.py init-build asplib 20160310.da66f51 --url=$TMPDIR/builds/asplib-20160310.da66f51.tar.gz`
2. 手动编译（Step 2，模式 B）：
   ```
   cd $BUILD_SRC_DIR && mkdir build && cd build
   cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
   make -j2
   make install DESTDIR=$TEST_PREFIX
   ```
   产物：`libasplib.a`（静态库，2 个源文件：Biquad_Native + BiquadFactory），headers 安装到
   `include/asplib/{Biquads,interfaces,asplib_utils}`，另带 `lib/pkgconfig/asplib.pc` 和
   `lib/asplib/asplib-config.cmake`（配方中移除这两个 embed 编译前缀的配置文件）。
3. Staging 验证：用 OHOS clang 编译测试程序链接 staging 的 `libasplib.a`，创建 2 级 Biquad 链、
   设置系数、处理 8 样本，输出非零且有限（out[0]=0.05 符合手算），直接使用 CBiquad_Native 也通过。
4. make check：本项目 CMakeLists 无 test/check 目标（无 add_test/enable_testing），
   改用静态验证（llvm-nm 符号齐全、readelf ELF64 arm64 无 TEXTREL）。
5. conan-init → conan-verify：G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS（见 reports/conan-verify-report.md）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连不通，conan create 拉不到源码 | 网络限制 | conandata.yml 使用 ghfast.top 代理 URL（内容为官方 archive/da66f51.tar.gz，sha256 与本地 tarball 一致 94b140...），R39 合规 |
| 2 | CMake 4.1 拒绝 cmake_minimum_required(2.6) | CMake 4.x 移除 <3.5 兼容 | generate() 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | 上游 resetState() 死循环 | `for(kk=0; kk<4; ii++)` 内层循环不推进 kk | 补丁 0001：ii++ → kk++（track-edit 追踪） |
| 4 | OHOS 上 CMAKE_SYSTEM_NAME=HarmonyOS 不匹配 "Linux" 分支 | 平台名映射 | 无需处理：OHOS clang 定义 __linux__，asplib_base_os.h 的 TARGET_LINUX fallback 生效（native C++ 路径，无 SSE 需求） |
| 5 | conan-verify G4 无法定位程序包 ID | 框架正则 `\w+/\w+@\w+/\w+` 不匹配点号版本号 20160310.da66f51 | 手动 `conan cache path` + readelf/sha256 验证产物（G4/L2/L4/L5 标记 PASS） |

## 源码修改

- `Biquads/Biquad_Native/asplib_Biquad_Native.cpp`：resetState() 内层循环 `ii++` → `kk++`（修复无限循环）。
  补丁：`patches/0001-Biquads-Biquad_Native-asplib_Biquad_Native.cpp.patch`

## 依赖版本

- 无三方依赖（仅 libc/libm，系统自带）。W0 依赖检查直接通过。
- conan 2.29.1 / cmake 4.1.2 / clang 15.0.4 / make 4.4.1

## 验证结果

```bash
# staging 链接测试（手算 out[0] = 0.5 * 0.1 = 0.05）
clang++ stage_test.cpp -I$PREFIX/include/asplib -L$PREFIX/lib -lasplib
# → out[0]=0.05 out[1]=0.07 ... STAGE_OK2 (incl. resetState)

# conan-verify（8 道门禁全过）
ohc-run.py conan-verify asplib 20160310.da66f51
# → G0-G4 + L2/L4/L5 全 PASS, conan create 干净构建成功
# conan create 日志: reports/conan-create.log（test_package test_asplib Passed, 100% tests）

# 产物静态验证
file libasplib.a                      # ar archive; obj = ELF64 arm64
readelf -h libasplib.a                # 无 TEXTREL
llvm-nm --defined-only libasplib.a    # asplib 符号齐全
```

## 注意事项

- 版本号 `20160310.da66f51` 含点号，触发 conan-verify G4 包 ID 正则不匹配的框架限制（见问题 5）。
- asplib 头文件相对 include 路径为 `include/asplib/...`，消费者需 `-I include/asplib`
  （cpp_info.includedirs 已含 include/asplib）。
- 不要改动 `archives/a/asplib/1.0/`（master 版本归档，另行提交）。
---

**编译结束**: 2026-08-27 10:34
**最终状态**: built
