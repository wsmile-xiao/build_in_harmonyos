# DRAFT-quicktun-2.2.6-bare-script-silent-backend-swap — 裸 shell 构建入口的"探测即选型"失败会**静默换成仓库内置实现**且退出码 0：当 `config.h` / 编译命令行 / `DT_NEEDED` 三层判据全部不可用时，唯一硬判据是**链接期产物双断言**

> Contributor: 主理-45-子代理2 / Status: **DRAFT** / Updated: 2026-09-25 / Severity: 2 (medium)
> Source: `quicktun/2.2.6` 适配（分支 `feat/quicktun-2.2.6`，鸿蒙 PC B 机真机实测）
> Prospect ID: `DRAFT-quicktun-2.2.6-bare-script-silent-backend-swap`（正式编号由主编 `graph promote` 分配）

## 一句话

上游构建入口是一个**没有任何配置出口的裸 shell 脚本**时，它常用"编译器能不能链上某个库"
来**选实现后端**；探测失败**不报错**，而是改编仓库自带的另一份实现，**照常产出全部二进制、
退出码仍是 0**。于是配方向 Conan 声明的 `requires()` 与实际交付物**不再一致**，
而所有机械门禁（退出码 / G0–G4 / L0–L5 / 消费者测试）都照样通过。
本条给出在这种"三层判据都不可用"的场景下**唯一还能立住的判据**：链接期产物双断言。

## 相关既有条目（同族差异化定位，按文件名+行号引用）

| 既有条目（文件名:行号） | 它的判据层 / 处置 | 本条的增量（为什么不能复用它的解法） |
|---|---|---|
| `knowledge/drafts/DRAFT-libdv-tools-1.0.0-ac-check-lib-warns-instead-of-failing.kv:34,37,40,43` | 处置哲学相同（"在 build 阶段断言，把静默降级变成构建期失败"）；判据 = **`config.h` 里的 `#define HAVE_X`**（`rec_impl: assert-config-h-define-after-configure`），外加运行期"`--version` 非空 / 裸跑不能 139" | 本类包**没有 configure、没有 `config.h`、没有任何中间配置文件**（上游树里只有 `build.sh` + `src/*.c`）⇒ 该判据**无对象可读**。更关键：它的运行期断言在本类包上**恒不成立地通过**——换的是**功能等价的另一份实现**，输出逐字节相同，**运行期无症可查**（见下「实测证据」第 5 行） |
| `knowledge/drafts/DRAFT-ohos-optional-dep-silent-degrade-stub-api.md:22-24,80,84-92,94-102` | 判据 = 读 `configure.ac` 里 `PKG_CHECK_MODULES` 的**第三参**是不是 `AC_MSG_ERROR`（line 80）；处置 = 定性→文档显式化→测试划界，允许 `if downgraded: self.output.warning(...)`（line 94-102）；line 87-88 还明令"若是 optional，不得为消除告警强行补依赖" | 本条**处置方向相反**：依赖**已发布**、配方**已显式 `requires()`**，此时"退到内置实现"不是可接受的上游语义，而是**声明与交付不一致** ⇒ 必须**硬失败**，`warning` 会把它放过去。且 line 80 的判据入口（`configure.ac`）在本类包里根本不存在 |
| `knowledge/drafts/DRAFT-E590-libyal-optional-dep-autodetect-ohos.md:10-18,37-52` | 「假绿只体现在 configure 摘要里」（line 16）⇒ 办法是"先只跑一次 configure，读能力摘要"（line 37-52） | 本类包没有 configure ⇒ 没有摘要。上游只把探测结论 `echo` 成一行文字（`build.sh:38` `Using shared libsodium.` / `:50` `Building TweetNaCl...`），**措辞随上游改动而变**，不能当判据 |
| `knowledge/drafts/DRAFT-E2186-autotools-deps-missing-dep-flags.md:33-43` | 判据 = **编译命令行里有没有依赖的 `-I/-L`**（该条实证就是把 compile 命令行贴出来） | 本类包的构建入口不回显探测阶段命令行、也没有 `makeopts`/`config.log` 落盘 ⇒ 拿不到可 grep 的命令行。可观测面只剩 `out/*` 与 `obj/*.o` |
| `knowledge/drafts/DRAFT-E623-libheif-dav1d-1.23.0-plugin-consumer-contract-and-dlopen-signing.md:151-158` | 「负对照最不该省：只断言能力可用，任何别的后端（含内置 fallback）都能让断言变绿」 | 同一原则，但那条落在**消费者测试面**；本条把它下沉到**构建期产物**，并给出"怎样选一个**只可能来自被声明依赖**的符号"的可操作步骤（在上游整棵树里证明该符号出现 0 次） |
| DT_NEEDED 族（`knowledge/doc/E330.md`、`E502.md`、`E537.md`、`E465.md`；`knowledge/` 内 123 个文件命中 `DT_NEEDED`） | 用 `readelf -d` 的 `DT_NEEDED` 核对依赖是否真被链接 | **本类实测不可用**：静态折入式构建下 `NEEDED` 只剩 `libc.so`，被声明的依赖**不在动态依赖表里**（见「实测证据」第 3 行）⇒ 判据只能是"符号有没有被折进产物"，不是"有没有 DT_NEEDED" |

