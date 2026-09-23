# conan-verify 人工补测 — debfoster 2.8

> **关于本文引用的原始日志**：本文提到的 `reports/conan-create.log`、
> `reports/conan-create-l5-round2.log`、`reports/w3-local-ci.log` 是工具在本地生成的
> 原始转储（`*.log`），按 `.gitcode/review-memory.md` 第 19 条「PR 中禁止的文件」
> **不随 PR 提交**；其**完整内容已按 workflow 第 6.1 节逐字 fenced 留档**为
> `reports/conan-create-log.md`、`reports/conan-create-l5-round2-log.md`、
> `reports/w3-local-ci-log.md`（各文件头部声明原始字节数/行数/sha256 与生成命令），
> 索引与计数复核命令另见 `reports/evidence-excerpts.md`。本文对日志内容的引用
> 都可对照这些文件复核。
>
> 证据来源：本文件登记的两轮 `conan create` 均由**同一份编译输入**产生——
> `conandata.yml`、`patches/`、`generated/` 从全量审计 SHA 到最终 SHA
> `fd962a6173350241b04e1b50b16f56ab6bf07369` **逐字节未变**（可用
> `git diff <base>..HEAD -- archives/d/debfoster/2.8/conandata.yml
> archives/d/debfoster/2.8/patches archives/d/debfoster/2.8/generated` 复核，输出为空）。
> 两次修订只改注释、文档与 `test_package` 的解释器选择，不改变包内产物。
>
> ⚠️ **三份日志的 recipe revision 互不相同，勿以 revision 当同一性锚点**（实测值）：
>
> | 日志（本地，不入库） | revision |
> | --- | --- |
> | `reports/w3-local-ci.log` | `122450db94d2` |
> | `reports/conan-create.log` | `4687874699f1` |
> | `reports/conan-create-l5-round2.log` | `eb1bdc2ee08e` |
>
> `w3-local-ci.log` 与两份 `conan-create*.log` 的差异来自 W3 预下载器：它会把
> `conandata.yml` 就地改写成 `file://<本机>/.build-cache/predl_cache/...` 形态再还原
> （该日志第 99 行 `conandata.yml updated to file:// URLs`、第 733 行 `已还原为官方 URL`），
> 改写期间导出的 revision 因而不同。两份 `conan-create*.log` 之间的差异则来自它们是
> 不同轮次的 export（配方 revision 随批次变化），两轮的**编译输入**相同（见上段不变量）。
> **提交版 `conandata.yml` 是干净的 https URL**
> （`git show HEAD:archives/d/debfoster/2.8/conandata.yml` 实测），工作区亦无残留。
> 权威锚点是各级日志里的产物 sha256（§6.2）与 `conandata.yml` 的 tarball sha256，
> 不是 recipe revision。
>
> 工具报告：`reports/conan-verify-report.md`（`Verdict: PASS`）

## 1. 为什么需要补测

`conan-verify` 报告里 G4/L2/L4/L5 四项都是「✅ PASS」与「⏭️ 跳过（无 cache 路径）」
并存：

```text
## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
```

按 workflow 第 7.2 节，`✅ PASS` 与 `⏭️ 跳过` 并存时**以跳过为准**，跳过态必须人工
补测并留档。触发点是已知工具缺陷：G4 的定位依赖 `conan list --format=json` 的顶层键，
而本包以 `--user=ohpcd --channel=stable` 形态构建时顶层键带 `@ohpcd/stable`、
`self.ref` 不带，`conan_verify.py:737` 的 `KeyError` 被吞掉，于是 L2/L4/L5 全部走
「无 cache 路径」分支，而 `g.passed` 初值为 `True` 使报告仍打印 ✅。

包目录一律用 glob 兜底定位（分片目录名是「名前 5 字符 + hash」，每轮重建）：

```sh
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/debfo*/p | head -1)
```

## 2. 环境与轮次

