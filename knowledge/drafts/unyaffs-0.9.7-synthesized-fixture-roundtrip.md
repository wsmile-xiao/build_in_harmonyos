# 二进制容器格式解析工具：程序化合成夹具 + 往返属性

> Draft: `DRAFT-UNYAFFS-SYNTHESIZED-FIXTURE-ROUNDTRIP`
> Stem: `unyaffs-0.9.7-synthesized-fixture-roundtrip` — 与同 stem 的 `.kv` 成对
> 实例：unyaffs 0.9.7（`archives/u/unyaffs/0.9.7`，PR !9xxx）

## 基本信息

- **ID**: `DRAFT-UNYAFFS-SYNTHESIZED-FIXTURE-ROUNDTRIP`
- **严重度**: 3（判据质量——决定 CI 绿灯是否等价于"解析器真的能用"）
- **类别**: test-design, fixtures, coverage, ci-gate
- **触发工具**: ci（L1 测试执行验证）
- **阶段**: testing

## 问题：两种退化的夹具写法

对"解析某种二进制容器格式"的工具（文件系统镜像、归档、协议帧、固件包、字体、位图），
消费者测试常见两种退化：

| 退化写法 | 后果 |
| --- | --- |
| **① 把二进制样本提交进仓库** | 样本来源不明、体积大、无法审查；上游格式一变就失效 |
| **② 只测 `--help` / 版本 / 不存在的文件** | 真正决定价值的解析逻辑**一行都没覆盖**，测试全绿而工具可能完全跑不通 |

根因是默认"**夹具必须是一个真实文件**"。于是要么去找样本、要么放弃功能测试。

而实际上，只要被测程序**不校验校验和 / 纠错码**，夹具完全可以在测试进程内
**按格式规范程序化构造**。

## 前置条件：先判定合成可行性

```bash
$ grep -n 'ecc\|crc\|checksum\|verify' unyaffs.c unyaffs.h
unyaffs.h:28:} yaffs_ECCOther;
unyaffs.h:32:    yaffs_ECCOther ecc;
```

实测：**只有结构体定义，`unyaffs.c` 里没有任何校验逻辑** → 合成可行。

若被测程序确实校验，则必须实现该校验算法（可行但要额外对齐规范），或退回真实样本，
并在测试里写明原因——**不要因为"合成不了"就跳过功能测试**。

## 四步改法

### ① 夹具构造器：字段偏移要与被测程序的 C 结构体布局一致

最稳的做法是把上游头文件里的 `typedef struct` **原样抄进测试**（编译器会算出相同偏移），
而不是手工数偏移。本包同时提供实测标定的偏移宏作为交叉校验：

```c
/* 与 unyaffs.h 一致的对象头字段偏移（aarch64 编译器对齐下实测标定） */
#define OH_TYPE      0     /* yaffs_ObjectType type          */
#define OH_PARENT    4     /* int parentObjectId            */
#define OH_NAME      10    /* char name[256]                 */
#define OH_MODE      268   /* __u32 yst_mode                 */
#define OH_FILESIZE  292   /* int fileSize                   */
#define OH_ALIAS     300   /* char alias[160]                */
```

YAFFS2 的 chunk 布局 = 数据区 + spare（OOB）标签区：

```c
#define CHUNK_SIZE 2048
#define SPARE_SIZE 64
#define CHUNK_TOTAL (CHUNK_SIZE + SPARE_SIZE)

static void make_chunk(unsigned char *out, const unsigned char *data, size_t dlen,
                       unsigned seq, unsigned objid, unsigned chunkid, unsigned nbytes)
{
    memset(out, 0xff, CHUNK_TOTAL);        /* spare 未用区填 0xff（NAND 擦除态） */
    if (data && dlen)
        memcpy(out, data, dlen);
    put32(out + CHUNK_SIZE + 0,  seq);     /* yaffs_PackedTags2 四字段，小端 */
    put32(out + CHUNK_SIZE + 4,  objid);
    put32(out + CHUNK_SIZE + 8,  chunkid);
    put32(out + CHUNK_SIZE + 12, nbytes);
}
```

### ② 判据主体：往返属性，穷举块边界

```
合成(输入集合) → 被测程序解析/提取 → 逐字节比对
```

输入集合必须**穷举块边界**：

```c
static const size_t SIZES[] = { 0, 1, 2047, 2048, 2049, 4096, 10000 };
/*                            空  1B  块-1  块   块+1   2块   跨5块 */
```

实测（全绿）：

```
[PASS] 往返 0 字节：提取内容逐字节一致（实际 0 字节）
[PASS] 往返 1 字节：提取内容逐字节一致（实际 1 字节）
[PASS] 往返 2047 字节：提取内容逐字节一致（实际 2047 字节）
[PASS] 往返 2048 字节：提取内容逐字节一致（实际 2048 字节）
[PASS] 往返 2049 字节：提取内容逐字节一致（实际 2049 字节）
[PASS] 往返 4096 字节：提取内容逐字节一致（实际 4096 字节）
[PASS] 往返 10000 字节：提取内容逐字节一致（实际 10000 字节）
```

这一条把"解析器是否正确重建了数据"完全交给被测程序自证，且**不需要任何期望输出表**。

