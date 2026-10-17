# 测试报告 — xxhash 0.8.2

> **项目**: xxhash  
> **测试日期**: 2026-08-31  
> **测试环境**: HarmonyOS (aarch64, clang 15.0.4)  
> **测试类型**: 官方测试套件 (make check / test-xxhsum-c / test-unicode) + Conan L1 消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试目标 | 4 | 100% |
| 通过 (PASS) | 4 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**上游测试套件通过率**: ✅ **100%**

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| test_package 消费者测试 | 1 | 100% |
| 通过 | 1 | 100% |
| 失败 | 0 | 0% |

---

## 二、测试结论

### 2.1 总体评价

✅ **上游全部测试目标通过，无失败、无跳过。**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | 无 | 无 |

### 2.3 可用功能清单

```
✅ libxxhash.a / libxxhash.so.0.8.2: 静态与共享库构建、安装
✅ xxhsum CLI: xxh32sum / xxh64sum / xxh128sum 符号链接齐全
✅ XXH32/XXH64/XXH3/XXH128: 全算法 sanity 验证 (49948 断言)
✅ CLI 校验/校验和/基准测试: 全部功能正常
✅ Unicode 文件名处理: 正常
```

### 2.4 已知限制

1. 无。

---

## 三、测试详情

### 3.1 通过的测试（上游官方测试目标）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `make check` — tests/sanity_test | sanity_test.c 全算法向量校验，**49948 断言全部通过** | ✅ PASS |
| `make check` — xxhsum CLI 10 组 | stdin 哈希、多文件、内部基准、--benchmark-all、变体基准 (-b1,2,3)、文件基准、-H0/-H2/-H3 输出、非法变体 -H9 报错退出码=1 | ✅ PASS |
| `make test-xxhsum-c` — 65 组命令 | xxhsum 生成/校验往返、--tag/--little-endian 全变体 (XXH32/64/128/XXH3 × BE/LE)、stdin 列表校验、'*' 分隔符、BSD 风格输出、improperly formatted 警告、FAILED/FAILED-open-or-read 错误路径退出码 | ✅ PASS |
| `make test-unicode` | Unicode 文件名哈希与校验 (2 项检查) | ✅ PASS |
| conan test_package (test.c) | 消费者 API 调用: XXH32/XXH64/XXH3_64bits 实际计算哈希 | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无 | — |

> 注：`make test-mem`（valgrind 内存检测）上游设计为可选目标，设备无 valgrind，未纳入本次统计；上游 `make check` 默认套件不含该目标。`tests/bench`、`tests/collisions` 为上游专用基准/碰撞研究套件，不属于 `make check` 默认测试路径。

---

## 四、关键问题分析

### 问题1: `make install` 在 HarmonyOS 上失败

**现象**：
```
make: *** No rule to make target 'install'.  Stop.
make: install: No such file or directory
make: *** [Makefile:577: install_libxxhash.a] Error 127
```

**根因分析**：
上游 Makefile 第 498 行 `ifneq (,$(filter Linux Darwin ... , $(UNAME)))` 的白名单不含 `HarmonyOS`，导致整个安装规则段（含 `install:` 目标与 DESTDIR 目录变量）未定义；且系统无 GNU `install` 命令（Error 127）。

**解决方案**：
补丁 `patches/0001-Makefile.patch`：① UNAME 过滤器追加 `HarmonyOS`；② HarmonyOS 分支下 `INSTALL=cp -p`、`INSTALL_DATA=cp -p`、`INSTALL_DIR=mkdir -p`，install_libxxhash.includes 目标用 `mkdir -p` 建目录。

---

## 五、测试环境

```
xxhash 0.8.2 (upstream v0.8.2 tarball, sha256 baee0c6a...)
HarmonyOS aarch64 (UNAME=HarmonyOS)
clang 15.0.4, GNU Make 4.4.1, cmake 4.1.2
CFLAGS: -fPIC -O2 (默认), profile: ohos-aarch64 (os=OHOS, cppstd=17)
```

---

*报告生成时间: 2026-08-31*
