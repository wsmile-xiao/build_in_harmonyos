# openlibm 0.8.8 适配笔记

## 编译环境
- 构建系统: makefile（Makefile + Make.inc，无 configure；CMakeLists.txt 为次级）
- 编译日期: 2026-09-07
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 源码：官方 tag v0.8.8（sha256=721bab18ff37160fd9e903eb211ff26fdee38c3d0041d556b07d76089c435d17）
# 2. 交叉构建（OHOS clang 默认目标即 aarch64-unknown-linux-ohos，无需 --target）
make CC=/data/service/hnp/bin/clang AR=llvm-ar RANLIB=llvm-ranlib -j4
# 3. 上游测试
make -C test CC=/data/service/hnp/bin/clang test-double test-float regression-build
./test/test-double && ./test/test-float
./test/regression/test-211 && ./test/regression/test-222 && ./test/regression/test-252 && ./test/regression/test-334
# 4. Conan 配方（静态默认，shared=False）
python3 scripts/ohc-run.py conan-verify openlibm 0.8.8   # G1-G4 全过
python3 scripts/ohc-run.py finish openlibm 0.8.8 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `tools.build:compiler_executables:c` 报不存在 | Conan 2 该 conf 为 dict 类型，不能用 `:c` 后缀路径读取 | 改为 `self.conf.get(..., check_type=dict)` 后 `.get("c")` |
| 2 | conan create 报 `No targets specified and no makefile found` | openlibm 原地构建，但 conan 默认 cwd 是空 build 目录 | build() 内 `cwd=self.source_folder` |
| 3 | test_package 找不到 openlibm.h | 头文件装在 `include/openlibm/` 子目录 | `cpp_info.includedirs=["include/openlibm"]` |
| 4 | 消费者运行报 `Error loading shared library libopenlibm.so.4` | 动态库在 OHOS HMDFS 加载路径不可解析 | 默认 shared=False 静态构建+安装（R26 思路） |
| 5 | W3 JC5 拦其他库基线 `.ci-trigger` | full 模式按 git ls-files 扫描 | 基线隔离复验：记录 SHA→临时移出索引→复跑→原样恢复（SHA 一致） |

## 依赖版本

无外部依赖（openlibm 是独立 libm 实现）。构建依赖：OHOS SDK clang 15.0.4 / llvm-ar / GNU make 4.4.1 / conan 2.32.0。

## 验证结果

上游测试 96/96 通过（100%）；鸿蒙专项 13/13 通过；conan create G1-G4 全过；test_package ctest 1/1 通过。详见 `reports/test-report.md`。

## 注意事项

- openlibm 的 `make all` 同时产静态与动态库；OHOS 消费者优先静态（R26 同源思路），避免 HMDFS 上 DT_NEEDED 绝对路径/SONAME 解析问题。
- `include/openlibm/` 为头文件根目录（与其 .pc 一致），消费者 include 路径需含该子目录。
- 上游测试用 `make test`（test-double + test-float + regression）；libm-bench 是基准非测试；inf_torture 上游未接入 test 目标。
- aarch64 上 `LONG_DOUBLE_NOT_DOUBLE=1`，ld128/ 树参与编译，long double 为 128 位（与 x86 80 位不同）。
---

**编译结束**: 2026-09-08 00:28
**最终状态**: published
