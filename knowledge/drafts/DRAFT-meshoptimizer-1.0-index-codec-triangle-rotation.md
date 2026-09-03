# DRAFT-meshoptimizer-1.0：索引编解码器三角形旋转 — 消费者往返测试必须按三角形集合等价比较

> Contributor: pc1-29 | Status: Draft | Updated: 2026-09-03
> Source: PR（meshoptimizer 1.0 适配，conan-verify G2 test_package 修复链）

## 背景

meshoptimizer 1.0 适配到 HarmonyOS PC（arm64）时，为 test_package 编写消费者测试，
以立方体（24 顶点 / 36 索引）验证 meshopt_encodeIndexBuffer/decodeIndexBuffer 无损往返。
初版以 memcmp 逐字节比较解码结果与原始索引，测试失败。

## 错误 1：decode 传 bound 大小 → rc=-3

### 现象

```text
FAIL: meshopt_decodeIndexBuffer rc=-3
```

### 根因

`meshopt_decodeIndexBuffer` 的 buffer_size 参数必须传**实际编码长度**（encode 返回值），
不能传 `meshopt_encodeIndexBufferBound` 的界值：bound 缓冲区含尾随零字节，解码器
读到 data != data_safe_end（数据未恰好结束于尾表边界）返回 -3。

### 修复

```cpp
size_t encoded_size = meshopt_encodeIndexBuffer(enc.data(), enc.size(), idx.data(), idx.size());
int rc = meshopt_decodeIndexBuffer(dec.data(), idx.size(), enc.data(), encoded_size); // 用 encoded_size
```

## 错误 2：memcmp 往返比较假失败（三角形轮换）

### 现象

```text
FAIL: index codec round-trip mismatch
```

解码结果 6 处索引与输入不同，但均为三角形内顶点轮换（如 `(0,3,2)` ↔ `(2,0,3)`），
拓扑完全等价。

### 根因

meshoptimizer 编码器 `getEdgeFifo` 为匹配已编码边缘会**隐式旋转三角形顶点**（
indexcodec.cpp 注释："getEdgeFifo implicitly rotates triangles by matching a/b to
existing edge"）。解码结果保证三角形集合等价，不保证字节一致。上游 roundtripIndexTricky
等测试数据恰好不触发旋转路径，其 memcmp 断言成立，掩盖了该语义。

### 修复

改为按排序三角形（canonical tuple）集合等价比较：

```cpp
// 每个三角形 3 索引排序成元组，比较集合
std::sort(orig_set.begin(), orig_set.end());
std::sort(decoded_set.begin(), decoded_set.end());
if (orig_set != decoded_set) FAIL;
```

## 验证

- 本地 repro：`simplify 36->36 idx, vcache optimized, codec roundtrip 52 bytes` OK，exit=0
- conan-verify：G1/G2/G3/G4 全过；上游 demo runTests() 93/93 用例 + 328 assert 通过
- W3 本地 CI：JC pass / L0 pass / L1 pass / 100%

## 适用边界

任何以 meshoptimizer 索引编解码器做无损往返验证的消费者测试（Conan test_package、
下游集成测试）均应使用三角形集合等价比较，不得 memcmp。同一原则适用于其他
边缘复用型索引编码器。decode 的 buffer_size 必须传实际编码长度。