**四范围全库查证**（计数=文件数，`grep -rliE`；命中≠语义命中，语义收窄见下）：

| 检索式 | `knowledge/` | `knowledge/drafts`+`draft` | 仓内规则件 `ci/config`+`ci/scripts`+`scripts/ohc` | `经验文档/B草稿库/` |
|---|---|---|---|---|
| `tweetnacl` / `TweetNaCl` | 0 | 0 | 0 | 0 |
| `lsodium` | 0 | 0 | 0 | 0 |
| `链接期产物` | 0 | 0 | 0 | 0 |
| `静默降级` | 35 | 31 | 0 | 0 |
| `假绿` | 71 | 71 | 0 | 0 |
| `DT_NEEDED` | 123 | 111 | 0 | 0 |

语义收窄：在 `knowledge/` 内取
`(假绿|静默降级|silently (degrade|fall|use)|falls? back)` ∩ `(断言|assert)`
= 143 ∩ 957 = **58 个文件**，逐一扫面后只有上表 5 条落在同一问题域，**逐条层次差见上表**。
（`draft-review` 的相似面只取 `knowledge/graph/index.tsv`、**不扫 `knowledge/drafts/`**
⇒ 上表的第二范围计数是手工 grep 得出的。）

## Scope（何时用）

同时满足以下三条的包：

1. 上游构建入口是**裸 shell 脚本 / 裸命令序列**，没有 `configure`、没有 `Makefile.am`、
   没有 CMake/meson ⇒ 没有任何"配置出口"可用来指定依赖位置或选定后端；
2. 脚本内部用**编译器探测**来选实现（典型形如
   `if $cc -shared -l<dep> tmp/probe.c -o tmp/probe 2>/dev/null; then …; else 编内置实现; fi`），
   且 `else` 分支**不退出**；
3. 该依赖在 Conan 制品仓**已发布**、配方**显式 `requires()`** 它（即"用内置实现"不是
   上游设计意图下的合法降级，而是**交付与声明不符**）。

典型命中：自带 TweetNaCl/libtomcrypt 替身版的加密工具、自带 SHA/JSON 单文件实现的 CLI、
任何"探测到就 `<某库>`，否则就编 `src/<vendor>.c`"的裸脚本。

## Symptom（逐字读数，不是概括）

原样构建（未注入依赖搜索路径、未打补丁）：

```console
Cleaning up...
Creating source archive...
Building TweetNaCl...
The TweetNaCl cryptography library is not optimized for performance. Please install libsodium or libnacl before building QuickTun for best performance.
build.sh[58]: cc: inaccessible or not found
```

