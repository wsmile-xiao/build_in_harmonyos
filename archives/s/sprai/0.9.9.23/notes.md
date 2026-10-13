# sprai 0.9.9.23 → HarmonyOS PC (aarch64) 适配笔记

## 1. 这是什么

sprai = *single-pass read accuracy improver*，Takamasa Imai（Kasahara Lab, UTokyo）
写的 PacBio CLR 错误纠正流水线，2013 年首发，最后一版 **v0.9.9.23（2017-02-12）**
至今未再更新。上游站 `zombie.cb.k.u-tokyo.ac.jp/sprai` 已整体下线。

它的**可编译部分**只有 4 个纯 C 命令行程序，彼此用管道串成一条四段流水线：

```
bowtie -m5 输出
   │  m52bfmt7   (bowtie m5 → blastn -outfmt 7 风格表格)
   ▼
   │  bfmt72s     (表格 → sprai 私有 SAM，带 AS:i:/EV:Z:/PI:Z: 标签；-i 把 query 当 reference)
   ▼
   │  nss2v_v3    (SAM → 纵向比对 .nss，-v 设最少投票数)
   ▼
myrealigner      (.nss → 共识 FASTA/FASTQ)
```

另有 17 个 Perl 驱动脚本（`ezez_vx1.pl` / `ca_ikki_v5.pl` / `dumbbell_filter.pl` …），
是真正的流水线编排层（切分、调度 SGE、调用 Celera Assembler 装配），运行期需要
Perl + NCBI BLAST+ + Celera Assembler。

所以本包提供的是 **4 个 C 程序 + 它们之间的格式转换契约**；驱动层按参考载荷装到
`share/sprai/`（理由见 §4.3）。

## 2. 源码溯源与完整性

### 2.1 上游归档已下线（实测 2026-10-05）

| URL | 结果 |
|---|---|
| `http://zombie.cb.k.u-tokyo.ac.jp/sprai/dist/sprai-0.9.9.23.tar.gz` | 301 → `https://kasahara-lab.github.io/sprai_doc/dist/sprai-0.9.9.23.tar.gz` → **404** |
| `http://zombie.cb.k.u-tokyo.ac.jp/sprai/` | 200（重定向到文档站 `kasahara-lab.github.io/sprai_doc/`） |
| `https://api.github.com/repos/kasahara-lab/sprai_doc/releases` | `[]`（无 release 资产） |
| `kasahara-lab` 名下仓库 | 只有 `notifier` 与 `sprai_doc` 两个**文档**仓库，无源码仓库 |

文档站自己的 `Download.html` 里，每个 dist 链接都被写成 Sphinx 注释（`..`），
`kasahara-lab.github.io/sprai_doc/_sources/Download.rst.txt` 原文即：

```rst
Download The Latest Version
===========================
.. http://zombie.cb.k.u-tokyo.ac.jp/sprai/dist/sprai-0.9.9.23.tar.gz
```

也就是说**上游自己把下载入口下掉了**，只剩 rst 源码里的历史字符串。

Wayback 取不到：`web.archive.org` / `archive.org` 在本机网络不可达
（DNS 解析到 108.160.170.39，TCP 连接全部超时，Windows 侧同样失败）；
`archive.ph`、`archive.softwareheritage.org`（404）、`www.kasahara.ws`（LPM，
连接超时）也都不通。

Debian 侧对同一事实有官方记录：

- `debian/README.source`：*The upstream website vanished. Latest source was verified at wayback machine.*
- `debian/watch`：整段 watch 规则被注释，注明 *Upstream site vanished and parsing web.archive does not sound sensible*

### 2.2 因此取 Debian 官方池的 upstream orig 包

```
https://deb.debian.org/debian/pool/main/s/sprai/sprai_0.9.9.23+dfsg1.orig.tar.xz
Content-Length: 60428
sha256: b7190784e07c803e465a07b4b3aba86b8c82c93878c4e252e8c715d20d22c2
```

`deb.debian.org` 是 Debian 的**正式发行归档**（不是第三方镜像），本仓库已有
497 个配方的 `conandata.yml` 走同一来源。它是上游 0.9.9.23 tarball 的 `+dfsg1`
重打包，`debian/copyright` 的 `Files-Excluded` 写明删掉了：

- `doc/_build/html/*.html` `*.js` `*.inv` `_static` —— 已构建好的文档产物
- `waf` `waflib` `wscript` —— 上游 waf 框架，本包用裸 `makefile` 构建，从不使用

删掉的这 5 类文件对本包的构建与产物**零影响**：4 个 `.c`、`col2fqcell.h`、
`makefile`、`configure`、17 个 `.pl` 全部在包内（`tar -tJf` 共 35 项，已逐项核对）。

### 2.3 完整性证据链

