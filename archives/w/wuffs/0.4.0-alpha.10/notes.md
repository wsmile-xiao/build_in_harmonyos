# wuffs 0.4.0-alpha.10 — OpenHarmony 适配笔记

## 1. 任务与结论

- 软件：wuffs（C），版本 `0.4.0-alpha.10`（上游 tag `v0.4.0-alpha.10`）。
- 设备：OpenHarmony / HarmonyOS PC（aarch64），`clang 15.0.4`
  （`aarch64-unknown-linux-ohos`）、`conan 2.29.1`、profile
  `ci/conan/profiles/ohos-aarch64`。
- 结论：**零源码修改适配通过**。包只安装 `release/c/wuffs-v0.4.c`
  一个文件；30 个上游 C 测试程序（232 用例）与 `build-all.sh` 的 4 项编译
  一致性检查、2 项黄金回归数据比对全部在 `conan create` 内真实执行并通过。

## 2. 这是什么形态的包

wuffs 不是常规「configure && make」项目。上游 `BUILD.md` 开门见山列出
「Wuffs」一词的 5 种含义，其中第 1 种才是本任务对象：

> 1. The Wuffs library (e.g. image decoders) in C/C++ form.

并且明确：

> There's no build step, in that there's no "configure and make" step needed
> before moving on to building the example programs.

转译（`.wuffs` → `.c`）由**检入代码的人**完成，不由检出仓库的人完成：

> It's done by whoever *checks in* code changes.

因此 `release/c/wuffs-v0.4.c` 是已生成并入库的正式产物，本包把它当普通
第三方 C 库安装即可。仓库其余部分（`lang/`、`std/*.wuffs`、`internal/`、
`cmd/`）服务于 Wuffs 语言工具链，不在本包范围。

### 2.1 只装版本化产物，不装 snapshot

`release/c/` 下有两个「全量」文件：

| 文件 | `WUFFS_VERSION` | 定位 |
| --- | --- | --- |
| `wuffs-unsupported-snapshot.c` | `0`（`"¡ Some code generation programs can override WUFFS_VERSION."`） | 开发期快照，文件名即 `unsupported` |
| `wuffs-v0.4.c` | `0x000040000`，`WUFFS_VERSION_STRING "0.4.0-alpha.10+3966.20260623"` | 版本化发布产物 |

两者差异极小（`diff` 只有版本宏那几行），但 `release/c/README.md` 明确写着
「Typically, pick the latest stable version (**but not the unsupported
snapshot**)」，且 snapshot 的版本宏为 0 意味着它只能配合 `wuffs test` /
`wuffs genlib` 生成的代码使用 —— 于是本包只安装 `wuffs-v0.4.c`。

## 3. 上游测试怎么跑（以及为什么改成指向版本化产物）

### 3.1 上游的测试入口链

```
build-all.sh
 ├── go install github.com/google/wuffs/cmd/...
 ├── go test    github.com/google/wuffs/...        ← Go 工具链自身测试
 ├── wuffs gen                                      ← .wuffs → release/c/*.c 转译
 ├── 4 项「编译干净」检查（release/c/wuffs-unsupported-snapshot.c，C99/C++11 × 头/实现）
 ├── wuffs test -skipgen -mimic ──┐
 ├── wuffs bench ...              │  wuffs-c test → 对每个 test/c/std/*.c
 ├── ./build-example.sh           │               `-std=c99 -Wall -Werror` 编译后直接运行
 ├── ./build-fuzz.sh              │
 └── 6 项端到端检查（crc32 / jsonptr / nia 黄金数据 / mzcat 黄金数据 / fuzz）
```

CI 镜像**不含 Go 工具链**（`command -v go` 为空），所以本包 `build()` 移植的是
上图中不依赖 Go 的部分，并且只做「移植」不做「发明」：

1. **4 项编译一致性检查** —— 原样搬用 `build-all.sh` 里那 4 条命令与它的
   `WARNING_FLAGS` 集（`-Wall -Werror -Wpedantic -Wcast-qual -Wcast-align
   -Wpointer-arith -Wfloat-equal -Wundef -Wvla -Wconversion -Wshadow
   -Wredundant-decls -Wunused-const-variable`，C 另加 `-Wstrict-prototypes
   -Wold-style-definition`），C99 与 C++11 各跑头模式与实现模式。对象换成
   本包真正安装的 `wuffs-v0.4.c`。
