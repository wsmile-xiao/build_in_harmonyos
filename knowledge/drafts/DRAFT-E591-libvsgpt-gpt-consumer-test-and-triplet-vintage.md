# DRAFT-E591 — libvsgpt/libyal GPT 卷系统在 OHOS 上的四个确定性陷阱

- **id**：`DRAFT-E591-libvsgpt-gpt-consumer-test-and-triplet-vintage`
- **状态**：pending-editor-review
- **适用阶段**：build / test
- **实测对象**：`libvsgpt 0-20240504`（Debian pristine orig tarball，sha256
  `60e8239d29c7f1a43282a96d86e82e147c3b87a4aa343db73be2870c465c6ac9`），
  任务 `feat/libvsgpt-0-20240504`，2026-09-20 于鸿蒙设备实测。

## 1. 同一族 `config.sub` 对 `linux-ohos` 的接受度随发行版年代翻转

设备实测（随包 autotools 文件；取值命令
`tar xzf libvsgpt_0~20240504.orig.tar.gz && grep -m1 "^timestamp=" */config.guess */config.sub`，
本包两份均为 `timestamp='2023-06-23'`）：

```text
$ grep -m1 "^timestamp=" config.guess config.sub
config.guess:timestamp='2023-06-23'
config.sub:timestamp='2023-06-23'
$ ./config.sub aarch64-unknown-linux-ohos
Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized
$ ./config.sub aarch64-unknown-linux-gnu
aarch64-unknown-linux-gnu
```

同族 `libfsfat 0-20260208` 的随包 `config.sub` 世代为 `timestamp='2024-05-27'`
（其 `config.guess` 为 `2024-07-27`），实测**原生接受** `linux-ohos`
（`config.sub aarch64-unknown-linux-ohos` → `aarch64-unknown-linux-ohos`）。
因此「libyal 用 `linux-ohos` 三元组」这条族级经验**不能跨发行版年代套用**：
分界点在 `config.sub` 的世代（本包 2023-06-23 拒绝 / 同族 2024-05-27 接受），
判据必须取**随包 `config.sub` 的实测行为与世代**，不要照抄兄弟任务的读数。

判据与处置：配方写 `--build/--host` 之前，先对**随包** `config.sub` 实测目标三元组；
不识别就退回 `aarch64-unknown-linux-gnu`（libtool 仍走共享库 PIC 分支，交付
`libvsgpt.so.1.0.0` 正常）。用 `update_configure_args()` 覆盖而非追加，避免与
`AutotoolsToolchain` 自己生成的三元组重复。**不要**为此改上游 `config.sub`。

## 2. `cp -r` 丢 mtime → 假 `automake-1.16: inaccessible or not found`

原生探索用 `cp -r` 复制源码树时，所有文件被刷成同一 mtime，automake 的维护者模式
认为 `Makefile.in` 相对 `Makefile.am` 过期并尝试重建：

```text
$ make -j2
 cd . && /bin/sh .../native/src/missing automake-1.16 --gnu
.../missing[81]: automake-1.16: inaccessible or not found
WARNING: 'automake-1.16' is missing on your system.
make: *** [Makefile:641: Makefile.in] Error 1
```

设备实际有 **automake 1.19**（`automake --version` 实测），报错只是因为 tarball 的
`missing` 脚本按 `automake-1.16` 命名查找；真实原因是拷贝方式丢了 mtime。
tarball 内时间戳本来是自洽的（`Makefile.am` 12:31 < `Makefile.in` 12:44、
`configure.ac` 12:26 < `configure` 12:43），`cp -a` / `tar x` / conan `get()` 都保留。

处置：探索脚本一律 `cp -a`；见到该报错先 `ls -l Makefile.am Makefile.in` 比对 mtime，
**不要**据此判「设备缺 automake」，也不要 `touch`/改上游文件来掩盖。

## 3. `*_by_identifier` / `*_with_identifier` 实为 **entry index**

`include/libvsgpt.h.in`（公开头文件）：

```c
/* Determines if the volume contains a partition with the corresponding (partition) entry index
 * Returns 1 if the volume contains such a partition, 0 if not or -1 on error */
int libvsgpt_volume_has_partition_with_identifier(
     libvsgpt_volume_t *volume,
     uint32_t entry_index,          /* ← 不是 GUID */
     libvsgpt_error_t **error );

int libvsgpt_volume_get_partition_by_identifier(
     libvsgpt_volume_t *volume,
     uint32_t entry_index,          /* ← 不是 GUID */
     libvsgpt_partition_t **partition,
     libvsgpt_error_t **error );
```

内部实现逐字确认：走 `libvsgpt_internal_volume_get_partition_values_by_identifier()`，
在该函数里是 `if( safe_entry_index == entry_index )` 的**条目序号**比对。
配套的返回值约定（实测，易错）：

