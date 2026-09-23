# aarch64/OHOS 无符号 char 使 CLI 数值转换（strtoll+clamp）负值钳位，上游 char 转换用例失败（clipp 等 CLI 解析库）

> **结构化数据**: [graph/DRAFT-clipp-1.2.3-ohos-char-signedness-value-conversion.kv](../graph/DRAFT-clipp-1.2.3-ohos-char-signedness-value-conversion.kv)
> **严重度**: 🟡 medium | **阶段**: testing | **工具**: clang / 上游测试二进制
> **来源**: clipp 1.2.3 R01 上游测试 39 可执行实测（2026-09-05）

---

## 问题现象

在 aarch64（含 OHOS）默认无符号 `plain char` 的宿主上运行 clipp 1.2.3 上游测试
（39 个独立测试可执行，`test/*.cpp` 逐文件编译运行），**38/39 通过**，唯一失败：

- `values_conversion_test`（第 165 行）：
  `test<char>(__LINE__, 0, "-128", -128)` —— 期望 -128，实际得到 **0**。

命令行复现与失败输出：

```
$ clang++ -I include -std=c++11 -Wall -Wextra -Wpedantic -O0 -o bin/values_conversion_test test/values_conversion_test.cpp
$ ./bin/values_conversion_test
failed test test/values_conversion_test.cpp in line 165
```

## 根因

C/C++ 中 plain `char` 的符号性由实现定义。**aarch64（含 OHOS，AAPCS64）默认 plain
`char` 为无符号（0..255）**。clipp 的 `make<char>` 实现为：

```cpp
static inline char from(const char* s) {
    // 先试单字符解析，否则走数值转换
    return clamped_on_limits<char>(std::strtoll(s, nullptr, 10));
}
```

`clamped_on_limits<char>` 按 `std::numeric_limits<char>::min()..max()` 钳位：
无符号 char 下 min=0、max=255，因此 `strtoll("-128") = -128` 被钳为 **0**，
与上游测试基于有符号 char 语义的期望 `-128` 不符。这是平台 ABI 语义差异，
**不是 clipp 缺陷**：字节/数值在无符号 char 平台上本就不能表示 -128。

## 方案

1. **归因为平台 ABI 差异**：不修改 clipp、不改上游断言、不禁用测试、不伪造全绿。
2. **控制组证明**：用 `-fsigned-char` 重编译同一测试，同套件恢复正常
   （ETL 20.38.4 同根因先例已由 DRAFT-etl 验证 8440/8440 全绿）：

```bash
clang++ -fsigned-char -I include -std=c++11 -o bin/values_conversion_test_signed test/values_conversion_test.cpp && \
./bin/values_conversion_test_signed
```

3. **如实上报双口径**：全量 38/39 = 97.4%；当前配置可执行集合 38/38 = 100%。
4. **消费者验证兜底**：test_package 消费者测试（clipp::parse）+ HarmonyOS 专项测试
   全通过，库本身在 OHOS 上可用。

## 验证

- 编译命令（ohos clang-15, aarch64-unknown-linux-ohos）：rc=0
- 运行：38/39 通过；失败项输出 `failed test test/values_conversion_test.cpp in line 165`
- `volatile char c=-1; c>=0` 实测：OHOS aarch64 上为真（char 无符号），直接佐证根因
- conan create ＋ test_package（test_clipp + test_ohos_special）：1/1 通过
- W3 本地 CI：JC/L0/L1 pass，Success 1/1，`.ci-result.json` exit_code=0

## 适用边界（applicable_to）

- 将字符串数值转换到 plain `char` 的库（CLI 参数解析、配置解析、格式转换）
- 转换实现走 `strtoll/strtol + clamp`（`clamped_on_limits<char>` 类）
- 目标平台默认无符号 char（aarch64 / OHOS / AAPCS64）

## 不可适用情形（not_applicable_to）

- 目标平台 plain char 为有符号（x86-64 Linux/macOS 等）
- 不使用 char 数值转换的库
- 显式使用 `signed char`/`int8_t` 作为转换目标的代码（不受影响，R 同 E419）

## 查重（dedup）

- **E419**（正式）：plain-char signedness 改变 INT8 API 结果（C 库、图像/光栅像素采样）——
  同根因（aarch64 默认无符号 char），但场景为 INT8 采样 API，非 CLI 数值转换；
  覆盖根因层，未覆盖"strtoll+clamp 值转换钳位"这一 CLI 解析库表面。
- **DRAFT-etl-20.38.4-char-signedness-upstream-tests**（草稿）：C++ 模板库上游测试
  char 当有符号（位流/坐标/统计采样）——同根因同方案（-fsigned-char 控制组），
  覆盖数据采样表面；本稿补充**CLI 值转换/解析库表面**（make<char> strtoll+clamp 钳位），
  且 clipp 为无构建系统单头文件库、上游测试为 39 独立可执行，与 etl 的
  CMake/UnitTest++ 套件形态不同。
- 结论：与 E419、DRAFT-etl 部分覆盖；新增差异（CLI 值转换钳位场景 + 单头文件
  无构建系统库的逐文件测试枚举形态）已由本轮真实日志验证、可跨 CLI 解析库复用，
  → 路径 B，建本配对草稿；`similar_to` 已标注。

## 新增价值

ETL/E419 覆盖"char 当有符号数据"表面；本稿覆盖"CLI/解析库把字符串数值
转换到 char（strtoll+clamp）在无符号 char 目标上把负值钳为 0"这一独立表面，
错误签名（Expected -128 but was 0）、受影响转换入口与修复验证（-fsigned-char
控制组）均可直接迁移到其他 CLI/值转换库。