2. **30 个上游 C 测试程序** —— 按 `cmd/wuffs-c/test.go` 的方式编译运行
   （`-std=c99 -Wall -Werror` + 程序自报 `PASS (N tests)`），并要求
   `N > 0`。这 30 个程序正是不带 Go 也能跑的那部分上游测试套件。
3. **2 项黄金回归数据比对** —— `build-all.sh` 会跑
   `script/print-nia-checksums.sh` / `print-mzcat-checksums.sh` 与仓库内冻结的
   `test/nia-checksums-of-data.txt` / `test/mzcat-checksums-of-data.txt` 做
   `diff`，另加 `example-crc32`、`example-jsonptr | example-crc32` 两个
   固定值检查。本包用 Python 复刻同一取数流程（脚本本身依赖 `gen/bin` 的
   预先构建，而且我需要的产物路径不同）。

### 3.2 关键改动：测试 include 指向版本化产物

`test/c/std/*.c` 这 30 个程序**全都**include 开发期快照：

```c
#include "../../../release/c/wuffs-unsupported-snapshot.c"
```

若照抄，测试覆盖的将是「没人安装的那个文件」，而且
`wuffs_png__decoder__initialize(&dec, sizeof dec, WUFFS_VERSION, ...)` 这类调用
会因为快照 `WUFFS_VERSION == 0` 而语义错位。因此 30 个补丁**只改这一行
include**：

```diff
-#include "../../../release/c/wuffs-unsupported-snapshot.c"
+#include "../../../release/c/wuffs-v0.4.c"
```

不改任何测试逻辑、断言、黄金值或数据。改动后测试真正覆盖所发布的文件，
且 `WUFFS_VERSION` 校验成立。验证方式：

- `patch_ng.fromfile(f).apply(strip=1, root=tree)` 30/30 应用成功，且结果树与
  做修改的探索树 `diff -rq` 逐字节一致（不是只看 CLI `patch` 的退出码）。
- 补丁生成用 `ohc-run.py refresh-patch --auto`；生成物中的 `+1/-1` 计数与
  逐文件单行改动吻合。

### 3.3 上游测试实况（设备实测）

```
$ clang -std=c99 -Wall -Werror test/c/std/<prog>.c -o <bin>
$ ./<bin>            # 自行 chdir 到 wuffs 根目录
std/<prog>      clang15 PASS (N tests)
```

30 个程序逐项：adler32 3、bmp 4、bzip2 7、cbor 4、crc32 3、crc64 3、
deflate 19、etc2 3、gif 45、gzip 9、handsum 6、jpeg 7、json 33、lzip 1、
lzma 4、lzw 11、netpbm 4、nie 5、png 12、qoi 3、sha256 3、targa 2、
thumbhash 4、vp8 5、wbmp 8、webp 3、xxhash32 3、xxhash64 3、xz 5、zlib 10。

- TOTAL = 232，PASS = 232，FAIL = 0，SKIP = 0，NOT_RUN = 0。
- 统计单位：上游 `testlib` 的测试过程（`g_tests[]` 数组元素），也是上游打印
  `PASS (N tests)` 时自报的口径。取数命令见 `test_package/MANIFEST.yml`。