| 项 | 值 |
| --- | --- |
| 设备 | HarmonyOS PC aarch64，clang 15.0.4，Conan 2.29.1，GNU Make 4.4.1 |
| profile | `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同值） |
| 命令 | `conan create archives/d/debfoster/2.8 -pr:h=$HOST_PROFILE -pr:b=$HOST_PROFILE --build=missing --user=ohpcd --channel=stable` |
| 轮次 | 两轮独立**清缓存**干净构建（第 7.2 节四步：限 ref → 裸 ref → 分片目录 → `p/cache.sqlite3` 两表回查为空） |

| 轮 | 日志（**本地原始日志，不入库**；逐字摘录见 `reports/evidence-excerpts.md`） | 包目录（复核时用 §1 的 glob 定位；缓存目录每轮重建，**事后可能已被后续流程清掉**） |
| --- | --- | --- |
| 轮 1 | `reports/conan-create-l5-round2.log`，46472 B，sha256 `f731d5e86525bdf5aac6dadcc8d9955352b9ca71d996c240ef16d49c9424e9be`（手工清缓存后重跑） | `p/b/debfo672a3cdec7510/p` —— **已不存在**（被后续清缓存流程删除） |
| 轮 2 | `reports/conan-create.log`，46472 B，sha256 `ef35ef54f139228d7a36ae7da3f84be931dd4bc26e0fa75004c452233dbfbb7a`（由 `conan-verify` 的 G2 写出，即采信轮） | `p/b/debfo567d371d4110f/p` —— 复核本文件时实测**仍然存在**，§6.2 的 7/7 sha256 已在该目录上逐条重新复算通过 |

两轮的**编译输入逐字节相同**（见文首说明），差别只在注释、文档与 `test_package`
的解释器选择，因此两轮构建产物可直接交叉比对（`bin/debfoster` 的 sha256 完全相同，
见 §6.2）。两轮都是干净轮（非缓存命中），标志行计数逐项一致：

> **§6.2 的 sha256 表是三处引用中的权威值**；审计者已独立复算并确认逐条一致。
>
> **解释器回归的修复留痕**：中间一版曾把 `CONFIG_SHELL` 写成
> `CONFIG_SHELL or SHELL or <device bash>` 的回退链。实测 `CONFIG_SHELL` 并未导出到
> `test()` 的环境、`SHELL` 是 `/bin/sh`，于是 `test()` 实际改用 toybox ash 运行，
> 采信轮 RUN 行变成 `RUN: /bin/sh .../test.sh`（W4 增量复审据此判 P1）。现已改为
> `os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"`，采信轮的 RUN 行
> 恢复为 `RUN: /data/service/hnp/bin/bash .../test_package/test.sh`（可直接 grep 复核）。

| 标志 | 轮 1 | 轮 2 |
| --- | --- | --- |
| `Calling build()` | 1 | 1 |
| `RUN: make -j1` | 1 | 1 |
| `RUN: make check -j1` | 1 | 1 |
| `Apply patch (portability)` | 3 | 3 |
| `Nothing to be done for 'check'` | 3 | 3 |
| `check-am` | 1 | 1 |
| `RUN: /data/service/hnp/bin/bash .../test.sh` | 1 | 1 |
| `HMBS_TEST_SUMMARY discovered=36 passed=36 failed=0 skipped=0` | 1 | 1 |

## 3. G4：声明产物与真实产物互相印证

`find $PKG -type f`（排除 conan 元数据）：

```text
bin/debfoster
etc/debfoster.conf
licenses/COPYING
licenses/LICENSE.AVLTree
licenses/LICENSE.debfoster
licenses/LICENSE.symbol
share/man/man8/debfoster.8
```

与 `package_info()` 一致：`cpp_info.libs = []`、`cpp_info.bindirs = ["bin"]`，
即唯一可执行产物是 `bin/debfoster`，无 `lib/`、无 `include/`。`etc/`、`licenses/`、
`share/man/` 是 `autotools.install()` 与 `package()` 的显式副本，不是 bindirs 声明面。
`conaninfo.txt`/`conanmanifest.txt` 属 Conan 元数据，不计入产物清单。

## 4. L2：真实驱动已安装的 `bin/debfoster`

`conan-verify` 的 L2 探针只试 `--version`/`--help`，本包恰好都支持，但仍按第 7.2 节
做实质补测——只跑「启动成功」不算行为验证。用运行期生成的 dpkg 状态夹具驱动包内
二进制：

