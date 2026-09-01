# aarch64/OHOS 默认无符号 char 使上游测试的"char 当作有符号"假设失败（ETL 等 C++ 模板库上游测试套件）

> **结构化数据**: [graph/DRAFT-etl-20.38.4-char-signedness-upstream-tests.kv](../graph/DRAFT-etl-20.38.4-char-signedness-upstream-tests.kv)
> **严重度**: 🟡 medium | **阶段**: testing | **工具**: clang / ctest / UnitTest++
> **来源**: etl 20.38.4 R03 上游失败 reconcile（25 用例 / 60 断言失败归因，2026-08-31）

---

## 问题现象

在 aarch64（含 OHOS）默认无符号 `char` 的宿主上运行 ETL 20.38.4 上游测试套件
（`test/CMakeLists.txt` → `etl_tests`，UnitTest++），8440 个测试中 **25 个测试用例、
60 次断言失败**，集中出现在把 `char` 当作有符号类型使用的测试：

- `test_bit_stream.cpp` / `test_bit_stream_reader_big_endian.cpp` /
  `test_bit_stream_reader_little_endian.cpp`：`put_get_multiple_variable_size`、
  `test_read_int8_t`、`test_read_int8_t_5bits`、`test_read_checked|unchecked_int8_t_*`
- `test_bresenham_line.cpp`：14 个坐标/复位测试（horizontal/vertical/low|high slope
  diagonal/reset）
- `test_correlation.cpp` / `test_covariance.cpp`：`test_char_correlation|covariance_*`
- `test_rms.cpp`：`test_char_rms`

## error_signature

```
Failure in test_<name>: Expected <num> (+/- <tol>)? but was <num>
25 out of 8440 tests failed (60 failures).
Expected 165 but was -91
Expected 255 but was -1
Expected 11 but was 247
Expected -8.25 +/- 0.1 but was 106.95
Expected -9.17 +/- 0.1 but was 118.833
Expected 5.21 +/- 0.05 but was 167.721
```

## 根因

C/C++ 中 plain `char` 的符号性由实现定义。**aarch64（含 OHOS）默认 plain `char` 为
无符号**，而上游测试代码按"`char` 有符号"编写：

- **位流存储**：`test_bit_stream_reader_big_endian.cpp` 用
  `std::array<char, 4U> storage = { char(0x01), char(0x5A), char(0xA5), char(0xFF) }`
  存 int8_t 负值，无符号 `char` 把 `0xA5`/`0xFF` 窄化为 165/255，而 ETL `read<int8_t>`
  按位模式正确返回 -91/-1，比较失败。
- **坐标值**：`test_bresenham_line.cpp` 用 `using Value = char;`，无符号 `char` 下坐标
  算术/范围断言（如 11 vs 247）失败。
- **数值统计采样**：`test_correlation|covariance|rms` 用 `char` 作采样输入，无符号
  `char` 使均值/方差等统计量偏移（如 -8.25 vs 106.95）。

同一字节存储不变，但整数提升把 -128..127 变成 0..255，比较/断言只在目标平台失败。

## 最小复现

```bash
# 1) 确认宿主 char 符号性（aarch64 -> CHAR_IS_UNSIGNED）
cat > charprobe.cpp <<'EOF'
#include <cstdio>
int main(){ char c=-1; printf("%d\n",(int)c); return 0; }
EOF
clang++ charprobe.cpp -o charprobe && ./charprobe   # 输出 255 => 无符号

# 2) 默认构建并运行上游测试（25 用例 / 60 断言失败）
cmake -B build-upstream -DBUILD_TESTS=ON -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  && cmake --build build-upstream -j4 \
  && ./build-upstream/test/etl_tests
```

> 实测证据（R03）：`/storage/Users/currentUser/tmp/etl-logs/upstream-run3.log`
> SHA-256 `e318e798f5bad0e773cde2f15b2221fb3add886f5bcf9771c05d3c09b30354e5`，退出码 60。
> 逐项失败清单：`/storage/Users/currentUser/tmp/etl-logs/upstream-failures.txt`。

## 控制组证据

同一套件加 `-fsigned-char`（模拟有符号 `char` 语义）构建运行 → **8440/8440 全绿**：

```bash
cmake -B build-upstream-signed -DBUILD_TESTS=ON -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS=-fsigned-char \
  && cmake --build build-upstream-signed -j4 \
  && ./build-upstream-signed/test/etl_tests   # Success: 8440 tests passed, exit 0
```

> 实测证据（R03）：`/storage/Users/currentUser/tmp/etl-logs/upstream-signed-run.log`
> SHA-256 `6865ae4cdfdafd44be048569d93ae17aca94655638bb036930e831371be23b53`。

## 适用范围

以 CMake/UnitTest++ 等框架运行上游测试套件的 C++ 模板库，若测试代码用 plain `char`
承载有符号数值 / 坐标 / 统计采样，且在默认无符号 `char` 的目标（aarch64/OHOS）上运行。

## 解决方案

1. **归因（推荐）**：明确为上游测试可移植性假设，而非库缺陷。不修改库、不改上游断言、
   不禁用测试；用 `-fsigned-char` 控制组证明同套件全绿。
2. **恢复条件**：在 signed-char 平台或加 `-fsigned-char` 运行上游测试即可全绿。
3. **消费者兜底验证**：若上游套件无法在目标语义下运行，以实际消费者测试为准——
   ETL 的 OHOS profile test_package 1/1 Passed（`conan create . --build=missing
   -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`），证明库本身可用，上游失败不影响交付，
   但报告须说明恢复条件。

## 验证命令

```bash
./etl_tests                                          # 复现：25/60 失败
./build-upstream-signed/test/etl_tests               # 控制组：8440/8440 全绿
conan create . --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64  # 消费者 1/1
```

## ⛔ 禁止

- 修改上游断言、禁用测试或宽泛排除以伪造全绿——掩盖平台差异，违反 R6/诚实归因。
- 把 `-fsigned-char` 写死进库配方（R33：编译器 flag 由 Toolchain 提供，不裸写）。
- 把草稿写入正式 `knowledge/doc/**` 或 `knowledge/graph/**`，或编造条目编号。

## 与现有条目差异（查重）

- 无同题既有条目（已查 `knowledge/drafts/` 530 项 + `knowledge/doc|graph`）。
- **最相近 `E2158-draft-2301`**（"Target plain-char signedness can change INT8 API
  results without changing stored bytes"）：同为 plain-char 符号性/整数提升机制，但对象
  不同——E2158 聚焦 **C 库 API 结果**（`-120`→`136` 等 INT8 样本比较失败），本条目聚焦
  **C++ 模板库上游测试套件断言**（位流/坐标/统计测试 25 用例/60 断言失败 + `-fsigned-char`
  控制组 8440/8440）。场景、error_signature、证据不同，互为 similar_to。
- `DRAFT-boost-ohos-representative-upstream-tests`：Boost 组件上游清单校验，主题不同。
- 正式条目 E037/E049/E215/E229/E236/E247/E270/E294/E296/E302：shebang/LuaRocks/libc
  fallback/libtool/pkg-config/CLOCK/Meson 等，均与 char 符号性无同题。

---

*DRAFT-etl-20.38.4-char-signedness-upstream-tests · 2026-08-31 · etl 20.38.4 R03 上游失败 reconcile · 作者 pc2-12*