- 自报数字与源码静态计数的关系（**用 `clang -E` 真实预处理后按花括号/顶层逗号
  解析 `g_tests[]` 得到，逐文件与上表实测数字 30/30 完全吻合**）：
  - 定义 `-DWUFFS_MIMIC` 时 `g_tests[]` 元素总数 = **295**；
  - 其中位于 `#ifdef WUFFS_MIMIC` 内、**上游默认不编译故本包既不编译也不执行**
    的 = **63**；
  - 未定义该宏（上游默认）时 = **232**，即上面实测执行的数字。
  这不是「跳过」，是上游默认口径；`-mimic` 需要 giflib/libpng/libjpeg/libwebp/
  zlib 等未发布的第三方库，本包未启用。
  取数命令：
  ```sh
  # 对每个 test/c/std/*.c 取数（可直接跑；注意必须先取出 g_tests[] 块再预处理，
  # 因为整文件带 -DWUFFS_MIMIC 预处理会因缺 bzlib.h/gif_lib.h/jpeglib.h/lzma.h/
  # png.h/openssl/evp.h/webp/decode.h/xxhash.h 等未发布第三方头文件而失败，
  # 实测整文件预处理在 30 个文件中有 10 个失败）：
  #   1) 从源码里按花括号配平取出 `proc g_tests[] = { ... }` 块文本；
  #   2) 把该块交给 `clang -E [-DWUFFS_MIMIC] -x c -` 预处理；
  #   3) 滤掉以 # 开头的 linemarker 行；
  #   4) 按顶层逗号切分，去掉末尾 NULL/((void*)0) 哨兵 → 元素数。
  # 不带宏逐文件求和 = 232（与实跑产生的 30 条 PASS (N tests) 逐文件吻合；
  #   该 30 行原始输出见 reports/upstream-c-tests-log.md——conan create 日志里
  #   只有汇总行，因为配方把程序 stdout 重定向到 <name>.out 后再断言 PASS 行）；
  # 带宏 = 295；两者之差 = 63。
  ```
  **勘误**：本笔记与 `reports/native-build-test.md`、
  `knowledge/drafts/E565-draft-CBFA.md` 的早期版本曾把这两个数字写成
  「242 / 10」；`knowledge/drafts/E565-draft-CBFA.kv` 从未包含这些数字。
  两条叠加的取数缺陷：
  1. 用正则扫源码、以非贪婪方式删除 `#ifdef ... #endif` 块，会误删大量非
     mimic 区域，得到偏小的假总数（误得 242，真值 295）；
  2. 沿用 `clang -E` 输出而未滤除 `# <line> "<file>"` linemarker：在**实际触发该合并的 10 个文件**上（`g_tests[]` 内含 `#ifdef WUFFS_MIMIC` 分支的
     文件共 28 个，其中 10 个因此多计 1），`#endif` 回填产生的 linemarker 与末尾
     `NULL` 哨兵落在同一个逗号片段，使哨兵不再被识别而被计入（默认口径 232 → 242）；
     带宏时无此现象（295 恒等）。
  改按上述四步口径复算即得 295 / 63 / 232，且逐文件与实跑产生的 30 条 `PASS (N tests)`
30/30 吻合（该 30 行原始输出见 `reports/upstream-c-tests-log.md`；`conan create` 日志因配方
把每个程序的 stdout 重定向到 `<name>.out`，只有汇总行，没有逐程序 PASS 行）。
  W4 独立审计（`reports/audit-result.json`）以 P0 记录了该错误计数，本轮已订正。

`build-all.sh` 端到端检查实测值：

```
example-crc32 < test/data/json-things.formatted.json   = cdcc7e35   (期望 cdcc7e35)
example-jsonptr < json-things.unformatted.json | example-crc32 = cdcc7e35
script/print-nia-checksums.sh   vs test/nia-checksums-of-data.txt   → diff 空 (202 条)
script/print-mzcat-checksums.sh vs test/mzcat-checksums-of-data.txt → diff 空 (34 条)
```

### 3.4 明确未运行的部分

| 项目 | 原因 | 影响 |
| --- | --- | --- |
| `wuffs test` / `wuffs test -mimic` / `wuffs bench` 的 Go 驱动层、`wuffs gen`、`go test ./...` | CI 镜像无 Go 工具链（`command -v go` 为空）。驱动层做的事是：转译 `std/*.wuffs` → `release/c/*.c`，再用 `wuffs-c test` 编译运行下游 C 测试 | 本包不修改任何 `.wuffs` 源，转译结果与入库产物相同；其下游 C 测试（30 个程序、232 用例）已全部真实执行。未覆盖范围仅限于「Wuffs 语言编译器/证明检查器自身的测试」，与所发布的 C 产物无关 |
| `test/c/mimiclib` 对比测试（`-DWUFFS_MIMIC`） | 上游默认不编译（`#ifdef` 包裹），且需 giflib/libpng/libjpeg/libwebp/zlib 等未发布的第三方库 | 上游默认口径，非本包引入；该宏下的 **63** 个测试过程既不编译也不执行，对应的非 mimic 用例（232）全部执行 |