```sh
$ $PKG/bin/debfoster --version
debfoster 2.8 -- Copyright (C) 2000,2001 Wessel Dankers.
Distributed under the GNU General Public License.
rc=0

$ $PKG/bin/debfoster -c $W/conf -k $W/keepers -s
The following packages have been orphaned:
  straygamma toolbeta
rc=0

$ $PKG/bin/debfoster -c $W/conf -k $W/keepers -e libalpha1
The following 1 packages on the keeper list rely on libalpha1:
  toolbeta
Packages kept by default rules do not rely on libalpha1.
rc=0
```

可执行性判据按第 7.2 节用「退出码 ≠ 126」，实测 rc=0；更强证据是上面两条带真实参数、
比对业务输出的查询（孤立包判定与依赖者解析），而非仅 `--version`。

stderr 全集（`sort -u`）只有一行，即 `gc/8.2.12` 的既知告警：

```text
GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region
```

完整 36 项行为断言由 `conan create` 的 `test_package` 执行，两轮均
`HMBS_TEST_SUMMARY discovered=36 passed=36 failed=0 skipped=0`，日志中 `^FAIL ` 计数为 0。

## 5. L4：安全属性（可执行包按 `bin/` 逐个判据）

```text
$ readelf -h $PKG/bin/debfoster
  Class:   ELF64
  Type:    DYN (Position-Independent Executable file)
  Machine: AArch64

$ readelf -lW $PKG/bin/debfoster | grep -E 'GNU_STACK|GNU_RELRO'
  LOAD           0x02a1d0 ... R   0x1000
  LOAD           0x02abb8 ... RW  0x1000
  GNU_RELRO      0x02a1d0 0x000000000002c1d0 ... 0x0009e8 0x000e30 R   0x1
  GNU_STACK      0x000000 0x0000000000000000 ... 0x000000 0x000000 RW  0

$ readelf -dW $PKG/bin/debfoster | grep -E 'BIND_NOW|FLAGS|NEEDED'
  0x0000000000000001 (NEEDED)  Shared library: [libc.so]
  0x000000000000001e (FLAGS)   BIND_NOW
  0x000000006ffffffb (FLAGS_1) Flags: NOW PIE
```

判据逐项：`DYN` ✔、`GNU_STACK RW`（无 `E`，栈不可执行）✔、`GNU_RELRO` ✔、
`FLAGS BIND_NOW` ✔、`FLAGS_1 PIE` ✔。`DT_NEEDED` 只有 `libc.so` —— 与
`gc/8.2.12` 是静态归档（`libgc.a`）的事实一致，运行期无额外共享库依赖。

## 6. L5：产物基线与可复现性

工具未实现 build-tree 与打包副本的 sha256 对比，手工补做并扩展为**清缓存构建交叉比对**。

### 6.1 打包副本 = 构建树副本（同一轮内）

```text
$ sha256sum $PKG/../b/build-release/src/debfoster $PKG/bin/debfoster
17c66a113ca9d80dfb485b6ed46da9eb96ce81d39d25fcf5ee4862daebd2b5ce  .../b/build-release/src/debfoster
17c66a113ca9d80dfb485b6ed46da9eb96ce81d39d25fcf5ee4862daebd2b5ce  .../p/bin/debfoster
```

一致。这一项在 workflow 第 5.3 节记录过反例（`meson install --destdir` 会原位改写
安装副本的 `.dynstr`、破坏 hnp 产物的 `.codesign`，导致打包副本与 build-tree 的
`sha256` 不一致、加载报 `Error loading shared library`）；本包各轮均一致，不存在该问题。

### 6.2 清缓存构建逐产物比对

| 产物 | 轮 1 | 轮 2 | 一致 |
| --- | --- | --- | --- |
| `bin/debfoster` | `17c66a113ca9d80dfb485b6ed46da9eb96ce81d39d25fcf5ee4862daebd2b5ce` | 同左 | ✔ |
| `etc/debfoster.conf` | `7ca9db900d969dc9efdd8b7cbf1953dfccb16c4426b1a0a9585bed2135d8eaf7` | 同左 | ✔ |
| `licenses/COPYING` | `876406815e3912e17d794fb16c3d0bbbe3317ba8aa3263cc5802b73b6c3e1a35` | 同左 | ✔ |
| `licenses/LICENSE.AVLTree` | `7a4436f9ec37603356791c87de3bc444989befd2682d29efb3d97604e04c1852` | 同左 | ✔ |
| `licenses/LICENSE.debfoster` | `32b1062f7da84967e7019d01ab805935caa7ab7321a7ced0e30ebe75e5df1670` | 同左 | ✔ |
| `licenses/LICENSE.symbol` | `5bbcbb737e60fe9deba08ecbd00920cfcc3403ba2e534c64fdeea49d6bb87509` | 同左 | ✔ |
| `share/man/man8/debfoster.8` | `fc63e0c9236adea0127612a3c62bc6f62b4217ae0941132371eb5c8b915cea18` | 同左 | ✔ |

