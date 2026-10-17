# E595（草稿）: 1990s 32 位假设的解包工具在 LP64 目标上的三类系统性断裂（ULONG 宽度 / 链接行硬编码 gcc / on-disk 指针不推进）

## 现象

unace 1.2b（1998/2004 上游原版，Debian pool tarball）在 OHOS aarch64（clang 15，LP64）上
构建成功后，功能面出现一组看似互不相干的异常：

- 列表模式 `unace l` 能识别档案与文件数，但**文件名一列为空**、日期显示 `00.00.80`、
  `t`（完整性测试）报 `CRC-check error`；
- 若给 FILE 头去掉 ADDSIZE 字段，列表/日期/文件名**全部恢复正常**，但解压读不到任何数据；
- 编译期伴随每文件一条 `argument unused during compilation: '-dLO_HI_BYTE_ORDER'`；
- 直接 `make` 报 `gcc: No such file or directory`（链接行）。

## 根因

三个独立的 32 位时代假设在 LP64 上同时断裂：

1. **typedef 宽度**：`declare.h` 把 `ULONG`/`LONG` 定义为 `unsigned long`/`long`
   （LP64 = 8 字节），而 ACE on-disk 结构全部按 32 位设计；解析宏
   `BUFP2LONG(p) *(ULONG*)((p+=4)-4)` 指针步进 4 字节、按 `ULONG*` 解引用读写——
   结构体槽位（thead/tfhead 与 head 缓冲共享视图）变 8 字节后与步进错位，
   每个字段读到半个邻居。
2. **read_header 不消费 ADDSIZE**：带 `ACE_ADDSIZE` flag 的 FILE 头布局为
   `TYPE FLAGS ADDSIZE PSIZE SIZE ...`（acefile 0.6.8 权威解析器确认 FILE 头必须置位，
   否则判 CorruptedArchive），而上游 `read_header` 用**不推进指针**的
   `BUF2LONG(tp)` 读 ADDSIZE，随后 `fhead.PSIZE=BUFP2LONG(tp)` 从 ADDSIZE 的位置读起——
   PSIZE/SIZE/FTIME/ATTR/CRC32/TECH/FNAME 整体错位一格：FNAME_SIZE 读到 TECH.PARM=0
   （文件名列空）、CRC32 读到 ATTR（CRC 校验必失败）、FTIME 读到 SIZE（日期乱）。
3. **makefile 链接行硬编码 `gcc`**：`unace$(EXEEXT): gcc $(CFLAGS) -o $@ $^`——
   命令行 `CC=clang` 只覆盖编译规则，链接行照样找 gcc；无 gcc 的环境直接
   `gcc: No such file or directory`。另有 BCC/Watcom 风格 `-dNAME` 传宏（clang 报
   unused-argument warning，宏从未生效，属死 flag 非阻断）。

## 修复/验证方法

```sh
# 1) typedef 固定 32 位（declare.h；Debian 004_64_bit_clean 同方向，其用 <stdint.h>）
#    unsigned long ULONG -> unsigned int ULONG; long LONG -> int LONG
# 2) read_header 读 ADDSIZE 同时推进指针（unace.c 一处）：
#    skipsize = head.ADDSIZE = BUF2LONG(tp);   ->   BUFP2LONG(tp);
#    （MAIN 头规范上不带 ADDSIZE flag，ACESIGN 从 body[3] 读起的路径不受影响）
# 3) 链接行 gcc -> $(CC)，编译器用命令行 CC= 覆盖（Debian 001 同方向）
# 复验：用最小 stored 档案驱动 l/t/e/x 四命令面，断言文件名/日期/CRC OK/内容逐字节一致
python3 mkace_test.py /path/to/test.ace   # 档案生成器（纯文本入库，避免二进制进提交面）
sh test_unace.sh <包产物>/bin/unace test.ace work   # 7 断言，SUMMARY pass=7 fail=0
```

判定标准：`l` 显示文件名与 `21.09.26` 型日期、`t` 打 2 次 `CRC OK`、`e`/`x` 提取内容与
夹具逐字节一致 ⇒ 三处断裂全部修复；只修 typedef 时文件名仍空 ⇒ 是 ADDSIZE 错位；
只修 read_header 时字段仍乱 ⇒ 是 typedef 宽度。

## 实证

unace 1.2b（OHOS aarch64，任务分支 feat/unace-1.2b，HEAD f95d6f1f）：
三处全修后 conan create 干净轮 + test_package 消费者 7 断言全过；包产物
`readelf` 五项（DYN/PIE、GNU_STACK RW、GNU_RELRO、BIND_NOW、FLAGS_1 PIE）全过。
源选择教训：pkgsrc distfiles 的 `unace-1.2b.tar.gz` 与 Debian pool
`unace_1.2b.orig.tar.gz` 字节不同，前者带陈旧 `.o` 编译残留（会把 make 骗进
「目标已最新」），同类老包选源时必须解包核对。

- 关联：Debian unace 补丁系列（001_cpp_define / 004_64_bit_clean）
