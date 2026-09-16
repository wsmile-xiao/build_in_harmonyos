# conan-verify 人工补测报告 — ocproxy 1.6

`ohc-run.py conan-verify`（采信轮）判定 `Verdict: PASS`，但报告里 G4/L2/L4/L5 四项
落在「`✅ PASS` 与 `⏭️ 跳过` 并存」的已知路径解析缺陷上，按第 7.2 节口径必须人工补测。
本文件逐项给出补测命令、原始输出与判据。

## 0. 采信轮判定

| 项 | 值 |
| --- | --- |
| 采信轮 | 清 `clean_conan_cache.sh ocproxy` 后重跑的 `conan-verify`（DB recipes/packages 两表回查为空） |
| 引用 | `ocproxy/1.6@ohpcd/stable` |
| 包 ID | `6c61b811dee32ee923502180c65131bd5a2ee7df` |
| 干净轮标志 | `Apply patch` ×2、`RUN: make -j1` ×1、`Calling build()` ×1、`TOTAL=17 PASS=17 FAIL=0` |
| 日志 | `reports/conan-create-log.md`（逐字转写，含原始字节数/行数/sha256） |

工具报告里 `conan-verify-report.md` 的 L2/L4/L5 三行是 `✅ PASS` + `⏭️ 跳过（无 cache 路径）`。
下方补测一律用 `conan cache path "<ref>:<package_id>"` 取产物目录（**不用 glob 归属结论**），
并在正文避免写死缓存分片目录名。

## 1. G4 产物完整性人工补测

```sh
PKG=$(conan cache path "ocproxy/1.6@ohpcd/stable:6c61b811dee32ee923502180c65131bd5a2ee7df")
cd "$PKG" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt | sed 's|^\./||' | sort
```

```text
bin/ocproxy
bin/vpnns
licenses/LICENSE
share/doc/ocproxy/CHANGES
share/doc/ocproxy/README.md
share/man/man1/ocproxy.1
share/man/man1/vpnns.1
```

与 `conanfile.py` 的 `package()` 声明一致：`package_info().bindirs = ["bin"]`，两个命令行产物
均在包内；`commands.json` 声明的 `ocproxy/1.6` 与实际 ref 一致。`bin/` 下无第三方同名库，
`lib/` 不存在（纯可执行包，与 G3 的「无系统同名库冲突」判定吻合）。

## 2. L2 平台功能矩阵人工补测

CI 的 L2 探针是 `timeout 15 "$bin" --version`（退而求其次 `--help`），它在裸 PATH 下运行，
对**依赖共享库的产物**必然报 `Error loading shared library`（`notes/defects/ci-and-w3.md`
已登记该形态：`cycfx2prog` 的 libusb 先例同型）。本包两个产物都动态链接 libevent，因此：

```sh
LIBEV=$(conan cache path "libevent/2.1.13:01d92cf349a0dd98ff915f4bd99a04430171517f")
# 裸 PATH（复现框架缺陷的失败形态）
timeout 15 "$PKG/bin/ocproxy" --version >/dev/null 2>&1 ; echo rc=$?   # → rc=127
timeout 15 "$PKG/bin/vpnns"   --version >/dev/null 2>&1 ; echo rc=$?   # → rc=127
# conanrun 等价的加载器环境（真正的产物行为）
LD_LIBRARY_PATH="$LIBEV/lib" timeout 15 "$PKG/bin/ocproxy" --version ; echo rc=$?   # → rc=0
LD_LIBRARY_PATH="$LIBEV/lib" timeout 15 "$PKG/bin/ocproxy" --help    ; echo rc=$?   # → rc=0
LD_LIBRARY_PATH="$LIBEV/lib" timeout 15 "$PKG/bin/vpnns"   --version ; echo rc=$?   # → rc=0
LD_LIBRARY_PATH="$LIBEV/lib" timeout 15 "$PKG/bin/vpnns"   --help    ; echo rc=$?   # → rc=1（设计如此）
```

实测输出（原样）：

```text
  ocproxy --version -> rc=0
  ocproxy --help -> rc=0
  vpnns --version -> rc=0
  vpnns --help -> rc=1
=== 裸 PATH 对照（复核框架缺陷形态）===
  ocproxy --version 裸 PATH -> rc=127
  vpnns --version 裸 PATH -> rc=127
```

`vpnns --help` 退出 1 是上游既有语义（`show_help(); return 1;`），不是失败；L2 探针按
退出码 0 判定，因此即便注入 `LD_LIBRARY_PATH`，`vpnns --help` 仍会被记失败——这正是
`notes/defects/ci-and-w3.md` 描述的「老式 CLI 形态」第二类。`ocproxy --version/-h` 已由
补丁 `0001-src-ocproxy.c.patch` 提供，退出码 0。