1. **与签名 .dsc 一致**：`sprai_0.9.9.23+dfsg1-3.dsc`
   （sha256 `50b26cb58aa98a060b4eae9454587417332d03fbea78316743245c626fef651a`）
   的 `Checksums-Sha256` 段里 orig 包就是上面那个值，逐字相同。
   `conan get()` 的 `verify=True` 默认开启，第一次 `conan create` 就因为手抄
   sha256 掉了两个字符被当场拦下（`Computed hash: ...`），改用实测值后通过 ——
   这条本身就是校验链生效的证据。
2. **与独立第三方镜像逐文件交叉验证**：第三方 GitHub 仓库
   `frikiluser/sprai`（2020 年镜像，内容是上游 0.9.9.23 源码 + Debian 打包目录）
   与本包用 `git hash-object` 比对 27 个文件：

   | 结果 | 文件 |
   |---|---|
   | SAME（23） | `bfmt72s.c` `nss2v_v3.c` `myrealigner.c` `m52bfmt7.c` `col2fqcell.h` `makefile` `configure` `ChangeLog.txt` `LICENSE.txt` `ec.spec`… 中的 13 个 `.pl` |
   | DIFF（4） | `ec.spec` `ezez4makefile_v4.pl` `ezez4qsub_vx1.pl` `ezez_vx1.pl` |

   那 4 个 DIFF **恰好就是** Debian `debian/patches/series` 里
   `libexec.patch` + `example-specs.patch` 所改的 4 个文件（镜像那份已套用 Debian
   补丁）。也就是说：本包是**未打任何补丁的上游原始内容**，与第三方镜像的差异
   全部可由 Debian 补丁逐条解释，没有第三方改动的余地。

3. 构建产物与上游版本号自洽：包内 `makefile` 头两行即
   `APPNAME = 'sprai'` / `VERSION = '0.9.9.23'`，与目录名、配方 `version`、
   `commands.json` 的 key 四处一致。

## 3. 构建系统勘察

- **唯一可用的构建入口是裸 `makefile`**（文件名全小写，GNU make）。只有两个 target：
  - `all` → `$(COMPILED)` = `bfmt72s` `nss2v_v3` `myrealigner` `m52bfmt7`
  - `install` → `chmod 766 $^ && cp -p $^ $(PREFIX)/bin/`（`PREFIX=$(PWD)`）
- 4 条编译规则把 flags **硬编码**在规则里：
  `$(CC) -Wall -O3 -g -o $@ $<` —— 命令行传 `CFLAGS=` 完全无效（实测）。
- 编译规则全是相对路径，没有 srcdir/builddir 概念 → 只能**就地构建**
  （配方 `layout()` 把 `folders.source` 指到 `source_folder`，与
  `magicrescue/1.1.10` / `termdebug/2.2` 同款）。
- 依赖：4 个 `.c` 只 include `stdio.h` `stdlib.h` `string.h` `unistd.h`
  `getopt.h` `ctype.h` `assert.h` 和本地的 `col2fqcell.h`。**零外部库**。

### 3.1 为什么不跑 `./configure`

tarball 里确实有个 `configure`，但它**不是** autoconf —— 打开看是 "waf configure
wrapper"：检查 `waf`/`waf-light` 是否存在，生成一个转发到 `waf configure` 的
`Makefile`，然后执行 waf。而 `+dfsg` 重打包已按 `Files-Excluded` 删掉
`waf` / `waflib` / `wscript`，所以在本包里它必然走到
`not found` → `exit 1`。

Debian 自己也明确不用它：`debian/rules` 是
`dh $@ --buildsystem=makefile`（changelog: *Fix FTCBFS: use the makefile buildsystem*）。

## 4. 适配决策

### 4.1 【必需】`-fsigned-char`：aarch64 上 myrealigner 必崩

这是本轮唯一的**功能性**适配，也是不做就一定交付不了包的地方。

`col2fqcell.h` 第 2-5 行：

```c
typedef struct base_t{
  char base;
  ...
}base_t;
```

`myrealigner.c` 把 `-1` 当作 `el.base` 的哨兵，共 4 处：

- `myrealigner.c:628` `else if(curEl[row]->el.base == -1){`
- `myrealigner.c:745` `for(ptr=pf->ofrag; ptr->el.base != -1; ptr=ptr->next){`
- `myrealigner.c:977` `if(fptr->next->el.base != -1){`
- `myrealigner.c:1007` `while(ptr->el.base != -1){`

plain `char` 在 x86-64 上默认 **signed**，在 aarch64（AAPCS64 / clang 默认）上是
**unsigned**。于是 `base != -1` 变成恒真，片段链表被 walk 出界。

实测对照（同一份输入 `.nss`，同一台机器）：

| 构建 | 结果 |
|---|---|
| x86-64 + 系统 gcc 11（默认 signed char） | 正常输出共识 `ACGTACGTAC` / 深度 5 |
| aarch64 + OHOS clang 15（默认 unsigned char） | **每次调用都 SIGSEGV**（rc 139） |
| aarch64 + OHOS clang 15 + `-fsigned-char` | 与 x86-64 输出逐字节相同 |