### ③ 用合成能力覆盖安全边界：路径穿越

合成夹具的最大优势是**能构造真实样本里罕见的恶意输入**：

```c
static const char *const bad[] = { "evil/../escape.txt" };
build_image(img, bad, bd, bl, 1);

rc = run_capture("-c 2 -s 64 \"%s\" \"%s\"", img, outdir);
expect(rc != 0, "含 '/' 的对象名被拒绝（非 0 退出码）", "");
expect_contains("非法文件名", buf, "Illegal file name");

/* ★ 关键：断言没有写到目标目录之外 */
f = fopen("<scratch>/escape.txt", "rb");
expect(f == NULL, "未在 scratch 根目录写出 escape.txt（无路径穿越）", p1);
if (f) fclose(f);
```

实测结果（三次全部 PASS）：

```
── unyaffs -c 2 -s 64 <badname> <badout>（对象名含 '/'）
  [PASS] 含 '/' 的对象名被拒绝（非 0 退出码）
  [PASS] 非法文件名: 输出含 "Illegal file name"
  [PASS] 未在 scratch 根目录写出 escape.txt（无路径穿越）
```

★ 只断言"拒绝了"是不够的——**必须同时探测目标目录之外有没有落地文件**，
否则一个"报了错但已经写了一半"的实现仍然算通过。

### ④ 损坏输入与选项边界

| 类别 | 构造方式 | 断言 |
| --- | --- | --- |
| 空文件 | 0 字节 | 非 0 退出 + 明确错误 |
| 纯随机 | 4096 字节 `(i*13+7)&0xff` | 非 0 退出 + 明确错误 |
| **截断镜像** | 合法镜像的前 1.5 个 chunk | **不得因信号终止**（`code∈{126,127}` / `>=128` / `!WIFEXITED` 判"跑不起来"） |
| 选项上限 | `-c 16`（上限）/ `-c 17`（越界）/ `-c abc`（非数字） | 边界内成功、越界回落用法 + 非 0 退出 |

## 可写目录：合成产物必须落在 scratch

OHOS 上 `/tmp` 只读。合成镜像与提取输出都写 `argv` 传入的 scratch 目录，
并**先写探针文件探测可写性**，把"目录不可写"与"被测程序有缺陷"区分开：

```c
f = fopen(probe_tmp, "wb");
if (!f) { expect(0, "scratch 目录可写（探针文件写入成功）", probe_tmp); goto summary; }
fputs("probe", f); fclose(f); remove(probe_tmp);
expect(1, "scratch 目录可写（探针文件写入成功）", "");
```

## 实测结果

```
=== unyaffs 0.9.7 消费者测试 ===
...
=== 汇总: 54 通过, 0 失败 ===
```

54 条断言：版本/用法契约 10、选项边界 8、打不开的镜像 2、列表与元数据 8、
提取逐字节比对 3、**往返属性 7**、多文件列表 4、**路径穿越安全 3**、
损坏输入 7、scratch 可写性 1、截断镜像健壮性 1。

## 可套用范围

| 工具/格式 | 合成可行性取决于 |
| --- | --- |
| tar / cpio / ar | 无校验 → 可行（cpio 有 magic，直接写头） |
| zip / gzip | 有 CRC32 → 需实现 CRC32（简单） |
| FAT / ext 镜像工具 | 无全盘校验 → 可行 |
| PCAP | 无校验 → 可行 |
| BMP / PNG | PNG 有 CRC32 → 需实现 CRC32 |
| SQLite 文件工具 | 页校验可选 → 可行 |
| ELF / PE / DWARF 读取器 | 无校验 → 可行 |
| 字体（TTF/OTF） | 有 checksumAdjustment → 需实现或填 0 试 |
| bittorrent bencode | 无校验 → 可行 |

★ 通用原则：**先 `grep` 校验逻辑判定可行性；可行就合成，不可行就实现校验算法或退回真实样本并写明原因——绝不因为"找不到样本"而放弃功能测试。**

## 与其它判据的分工

| 判据 | 适用 | 参考 |
| --- | --- | --- |
| 往返一致性 | 可逆转换（encode/decode） | `DRAFT-LUNAR-ROUNDTRIP-PROPERTY-CONSUMER-TEST` |
| 结构不变量 | 不可逆但输出有约束 | `DRAFT-LETTERIZE-STRUCTURAL-INVARIANT-CONSUMER-TEST` |
| 两段式调用 | 有状态的修改类工具 | `DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS` |
| 干跑 + 独立历法 | 输出与当前时刻相关 | `DRAFT-SNOOZE-TIMELESS-DRYRUN-CALENDAR-CROSSCHECK` |
| 平台专有选项分级 | 选项含平台专有子集 | `DRAFT-PRCTL-PLATFORM-CAPABILITY-TIERED-ASSERTIONS` |
| **合成夹具 + 往返属性**（本条） | 解析结构化二进制输入 | — |

## 参考实现

- `archives/u/unyaffs/0.9.7/test_package/test_unyaffs.c` — 54 条断言
- `archives/u/unyaffs/0.9.7/test_package/conanfile.py` — scratch 目录构造与传参
