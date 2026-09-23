# pnglite 0.1.17 测试报告

> **项目**: pnglite 0.1.17
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS/OpenHarmony 6.0 AArch64 ABI（OHOS Clang 15.0.4，QEMU AArch64 运行环境）
> **测试类型**: 上游测试清点、消费者功能测试、HarmonyOS 专项测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

上游发布包测试数为 0；适配后新增 2 个测试、25 个断言，测试数量未减少。

---

## 二、测试结论

### 2.1 总体评价

✅ **全部适用测试通过，可用于 HarmonyOS PC AArch64。**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 未解决测试问题 | 无 | 🟢 |
| 未解决构建问题 | 无 | 🟢 |

### 2.3 可用功能清单

```text
✅ 回调 IO：内存写入和读取
✅ PNG 写入：zlib 压缩、IHDR/IDAT/IEND 生成
✅ PNG 读取：CRC、元数据、解压和反滤波
✅ 错误处理：错误字符串、非法参数、错误及截断签名
✅ HarmonyOS：`__OHOS__` 平台宏、AArch64、zlib 编码路径
```

### 2.4 已知限制

1. 索引色 PNG 按上游 0.1.17 行为返回 `PNG_NOT_SUPPORTED`。
2. 交错 PNG 按上游 0.1.17 行为返回 `PNG_NOT_SUPPORTED`。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `test_pnglite` | 20 断言覆盖公开 API、RGBA 编解码往返、元数据、错误输入 | ✅ PASS |
| `harmonyos_specific_test` | 5 断言覆盖 OHOS/AArch64 及 zlib 灰度 PNG 编码 | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | 无 | 0 个失败 |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无 | 0 个跳过 |

---

## 四、关键问题分析

### 问题1: IDAT 压缩缓冲区越界

**现象**：

```text
AddressSanitizer: heap-buffer-overflow in compress2 -> png_write_idats
```

**根因分析**：上游按未压缩数据大小分配缓冲区，未考虑 zlib 压缩输出上界及 chunk 元数据空间。

**解决方案**：使用 `compressBound()` 计算容量，额外预留 chunk 类型和 CRC 空间，并检查分配与 `compress()` 返回值；修复后 ASan+UBSan 20/20 断言通过。

复核命令（在官方源码应用归档内两个补丁后执行）：

```bash
cc -std=c99 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I"$SOURCE_DIR" "$SOURCE_DIR/pnglite.c" \
  test_package/test_pnglite.c -lz -o "$BUILD_DIR/test_pnglite_sanitize"
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 \
  "$BUILD_DIR/test_pnglite_sanitize"
```

输出：`pnglite API round-trip: 20 assertions passed`，ASan 与 UBSan 均无诊断。

---

## 五、测试环境

```text
OpenHarmony public SDK: 6.0.0.47
OHOS Clang: 15.0.4
Target: aarch64-unknown-linux-ohos
Conan: 2.29.1
CMake: 4.2.3
QEMU: 10.2.1
Dependency: zlib/1.3.1
W3 local CI: 1/1 PASS, 100%
```

---

*报告生成时间: 2026-09-15*