clang 在编译期就点破了这件事：

```
myrealigner.c:628:35: warning: result of comparison of constant -1 with
  expression of type 'char' is always false [-Wtautological-constant-out-of-range-compare]
```

所以解法是**加 `-fsigned-char`**（复现作者写代码时假定的 char 语义），而不是改
那 4 行 —— 改源码会偏离「端口适配」的范围，而且 `-1` 哨兵在 `bfmt72s.c:26` /
`nss2v_v3.c:197` 等处还有同类用法，逐个改不彻底。

顺带说明：另外 3 个程序的 `!= -1` 都是 `getopt()` 的返回值比较（`int`），
不受影响；但统一对 4 个目标都加 `-fsigned-char` 更符合「让整个包跑在作者假定的
语义下」这个理由。

### 4.2 `patches/0001-makefile-honour-cflags.patch`：让 CFLAGS 传得进去

因为 4.1 的 flag 必须进去，而 makefile 硬编码 flags，所以照 Debian
`debian/patches/flags.patch`（Chris Lamb, Bug-Debian #956473）的同一改法，
把 4 条规则改成：

```make
$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ $<
```

配方随后传 `CFLAGS='-O3 -fsigned-char'`：保留上游的 `-O3`（作者的优化意图），
去掉 `-g`（Conan 包是发布件，不带调试信息）。

> 附带观察：本地产物里仍有 `.debug_*` 段，但它们来自本地 clang shim 静态链接进来的
> `libc++abi.a` / `libc++.a` / `libunwind`，不是我们这条命令产生的
> （单独 `-c` 编出的 `.o` 里 `readelf -S | grep -c debug_info` 为 0）。

### 4.3 17 个 Perl 脚本装 `share/sprai/`，不进 `bin/`

它们是 sprai 真正的编排层，但运行期要 Perl + NCBI BLAST+ + Celera Assembler。
实测制品仓：

```
conan list "perl/*@ohpcd/stable" -r=ohpcd   → Found 0 pkg/version recipes
conan list "blast*"                -r=ohpcd   → Found 0 pkg/version recipes
```

即 OHOS aarch64 下这三样一个都没有。放进 `bin/` 会让 CI 的 L2 冒烟门禁
（逐个执行 `bin/*`）去跑一堆注定失败的 perl 脚本，还会让 `commands.json`
声称提供了实际不可用的命令。所以：

- `bin/` = 恰好 makefile `COMPILED` 的 4 个 ELF（配方硬断言多一个少一个就失败）
- `share/sprai/` = 17 个 `.pl`（755）+ `ec.spec` + `pbasm.spec` +
  上游 6 份文档（`doc/_build/html/_sources/*.txt`）+ `ChangeLog.txt` + `LICENSE.txt`

`ec.spec` 里带着作者本机的绝对路径（`ca_path /home/imai/wgs/Linux-amd64/bin/`、
`blast_path /home/imai/bin/`）。Debian 用 `libexec.patch` 注释掉了它们；本包
**不改上游 spec 内容**（那属于运行期配置而非构建适配），但在 `notes`/`manifest`
里写明它只是数据、不会被当可执行文件安装。

### 4.4 ELF 自签

真机 HMDFS 拒绝执行未签名 ELF（cronutils 首轮 `PermissionError errno 13`），
`package()` 里按仓库惯例做 `binary-sign-tool -selfSign 1`。本机没有该工具，
走 warning 分支跳过；真机 CI 上由 `/data/service/hnp/bin/binary-sign-tool` 完成。

## 5. 为什么静态段不是空壳

静态段 93 条断言里有 50+ 条是**反证型**的：

- `bin/` 必须**恰好**是 `makefile` 的 `COMPILED` 四个目标（不是「至少有」）
- 四个目标必须是**四份互不相同**的普通文件：symlink 判失败、sha256 去重后必须
  仍是 4 个（挡住「一个二进制复制成四个名字」或「四个名字软链到同一份内容」）
- 每个 ELF 手工解析 ELF 头：`ELF64` / little-endian / `e_machine == 0xB7 (EM_AARCH64)`
- 手工解析 program headers：`PT_INTERP` 为 OHOS aarch64 加载器 —— 本机交叉 profile 产出
  glibc 形态 `/lib/ld-linux-aarch64.so.1`，CI 真机 worker 产出 musl 形态
  `/lib/ld-musl-aarch64.so.1`，两者都是 OHOS 系统加载器（见 §11.5）
- 手工解析 `.dynamic` + `.dynstr`：`DT_NEEDED` 含 `libc.so`（不是宿主 glibc）
- 遍历整个包，任何文件的 ELF 头若不是 aarch64 即判失败（防止 x86-64 混入）
- 17 个 `.pl` 的首行必须是含 `perl` 的 shebang
- `LICENSE.txt` 必须含 MIT 正文（`Permission is hereby granted, free of charge`）

