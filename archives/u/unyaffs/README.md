# unyaffs

`unyaffs` 是 **YAFFS2（Yet Another Flash File System, version 2）镜像的只读提取工具**。
YAFFS2 是 NAND 闪存上广泛使用的日志结构文件系统（Android 早期 `system`/`data` 分区、
嵌入式 Linux 根文件系统）。与 ext2/ext4 镜像不同，它按 **chunk（数据区 + spare/OOB
标签区）** 组织，需要理解其对象头与标签布局才能还原文件。

## Versions

| Version | Status | Assertions |
| --- | --- | --- |
| 0.9.7 | built | 54 |

Homepage: https://github.com/ehlers/unyaffs

## 用法

```bash
# 自动探测 NAND 布局后列出镜像内容
unyaffs -t system.img

# 带权限/大小/时间列出
unyaffs -v -t system.img

# 显式指定布局（chunk 2K = -c 2，spare 64 字节 = -s 64），提取到目录
unyaffs -c 2 -s 64 system.img ./out

# 仅探测布局（不提取）
unyaffs -d system.img

# 打印版本
unyaffs -V          # → V0.9.7
```

| 选项 | 说明 |
| --- | --- |
| `-d` | 探测 flash 布局，不提取 |
| `-b` | spare 区含坏块信息（偏移 2 字节）|
| `-c <KByte>` | 设定 chunk 大小，0 ≤ n ≤ 16（默认自动探测）|
| `-s <Byte>` | 设定 spare 大小，0 ≤ n ≤ 512（默认自动探测）|
| `-t` | 列出镜像内容 |
| `-v` | 详细输出（`-v -t` 给出权限/大小/时间）|
| `-V` | 打印版本 |
| `-h` / `?` | 用法 |

> 上游的**布局自动探测**要求镜像带有真实 NAND 布局特征（chunk ∈ {2K,4K,8K,16K} ×
> spare ∈ {64..512, 步长 16} × 坏块偏移 ∈ {0,2}，并匹配对象头特征）。当镜像由
> 程序化合成的最小结构（只有对象头与数据 chunk）时探测会返回 `Detected flash
> layout(s): -- none --` 并以 1 退出——**这是预期行为**，此时用 `-c`/`-s` 显式指定
> 布局即可正常解析。本包测试同时覆盖这两条路径。

## 退出码约定

| 调用 | 退出码 |
| --- | --- |
| `-V` / 正常列表 / 正常提取 | 0 |
| 无参数 / `-h` / 位置参数 >2 / 选项越界（`-c 17`、`-s 513`、非数字） | 1（打印用法）|
| 打不开镜像 | 1（`Open image file failed`）|
| 布局无法确定 | 1（`Can't determine flash layout, perhaps not a yaffs2 image`）|
| `-d` 且未匹配到任何布局 | 1（`Detected flash layout(s): -- none --`）|
| 对象名含路径分隔符 | 非 0（`Illegal file name …`）|

## OHOS 适配

| 项目 | 说明 |
| --- | --- |
| 目标 | `aarch64-linux-ohos`（musl）|
| 源码 | 单 `.c` + `.h`（`unyaffs.c` ~21 KB）|
| 外部库 | 无（仅 `stdio`/`stdlib`/`string`/`errno`/`fcntl`/`getopt`/`limits`/`ctype`/`sys/stat`/`sys/types`/`unistd`）|
| patch | 无 |
| 构建 | 直驱 clang：`clang -O2 -w -std=gnu99 -o unyaffs unyaffs.c` |
| 产物 | `bin/unyaffs`（约 29 KB）；`share/man/man1/unyaffs.1`、`share/doc/unyaffs/README` |

上游 `Makefile` 只有 `unyaffs` 与 `clean` 两个目标，用 `$(CC)` 直编单文件，
`build()` 直驱 `clang` 与之一致但不依赖 `make`。

### 不校验 ECC（对测试很重要）

`unyaffs.h` 里虽然定义了 `yaffs_ECCOther`，但 `unyaffs.c` **没有任何校验逻辑**——
它只读 `yaffs_PackedTags2` 的 `sequenceNumber` / `objectId` / `chunkId` / `byteCount`
四个字段。因此消费者测试可以**程序化合成**合法镜像，无需实现 NAND ECC 算法。

## 测试

上游**不含任何测试套件**：`Makefile` 只有 `all` 与 `clean`，**没有 `check` 或
`test` 目标**，源码 tarball 内也不含测试源文件或 YAFFS2 测试镜像。

`test_package/test_unyaffs.c` 提供 **54 条断言**，夹具**在测试进程内合成**
（按对象头布局与标签逐 chunk 拼装 2048+64 布局镜像，零二进制资产）：

| 分组 | 条数 | 内容 |
| --- | --- | --- |
| 版本/用法契约 | 10 | `-V` → `V0.9.7`；无参数/`-h`/位置参数 >2 均回落用法 + rc 1 |
| 选项边界 | 8 | `-c 16`（上限内成功）、`-c 17`、`-s 513`、`-c abc` 均回落用法 + rc 1 |
| 打不开的镜像 | 2 | rc 1 + `Open image file failed` |
| 列表与元数据 | 8 | `-t` 列出 `.`/`hello.txt`/`big.bin`；`-v -t` 含大小 14 / 5120 |
| 提取逐字节比对 | 3 | 14 B 与跨 3 个 chunk 的 5120 B |
| **往返属性** | 7 | 尺寸 0/1/2047/2048/2049/4096/10000 字节，合成→提取→逐字节一致 |
| 多文件列表 | 4 | 列表行数 == 文件数 + 1 |
| **路径穿越安全** | 3 | 对象名含 `/` 被拒绝（`Illegal file name`），且未写出到目标目录之外 |
| 损坏输入 | 7 | 0 字节 / 随机字节 / 截断镜像 |
| scratch 可写性、截断健壮性 | 2 | 显式探测可写性；截断镜像不得因信号终止 |

判据主体是**往返属性**而非 golden 向量 —— 由被测程序自己证明自己的镜像解析与
文件重建自洽，不需要任何期望输出表。全程用 `popen` 内存管道直读，**不写任何临时
文件**；合成镜像与提取输出只落在 `test()` 阶段创建于 `build_folder` 下的 scratch
目录（OHOS 上 `/tmp` 只读）。
