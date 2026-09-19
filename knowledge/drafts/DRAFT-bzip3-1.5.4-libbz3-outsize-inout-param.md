# libbz3 高层 API 的 *out_size 是 in/out 参数：调用前必须预置输出缓冲区容量

- **草稿 ID**: DRAFT-bzip3-1.5.4-libbz3-outsize-inout-param
- **来源**: bzip3 1.5.4 HarmonyOS PC 适配（鸿蒙专项测试首次运行返回 BZ3_ERR_DATA_TOO_BIG）
- **分类**: c-api / runtime / testing / consumer-test
- **状态**: 本地草稿（路径 B 知识库扩展，随 bzip3 1.5.4 归档 PR 交付）

## 问题 / 错误签名

- **鸿蒙专项测试首次运行失败**：
  ```
  bzip3 library version: 1.5.4
  OHOS_BZIP3_TEST FAIL: bz3_compress failed   (退出码 6)
  ```
- **诊断输出**：`bz3_compress rc=-6 out_size=0`（-6 = BZ3_ERR_DATA_TOO_BIG）
- **复现条件**：`size_t comp_size = 0; bz3_compress(16, in, comp, in_size, &comp_size);`

## 根因

`bz3_compress(uint32_t block_size, const uint8_t *in, uint8_t *out, size_t in_size, size_t *out_size)`
的 `*out_size` 是 **in/out 参数**：进入时表示输出缓冲区容量，返回时回写实际压缩大小。
libbz3.h 98-99 行明确要求 "Make sure to set out_size to the size of the output buffer
before the operation; out_size must be at least equal to bz3_bound(in_size)"。
函数内部以 `buf_max = *out_size` 参与容量校验（`if (buf_max < 13 || buf_max < bz3_bound(in_size))`），
按惯例初始化为 0 时必然返回 BZ3_ERR_DATA_TOO_BIG(-6)。这是 API 契约细节，不是库缺陷或平台问题。

## 最小修复方案

调用前把 `*out_size` 预置为输出缓冲区容量：

```c
size_t comp_size = bz3_bound(in_size);          /* 压缩：容量 = bz3_bound(in_size) */
int rc = bz3_compress(16, in, comp, in_size, &comp_size);
...
size_t decomp_size = in_size + 4096;            /* 解压：容量 = 原大小 + 余量 */
rc = bz3_decompress(comp, decomp, comp_size, &decomp_size);
```

## 验证结果

修复后鸿蒙专项测试全过（退出码 0）：
```
bzip3 library version: 1.5.4
payload 1: 65536 bytes -> 131 compressed -> 65536 decompressed [OK]
payload 2: 262144 bytes -> 264082 compressed -> 262144 decompressed [OK]
OHOS_BZIP3_TEST PASS
```
消费者用例与 test_package 采用相同模式，均通过。

## 适用边界

- 适用：以输出大小参数同时承载输入容量与输出回写的 C API（libbz3 实测）。
- 反例：纯 out 参数的 API（调用前无需预置）不适用本修复。

## 查重差异（与既有条目）

- E244（C API 错误通过 out-param 上报、关闭后误读）仅触发面部分重叠（同为 out-parameter 契约陷阱），
  根因（错误归属 vs 容量 in/out）与方案（错误变量分离 vs 预置容量）均不同，二者互补。
- 新增差异：容量类 in/out 参数必须预置为 bz3_bound() 容量。similar_to: E244 | caused_by: 上游 API 契约文档细节 | conflicts_with: 无。