以上两项均不计入 232，也不写成 PASS。

## 4. 踩过的坑

### 4.1 Conan `get()` 按 URL 末段猜解压器 → `BadZipFile`

首轮 `conan create` 在 `source()` 失败：

```
wuffs/0.4.0-alpha.10@ohpcd/stable: Downloading 15.8MB v0.4.0-alpha.10
wuffs/0.4.0-alpha.10@ohpcd/stable: Sources correctly downloaded from
  https://codeload.github.com/google/wuffs/tar.gz/refs/tags/v0.4.0-alpha.10
wuffs/0.4.0-alpha.10@ohpcd/stable: Uncompressing v0.4.0-alpha.10 to .
ERROR: ... Error in source() method, line 113
	get(self, **self.conan_data["sources"], strip_root=True)
	BadZipFile: File is not a zip file
```

根因：codeload 形态的 URL 是 `.../tar.gz/refs/tags/<tag>`，**末段是 tag 名，
没有扩展名**，Conan 据此无法判定归档类型而落到 zip 分支（模块级函数
`conan.tools.files.get()` 按 `os.path.basename(url)` 推断文件名，归档类型判定在它
调用的 `unzip()` 里按 `.tar.gz`/`.tgz` 等后缀分支；与 `ConanFile.run()` 无关）。下载与 sha256 校验都正常，
只在解压阶段炸。两种修法（本包最终并用）：在 `sources:` 显式给 `filename:`；
或把 URL 换成末段带 `.tar.gz` 扩展名的 `github.com/.../archive/refs/tags/`
形态。本包最终 `conandata.yml` 采用的是
`github.com/.../archive/refs/tags/<tag>.tar.gz` 形态（与 codeload 形态实测字节
与 sha256 完全一致），原因是 CI worker 侧的网络兜底：`ci/conan/build_and_test.sh`
的镜像改写正则只认 `github.com` 等域名列表，codeload 形态 URL 不会被改写成
gh-proxy 镜像列表，而 `github.com` 归档形态会。`filename:` 仍显式保留（对
两种形态都无害，且防止后续换回无扩展名形态时再踩同一个坑）。这属于应记入
知识库的可复用形态（见 manifest 的 `knowledge_gained`）。

仓库内 URL 形态存量（`upstream/main`，含本包所在分支前统计，命令为
`git grep -l <pattern> upstream/main -- 'archives/*/*/*/conandata.yml' | wc -l`）：
`github.com/<owner>/<repo>/archive/refs/tags` 形态 **1714** 个、`codeload.github.com`
形态 **204** 个、带显式 `filename:` 键的 **265** 个（2026-09-11 在 `upstream/main`
上按上述命令重测；此前的 1637/191/254 是未锚定的旧测量，已在本次审计中订正）。
即 github 归档形态才是主流，带 `filename:` 的仍是少数——所以「codeload + 无
filename:」组合确实容易踩坑。

### 4.2 `self.run()` 不回传子进程 stdout

第二轮的失败形如：

```
wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: ".../test-bin/adler32"
std/adler32     clang15 PASS (3 tests)          ← 测试确实跑了且通过
wuffs/0.4.0-alpha.10@ohpcd/stable: ERROR: upstream C test adler32 printed no
  'PASS (N tests)' line                        ← 但配方拿到的是空串
```

`ConanFile.run()` 只把子进程输出写进 Conan 日志，**不返回**它。测试结果提取
必须显式重定向到文件再读：

```python
out_file = os.path.join(bindir, name + ".out")
self.run('"%s" > "%s" 2>&1' % (exe, out_file), cwd=self.source_folder)
out = open(out_file, encoding="utf-8", errors="replace").read()
```

同时把 `N == 0` 也判为失败，避免「打印了 PASS 行但一个用例都没跑」的假绿。