## 5.1 文件自带的三条反假绿守卫

「断言写得再多，也可能是空壳」。所以 `test_sprai.py` 自己带三个**会把自己判红**的守卫：

| 守卫 | 阈值 | 挡住什么 |
|---|---|---|
| `RUNTIME_MIN_EXECS` | 运行段必须真实 fork 出 ≥15 次子进程（管道那一条单独计数） | 把 `run()` 调用删掉/短路掉后「什么都没跑所以 pass」 |
| `STATIC_MIN_ASSERTIONS` | 静态段断言数 ≥55 | 把深层断言整段注释掉后仍报 pass |
| `MIN_ASSERTIONS` | 总断言数 ≥80 | 同上 |

另有 `run()` 捕获 `OSError`：产物被换成 0 字节桩 / 非 ELF 时，报
`FAIL: … usage banner missing (stderr='RUN FAILED: Exec format error: …')`
这种**可读的红断言**，而不是一个 `Traceback` —— traceback 只证明脚本崩了，
红断言才证明行为契约被破坏。

## 6. 验证记录

### 6.1 本地交叉编译（WSL 原生盘 ext4）

```
conan create /root/ohpcd-work/wt-sprai/archives/s/sprai/0.9.9.23 \
  --name=sprai --version=0.9.9.23 \
  -pr:h=ohos-aarch64-wsl-xbuild -pr:b=default --build=missing
→ EXIT_RC=0
package sprai/0.9.9.23#4970b7b49b9037e6dac13dfd53a23d31:6b129b068851896169fae42d399fa922d239ce8a
```

编译行（证明补丁与必需 flag 都到位）：

```
/opt/lpk-fixed/clang  -O3 -fsigned-char  -o myrealigner myrealigner.c
```

产物（`bin/` 四个，全 aarch64 PIE，只依赖 `libc.so`）：

| 文件 | 字节 | sha256 |
|---|---|---|
| `bin/bfmt72s` | 29960 | `b56d9e26a62b4f849c8b33981d1d241c6265c09840e3791f15128866029961f6` |
| `bin/nss2v_v3` | 34736 | `ca15fb31b42f3ebc00dd42a51ae6f073e012ee931ba9fdefae8272565a0e27c3` |
| `bin/myrealigner` | 36544 | `3330c2235752ab676f7f6d605acb24dbbcfd9ae11bf591773fbce9c2f0ed2879` |
| `bin/m52bfmt7` | 16712 | `5d74865cbdb34ae91984a8c8697cd63b603730b218a582f747c7a89261528b99` |

`file(1)`：四个都是
`ELF 64-bit LSB pie executable, ARM aarch64, dynamically linked, interpreter /lib/ld-linux-aarch64.so.1`
（**这是本机交叉 profile 的产物形态**；CI 真机 worker 用的是 OHOS 默认 musl 工具链，
解释器是 `/lib/ld-musl-aarch64.so.1`。两者都是 OHOS aarch64 系统加载器，见 §11.5。）

### 6.2 消费者测试

两段都跑。交叉 profile（`-pr:h=ohos-aarch64-wsl-xbuild -pr:b=default`，
显式 `tools.build.cross_building:can_run=false`）下只跑静态段；
门禁/原生 profile（`-pr:h/-pr:b` 同为 `ohos-aarch64-wsl`）下 `can_run()` 为真，
**两段一起跑**。2026-10-11 本地同源门禁实测：

```
sprai/0.9.9.23 (test package): RUN: "…/test_sprai.py" "/root/.conan2/p/b/spraica2fb41e24bf2/p" --runtime
SPRAi_RUNTIME=executed execs=15
sprai consumer test: 119 passed, 0 failed
L_RESULT=pass: 119/119 assertions
```

即静态段 93 条 + 运行段 26 条 = 119 条，全程在**打包后**的 aarch64 产物上实跑。

运行段断言的是**格式转换契约**，逐字段精确比对（不是"跑通就算"）：

1. `m52bfmt7`：m5 → 表格。含 `read0001/1 → read0001` 的 `/` 截断、
   `sstt+1` 的 1-originize、`pident = nMatch/(nMatch+nMismatch+nIns+nDel)`
   按 `%f` 打印（`78/79→0.987342`、`10/11→0.909091`、`10/12→0.833333`）
2. `bfmt72s -i`：表格 → SAM。`-i` 下 QNAME/RNAME 互换、`PI:Z` 是 pident 保留两位
3. `nss2v_v3 -v 3`：SAM → 纵向比对。含一条 `qname==rname` 的 ref-ref 记录
   （**必需**，见 §8）
