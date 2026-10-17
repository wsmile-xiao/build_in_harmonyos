# openlibm 0.8.7 适配笔记

## 编译环境
- 构建系统: makefile (Makefile + Make.inc)
- 编译日期: 2026-09-04
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

```bash
make USECLANG=1 libopenlibm.a -j1
make USECLANG=1 install-static install-headers install-pkgconfig DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX
make USECLANG=1 check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 编译失败：`<openlibm_complex.h> file not found` | 头文件内部用无前缀 include | `includedirs = ["include/openlibm"]` |
| 2 | test_package 链接失败：动态库找不到 | 静态模式下 Makefile 仍生成 .so | 根据 `shared` 选项分别构建 |
| 3 | GitHub 下载超时 | 本地环境无法直连 github.com | source() 加镜像 fallback |

## 验证结果

### 上游测试（make check）
- test-double: 1118 + 932 = 2050 项全通过
- test-float: 1101 + 923 = 2024 项全通过

### Conan test_package
- 100% tests passed (1/1)
