# 上游行读取器未初始化 lsize + 翻倍复合导致指数级 realloc 爆炸

> 草稿（DRAFT）。与同目录 `libgetline-1.0-upstream-uninitialized-lsize-exponential-realloc.kv` 成对。

## 问题

libgetline 1.0 的 `libgetln_getline` 在鸿蒙适配测试中**挂起 / 返回 SIZE_MAX**：
- 16 字节缓冲读 14 字节短行时"侥幸"通过；
- 4 字节缓冲读 201 字节长行时：`test_package` 的 ohos_platform 测试在 ctest 中
  Subprocess killed（挂起约 277s），独立复现显示 getline 返回 `(size_t)-1`。

## 根因

```c
size_t need, cplen, lsize, llen = 0;   // 只有 llen 被初始化 —— UB
...
lsize = lsize + need;
if (*size < lsize) {
    if (lsize < *size * 2 && !MSB(size_t, *size))
        lsize = *size * 2;             // 翻倍结果写回"运行总量" lsize！
    new = realloc(*line, lsize);
    ...
    *size = lsize;
}
```

1. **lsize 未初始化**（只有 `llen = 0`）：首块数据就使用垃圾值，`realloc(NULL, 垃圾值)`
   可能失败返回 SIZE_MAX；-O2/-O3 下 UB 可表现为任何行为（挂起、崩溃）。
2. **翻倍复合进 lsize**：翻倍把 lsize 变成 2×cap，下一块 `lsize += need` 从翻倍值继续，
   每次 realloc 都翻倍 —— cap 呈 2^N 指数增长（5→10→20→…→GB/PB 级），
   小缓冲逐块读长行必然触发。16 字节缓冲 + 短行时翻倍次数少且堆栈残留 0，
   侥幸通过，掩盖了缺陷。

## 方案（patches/0002-src-libgetline.c.patch）

```c
size_t need, cplen, lsize = 0, llen = 0;      // ① 初始化 lsize，消除 UB
...
if (*size < lsize) {
    size_t newsize = lsize;                    // ② 独立翻倍变量
    if (lsize < *size * 2 && !MSB(size_t, *size))
        newsize = *size * 2;                   // 不回写 lsize
    new = realloc(*line, newsize);
    ...
    *size = newsize;
}
```

## 验证

- `-O0` 与 `-O3` 独立复现程序均稳定返回：201 字节行 `n=201, cap=320`（修复前 -O0 返回
  SIZE_MAX、-O3 挂起）；
- conan create（ohos-aarch64, clang 15, -O2 -O3）：消费者用例 + 鸿蒙专项用例
  （NOBLANK/EOF/NOCLOSE/EBADF/长行增长 33 项断言）全部通过；
- conan-verify G1-G4 PASS。

## 适用边界

- 适用于任何"读一行/读流并自动扩容"的 C 库：**增长翻倍若写回"运行累计总量"变量必现
  指数级 realloc**；**所有局部变量使用前必须初始化**（-O3 会把 UB 放大为挂起/崩溃）。
- 修复为最小源码补丁（portability），不涉及平台宏，CI 全平台可应用。

## 查重差异

- 知识图谱无任何条目命中（realloc 指数增长 / 未初始化 lsize / libgetline）——
  `combination_novelty` 成立，新建条目。
- 与既有 autotools/配置类条目（E007/E072/E160/E279）无触发重叠（那些是 configure
  脚本与 triplet 问题，不是读库内存缺陷）。
- 测试迁移价值：`test_migration_novelty` —— 新增的 4 字节缓冲长行增长测试用例
  可作为"小缓冲读长行"的通用压力用例迁移到其他行读取类库。
