# dds2tar 2.5.2 适配笔记

## 上游信息
- 上游: GWDG（德国哥廷根大学计算中心）的 dds2tar，作者 Jörg Weule
- 功能: 读取 DDS/DAT（Digital Data Storage）磁带上的 tar 归档
- 形态: 7 个 C 文件（~2200 行）+ 一个传统 Makefile，无 autotools/cmake

## 源码获取
上游站点在 CI worker 上不可达。改用 **Debian pool 的 orig.tar.gz**：
```
https://deb.debian.org/debian/pool/main/d/dds2tar/dds2tar_2.5.2.orig.tar.gz
sha256 = 5faebb922f7bb0a4313b1f13abd92910e0bff8bdc470adce7610ed469751e82c
```
解包根目录为 `dds2tar-2.5.2.orig`（配方用 `strip_root=True` 忽略）。

## 编译：一份源文件 → 两个工具

上游 Makefile 的关键设计（也是本包最值得沉淀的点）：

```make
OBJ = dds_index.o dds_extract.o dds_tape.o dds_quote.o
dds2tar:    dds2tar.o  $(OBJ)   →  $(CC) dds2tar.o  $(OBJ) -o dds2tar
dds2index:  dds2index.o $(OBJ)  →  $(CC) dds2index.o $(OBJ) -o dds2index
dds2tar.o:  $(CC) -c dds2tar.c  ... -DPROGRAM=DDS2TAR   -o dds2tar.o
dds2index.o:$(CC) -c dds2tar.c  ... -DPROGRAM=DDS2INDEX -o dds2index.o
```

即：**同一份 `dds2tar.c` 用不同 `-DPROGRAM=` 宏编译两次**，再各自与同一组公共
目标文件链接，产出两个用途不同的可执行文件。配方按同样的宏分支逐个编译：

```
clang -O2 -Wall -DPROGRAM=DDS2TAR   -c dds2tar.c -o dds2tar.o
clang -O2 -Wall -DPROGRAM=DDS2INDEX -c dds2tar.c -o dds2index.o
clang -O2 -Wall dds2tar.o  <OBJ> -o dds2tar
clang -O2 -Wall dds2index.o <OBJ> -o dds2index
```

**不用 make 的原因**：上游的 `.c.o` 隐式规则与自定义后缀规则依赖 `$<`/`$@`，
且 `CC=cc -g` 把选项塞进了编译器变量；直接驱动 clang 更可复现。另 CCOPT 里的
`-O4` 在 clang 上是未知优化级别（会警告并降级），配方统一 `-O2`。

## 运行验证
- `dds2tar` / `dds2index` 无参数/带 `-h` 时走 usage 提示路径，退出码非 0 属预期。
- 真实磁带读取需要 DDS 硬件与 root，不在本 PR 范围。
- 上游 `dds2tar-test.sh` 同样需要真实磁带设备，故不计入自动化测试（MANIFEST.yml 已声明）。

## 测试（test_package，9 条断言）
1–2. dds2tar / dds2index / ddstool 存在、可执行
3.   dds2tar / dds2index 为 ELF64/AArch64（e_machine == 0xB7）
4.   dds2tar 真实执行：未被信号杀死、退出码不在 {126,127,255}
5.   dds2tar 输出非空
6.   dds2index 真实执行：同样排除加载失败码

assertion_count = 9（上游可自动化项为 0）。

**注意**：断言全部用 `popen` 直读子进程输出，**不落盘 /tmp**（OHOS 上 /tmp 只读）。