**7/7 产物逐字节一致**，各轮之间没有任何不可复现项，因此无需声明「不可复现 + 根因」，
基线对整个产物集成立。

**比对本节的可复核性说明（含新增复算）**：轮 1 的包目录 `p/b/debfo672a3cdec7510/p`
已被后续清缓存流程删除；轮 2 的 `p/b/debfo567d371d4110f/p` 在复核本文件时**仍然存在**，
因此上表已于该目录上逐条重新复算通过（命令与输出同 §6.1/§6.2，`bin/debfoster` 的
`17c66a11…` 与 §6.1 的 build-tree 副本 sha256 相同）。

两轮的**原始日志**（`reports/conan-create-l5-round2.log`、`reports/conan-create.log`）
是本地产出、**不入库**的转储；本文对它们的引用以 `reports/evidence-excerpts.md` 的
逐字摘录为准（该文件同时登记了两份日志的字节数与 sha256，用于确认**本地文件未被后续
重跑覆盖**——不是用来判断「是否与某轮构建等价」，跨轮日志不会逐字节一致）。
若两个包目录都被后续流程清掉，上表仍可从 `evidence-excerpts.md` 摘录的构建命令行
（含依赖 `-I`）与产物清单交叉对照。

> 复算命令（在存活的轮 2 目录上）：
>
> ```sh
> PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/debfo*/p | head -1)
> find "$PKG" -type f -not -name 'conaninfo.txt' -not -name 'conanmanifest.txt' \
>   | sed "s|$PKG/||" | sort | while read -r f; do
>       printf '%s  %s\n' "$(sha256sum "$PKG/$f" | cut -d' ' -f1)" "$f"; done
> sha256sum "$PKG/../b/build-release/src/debfoster" "$PKG/bin/debfoster"
> ```

已知的两类常见漂移根因在本包都不存在：上游源码没有内嵌
`__DATE__`/`__TIME__`（`grep -rn '__DATE__\|__TIME__' src/` 计数为 0），且构建未用 `-g`
（两轮编译行（各自第 187 行）已逐字摘录在 `reports/evidence-excerpts.md` §4，
其 flags 去重后为 `-DNDEBUG -Wall -O3`；也可用下方命令在本地原始日志上复算），
因此没有 DWARF `DW_AT_comp_dir` 随每轮缓存构建目录名漂移的问题：

```sh
grep -m1 'clang -DHAVE_CONFIG_H' reports/conan-create-l5-round2.log \
  | tr ' ' '\n' | grep -E '^-O|^-DNDEBUG|^-Wall|^-g' | sort -u
# -DNDEBUG
# -O3
# -Wall
```

同一出处（`evidence-excerpts.md` §4）也摘录了编译行里的
`-I/storage/Users/currentUser/.conan2/p/gc8d81fb4baf197/p/include`，
即 §6.2 判据所依赖的「依赖 `-I` 确实注入」的直接证据。

`bin/debfoster` 未 strip（`file` 报 `not stripped`，`readelf -S` 有 11 个 `.debug_*` 节），
按设备实测口径未 strip 的二进制 rc=0（strip 后才 rc=126），与第 4 节的运行结果一致。

### 6.3 聚合指纹的定位方式

本节直接引用具体分片目录名（`debfo672a3cdec7510` / `debfo567d371d4110f`）仅是为了
说明两轮目录名确实不同；台账中可复核的稳定信息是上表的**逐产物 sha256**——它们与
`bin/debfoster` 的路径无关，跨轮、跨任务均可直接比对（workflow 第 7.2 节：带绝对路径
的聚合指纹必然漂移，不可作为基线）。

## 7. 结论