4. `myrealigner`：纵向比对 → 共识，深度 5 = 4 条 read + 1 条 reference 片段
5. `myrealigner -f -c`：同一输入出 FASTQ，quality `5` = Phred 20 = 5 票
6. 整条管道 `m52bfmt7 | bfmt72s -i | nss2v_v3 -v 3 | myrealigner -f -c` 端到端比对
7. 错误路径 4 条：m5 畸形行 / `-u -U` 互斥 / `-v 0` / SAM 截断

第 4 条正是 4.1 那个 bug 的**载荷断言**：不修 `-fsigned-char` 时 `myrealigner`
在 aarch64 上根本走不到比对，跑不出 rc=0，更不用说逐字段比对深度值。

## 7. CI 门禁预期

| 门禁 | 预期 | 依据 |
|---|---|---|
| L1 上游测试 | `skip`（需维护者在 `ci/config/no_official_test.txt` 侧加 sprai） | 上游零测试目标。本 PR **不改 `ci/`**（R21 越权目录），见 §10 |
| L2 冒烟 | `[warn]`（非阻塞） | 上游 4 个工具都没有 `--version`/`--help`，getopt 遇未知选项即 usage + 非零退出 |
| L4 补丁扫描 | `pass` | `patches/0001-makefile-honour-cflags.patch` 不含 `strcpy/sprintf/gets/strcat` |
| L5 产物 | `pass` | `bin/` 有内容；无 `.so`，R26/SO﻿NAME 规则不适用 |
| PF8 | `pass` | `settings` 四项齐全、slug `sprai` 合规、`commands.json` 已补 |
| PF9 | 需 `--no-preflight` | 仓库工具自相矛盾：PF8 强制 CLI 包带 `archives/<字母>/<包>/commands.json`（4 段路径），PF9 又拦任何 `archives/` 下 `len(split('/')) < 5` 的变更。**所有**纯 CLI 包的 PR 都必然被拦，只能 `--no-preflight` 并在 PR 正文写明理由 |

## 8. 写端到端测试数据时踩到的上游约束

**`nss2v_v3` 拒绝输出，除非输入里至少有一条 `qname == rname` 的 ref-ref 记录。**
`nss2v_v3.c:914-926`：

```c
if(strcmp(t_sam->rname,t_sam->qname) == 0){/* this is a ref-ref hit */
  ...
  ++ref_count;
}else{
  if(ref_count <= 0){ continue; }   /* 对没有 ref-ref 的区段直接丢弃 */
}
```

`bfmt72s` 的 `-i`（*regards blasted queries as references in the output sam*）
正是为此存在。第一次写测试数据时忘了这条，`nss2v_v3` 静默输出空文件、rc=0，
看起来像「没输出也没报错」的 bug。

另外它要求输入**按「染色体名 → evalue → bitScore」排序**（靠相邻染色体切换来
flush 投票列），usage 里也写了；测试数据因此让 4 条记录同区间、同染色体。

## 9. 上游遗留问题（本轮不修，仅记录）

1. **`abs()` 处理 double**（`bfmt72s.c:707` / `:711` / `:839`）：
   `blast.bitscore` 是 `double`，却传给 `abs(int)`。clang 报
   `-Wabsolute-value`。默认路径上 bitscore 恒为正，结果恰好正确；
   负 bitscore 场景（如反向链的某些 BLAST 配置）会得到无意义值。
   属于上游逻辑缺陷，不在「端口适配」范围内，改了会偏离上游行为。
2. **调试残留 `printf("humei\n")`**：`bfmt72s.c:347` / `m52bfmt7.c:48` /
   `nss2v_v3.c:827` 在 getopt 的 `case '?'` 里。任何非法选项都会往 **stdout**
   打若干行 `humei`。消费者测试因此只断言 stderr 的 usage 文本，不断言 stdout。
3. **`-s` 是死开关**：`m52bfmt7` 的 `-s` 只置了个没人读的
   `opt_swap_query_and_subject`，功能未实现。
4. **`-Wunused-result` / `-Wmisleading-indentation` / `-Wabsolute-value`**：
   上游若干处 `fgets()` 未查返回值、`myrealigner.c:1313` 的 `for` 体缩进有歧义。
   都不影响本平台的正确性，未改。

## 10. 待人工确认 / 后续

- **上游站已死**：配方用的是 Debian 官方池的 `+dfsg1` 重打包（§2 已用两条独立
  证据链证明它就是未打补丁的上游 0.9.9.23）。若维护者认为应当改用 Wayback 快照
  （`https://web.archive.org/web/20180307125408/http://zombie.cb.k.u-tokyo.ac.jp/sprai/dist/sprai-0.9.9.23.tar.gz`，
  bioconda 记录的 md5 是 `8c4978fe51d51c89ea7bccd99af47f25`），只需替换
  `conandata.yml` 的 url+sha256 —— 但**本机网络到 archive.org 不可达**，无法预验证。