### 4.3 C++ 侧 `-Wpedantic` 与上游 NEON 代码

`build-all.sh` 对 C++ 也用同一套 `-Wpedantic` warning 集。在 aarch64 上，
上游自动生成的 NEON 代码路径含 C99 复合字面量，`-Wpedantic` 下是 8 条
`-Wc99-extensions` **错误**：

```
release/c/wuffs-v0.4.c:35246:51: error: compound literals are a C99-specific
  feature [-Werror,-Wc99-extensions]
    v_v2 = vmlal_u16(v_v1, vget_low_u16(v_col2), ((uint16x4_t){16u, 15u, 14u, 13u}));
```

上游自己的立场是「Wuffs' C code is generated automatically, not hand-written.
These warnings' costs outweigh the benefits」（文件开头就有一组
`#pragma GCC diagnostic ignored ...`）。本包的处理是在 C++ 检查里**只**补
`-Wno-c99-extensions` 一个开关，而不是整体降级 warning 等级，保持其余
`-Werror` 仍然有效；这属于适配层选择，已在配方注释与 PR 正文说明。

（补充：该文件在 x86_64 上不会命中，因为 NEON 分支由 `__ARM_NEON` 守卫；
这正是「设备实测才发现」的一类差异。）

### 4.4 不透明类型：头模式翻译单元不能直接定义实例

未定义 `WUFFS_IMPLEMENTATION` 时，C 侧结构体是不完整类型（`sizeof` 不可用），
C++ 侧默认构造被 delete。上游注释给出的正统用法是
`sizeof__wuffs_crc32__ieee_hasher()` / `alloc()`。test_package 的第二个 C
翻译单元与 C++ 翻译单元都按这个用法写，顺带把「单文件库可作头文件在多翻译
单元中与唯一实现共存」这件真实消费者场景验证到了。

`decode_frame` 还需要一个 `workbuf_len().max_incl` 大小的临时缓冲，不能传空
slice —— 传空会得到 `#base: bad workbuf length`。上游自带调用方
（`example/convert-to-nia`、`example/mzcat`）都按自报长度分配。

## 5. 鸿蒙/aarch64 平台专项测试

wuffs 在**编译期**按 CPU 架构选择代码路径。`release/c/wuffs-v0.4.c` 的配置段写明：

```c
// To simplify Wuffs code, "cpu_arch >= arm_xxx" requires xxx but also
// unaligned little-endian load/stores.
#if defined(__ARM_FEATURE_UNALIGNED) && ... little-endian ...
#if defined(__ARM_FEATURE_CRC32)  ->  CPU_ARCH__ARM_CRC32
#if defined(__ARM_NEON)           ->  CPU_ARCH__ARM_NEON
```

即 OHOS PC（aarch64）上的默认构建立即走 **NEON 快速路径**，而该路径以两个平台
前提为条件：小端序、以及**可用的非对齐访存**。这两条在普通 Linux/macOS 上通常
自动成立，因此「换了平台之后它们是否仍成立」不会被任何纯可移植 C 测试发现——
因为跑的根本不是可移植那条路径。

`test_package/ohos_platform_test.c` 针对这一点做**同一源文件的两次构建对照**：

| 可执行文件 | 关键标志 | 库自报选中的路径 | 断言数 |
| --- | --- | --- | --- |
| `ohos_platform_test` | 默认 | `have_arm_neon() == 1`（NEON） | 32 |
| `ohos_platform_test_portable` | `-DWUFFS_CONFIG__AVOID_CPU_ARCH` | `have_arm_neon() == 0`（纯可移植） | 32 |

源文件在两个方向上都断言 `wuffs_base__cpu_arch__have_arm_neon()`
（默认=1 / 可移植=0），所以两次构建**可证明真的走了不同实现**；随后两者都必须
满足同一组断言：

1. **平台前提**：`__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__`、LP64
   （`sizeof(size_t) == sizeof(void*) == 8`）、以及经 `memcpy` 实测的
   非对齐 64 位小端读写往返（偏移 1..8）；