要点：`Building TweetNaCl...` 出现在**编译失败之前** —— 脚本已经选定了内置后端，
只要编译器名字对得上，它就会**一路走完并产出全部二进制**（`build.sh` 的 `set -e`
拦不住它，因为探测命令自己带了 `2>/dev/null` 且被用作 `if` 条件）。
"探测失败"与"构建失败"在这里**完全脱钩**。

## Root Cause

上游 `build.sh`（90 行）的后端选型段：

```sh
35: echo '#include <sodium/crypto_box_curve25519xsalsa20poly1305.h>' > tmp/libtest1.c
37: if [ "$1" = "debian" ] || $cc -shared -lsodium tmp/libtest1.c -o tmp/libtest 2>/dev/null; then
38:         echo Using shared libsodium.
42:         export CRYPTLIB="-lsodium"
43: elif $cc -shared -lnacl tmp/libtest2.c -o tmp/libtest 2>/dev/null; then
49: else
50:         echo Building TweetNaCl...
52:         $cc $CFLAGS -c src/tweetnacl.c -o obj/tweetnacl.o
57:         export CRYPTLIB="obj/randombytes.o obj/tweetnacl.o"
58: fi
```

三层机制叠起来才致命：

1. **探测即选型**：`if` 条件里那条 `-lsodium` 链接检查是唯一决策依据，脚本**没有**
   `--with-sodium` 之类开关，也**不接受**任何配置入参；能把依赖"喂进"那条检查的
   只有编译器环境变量（`CPATH`/`LIBRARY_PATH`）。
2. **降级不减功能**：`else` 分支换的是**同一套 Curve25519/XSalsa20/Poly1305 原语的另一份
   实现**。实测两版 `quicktun.keypair` 对同一秘密标量给出**逐字节相同**的公钥 ⇒
   行为测试、消费者测试、`--version` 烟雾**都区分不出来**（本包 `test_quicktun.c` 头部
   已把这条写成诚实边界，line 14-16）。
3. **产物侧无痕迹可查**：链成的是**静态折入**形态 —— `readelf -d out/quicktun.combined`
   的 `NEEDED` 只有 `libc.so`，libsodium 的 73 个符号却实打实在符号表里。
   ⇒ 常规的"查 DT_NEEDED 核对依赖"直接落空。

## Recommended Solution（priority 1）— 链接期产物双断言

放在 `build()` 里紧挨着构建命令之后（**不是**放 test_package，理由见「禁止做法」）：

```python
def _assert_libsodium_backend(self):
    # 判据①：内置实现的目标文件只有 else 分支才会被编出来
    tn_obj = os.path.join(self.source_folder, "obj", "tweetnacl.o")
    if os.path.isfile(tn_obj):
        raise ConanException("fell back to the bundled TweetNaCl: "
                             "CPATH/LIBRARY_PATH did not hit the libsodium package")
    # 判据②：产物里必须有"只可能来自被声明依赖"的符号
    combined = os.path.join(self._out_dir, "quicktun.combined")
    if not os.path.isfile(combined):
        raise ConanException("build produced no out/quicktun.combined")
    with open(combined, "rb") as handle:
        blob = handle.read()
    if b"crypto_generichash_blake2b" not in blob:
        raise ConanException("no libsodium-only symbol in the binary: "
                             "the crypto backend is not libsodium, refusing to ship")
```

三条**前置证明**（少一条，这个断言就是不可证伪的装饰）：

1. **证明上一层判据真的不可用**：树内没有 `config.h`/`configure`/命令行回显
   （文件清单逐条列出来，别凭印象）。
2. **证明所选符号是"排他的"**：在上游**整棵源码树**里 grep 该符号，命中必须为 **0**
   ——`grep -rc crypto_generichash <src>` 无输出、`src/tweetnacl.h` 导出的前缀只有
   `crypto_auth/box/core/hash/hashblocks/onetimeauth/scalarmult/secretbox/sign/stream/verify`。
   否则内置实现自己也提供该符号，断言恒真。
3. **证明判据不是文本措辞**：不要用 `if "Using shared libsodium" in stdout`——上游改一句
   文案就失效；`obj/*.o` 是否存在、产物里是否折入某符号，都是链接期的**既成事实**。