- **驱动层缺运行期依赖**：17 个 `.pl` 在 OHOS 上跑不了（无 Perl / 无 BLAST+ /
  无 Celera Assembler）。若后续希望提供完整流水线，需要先解决这三者的 OHOS aarch64
  可用性，那是独立的工作项。
- **L1 白名单需维护者操作**：上游零测试目标，L1 的上游测试检查需要 `sprai` 进
  `ci/config/no_official_test.txt`。本 PR **不再改 `ci/`**（R21 把 `ci/` 列为协作者
  越权目录，评审意见 192538236 已要求撤回该改动，且已撤回）——请维护者在
  `ci/` 侧统一加入，否则 L1 会 fail。这是本 PR 唯一需要维护者动手的点。
- **CI 结果**：本地同源门禁 `ci/conan/build_and_test.sh`（zsh，`JUNK_PR_DIFF` 喂真实
  PR diff）2026-10-11 实跑 `GATE_EXIT=0`，L0/L1/L2/L4/L5 全绿、L1e `[ok]` 且日志里
  有真实的 `[sabotage] bin/ moved away`；L2 三个工具走 `[warn]` 分支（非阻塞，
  符合 §7 预期）。真机 CI 结果见 PR !14783 评论流。

## 11. 评审意见处置与本轮复验（2026-10-11 第二轮）

### 11.1 评审意见逐条处置

| 意见 | 处置 |
|------|------|
| atomgit-bot #192538235（🟠 High）：`test_sprai.py` 的 `check()` 没有 `return condition`，调用方 `if not check(cond, msg): continue` 因 `not None` 恒真而短路，第 166 / 182 行的深层断言被静默跳过（报告 36 条，属「假成功」） | **已修**：`check()` 末尾补 `return condition`（`check_eq` / `check_ge` 同步），断言数 36 → **119**；并加三条反假绿下界守卫（`STATIC_MIN_ASSERTIONS=55` / `MIN_ASSERTIONS=80` / `RUNTIME_MIN_EXECS=15`），同类缺陷再犯会直接判 FAIL 而不是静默通过 |
| atomgit-bot #192538236（🟡 Medium）：PR 改了 `ci/config/no_official_test.txt`，触碰 R21 协作者越权目录 | **已撤回**：当前 diff 内 `ci/` 零改动，9 个改动文件全在 `archives/` 下；改为在本文件 §10 与 PR 正文请求维护者在 `ci/` 侧统一加入 `sprai` |
| Septest 行级评论「⚠ test_package 需复核」（#193049161 / #193079418 / #193183647 / #193190642 / #193196518） | **已复核并加固**：新增三条自带守卫 + 七段反向破坏对照，破坏产物功能必红、复原必绿（§11.2）；test_package 的 `conanfile.py` 不做 `can_run()` 静默跳过（静态段无条件执行），避免 T347 那类「L1e 反向验证必然红」的坑 |

### 11.2 反向破坏复跑（HEAD `897d54bd2f`，2026-10-11 本机实跑）

package folder 取自本轮 `conan create` 日志的
`Package folder /root/.conan2/p/b/spraic0a8497856a46/p`（不是 `conan list` 猜的）；
动手前三道硬守卫：必须非空、必须在 `/root/.conan2/p/b/` 下、`bin/` 与 4 个可执行文件必须存在。

| 场景 | 期望 | 实测 |
|------|------|------|
| A 基线（产物完整） | rc=0 | `conan test` rc=0；`--runtime` rc=0；`SPRAi_RUNTIME=executed execs=15`，`L_RESULT=pass: 119/119` |
| B 4 个 ELF 全换成 **0 字节桩** | 必须真失败 | rc=1；`70 passed, 29 failed`。红断言落在行为层：`FAIL: m52bfmt7 m5->tabular conversion`、`FAIL: bfmt72s tabular->SAM conversion`、`FAIL: nss2v_v3 SAM->vertical conversion`、`FAIL: myrealigner must exit 0 (RUN FAILED: Exec format error: …)`；**Traceback 数 = 0**（是红断言，不是脚本崩溃） |
| C 复原 | rc=0 | 四个 sha256 与同一次构建原件逐字相同；rc=0，`119/119` |
| D `bin/bfmt72s` 换成宿主 `/usr/bin/true`（x86-64） | 必须真失败 | rc=1；`111 passed, 8 failed`：`must be EM_AARCH64`、`must use the OHOS loader`、`package must contain no foreign-arch ELF`、`bfmt72s tabular->SAM conversion`、`end-to-end pipeline FASTQ output` |
| E 复原 | rc=0 | rc=0，`119/119` |
| F 移走 `share/sprai/ezez_vx1.pl` | 必须真失败 | rc=1；`117 passed, 1 failed`：`share/sprai/ezez_vx1.pl missing` |
| G 复原 | rc=0 | rc=0，`119/119` |