| API | 实测约定 |
|---|---|
| `libvsgpt_volume_close()` | 成功返回 **0**（头文件注释 "Returns 0 if successful or -1 on error"） |
| `libvsgpt_partition_get_offset()` | 返回**分区内当前读偏移**（初值 0，读完一扇区为 512）——**不是**卷内偏移 |
| `libvsgpt_partition_get_volume_offset()` | 返回**卷内字节偏移**（首分区 = 2048 × 512） |
| `libvsgpt_partition_get_size()` | 返回**字节**大小（1024 × 512） |
| `libvsgpt_get_version()` | 返回上游版本串 `20240504`，**不是** Conan 版本 `0-20240504` |
| `libvsgpt_check_volume_signature()` | 在 512/1024/2048/4096 四个偏移探测 `EFI PART`；命中 1 / 未命中 0 / IO 失败 -1 |

## 4. 合成「合法 GPT」做消费者测试的最小口径

`libvsgpt_volume_open()` 的要求（源码逐字判读）：

- 主头在 LBA 1（`partition_header_block_number != 1` 直接失败），读不到就在
  512→4096 之间翻倍探测 `bytes_per_sector`；
- **同时**读备头（`backup_partition_header_block_number`，取不到则回退到
  `size - bytes_per_sector`）；
- 主备逐字段比对：header/backup block number 互为镜像、`area_start/end`、
  disk identifier、entries 数、entry 大小、entries 校验和；
- `is_corrupt` 判据：头 CRC-32 `stored != 0 && stored != calculated`，或
  `major != 1 || minor != 0`；**校验和字段写 0 视为不损坏**；
- 主头 corrupt 才回退备头；两个都 corrupt → 直接失败。

因此最小夹具（512 B 扇区、2 MiB 镜像）应为：

| LBA | 内容 |
|---|---|
| 0 | 保护性 MBR（type `0xEE`，起始 LBA 1，扇区数 = 总扇区-1，尾部 `55 AA`） |
| 1 | 主 GPT 头（92 字节有效，CRC-32 = 前 92 字节、校验和字段置 0 的标准 reflected CRC-32，poly `0xEDB88320`，init/final `0xFFFFFFFF`） |
| 2..33 | 主 entries（128 × 128 B，非空条目：type GUID / unique GUID / first LBA / last LBA / 属性 / UTF-16LE 名字） |
| 34..(备 entries-1) | 可用区（第一个分区 2048..3071，payload 写可识别 marker） |
| 4063..4094 | 备 entries（与主 entries **逐字节相同**，CRC 相同） |
| 4095 | 备头（current/backup LBA 与主头镜像，entries 起始 LBA = 4063） |

设备实测：该镜像 `check_volume_signature()` = 1、`volume_open()` = 1、
`get_number_of_partitions()` = 1（**空 entries 会被跳过，不计数**）、
`get_bytes_per_sector()` = 512，分区 offset/size 为字节值，`read_buffer()` 读回 marker。

## 5. 同族假阳性（不重复登记）

`lang-preflight` 对本包同样报 `task=cpp, detected=mixed → env_unsupported`——本批
libyal 家族第 4 次独立复现，根因与处置已在 `DRAFT-E586-libyal-ohos-false-signals-langdetect-and-api`
登记（根目录 `pyproject.toml`/`setup.cfg`/`setup.py` 是 pyvsgpt 绑定打包元数据、
`binding_override` 只认 `dominant == "cpp"`）。本条目不重复展开，只作为该形态的第 4 个
独立实测点。

## 6. 设备实测读数（本任务）

- 生效三元组：`aarch64-unknown-linux-gnu`；configure 参数
  `--enable-shared --disable-static --disable-python --enable-static-executables=no`。
- `make check`：`TESTS` 3 个入口（test_library.sh、test_tools.sh PASS；
  test_vsgptinfo.sh 因发布包不含 `tests/input/` 按上游规则 SKIP）+ `check_PROGRAMS`
  20 个 C 测试程序全部真实执行且 PASS ⇒ N = 23。
- 交付物：`lib/libvsgpt.so.1.0.0`、`include/libvsgpt.h`、`include/libvsgpt/*.h`、
  `bin/vsgptinfo`、`lib/pkgconfig/libvsgpt.pc`、`licenses/COPYING{,.LESSER}`。

## 7. 复现（设备可直接执行）

```sh
TASK_DIR=$HOME/tmp/libvsgpt-0-20240504
sh "$TASK_DIR/triplet-and-gpt-probe.sh"
```

脚本做两件事：①对 `$TASK_DIR/native/src/config.sub` 打印两个三元组的实测结果；
②按第 4 节布局合成 GPT 镜像并用已安装包（或原生构建产物）读回打印读数。