配套（缺一不可，否则"探测能过"本身是运气）：

- 用 `Environment` 把依赖**自己的** `package_folder` 下的 includedirs/libdirs
  追加进 `CPATH`/`LIBRARY_PATH`（R49：不引用任何共享系统前缀）；
- 若脚本把编译器名写死（`cc="cc"`），打**一个补丁**改成 `${CC:-cc}`，CC 由
  `AutotoolsToolchain` 注入（R33）——这一步是"探测能命中"的前提；
- 顺手核实脚本自己有没有往 `LIBRARY_PATH` 里塞系统前缀（本包 `build.sh:33` 塞了
  `/usr/local/lib/`）。本机实测 `/usr/local` **不存在** ⇒ 探测命中只能来自注入路径；
  若该目录存在且装有同名库，"依赖已发布"与"链到了系统库"就分不开，**必须在 notes 里写明**。

## 回退方案（priority 2）— 确实要交付内置实现时

如果判定"内置实现才是本包该交付的形态"（例如依赖未发布、或上游明确视其为可选），
那就**不要 `requires()` 那个依赖**，并把边界写死到三处：

1. `requirements()` 里去掉该依赖（**保留声明却交付内置实现 = 本条要拦的事**）；
2. `notes.md` 与 `manifest.yaml` 写明"交付物由 `<内置实现文件>` 提供该能力，
   **不是** `<依赖>`"，并给出等价性/差异性的实测；
3. `test_package/MANIFEST.yml` 里显式标注该覆盖边界。

代价：丢掉上游标榜的性能/审计口径（libsodium 有公开审计，TweetNaCl 主打小巧），
且后续若有人 `requires` 本包并期待真 libsodium，会拿到与预期不符的实现。

## 禁止做法

- ❌ 只看 `self.run()` 的退出码就认为后端选型正确（本条的全部前提就是"探测失败也 0"）；
- ❌ 用**探测结论文字**当判据（`grep "Using shared libsodium"`）——措辞是上游的自由；
- ❌ 用**行为等价性**当后端归真的证据（同原语⇒同输出，本包实测逐字节相同）；
- ❌ 把断言写进 `test_package`——测试包看不到 `obj/`，也无法区分两份等价实现，
  断言必然退化成"有没有产物"，等于没断言；
- ❌ 为了让门禁变绿去**删掉 `requires()`** 却留着"已用该依赖"的说法（声明与交付要一起改）；
- ❌ 借本条去**强行补一个未发布的可选依赖**——那是
  `DRAFT-ohos-optional-dep-silent-degrade-stub-api` 管的情形（那里明确禁止），
  本条只适用于依赖**已发布且已声明**的场景。

## 实测证据（2026-09-25，鸿蒙 PC B 机，`quicktun/2.2.6`）

| # | 项 | 一手读数 | 出处 |
|---|---|---|---|
| 1 | 未注入时**实跑进内置分支** | `Building TweetNaCl...` + 那句性能提示 | `~/tmp/uc2/z45-quicktun/build-asis.log:2-4` |
| 2 | 注入后后端归真 | `Using shared libsodium.` | `archives/q/quicktun/2.2.6/reports/w3-local-ci.log:189` |
| 3 | 静态折入、`DT_NEEDED` 不可用 | `NEEDED` 只有 `libc.so`，符号表里却有 73 个 libsodium 符号（含 `crypto_generichash_blake2b`，地址 `T 0000000000027e24`） | `~/tmp/uc2/z45-quicktun/artifact-probe.log:6-14` |
| 4 | 判据符号排他 | `grep -rc crypto_generichash <上游树>/src` ⇒ 命中 0；`src/tweetnacl.h` 不含该前缀 | 同上目录探针输出（整理见包内 `notes.md`） |
| 5 | 两版实现输出等价 | `quicktun.keypair` 对同一标量的公钥与 libsodium `crypto_scalarmult_base()` 逐字节相同 ⇒ 测试无法区分后端 | `test_package/test_quicktun.c:14-16`（作者自述边界）+ 46 条断言全绿 |
| 6 | 断言真的会拦（可反证） | `obj/tweetnacl.o` 与产物符号两条都是 `raise ConanException` 分支；判据取"文件是否存在/字节里有没有该符号"，两分支读数不同 | `archives/q/quicktun/2.2.6/conanfile.py:96-121` |

