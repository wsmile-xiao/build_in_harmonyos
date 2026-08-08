# liquid-dsp 1.8.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 真机）
- 状态: published

## 编译步骤

```bash
tar xzf liquid-dsp-1.8.0.tar.gz
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_EXAMPLES=OFF -DBUILD_AUTOTESTS=ON -DBUILD_BENCHMARKS=OFF \
    -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON -DFIND_FFTW=OFF \
    -DCMAKE_INSTALL_PREFIX=<prefix>
make -j$(nproc)
make install
```

configure 结果：NEON=Yes（aarch64 自动启用）、SSE/AVX/AVX512/AltiVec=No、Threads=Yes、FFTW=No。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无（编译零改动一次通过，autotest 全 PASS） | - | - |

## 源码修改

无补丁（零改动适配）。v1.8.0 使用 CMake 构建，在 OHOS 环境无需任何源码修改。

## 依赖版本

无外部编译依赖。可选 FFTW 加速（fftw3f）已关闭，使用 liquid 内置 FFT 实现；
制品仓 cnb 中已有 fftw3f/3.3.9、3.3.9.1、3.3.10 可供后续按需启用。

## 验证结果

```bash
$ ./xautotest
tests  : pass=1341  fail=0  skip=0
checks : pass=716520 fail=0
overall: PASS
```

- 安装产物：include/liquid/liquid.h、lib/libliquid-static.a、lib/cmake/liquid-static/、lib/pkgconfig/liquid-dsp.pc
- SHA256: abef8b2ddfd58c0a84ecda4f62158c4824b916144af4a2b07776e1a144d8cda4
- SHA512 与 vcpkg 官方记录一致: 83c55bf8...

## 注意事项

- 静态库文件名为 `libliquid-static.a`（非 libliquid.a），pkg-config 库名为 `liquid-dsp`。
- 安装时若用 DESTDIR 需先去掉 CMAKE_INSTALL_PREFIX 的绝对路径，否则 CMake 拼接路径失败。
- 上游 v1.8.0 起 CMake 为主构建系统，autotools 将逐步移除。

## 结束标记

最终状态: published