**产物在 ≠ 断言通过；破坏产物功能即失败。**

### 11.3 本轮门禁与 test_package 复跑

```
静态段（本机直接跑 test_sprai.py）: sprai consumer test: 93 passed, 0 failed
本地同源门禁 ci/conan/build_and_test.sh:
  JC_RESULT=pass            Junk Files: 0
  L0_RESULT=pass: all checks passed
  L1_RESULT=pass: test_package executed
  L1e: [sabotage] bin/ moved away → [ok] L1e: Negative test confirmed — test genuinely depends on sprai
  L2_RESULT=pass（bfmt72s/myrealigner/nss2v_v3 走 [warn] 非阻塞分支）
  L4_RESULT=pass: patches clean
  L5_RESULT=pass: bin/ has content
  ##### GATE_EXIT=0
```

### 11.4 文档同步

PR 标题加 `【积分赛】` 前缀；PR 描述按积分赛事模板重写（5 个基本信息字段用裸值、
上游/适配后两张测试用例统计表合计行自洽、两个勾选项、`编译状态：通过`），
取证内容（源码溯源、`-fsigned-char`、补丁、反向破坏、上游遗留）全部移入「补充说明」。

### 11.5 由 CI 构建 #84741 暴露并修掉的真实缺陷：loader 断言锁死了 glibc 形态

2026-10-11 19:28 的 CI 构建 **#84741**（worker CI-018）第一次真正跑完 `conan create`
（此前 #84638 是 worker `posix_spawn` EAGAIN，属 A 类平台故障）。结果：

```
SPRAi_RUNTIME=executed execs=15
sprai consumer test: 115 passed, 4 failed
FAIL: bin/bfmt72s must use the OHOS loader
    expected: '/lib/ld-linux-aarch64.so.1'
    actual:   '/lib/ld-musl-aarch64.so.1'
L_RESULT=fail: 115/119 assertions
```

**这是 test_package 自己的缺陷，不是库的缺陷。** 静态段的 loader 断言写成了
`check_eq(info["interp"], "/lib/ld-linux-aarch64.so.1", ...)` —— 那是**本机交叉
profile** 产出的形态；CI 真机 worker 用的是 OHOS 默认 **musl** 工具链，解释器是
`/lib/ld-musl-aarch64.so.1`。四个 `bin/` 目标各红一条，正好 4 条失败。

修法：把断言从「等于某个具体路径」改成「是 OHOS aarch64 的系统加载器」，
两种形态都接受，同时仍然拒绝宿主/外来架构的解释器与构建机绝对路径：

```python
OHOS_LOADERS = ("/lib/ld-musl-aarch64.so.1", "/lib/ld-linux-aarch64.so.1")
check(info["interp"] in OHOS_LOADERS,
      "bin/%s must use an OHOS aarch64 loader, got %r (accepted: %s)" % (...))
```

同一构建的正向证据（说明其余 115 条断言在真机上是成立的）：

- `[step] Pre-download: extracting source URLs from conandata.yml... found 1 source URL(s)`
  —— §11.4 的 T124 修复在真机 CI 上生效（改前是 `found 2`）；
- `SPRAi_RUNTIME=executed execs=15` —— 运行段**在真机上真的 fork 出了 15 个子进程**，
  四段流水线端到端跑了；
- `ConanException: Error 1 while executing` 来自 test() 第 41 行，即**断言红**，
  不是崩溃、不是编译错误。

**教训**：断言「平台特定的绝对路径」时，先问一句**CI 的工具链会不会给出另一个合法值**。
本机 profile 与 CI profile 不是同一套（本机 `/opt/lpk-fixed/clang` + shim，
CI `/data/service/hnp/bin/clang` + musl），凡是能从 `file(1)`/`readelf` 读出来的
平台细节，都要按**语法类别**判而不是按**字面量**判。

## 12. 第三轮评审（2402_87729496，2026-10-11 17:00）处置：rule7 CI 状态

### 12.1 意见与裁定

唯一 FAIL 项是 **rule7（CI 校验状态）**，引用的是 **#84638**。其余 12 条规则全 PASS，
且评审自己核实了上游 N=0 未少报、9 个文件均在 archives/knowledge 目录。

### 12.2 #84638 的根因：worker 资源耗尽，不是代码（见坑库 T460）

#84638（worker CI-015）日志末尾指纹：

```
/data/service/hnp/bin/clang ... -o bfmt72s bfmt72s.c
clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable
make: *** [makefile:41: bfmt72s] Error 1
ERROR: sprai/0.9.9.23: Error in build() method, line 122 → ConanException: Error 2
```

`posix_spawn failed: Resource temporarily unavailable` = worker 进程/线程配额耗尽（fork EAGAIN
同族），与代码无关。旁证：评审进行时（17:00 前）头 SHA 6cccbcd4bf 已在 worker CI-020
上有 #84741（代码真跑完、暴露并修掉 loader 断言缺陷，§11.5）与 #84921 之前的历史绿轮。