| 门禁 | 工具结论 | 人工补测结论 |
| --- | --- | --- |
| G0 | PASS（提示 E490：autotools 辅助脚本可执行位） | 已处置，见下 |
| G1 | PASS | — |
| G2 | PASS（干净轮） | 两轮清缓存干净轮复核通过 |
| G3 | PASS | 无系统同名库 |
| G4 | ⚠️ 无法找到程序包 ID | 人工核对通过（第 3 节） |
| L2 | ⏭️ 跳过 | 人工补测通过（第 4 节） |
| L4 | ⏭️ 跳过 | 人工补测通过（第 5 节） |
| L5 | ⏭️ 跳过 | 人工补测通过，7/7 逐字节可复现（第 6 节） |

G0 提示的 E490（autotools 辅助脚本被保留源码内容时丢失可执行位）在本包**不适用且已
验证**：`config.guess`、`config.sub`、`install-sh`、`missing`、`depcomp` 以 mode
`100755` 入库（`git ls-files -s archives/d/debfoster/2.8/generated/` 实测），并由
`export_sources()`/`source()` 用 `conan.tools.files.copy` 复制，该函数保留源文件权限位。
两轮构建中 `configure` 均正常调用 `config.guess` 并得到

```text
checking build system type... aarch64-unknown-linux-ohos
```

未出现 E490 描述的 permission denied 形态。该风险无需额外补丁。

## 8. W3 日志的留档口径

`reports/w3-local-ci.log` 是在最终态单独重跑 `scripts/ohc/workflow_checks.py` 的
`run_local_ci()` 得到的（不是 finish 内嵌那一轮——finish 会把该文件整文件重写成它自己
那一轮）。判读时注意三点：

1. **该轮确实执行了 `source()`，但下载源是被就地改写过的 `file://` 本地缓存**，不是官方
   URL。日志实证：

   ```text
   [step] Pre-download: extracting source URLs from conandata.yml...
     [done] Pre-downloaded 1 files, conandata.yml updated to file:// URLs     # 第 99 行
   debfoster/2.8: Calling source() in .../.conan2/p/debfo1c30c4915b19f/s       # 第 171 行
   debfoster/2.8: Sources correctly downloaded from
     file:///storage/.../wt-debfoster-2.8/.build-cache/predl_cache/86b8c49b_debfoster_2.8.orig.tar.xz
                                                                              # 第 172 行
   [step] Pre-download: conandata.yml 已还原为官方 URL                          # 第 733 行
   ```

   即预下载器先按 `conandata.yml` 的官方 URL 取回 tarball，再把它就地改写成
   `file://` 形态交给 `source()`，跑完还原。**后果有两点**：
   - 该轮的 recipe revision（`122450db94d2`）与两份 `conan-create*.log` 的
     （`4687874699f1` / `eb1bdc2ee08e`）都不同，不能拿 revision 当跨日志的同一性锚点
     （见文首说明）；
   - **这一轮不构成「官方 URL 可达」的证据**——它验证的是 W3 流水线本身。官方 URL 的可达性
     与 `sha256` 锚定由 §2 的清缓存 `conan create` 轮（`conandata.yml` 未被改写、日志含
     `Sources correctly downloaded from https://deb.debian.org/...`）与
     `conanfile.py` 声明的 sha256 共同保证。
   - 收尾必须确认提交版 `conandata.yml` 未被留在 `file://` 形态（本 PR 实测干净：
     `git show HEAD:archives/d/debfoster/2.8/conandata.yml` 为官方 https URL，
     `git status --short` 为空，`.build-cache/` 已删除）。
2. 该轮的 `L1_RESULT=pass: upstream tests + test_package executed` 是 W3 的**宽泛正则**
   判定（workflow 第 17 节已登记 `L1c` 可被 `--check-build-system` 之类的子串误命中）。
   本包不依赖它的宽泛匹配：上游测试的真实形态由 §2 表中 `RUN: make check -j1` 段逐行
   给出，`test_package` 的真实执行由同一日志的 `HMBS_TEST_SUMMARY` 行给出。
3. 本仓 CI 的门禁集是 `G0`/`L0`/`L1`/`L2`/`L4`/`L5`（`ci/conan/build_and_test.sh` 只发这几个
   `*_RESULT`，全仓无 `L3` 定义），因此日志中不存在 `L3` 行属正常，不是漏跑。