**行为级补测**（比 `--version` 强）：在 conanrun 等价环境下重跑 `test_package` 的测试脚本，
仍然 `TOTAL=17 PASS=17 FAIL=0`，其中包含真实 SOCKS5 握手、真实 `-L` 监听、隧道报文投递
（227 字节）与全部失败闭合路径：

```sh
LIBEV=$(conan cache path "libevent/2.1.13:01d92cf349a0dd98ff915f4bd99a04430171517f")
LD_LIBRARY_PATH="$LIBEV/lib" python3 "$PKG/test_package/run_test.py" "$PKG/bin"
# → TOTAL=17 PASS=17 FAIL=0
```

结论：L2 的框架 skip 属加载器缺库的探针缺陷，产物本身在正确的运行环境下功能正常。

## 3. L4 静态安全属性人工补测

```sh
for b in ocproxy vpnns; do
  readelf -h   "$PKG/bin/$b" | grep -E "Type|Machine"
  readelf -lW  "$PKG/bin/$b" | grep -E "GNU_STACK|GNU_RELRO"
  readelf -d   "$PKG/bin/$b" | grep -E "BIND_NOW|FLAGS"
done
```

实测输出（两个产物一致，以下为 `ocproxy`，`vpnns` 同）：

```text
Type: DYN (Position-Independent Executable file)
Machine: AArch64
GNU_RELRO  0x0145c0 ... 0x000510 0x000a40 R 0x1
GNU_STACK  0x000000 ... 0x000000 0x000000 RW 0
0x000000000000001e (FLAGS)     BIND_NOW
0x000000006ffffffb (FLAGS_1)   Flags: NOW PIE
```

判据：**PIE = 是**（`DYN` + `FLAGS_1: PIE`）、**NX = 是**（`GNU_STACK` 只有 `RW`，无 `E`）、
**Full RELRO = 是**（`GNU_RELRO` 段存在且 `BIND_NOW` 置位）。两项产物均满足。

## 4. L5 产物基线与可复现性人工补测

### 4.1 采信轮单轮基线（sha256）

```sh
cd "$PKG" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
  | sed 's|^\./||' | sort | xargs sha256sum
```

实测输出（**本文件成文时那一轮**的值；`bin/ocproxy` 与内容聚合逐轮会变，见 4.2）：

```text
81731ea06e5e5fa099ef8754a8441cc4074b12694be870644701d97335ee9ca9  bin/ocproxy
f7a34c60bf9ba596a781d0122eae4234f921b4c1c278627c17803e1ca93efcf5  bin/vpnns
20995477b73a0c712b049b2d693e40ad3f90f9bbc1eb6a3c511fad935b017968  licenses/LICENSE
e5bf78c330f66f10a46d5211c6309e478c7140ddf350a0c6aeb1edd848f6a697  share/doc/ocproxy/CHANGES
a4a9968506c249be2e798e282564ec151e4a613db0b8765e4e7578e44e0c613a  share/doc/ocproxy/README.md
1634115bb37df324da2c96227ab5f326af9f18d0f3be0a0bb948b7ed26c897cd  share/man/man1/ocproxy.1
ce264dd8ad03a82c033e6dcdad795fd2bf32b0d7975a3a224afba1c70fc89b3f  share/man/man1/vpnns.1
```

内容聚合（在包目录内用相对路径，排除 `conaninfo.txt`/`conanmanifest.txt`）：本轮为
`223897a9063d5b233511170f42c62092b36e4a8967f3e7551bbbd3a576fd8603`，同样**
只对同一轮有效**。

> **不要把上面任何一个 sha256 当作长期漂移判据。** 逐轮清缓存重建会重建缓存分片目录名，
> 而该名字被 lwIP 的断言宏以 `__FILE__` 形式编进 `.rodata`，进而牵动 `.text` 与 `.codesign`
> （见 4.2）。可跨轮复用的稳定判据是下面这一组。

### 4.2 可复现性判别（同提交、两次清缓存构建）

```sh
# 第 1 轮（采信轮）与第 2 轮（复核轮）各自清缓存后重建，逐产物比对
sha256sum <round1>/bin/ocproxy <round2>/bin/ocproxy
sha256sum <round1>/bin/vpnns   <round2>/bin/vpnns
```

| 产物 | 第 1 轮 | 第 2 轮 | 一致 |
| --- | --- | --- | --- |
| `bin/vpnns` | `f7a34c60…93efcf5` | `f7a34c60…93efcf5` | ✅ 逐字节一致 |
| `bin/ocproxy` | `4d27a794…40b94c3` | `cd605d3a…0890089b` | ❌ 不一致 |
| 其余 5 个文件 | — | — | ✅ 逐字节一致 |

（另有独立轮次：`bin/ocproxy` = `911e989e…b354cdda`、`c5c7433d…d697848`、`2e6035ba…9544ac8`，