### 12.3 处置：不改码，重发 /rebuild，CI 已绿

2026-10-11 12:00 由 wzp780028 重发 /rebuild；**#84921**（worker CI-024，
22:50 +08，晚于评审意见）**CI 校验通过**：

- Conan test_package: 通过；L0 门禁：通过；L1 门禁：通过
- 7 个构建步骤全 ✅（worker_preparation / git-clone / checkout-pr / conan-setup /
  conan-build-test / cleanup）
- 日志：https://ohpcd.atomgit.com/ci?id=84921

结论：本轮 **零代码改动**，配方/补丁/test_package 均未动（6cccbcd4bf 之后的差异只有本
notes.md 的 §12 记录）。处置回复已按「意见 → 处置 → 证据」发到 PR 评论流
（2026-10-11 23:00，acc2/wzp780028），评审意见采用顶层 note 形态、平台不允许对该类型
做 resolve 操作（API 语义：This type of note can not be resolved），已用回复 + 本节记录
闭环。

### 12.4 本轮踩到的新坑（已登记坑库）

- AtomGit v5 顶层 PR 评论（pr_comment 类型）**不可 resolve、不可 PUT 改写、DELETE 405**；
  发评论前先校对正文，特别是 **bash 里内嵌反引号会被命令替换吞掉中间文本**——报错指纹
  丢失后无法原位修复，只能重发一条补全（第一条残缺评论留在了评论流里）。

## 13. 第四轮派单复核：rule7 的「绿构建必须落在 head 上」与重复派单根因（2026-10-11）

### 13.1 本轮没有新意见，是同一份意见的重复投递

管理员 2402_87729496 的裁决仍是最初那份（17:00 `VERDICT=FAIL`，唯一 FAIL 项 **rule7**，
引用 **#84638**）。本次派单是同一份意见的重复投递，根因在平台侧：**顶层裁决评论是
`pr_comment` 类型，AtomGit v5 上既没有 `resolved` 字段、也不可 resolve/编辑**
（§12.3，坑库 T363 / T467）——平台的 unresolved 计数无法归零，于是同一 PR 会被周期性
重复派活。

可 resolve 的**行级**意见只有一条，且已经是 `resolved=true`（unresolved = 0）：

| 意见 | 类型 | 状态 |
|---|---|---|
| 2402_87729496 #193197697 / 行级 #193197693「⚠ test_package 需复核」 | `diff_comment` | **resolved=true** |
| 2402_87729496 #193197685 `VERDICT=FAIL`（rule7） | `pr_comment` | 平台不支持 resolve（见上） |
| atomgit-bot #192538235（High，`check()` 恒返回 None）/ #192538236（Medium，越权改 `ci/`） | `diff_comment` | resolved=true（已修复/已撤回，见 §11.1） |

### 13.2 现场事实（2026-10-11 API 实测）

| 项 | 实测值 |
|---|---|
| PR head | `da128c32f9722731489690387b11050fd63adc4b`（feat/sprai-0.9.9.23） |
| PR base | main `e0d7b91d74d3f0befc29dbc103f5c072d60340a7` |
| 最新 CI 结论 | **#84921**（worker CI-024，2026-10-11 22:50:57 +08）`## CI 校验通过`，7 个步骤全 ✅ |
| 该绿构建对应的提交 | `6cccbcd4bf`（loader 断言修复），**早于当前 head** |
| 历史红构建根因 | #84638 = worker `posix_spawn failed: Resource temporarily unavailable`（A 类资源耗尽，§12.2 / T460）；#84741 = loader 断言缺陷，已由 `6cccbcd4bf` 修复（§11.5） |

### 13.3 本轮处置：修正上一轮的顺序缺陷（先文档、后触发 CI）

上一轮是「**先绿后推文档**」：`#84921` 在 22:50 绿，23:03 又推了只改本 notes 的
`da128c32f9` —— 最终 head 上没有对应的绿构建，rule7 仍留隐患。本轮把顺序倒过来：
**先落文档提交，再在最终 head 上重发 `/rebuild`**，让绿构建覆盖最终 head。

- **代码零改动**：`conanfile.py` / `conandata.yml` / `patches/` / `test_package/`
  与已绿轮 `6cccbcd4bf` **逐字节相同**（`git diff 6cccbcd4bf -- <上述路径>` 输出为空）。
- 本地同源门禁（`ci/conan/build_and_test.sh`，`CONAN_PROFILE=ohos-aarch64-wsl`，
  `JUNK_PR_DIFF` 喂真实 PR diff，跑在最终 head 上）与真机 CI 结果以
  PR !14783 评论流为准。
- 管理员的顶层裁决评论不可 resolve，按「意见 → 处置 → 证据」在 PR 评论流回复闭环
  （§12.3 / T467）。