2. **选中的代码路径正确**：未误选 x86 SSE4.2/AVX2（aarch64 上必须为 0）；
3. **非对齐输入下解码正确**（NEON 路径的前提）：把内嵌 PNG 放在故意错位的
   缓冲区里，从 **16 个不同字节偏移**（0..15）各解码一次，每次都要求
   `crc32(解码 RGB) == 0x6B64E606`（该值由 Python `binascii.crc32` 从先验
   像素图案独立算出，非从任何构建回读）；
4. **所选 CRC-32 实现取值与标准一致**：`crc32("123456789") == 0xCBF43926`。
   实测（`reports/conan-create-log.md` 的两行 `have_arm_crc32() = 0`）：本构建的 OHOS
   clang 15 默认目标**未定义** `__ARM_FEATURE_CRC32`（需显式 `-march=armv8-a+crc`
   才定义），因此 wuffs 在 OHOS PC 上**不走 ARM CRC-32 指令路径**，该断言校验的是
   可移植实现的取值契约。这是一条独立的平台事实：OHOS 默认目标不启用 CRC 扩展，
   而 `__ARM_NEON` 与 `__ARM_FEATURE_UNALIGNED` 均已定义，故 NEON 路径启用。

设备实测（`reports/conan-create-log.md`）：

```
# build: default (aarch64 fast paths enabled)
# wuffs_base__cpu_arch__have_arm_neon()     = 1 (want 1)
OK: 32 checks passed, 0 failed
# build: portable (WUFFS_CONFIG__AVOID_CPU_ARCH): arch-specific code disabled
# wuffs_base__cpu_arch__have_arm_neon()     = 0 (want 0)
OK: 32 checks passed, 0 failed
```

两条路径在同一批已知答案上完全一致，即 **OHOS PC 上 NEON 快速路径与可移植
回退路径行为等价**；而 NEON 路径被真正执行过（而非静默退化为可移植 C）。
两个可执行文件大小/哈希不同（379328 B / 362944 B），也佐证代码路径确有差异。

## 6. test_package 设计

一个可执行文件、三个翻译单元，覆盖单文件 C 库的三种老实用法：

| 翻译单元 | 模式 | 验证点 |
| --- | --- | --- |
| `test_wuffs.c` | C99 + `WUFFS_IMPLEMENTATION` | 唯一实现；版本宏确为 0.4.0-alpha.10；哈希标准校验值；解码内嵌 4x4 PNG 到 24bpp RGB 并比对像素哈希；错误路径 |
| `test_wuffs_header_only_tu.c` | C99 头模式 | `sizeof__wuffs_crc32__ieee_hasher()` + C API，链接到唯一实现 |
| `test_wuffs_cpp.cpp` | C++17 头模式 | `wuffs_png__decoder::alloc()` + C++ 便捷层，独立解码同一 PNG |

内嵌 PNG 是 4x4、8bpp RGB、每行 filter 0、无隔行，像素
`(x, y) = (11 + 40x, 23 + 50y, 7 + 30(x + y))`（各通道 mod 256）。因为像素
图案是先验已知的，期望哈希用 **Python `binascii.crc32` / `zlib.adler32`**
独立算出（`crc32(文件)=0x437F9210`、`crc32(RGB)=0x6B64E606`、
`adler32(RGB)=0x3A8710A1`），不是从某次 Wuffs 构建回读——这样字节序、
对齐或 NEON 代码路径的问题都会暴露为哈希不符，而不是被自证。

实测运行输出：`OK: 15 checks passed, 0 failed`。

## 7. 复现命令

```sh
. "$HOME/tmp/wuffs-0.4.0-alpha.10/env.sh"
cd "$PACKAGE_DIR"
conan create . --user=ohpcd --channel=stable \
  --profile:host="$MAIN_REPO/ci/conan/profiles/ohos-aarch64" \
  --profile:build="$MAIN_REPO/ci/conan/profiles/ohos-aarch64"
```

采信轮日志逐字留档：`reports/conan-create-log.md`（清缓存后的干净轮）。
原始 `reports/conan-create.log` 属运行日志，按 `.gitcode/review-memory.md` 规则 19
不入库，故逐字转存为 `.md`（头部含原始字节数/行数/sha256 与生成命令）。
