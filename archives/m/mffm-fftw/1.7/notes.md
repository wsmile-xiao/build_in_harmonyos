# mffm-fftw 1.7 适配笔记

## 编译环境
- 构建系统: raw Makefile（无 configure；init-build 误判为 autotools，配方按 raw Makefile 手写）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，OHOS SDK）
- 状态: built

## 编译步骤

1. 源码获取：Debian pool orig tarball
   `mffm-fftw_1.7.orig.tar.gz`（sha256 5c7be71270812f468d270481f8959643bd374736c3bf18a7b9d2dccb9690aad0）
2. 手动验证编译（work 目录）：
   - `clang++ -O3 -fPIC -I<fftw3.h dir> -c realFFT.cc realFFTData.cc complexFFT.cc real2DFFT.cc`
   - `clang++ -shared -Wl,-soname,libfft.so.1 -o libfft.so.1 realFFT.o realFFTData.o complexFFT.o -lfftw3`
   - `clang++ -shared -Wl,-soname,lib2Dfft.so.1 -o lib2Dfft.so.1 real2DFFT.o -lfftw3`
   - 三个示例（complexFFTExample/real2DFFTExample/realFFTExample）编译运行成功
3. conanfile.py：直接驱动 clang++ 编译链接（R33，编译器来自 conan conf），不依赖上游 Makefile 的 `g++` 硬编码
4. conan-verify G0-G4 + L2/L4/L5 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 编译找不到 fftw3.h | mffm-fftw 公共头文件 include/mffm/*.H 直接 `#include <fftw3.h>`；test_package 仅传递依赖 fftw 时 CMakeDeps 生成的 fftw_INCLUDE_DIRS_RELEASE 为空 | test_package 显式 `self.requires("fftw/3.3.11")` + CMakeLists 中 `find_package(fftw REQUIRED)` 并链接 `fftw::fftw` |
| 2 | test 运行报 libc++_shared.so 符号缺失 | musl loader 需要 libc++_shared.so（OHOS SDK libc++ 目录）与 libfftw3.so.3，conanrun 只注入直接依赖 libdir | 参考 fftwpp test_package：显式拼 LD_LIBRARY_PATH（SDK libc++ 目录 + /system/lib64）再运行 |
| 3 | realFFT 功率谱断言失败 | realFFTData::getHalfSize() 对偶数 N 返回 N/2，而 power_spectrum 数组实际分配 N/2+1（含 Nyquist bin） | 测试遍历 N/2+1 个元素（上游示例同样只用 (N+1)/2，属上游自身局限） |

## 源码修改

无补丁（纯配方层适配，不改源码）。

## 依赖版本

- fftw/3.3.11（ohpcd 制品仓已发布，conan create 直接复用预编译包）

## 验证结果

```bash
conan-verify mffm-fftw 1.7  # G0-G4 + L2/L4/L5 全部 PASS
# test_package 断言 5 项：complexFFT 能量守恒/DC 峰值/往返恢复 + realFFT 功率谱/往返恢复
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | raw Makefile 配方：编译 4 个 TU + 链接 libfft.so.1/lib2Dfft.so.1 |
| conandata.yml | 上游源码 URL + sha256 |
| test_package/ | 消费者 C++ 测试（complexFFT/realFFT 往返 + 功率谱断言） |

## 注意事项

- 上游 Makefile 的 `install` 目标依赖 GNU `install --directory` 且路径写死 DESTDIR/usr/lib，配方中未使用，改为在 package() 中直接复制产物并生成 `libfft.so -> libfft.so.1` 符号链接。
- 上游头文件按 `<mffm/realFFT.H>` 约定安装到 include/mffm/。
- 上游文档（docs 目标）需要 doxygen，配方中跳过（不生成文档，不影响功能）。
---

**编译结束**: 2026-09-19 17:37
**最终状态**: built