## 适用边界 / 反例 / 解除条件

- **不适用**：有 `configure`/`config.h` 的 autotools 包（走
  `DRAFT-libdv-tools-…` 的 `#define HAVE_X` 断言）、有 CMake option 池的包
  （直接读 option 并排除 `build/`）、依赖本就未发布的可选降级
  （走 `DRAFT-ohos-optional-dep-silent-degrade-stub-api`，那里禁止强行补依赖）。
- **反例**：若上游的 `else` 分支会**关掉功能**（而不是换实现），运行期会有症状，
  那用运行期断言更省；本条针对的正是"换实现⇒无症可查"这一格。
- **解除条件**：上游若加了显式的后端选择开关（`--with-libsodium` / `CRYPTLIB=…` 可传），
  优先用开关并**删掉本断言**，回归零补丁路线。
- **风险**：判据②按字节在产物里搜符号名，理论上会被"内联后符号被改名"影响；
  故两条判据**同时**用（①是结构事实、②是符号事实），并要求①的 `obj/*.o` 路径
  来自上游脚本自身那行编译命令（本包 `build.sh:52`），不是猜出来的。

## 查重与新增价值说明（组分清单）

按"组合型知识不判重"（`经验文档/手册/03-路径B与C.md` 第 89 行）申报。组分：

- A 层：探测即选型、`else` 不退出 ⇒ 既有（`DRAFT-libdv-tools-…`、
  `DRAFT-ohos-optional-dep-silent-degrade-stub-api`、`DRAFT-E590-…` 三条各占一角）；
- B 层：构建入口**无配置出口**⇒ 只能靠 `CPATH`/`LIBRARY_PATH` 注入 + 一处
  `${CC:-cc}` 补丁 ⇒ 部分既有（`DRAFT-9848-qbe-device-e2e-runtime-evidence.md:32,58`）；
- C 层：**静态折入使 `DT_NEEDED` 判据失效** + **换等价实现使运行期判据失效**
  ⇒ 两层"判据失效证明"叠加后落到**链接期产物双断言** ⇒ **无既有条目覆盖**。

新增的解题路径 = C 层：给出"当 `config.h`／编译命令行／`DT_NEEDED`／行为测试四层
判据逐条被证明不可用时，如何构造一个**可反证**的产物级判据"（含"符号必须在全树
命中 0 次"的排他性证明步骤）。适用面：任何"裸脚本 + 编译器探测 + 自带替身实现"的包。

## 关联条目

- 相似：`DRAFT-libdv-tools-1.0.0-ac-check-lib-warns-instead-of-failing`（同为
  "build 阶段把静默降级变硬失败"，判据层不同）、
  `DRAFT-ohos-optional-dep-silent-degrade-stub-api`（可选依赖降级语义，处置方向相反）、
  `DRAFT-E590-libyal-optional-dep-autodetect-ohos`（configure 摘要假绿）、
  `DRAFT-E2186-autotools-deps-missing-dep-flags`（flags 缺失假绿）、
  `DRAFT-E623-libheif-dav1d-1.23.0-plugin-consumer-contract-and-dlopen-signing`
  （"别的后端会把断言蒙绿"的负对照原则）
- 相关（同 PR 内的 hit，不占知识位）：`knowledge/doc/E079.md:11,20-22`（HMDFS 硬链接
  → cp 替换）、`knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.md:32,58`
  （写死 `cc` → `${CC:-cc}` + 显式传 CC）、
  `knowledge/drafts/E2164-draft-ocserv-vpn-tun-boundary.md:16-21,28`（TUN/chroot 能力面）
- 台账：`archives/q/quicktun/2.2.6/reports/knowledge-candidate-ledger.md`
