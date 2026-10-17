# kissfft 131 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS aarch64 toolchain, clang 15.0.4)
- 状态: built (conan-verify 8 道门禁全 PASS)

## 编译步骤

```bash
# 源码: GitHub 官方 API tarball v131 (sha256 97101f0b...)
# 补丁: 6 个（Makefile OHOS 构建/安装 + 测试 Python2->3 兼容 + testcpp M_PIl）
make CC=clang AR=llvm-ar KISSFFT_TOOLS=0 KISSFFT_STATIC=1 -j1      # 构建 libkissfft.a/.so
make install PREFIX=<prefix> KISSFFT_TOOLS=0 KISSFFT_STATIC=1      # 安装 lib + include/kissfft
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 ...             # 配方验证（含 test_package 1/1）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 硬编码 gcc、install 只装 libkissfft.so 到 /usr/local/lib | 上游 Makefile 面向 Linux 通用环境 | 补丁 0001：参数化 CC/AR/PREFIX，安装头文件与静态库，KISSFFT_STATIC 条件 install |
| 2 | testcpp.cc 编译失败 M_PIl 未声明 | OHOS libc math.h 无 long double PI 宏 | 补丁 0005：条件定义 M_PIl（`#ifndef`） |
| 3 | testkiss.py/compfft.py/fastfir.py/fft.py Python2 语法 | 上游 2019 年脚本为 Python 2 | 补丁 0002/0003/0004/0006：print()/dict.has_key/bytes join 兼容 |
| 4 | make -jN jobserver mkfifo Operation not permitted | 执行环境限制 | 使用 -j1 |
| 5 | github.com/archive 域不可达 | 网络环境 | 改用 api.github.com 官方 tarball 源 |
| 6 | conan get BadZipFile | api.github.com URL 无扩展名无法推断格式 | conandata.yml 增加 filename: kissfft-v131.tar.gz |

## 源码修改

- `patches/0001-Makefile.patch`: Makefile 构建/安装适配（CC/AR/PREFIX/KISSFFT_TOOLS/KISSFFT_STATIC）
- `patches/0002..0006`: 测试脚本/源 Python 2→3 与平台兼容

## 依赖版本

无编译依赖（纯 C 数学库）。测试依赖：numpy 2.5.2（testkiss.py 用，已安装 OHOS aarch64 wheel）。

## 验证结果

```bash
# conan-verify: G0-G5 全 PASS（G2 conan create 含 test_package 1/1 通过）
# 上游测试: 18/18 通过（当前配置可执行集合），全量 18/30 = 60.0%
# 鸿蒙专项测试: 全部通过（float/fixed-point/C++ 模板）
# 消费者用例: 通过（max_err=4.2e-22）
# W3 本地 CI: JC=pass, 100% (1/1)
```

详见 `reports/test-report.md`。

## 交付物

| 文件 | 说明 |
|------|------|
| packaging/kissfft-131-ohos-aarch64.tar.gz | 打包产物（libkissfft.a + include/kissfft/） |

## 注意事项

- 纯数学库无平台特定代码；上游工具目录（fftutil 等）依赖 libpng，构建时以 KISSFFT_TOOLS=0 禁用
- 测试统计未实例化项均为真实架构/依赖原因（simd 需 x86 -msse、bm_fftw 缺 fftw3f float 制品、compfft/fastfir 缺 Python2 FFTPACK/Numeric）---

**编译结束**: 2026-09-18 11:05
**最终状态**: built
---

**编译结束**: 2026-09-18 12:37
**最终状态**: built