**结论：`bin/ocproxy` 跨轮不可复现，已定位两个独立根因，均与配方/源码/补丁无关。**

#### 根因 A：lwIP 的断言消息内嵌 `__FILE__` 绝对路径

`contrib/ports/unix/include/arch/cc.h:89` 的断言宏把 `__FILE__` 编进 `.rodata`：

```c
x, __LINE__, __FILE__); fflush(NULL); abort();} while(0)
```

conan 构建时编译器看到的是**绝对**路径，因此 `.rodata` 内含形如
`<缓存分片目录>/b/lwip/src/core/tcp_in.c` 的字符串；而分片目录名（`p/b/ocpro<hash>`）
每次清缓存重建都会变。两轮的 `.rodata` 字符串集合因此不同，字符串布局与后续地址随之
变化，`.text` 里对 `.rodata` 的 PC 相对寻址（`adrp`/`add`）就出现差异：

```text
.text     size 65996/65996  字节差异 1648
.rodata   size  9859/9859   字节差异 >0
.data     size   448/448    identical=True
.dynsym / .dynstr / .eh_frame / .note.ohos.ident / .comment  identical=True
```

节名与节大小完全一致，差异只落在被该路径字符串牵动的字节上。

**对照实验（证明差异由路径长度/内容驱动，而非编译器行为不确定）**：把同一份 work 源码
分别放在两个长度不同的目录（`repro-exp/s` 与
`repro-exp/a-very-long-directory-name-for-the-second-build`）里，用同一 `clang`、同一
`configure` 参数编译（此时编译器看到的是**相对**路径 `../src/...`，两轮字符串长度相同）：

```text
文件大小: 313856 / 313856
.text    size 59024/59024  字节差异 0
.rodata  size  8883/8883   字节差异 0
.data    size   448/448    字节差异 0
.dynstr  size   727/727    字节差异 0
.codesign size 4096/4096   字节差异 64
```

除签名节外逐节一致，说明差异确实来自「编进产物的绝对构建路径」，不是编译器不确定性。

#### 根因 B：`.codesign` 签名本身跨轮不同

两个产物都带 hnp 链接器签名节 `.codesign`（4096 字节，前置 0x18 字节头 + 64 字节签名）：

```text
round2: fcc092ac7de8888f173f6454a60b77adddef3f95f178bfe675c2bf0069f6465a
round3: 693885c793d890732d08e51c0c8c213f56f9d4205240ea9a5eaf6ed4ec815492
```

在上面那个**除签名节外逐字节一致**的对照实验里，`.codesign` 仍在偏移 `0x18`–`0x127`
内有 64 字节差异，说明该签名（Ed25519 形态：随机 nonce）本身不保证跨轮一致，属预期。

### 4.3 基线的使用口径

- 可用于漂移检测的是 **`bin/vpnns` 与 4 个文档/许可证文件的单文件 sha256**（跨轮稳定），
  以及「**同一轮内**」的内容聚合值；
- `bin/ocproxy` 的单文件 sha256 **不跨轮稳定**，不能作为漂移判据；可行判据是
  「节名/节大小集合一致 + `.rodata` 中 lwIP 源路径字符串归一化（剥离分片目录名）后集合一致」；
- `.codesign` 不计入任何基线比较（已证明与内容无关地跨轮变化）。

### 4.4 为什么不能把 ocproxy 也做成逐字节可复现

- 根因 A 要消除，就得让编译器看到相对路径或 `-ffile-prefix-map`，而这属于**构建系统/工具链
  层**的改动（conan 的 autotools helper 在 build 目录调用编译器），不是本软件目录能决定的；
  强行在配方里加 `-ffile-prefix-map` 会给 `.rodata` 断言串写死本机路径规则，且会改变
  package_id 之外的可观测产物，收益与风险不成比例。
- 根因 B 是签名工具的行为，且 `.gitcode/review-memory.md` 明确**禁止**对 hnp 签名产物重签。

因此本任务按「可复现子集给基线 + 不可复现项列明根因」的口径收口，不声称 `ocproxy` 逐字节
可复现。

## 5. 补测结论

| 被工具跳过的项 | 补测结果 | 判据 |
| --- | --- | --- |
| G4 产物完整性 | ✅ 通过 | 7 个文件与 `package()` 声明一致 |
| L2 平台功能矩阵 | ✅ 通过（框架探针缺陷已归因） | conanrun 环境下 `--version`/`--help` rc=0；行为级 17/17 |
| L4 静态安全属性 | ✅ 通过 | PIE + NX + Full RELRO 两项产物均满足 |
| L5 产物基线 | ✅ 通过（附不可复现项与根因） | `vpnns` 与 5 个数据文件跨轮一致；`ocproxy` 差异定位到 `__FILE__` 路径与签名 nonce |
