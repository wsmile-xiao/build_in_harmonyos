# 路径 B 知识库扩展申请：二进制容器格式解析工具的合成夹具与往返属性

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#11535 unyaffs 0.9.7
- **关联 PR**：`!9xxx`（`feat/unyaffs-0.9.7`，配方 PR）
- **知识草稿**：`knowledge/drafts/unyaffs-0.9.7-synthesized-fixture-roundtrip.kv` / `.md`
- **草稿 ID**：`DRAFT-UNYAFFS-SYNTHESIZED-FIXTURE-ROUNDTRIP`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/unyaffs-0.9.7`）提交
- **申请日期**：2026-09-18

## 一、为什么这是"可跨仓库复用的知识"

本仓库有大量**解析结构化二进制输入**的工具（归档、文件系统镜像、协议帧、字体、
位图、可执行格式读取器……），而它们的 `test_package` 最容易退化成两种写法：

| 退化写法 | 后果 |
| --- | --- |
| 把二进制样本提交进仓库 | 来源不明、体积大、无法审查；上游格式一变就失效 |
| 只测 `--help` / 版本 / 不存在的文件 | 决定价值的解析逻辑**一行都没覆盖**，测试全绿而工具可能跑不通 |

根因是默认"**夹具必须是一个真实文件**"。本条给出替代方案：**在测试进程内按格式
规范程序化合成夹具**，并用"合成→解析→逐字节比对"的**往返属性**替代 golden 向量。
夹具即格式文档，随代码演进、可审查、零二进制资产，且天然支持参数化穷举边界。

## 二、前置条件：先判定合成可行性

```bash
$ grep -n 'ecc\|crc\|checksum\|verify' unyaffs.c unyaffs.h
unyaffs.h:28:} yaffs_ECCOther;
unyaffs.h:32:    yaffs_ECCOther ecc;
```

实测：**只有结构体定义，`unyaffs.c` 里没有任何校验逻辑** → 合成可行
（YAFFS2 的 ECC 存在但该工具不校验）。若被测程序确实校验，必须实现该校验算法
或退回真实样本，并**在测试里写明原因**——绝不因为"合成不了"而放弃功能测试。

## 三、夹具构造器：偏移与上游结构体布局对齐

最稳的做法是把上游头文件的 `typedef struct` **原样抄进测试**（编译器算出相同偏移），
本包另提供实测标定的偏移宏作交叉校验：

```c
#define OH_TYPE      0     /* yaffs_ObjectType type  */
#define OH_PARENT    4     /* int parentObjectId     */
#define OH_NAME      10    /* char name[256]         */
#define OH_MODE      268   /* __u32 yst_mode         */
#define OH_FILESIZE  292   /* int fileSize           */
#define OH_ALIAS     300   /* char alias[160]        */
```

YAFFS2 chunk = 数据区 + spare(OOB) 标签区：

```c
static void make_chunk(unsigned char *out, const unsigned char *data, size_t dlen,
                       unsigned seq, unsigned objid, unsigned chunkid, unsigned nbytes)
{
    memset(out, 0xff, CHUNK_SIZE + SPARE_SIZE);   /* spare 未用区填 0xff（NAND 擦除态） */
    if (data && dlen) memcpy(out, data, dlen);
    put32(out + CHUNK_SIZE + 0,  seq);            /* yaffs_PackedTags2 四字段，小端 */
    put32(out + CHUNK_SIZE + 4,  objid);
    put32(out + CHUNK_SIZE + 8,  chunkid);
    put32(out + CHUNK_SIZE + 12, nbytes);
}
```

## 四、判据主体：往返属性 + 穷举块边界

```c
static const size_t SIZES[] = { 0, 1, 2047, 2048, 2049, 4096, 10000 };
/*                            空  1B  块-1  块   块+1   2块   跨5块 */
```

实测（7/7 全绿）：

```
[PASS] 往返 0 字节：提取内容逐字节一致（实际 0 字节）
[PASS] 往返 1 字节：提取内容逐字节一致（实际 1 字节）
[PASS] 往返 2047 字节：提取内容逐字节一致（实际 2047 字节）
[PASS] 往返 2048 字节：提取内容逐字节一致（实际 2048 字节）
[PASS] 往返 2049 字节：提取内容逐字节一致（实际 2049 字节）
[PASS] 往返 4096 字节：提取内容逐字节一致（实际 4096 字节）
[PASS] 往返 10000 字节：提取内容逐字节一致（实际 10000 字节）
```

**不需要任何期望输出表**，覆盖度只受采样点数量限制。

## 五、用合成能力覆盖安全边界：路径穿越

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

实测：

```
── unyaffs -c 2 -s 64 <badname> <badout>（对象名含 '/'）
  [PASS] 含 '/' 的对象名被拒绝（非 0 退出码）
  [PASS] 非法文件名: 输出含 "Illegal file name"
  [PASS] 未在 scratch 根目录写出 escape.txt（无路径穿越）
