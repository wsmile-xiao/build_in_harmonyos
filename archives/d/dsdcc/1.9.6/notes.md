# dsdcc 1.9.6 适配笔记

## 编译环境
- 构建系统: cmake (init-build 误判 autotools,已手动改用 CMake 模板)
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, /data/service/hnp/bin)
- 状态: built

## 编译步骤

```bash
# 源码(官方上游 tag)
curl -sSL -o dsdcc-1.9.6.tar.gz https://github.com/f4exb/dsdcc/archive/refs/tags/v1.9.6.tar.gz
# SHA-256: 43505fe537b12492860a44d0373b6b2a7edacbaec058160b5007c341af1b40d9

# 探索编译(确认 CMake 构建可用)
cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DBUILD_TOOL=ON
make -C build -j4
make -C build install DESTDIR=$TEST_PREFIX

# 上游测试 testfec (12 独立用例)
PATH=~/tmp/bin:$PATH make -C testfec -j1   # g++ -> clang++ wrapper, -j1 规避 HMDFS fifo
# 逐个运行 qr/golay20/23/24/hamming7/12/15/16/viterbi/viterbi35/crc/pn → 12/12 exit=0

# Conan 配方验证 (OHOS profile)
conan create archives/d/dsdcc/1.9.6 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 生成 autotools 模板配方,conan create (G2) 失败 | 构建系统推断依据 URL,未核验 CMakeLists.txt | 改用 templates/conanfile-cmake.py.tmpl 重写 conanfile.py (CMakeToolchain + cmake_layout),见 DRAFT-dsdcc-conan-init-cmake-misdetect |
| 2 | testfec make 报 `g++: No such file or directory` 且 `jobserver mkfifo: Operation not permitted` | OHOS 无 g++/cc/c++;HMDFS 不支持 make jobserver fifo | `~/tmp/bin/g++ -> clang++` 符号链接 + PATH 前置 + `make -j1`,见 DRAFT-dsdcc-makefile-gxx-wrapper-hmdfs-fifo |
| 3 | test_package 消费者 `dsdcc/dsd_decoder.h` 找不到;`DSDDecoder` 未定义 | 头文件安装于 include/dsdcc/ 且使用 namespace DSDcc | package_info 保持默认 include/ 根(不设 includedirs=include/dsdcc),消费者 `#include <dsdcc/dsd_decoder.h>` + `using namespace DSDcc` |
| 4 | conan-verify 默认 profile libstdc++11 报 `invalid library name` | OHOS clang 15 只提供 libc++,拒绝 -stdlib=libstdc++ | 使用仓库预置 ci/conan/profiles/ohos-aarch64 (libc++) |
| 5 | W3 JC 门禁命中其他库基线空文件 (cloog/kics .staging-verified 等) | 提交前已存在的其他库运行时状态文件被 full 模式扫描 | 基线隔离复验:记录 SHA → git rm --cached → 复跑 W3 (exit 0) → 原样恢复 → post SHA 一致;不入 PR,见 reports/baseline-isolation-audit.md |

## 依赖版本

- 无强制外部依赖 (可选 mbelib/1.3.0、serialdv/1.1.5 未启用,registry 已发布可用)
- 工具链: clang/clang++ 15.0.4, cmake 4.1.2, make 4.4.1, conan 2.29.1

## 验证结果

```bash
# 上游测试 (testfec): 12/12 通过, 全量通过率 100% (12/12)
# 消费者用例 (test_package/test.cpp): DSDDecoder run()/getSamplesPerSymbol()/getSymbolSyncQuality()/formatStatusText() 全部通过
# conan-verify: G0/G1/G2/G3/G4 全部 PASS
# CLI: dsdccx --help exit=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | CMake 配方 (官方 URL + SHA-256) |
| test_package/ | 消费者用例 (test.cpp 真实调用公开 API) + MANIFEST.yml (上游 12 用例声明) |
| commands.json | R38 CLI 工具声明 (dsdccx) |
| packaging/dsdcc-1.9.6-ohos-aarch64.tar.gz | 库+头+CLI 打包 |
| knowledge/drafts/DRAFT-dsdcc-*.kv/.md | 知识库扩展草稿 (2 组同 stem 配对) |
| reports/ | 测试报告、conan-verify 报告、知识候选台账、基线隔离审计 |

## 注意事项

- 消费者用例必须用 `namespace DSDcc` 与 `<dsdcc/dsd_decoder.h>` 包含路径
- testfec 上游用例由 Makefile 驱动且硬编码 g++,构建时需 wrapper 与 -j1
- 任务为【知识库扩展】路径 B:2 个候选已验证可跨库复用,查重未命中/部分覆盖,建立 .md/.kv 配对草稿
---

**编译结束**: 2026-09-25 23:10
**最终状态**: built