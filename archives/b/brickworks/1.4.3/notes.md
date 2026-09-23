# brickworks 1.4.3 适配笔记

## 编译环境
- 构建系统: header-only（上游仅有 test/ 下的 Makefile，无库构建系统）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

brickworks 是 header-only C 音频 DSP 工具库（include/bw_*.h 共 59 个头文件），
无库源码需要编译。配方采用 header-only 变体（conanfile-headeronly.py.tmpl）：

1. init-build brickworks 1.4.3 --url=https://github.com/Orastron/brickworks/archive/refs/tags/v1.4.3.tar.gz
2. lang-preflight: 主体语言 C（task=cpp，c↔cpp 兼容族通过）
3. 上游测试: cd test && make CC=clang CFLAGS=-I../include → 1428 断言全过
4. conan-init 后按 header-only 模板重写 conanfile.py:
   - 无 build()；package() 复制 include/*.h → include/，LICENSE → licenses/
   - package_info(): bindirs/libdirs 置空；package_id clear（单 package_id）
5. test_package: test.c 真实 include <bw_math.h> 并验证 bw_absf/bw_pow2f/bw_clipf

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载项目主页 URL 得到 HTML | 非归档 URL | 改用官方 v1.4.3 标签 tarball 直链 |
| 2 | init-build 嵌套检测误提升 test/ 为源码根，include/ 丢失 | tarball 顶层无库 Makefile，检测器取到 test/ | 干净重建 .orig/.work 为 tarball 原始布局（include/ + test/） |

## 源码修改

无（header-only 库，无任何源码改动；无补丁）

## 依赖版本

无第三方依赖（requires 为空）

## 验证结果

```bash
# 上游测试（test/Makefile，CC 覆盖为 clang）
cd test && make CC=clang CFLAGS='-I../include' && ./build/bw_math
# → succeeded: 1428, failed: 0

# test_package 消费者测试
# → test brickworks 1.4.3: OK (absf/pow2f/clipf verified)
```

## 注意事项

- brickworks 许可证为 GPL-3.0（非 MIT），配方 license 字段必须为 GPL-3.0
- include/bw_rand.h 含 public domain 代码（README 声明），不影响整体 GPL-3.0 判定
---

**编译结束**: 2026-09-05 21:46
**最终状态**: built
