# unace 1.2b — OHOS 适配笔记

## 源码选择

- 任务上游（WinACE 官网）已不可达。1.2b 是 GPL 公开版（2004 年 Marcel Lemke 改 GPL，
  COPYING 为 GPL-2.0）。
- 选 Debian pool `unace_1.2b.orig.tar.gz`
  （sha256 `a5f3b7d0994b2c6aa3b95ac1196ee18605d8dbd0660f978f8d64b8583fb55490`）。
- pkgsrc distfiles 同名文件 `unace-1.2b.tar.gz`（sha256 `79e0027d…`）与其字节不同，
  解包见 `globals.o`/`uac_*.o` 等陈旧编译残留（会把 make 骗进"目标已最新"，链接出错误
  架构产物），不采用。
- tar 顶层目录为 `unace1.2b`（无连字符），`get(strip_root=True)` 后源码落 source_folder
  根、makefile 在 `unix/` 子目录。

## 构建

- raw make：`make -f unix/makefile CC=<clang> -j1`，无 configure、无依赖。
- 补丁 0003（unix/makefile）：链接行 `gcc $(CFLAGS) -o $@ $^ $(LIBS)` 硬编码 `gcc`
  → 改 `$(CC)`，配方以命令行 `CC=` 覆盖编译器（Debian 001 补丁同方向）。
- 上游 CFLAGS 默认值含 `-dLO_HI_BYTE_ORDER`：`-d` 是 BCC/Watcom 风格传宏，clang 仅报
  `argument unused during compilation` warning、不阻断编译，且该宏在代码里无任何消费点
  （portable.h 只 `#ifdef HI_LO_BYTE_ORDER`），从未生效过——保留原样减少 delta。
- 字节序：os.h 的 UNIX 分支只定义 `DIRSEP`，`LO_HI_BYTE_ORDER`/`HI_LO_BYTE_ORDER`
  都不定义；portable.h 走 `*(UWORD*)p` 主机序直读分支 —— aarch64 小端下正确，
  与 Debian amd64 同路径。不注入任何字节序宏。
- `-DCASEINSENSE` 保留：HMDFS 大小写不敏感，与上游对该类文件系统的默认一致。
- `OSTYPE` ifeq 分支两个非 DOS 出口等价（都加 `-DUNIX -DCASEINSENSE`），CI 与设备
  shell 差异不影响。
- 不跑 `make clean`/`make dep`：前者在大小写不敏感 FS 上有误删风险（§设备事实一.3），
  后者要 gccmaked + bash 且没必要（补丁后直接 make 用现成依赖行）。
- ELF 签名沿用 unzip/6.0 配方形态（llvm-objcopy 去 .codesign 后 binary-sign-tool
  selfSign 重签）。

## 源码修复（0001/0002 补丁）

### 0002 declare.h：LP64 宽度

`typedef unsigned long ULONG` 在 LP64（aarch64）下是 8 字节，而 ACE on-disk 结构全按
32 位设计、`BUFP2LONG`/`BUF2LONG` 宏按 4 字节步进/读取——结构体槽位（thead/tfhead 与
head 缓冲共享视图）与解析步进错位，实测表头字段值全部错乱。固定为 `unsigned int`/
`int`（4 字节）即自洽（Debian `004_64_bit_clean.patch` 用 stdint.h 同方向）。

### 0001 unace.c：read_header 的 ADDSIZE 消费

带 ADDSIZE flag 的 FILE 头布局为 `TYPE FLAGS ADDSIZE PSIZE SIZE ...`（acefile 0.6.8
解析器权威确认：FILE 头 `FLAG_ADDSIZE` 必须置位，否则判 CorruptedArchive）。而
`read_header` 用**不推进指针**的 `BUF2LONG(tp)` 读 ADDSIZE，随后 FILE_BLK 分支的
`fhead.PSIZE=BUFP2LONG(tp)` 从 ADDSIZE 的位置读起——后续所有字段整体错位一格：
文件名列空（FNAME_SIZE 读到 TECH.PARM=0）、FTIME 读到 SIZE、CRC32 读到 ATTR（CRC
校验必失败）。改 `BUFP2LONG(tp)`（一处、同时推进 tp）即全链对齐；MAIN 头规范上不带
ADDSIZE flag，ACESIGN 从 body[3] 读起的路径不受影响。两种布局的对照实验记录在
`reports/conan-verify-supplement.md`。

## 测试

- 上游无任何测试目标（`unix/makefile` 仅 `unace`/`clean`/`dep`），上游 N=0/0。
- test_package 自建最小 ACE v1.0 stored 档案（生成器 `mkace_test.py` 为纯文本入库，
  运行时生成，避免二进制条目进提交面），消费端 7 断言（A1 版本自报 / A2 A3 列表 /
  A4 双文件 CRC OK / A5 A6 平铺提取 / A7 带路径提取）。
- unace 的 main() 无显式 return，退出码不可靠 → 全部断言按输出/内容判定，
  driver 以 `[ "$fail" -eq 0 ]` 收口。
- `t` 命令（test archive integrity）走 analyze_file，`e`/`x` 走 extract_file，
  两者都过 `crc_print()` 的 `CRC OK` 校验。

## 已知限制

- 公开版 1.2b 本身不支持 ACE v2.0 档案、不支持解密（readme 明示），非 OHOS 适配缺口。