```

★ 只断言"拒绝了"是不够的——**必须同时探测目标目录之外有没有落地文件**，
否则一个"报了错但已经写了一半"的实现仍然算通过。

### 落地时真实命中的一次判据缺陷（已修）

初版多文件用例用了 `b/c.txt` 这种带子目录的名字，结果 unyaffs 报
`Illegal file name b/c.txt in object 3` 并失败。**这不是程序缺陷，而是我的夹具不符合
该工具的文件名约束**——上游要求对象名不含分隔符（正是上面那条路径穿越防护）。
修法：多文件用例改用扁平名，并把"含 `/` 的名字必须被拒绝"单独写成一个正向安全用例。

## 六、损坏输入与选项边界

| 类别 | 构造方式 | 断言 |
| --- | --- | --- |
| 空文件 | 0 字节 | 非 0 退出 + `Can't determine flash layout` |
| 纯随机 | 4096 字节 `(i*13+7)&0xff` | 非 0 退出 + 同上 |
| **截断镜像** | 合法镜像的前 1.5 个 chunk | **不得因信号终止**（`126/127/>=128/!WIFEXITED` 判"跑不起来"） |
| 选项上限 | `-c 16`（上限）/ `-c 17`（越界）/ `-c abc`（非数字） | 边界内成功、越界回落用法 + 非 0 退出 |
| 位置参数 | `a b c`（3 个） | 回落用法 + 非 0 退出 |

## 七、可写目录：合成产物必须落在 scratch

OHOS 上 `/tmp` 只读。合成镜像与提取输出都写 `argv` 传入的 scratch 目录，
并**先写探针文件探测可写性**，把"目录不可写"与"被测程序有缺陷"区分开：

```c
f = fopen(probe_tmp, "wb");
if (!f) { expect(0, "scratch 目录可写（探针文件写入成功）", probe_tmp); goto summary; }
fputs("probe", f); fclose(f); remove(probe_tmp);
expect(1, "scratch 目录可写（探针文件写入成功）", "");
```

## 八、实测结果

```
=== unyaffs 0.9.7 消费者测试 ===
...
=== 汇总: 54 通过, 0 失败 ===
```

| 分组 | 条数 |
| --- | --- |
| 版本/用法契约 | 10 |
| 选项边界 | 8 |
| 打不开的镜像 | 2 |
| 列表与元数据（`-t` / `-v -t`） | 8 |
| 提取后逐字节比对 | 3 |
| **往返属性（7 档尺寸）** | 7 |
| 多文件列表行数 | 4 |
| **路径穿越安全** | 3 |
| 损坏输入（空/随机/截断） | 7 |
| scratch 可写性 + 截断健壮性 | 2 |

## 九、可套用范围

| 工具/格式 | 合成可行性取决于 |
| --- | --- |
| tar / cpio / ar | 无校验 → 可行 |
| zip / gzip | 有 CRC32 → 需实现 CRC32（简单） |
| FAT / ext 镜像工具 | 无全盘校验 → 可行 |
| PCAP / SQLite / ELF / PE / DWARF | 无校验 → 可行 |
| PNG / BMP | PNG 有 CRC32 → 需实现 |
| 字体（TTF/OTF） | 有 checksumAdjustment → 需实现或先填 0 |
| bittorrent bencode | 无校验 → 可行 |

★ 通用原则：**先 `grep` 校验逻辑判定可行性；可行就合成，不可行就实现校验算法或
退回真实样本并写明原因——绝不因为"找不到样本"而放弃功能测试。**

## 十、与其它判据的分工

本条是判据工具箱的第 6 条，与本批次其余 5 条构成完整覆盖：

| 判据 | 适用 |
| --- | --- |
| 往返一致性（`DRAFT-LUNAR-ROUNDTRIP-PROPERTY-CONSUMER-TEST`） | 可逆转换 |
| 结构不变量（`DRAFT-LETTERIZE-STRUCTURAL-INVARIANT-CONSUMER-TEST`） | 不可逆但输出有约束 |
| 两段式调用（`DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS`） | 有状态的修改类工具 |
| 干跑 + 独立历法（`DRAFT-SNOOZE-TIMELESS-DRYRUN-CALENDAR-CROSSCHECK`） | 输出与当前时刻相关 |
| 平台专有选项分级（`DRAFT-PRCTL-PLATFORM-CAPABILITY-TIERED-ASSERTIONS`） | 选项含平台专有子集 |
| **合成夹具 + 往返属性**（本条） | 解析结构化二进制输入 |

## 十一、请主编审阅

本条草稿是**判据设计规约**，在 unyaffs 0.9.7 上完整落地并通过 OHOS aarch64 实测
（54/54）。落地过程中真实暴露了一次夹具与工具约束不匹配的问题（对象名含 `/`），
已在草稿中作为"判据缺陷修正"记录。若通过，请按 promote 流程转入正式知识库。
