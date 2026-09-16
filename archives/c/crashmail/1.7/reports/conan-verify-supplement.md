# conan-verify 补测报告 — crashmail 1.7

> 依据 workflow §7.2：`conan-verify` 报告里 G4/L2/L4/L5 打印
> `✅ PASS` 的同时带 `⏭️ 跳过（无 cache 路径）`，按显式 SKIPPED 对待，
> 需人工补测并留本文件。
>
> **采信轮标识**：本报告所依据的干净轮，其日志指纹如下（用日志自身的
> sha256 锚定"哪一轮"，不依赖提交号——提交号会随文档提交前移）。
>
> | 项 | 值 |
> | --- | --- |
| 采信轮 `conan-create.log` sha256 | `00f54393a51ff64ce6f14a98dac1b34f067c011f3951024e2f8d61a7b60fb175` |
> | 大小 / 行数 | 23246 字节 / 293 行 |
> | `RUN: make` | 1 |
> | `Apply patch` | 8 |
> | `Calling build()` | 1 |
> | `Calling source()` 的 source 分片 | `p/crashd4886786f2787/s/src`（新分片，非复用既有 source） |
> | 上游汇总行 | `Tests:    18 | Passed:   18 | Skipped:   0 | Failed:    0` |
> | `test_package` | `crashmail test_package PASSED (assertions=8)` |
> | 本轮包缓存目录 | `p/b/crashf7e8614fd7587/p` |
>
> **关于原始 `conan-create.log` 的存放**：本轮日志**不入库**（仓库
> `.gitignore` 的 `reports/` 规则本就忽略该目录，`review-memory` §19 的
> 「PR 中禁止的文件」也把 `*.log` 列为禁止入库类型，且日志内含 26 处
> `/storage/Users/currentUser/...` 形式的本机绝对路径）。原始日志按 workflow
> §7.2 的口径留在仓库外（`$TASK_DIR/conan-create-<SHA前7>.log`），本报告用
> 上表的 **sha256 + 字节数 + 行数 + 各标记计数**锚定其身份：复核者拿到该
> 文件即可用 `sha256sum` 与上表比对，并逐项复算下列所有数字。仓库内只保留
> 本报告（`.md`）作为数字与判据的载体。
>
> 另注：`reports/conan-verify-report.md` 由 `conan-verify` 自动生成，其中的
> `📄 日志: archives/c/crashmail/1.7/reports/conan-create.log` 一行指向的正是
> 上述**不入库**的日志。该行是生成器的固定文案，故说明记在这里：读到该指针时
> 请按本节开头的 sha256 在仓库外核对原始日志，不要认为它缺失或证据链断裂。
> 之所以不直接改那个 `.md`，是因为它每次重跑 `conan-verify` 都会被覆盖。
>
> 清缓存动作（顺序重要，见 workflow §7.2）：先
> `conan remove "crashmail/*@*" -c` 枚举 user/channel 形态，再
> `conan remove "crashmail/*" -c` 清裸 ref 形态，然后删 `p/` 下 `crash*`
> 分片目录，最后回查 `p/cache.sqlite3` 的 `recipes`/`packages` 两表对
> `%crashmail%` 均为空——**以 DB 两表为空为通过判据，不以目录为空为判据**
> （两种 ref 形态共享同一 `p/` 分片目录，"目录已清但 DB 仍有登记"是常态）。
> 洁净性另有日志判据佐证：本轮含 `Calling source()`（新 source 分片）、
> 8 条 `Apply patch`、`Calling build()` 与 `RUN: make`，非缓存命中。
>
> ⚠️ **缓存轮陷阱实测**：本轮之前有一次 `conan-verify` 因前台 60s 超时被
> SIGTERM 中断，而它派生的 `conan create` 子进程**未被回收**，继续跑完并把
> 包写进了缓存。随后一次 `conan-verify` 因此命中缓存，产出只有 103 行、
> `RUN: make` 计数为 0、而 `test_package` 段照常通过的**缓存轮日志**——若不按
> §7.2 逐项核对 `RUN: make`/`Apply patch`/`Calling build()`，很容易把它
> 当成采信轮。本轮是在确认无遗留 crashmail conan 进程、且 DB 两表回查为空
> 之后重跑取得的。

## 跳过原因

`conan-verify` 报告原文：

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

`--user=ohpcd --channel=stable` 形态下 G4 的 package_id 正则解析失败，
G4/L2/L4/L5 整组走了跳过分支（§17「conan-verify 缓存与定位缺陷」同型）。
本包是 `package_type = "application"` 纯可执行包（包内无 `lib/`、无 `.so`），
G3 的输出 `ℹ️ 无 lib/ 目录（纯可执行包）` 也印证了这一点，
属该缺陷的必然命中面，不是偶发。

## 包目录定位

按 §7.2 的 glob 兜底口径：

```sh
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/crash*/p | head -1)
# 本轮 -> /storage/Users/currentUser/.conan2/p/b/crashf7e8614fd7587/p
```

⚠️ 缓存里可能同时存在多个 `crash*/p` 分片（历次实测见过
`crash9171729868fc8`、`crash87ac3c9a5bdb5`、`crash816e33b541c7b` 等），此时 `head -1` 返回的是**字典序最前**的那个，
不一定是本节记录的 `crashf7e8614fd7587`。这不影响任何数字：两条 L5 聚合
（`facf968b…`、`59ac41cb…`）在两个分片上都实测一致，产物清单（23 文件 /
bin 8）与 L4 表也一致。若要精确定位本节所述分片，把 glob 换成完整路径，
或按 `ls -d` 的完整输出人工挑选。

注意：`p/b/<名前缀><hash>/` 的 hash 每轮重建都会变，因此**下文所有聚合命令
都在 `$PKG` 内用相对路径取名**；若写成绝对路径，路径文本本身会进 `sha256sum`
的输出并导致跨轮漂移（本轮实测两种写法结果不同）。

## G4 补测：产物清单与 `package_info()` 互相印证

`find "$PKG" -type f`，共 **23 个文件**（8 个在 `bin/`）：

```text
bin/crashexport      bin/crashgetnode    bin/crashlist       bin/crashlistout
bin/crashmail        bin/crashmaint      bin/crashstats      bin/crashwrite
licenses/LICENSE
share/doc/crashmail/{AreafixHelp.txt,ReadMe.txt,example.prefs,filter.txt}
share/man/man1/{crashexport,crashgetnode,crashlist,crashlistout,
                crashmail,crashmaint,crashstats,crashwrite}.1
conaninfo.txt  conanmanifest.txt
```

与配方 `package_info()` 的声明一致：`bindirs = ["bin"]`、
`libdirs = []`、`includedirs = []`、`cpp_info.libs = []`。
**无 `lib/` 目录**是预期结果（纯 CLI 工具包），与 G3 的结论互证。

`package()` 的 `Packaged` 日志行（取自本轮采信轮日志，见文首指纹）：

```text
package(): Packaged 9 files
package(): Packaged 8 '.1' files
package(): Packaged 3 '.txt' files: AreafixHelp.txt, ReadMe.txt, filter.txt
package(): Packaged 1 '.prefs' file: example.prefs
```

对账：9 = 8 个可执行文件 + `licenses/LICENSE`；9 + 8 + 3 + 1 = 21，
加 `conaninfo.txt` 与 `conanmanifest.txt` 两个 Conan 元数据文件即 23。

## L2 补测：打包产物真实功能验证

### 第一层：`conan create` 内的 `test_package`（已在本轮通过）

由 `VirtualRunEnv` 提供 PATH，被测对象就是上面 8 个**打包产物**：

```text
RUN: "<bash>" ".../test_package/test.sh" ".../test_package/build-release"
✅ A1 crashmail settings 自报版本 CrashMail II 1.7 并正常退出
✅ A2 crashlist 生成 nodelist/cmnodelist.index
✅ A3 crashgetnode 99:99/1.1 输出与上游期望逐字节一致
✅ A4 crashgetnode 99:99/99 输出与上游期望逐字节一致
✅ A5 crashwrite 生成 1 个 type-2+ 包（PKTTYPE=2 ORIGNODE=999 DESTNODE=1 YEAR=2026）
✅ A6 crashmail toss 报告 Area NETMAIL -- 1 messages
✅ A7 投递结果 areas/netmail/2.msg 含主题 Test netmail message
✅ A8 crashstats 解析 crashmail.stats 并输出 NETMAIL 统计
✅ crashmail test_package PASSED (assertions=8)
```

**反向验证**：`test.sh` 通过 PATH 解析调用 8 个程序、不引用任何包外路径；
包的 `bin/` 若被移走则 A1 立即失败（实测移除后 rc=127、无一条断言执行）
——A1..A8 全绿即证明测试确实依赖交付产物（与 W3 L1e 反向验证同思路）。

### 第二层：在包缓存目录上独立复跑完整 toss 周期（本次补测）

```sh
export PATH="$PKG/bin:$PATH"   # 直接指向打包产物
crashlist nodelist                                     # rc=0，生成 nodelist/cmnodelist.index
crashwrite dir spool/inbound FROMNAME F FROMADDR "99:99/999" \
  TONAME T TOADDR "99:99/1" SUBJECT S TEXT b.txt        # rc=0，生成恰好 1 个 .pkt
crashmail settings crashmail.prefs toss                # rc=0
  -> 日志含 "Area NETMAIL -- 1 messages"
  -> 投递产物 areas/netmail/2.msg 存在
crashstats crashmail.stats sort a                      # rc=0，输出含 NETMAIL
```

7 项全部满足。

### 动态加载

本包无 `.so` 产物（`find "$PKG" -name '*.so*'` = 0），
无 `dlopen` 适用场景；交付形态是 8 个独立可执行程序。

## L4 补测：安全属性与"产物确实可被内核加载"

安全属性对**打包副本**（非 build tree）逐个取：

```sh
readelf -hW  "$b" | awk '/Type:/{print $2}'      # DYN（PIE）
readelf -lW  "$b" | awk '/GNU_STACK/{print $7}'  # RW（NX 生效）
readelf -lW  "$b" | grep -c GNU_RELRO            # 1
readelf -dW  "$b" | grep -c 'BIND_NOW'           # 1
readelf -dW  "$b" | awk '/FLAGS_1/{print $NF}'   # PIE
```

8 个产物逐项一致：`Type: DYN`（PIE）+ `GNU_STACK RW`（NX）+
`GNU_RELRO` + `FLAGS: BIND_NOW` + `FLAGS_1: PIE`。

### 可执行性判据（务必按此判据读，不要用 rc=0）

判据是"**退出码不是 126**"外加"能看到该程序自己的输出"，而不是"退出码为 0"。
OHOS 上 `.codesign` 失效时内核拒绝 exec，表现为
`Operation not permitted` / 退出码 **126**；而已成功加载运行的程序在缺参数时
会打印各自的用法信息并按用法约定返回非零码。

逐个产物在空目录中无参执行的实测（⚠️ 测量时不要在同一行用
`$(basename ...)`，命令替换会重置 `$?`，导致读数恒为 0）：

| 产物 | 退出码 | 首行输出（证明已被加载执行） |
| --- | --- | --- |
| crashexport | 10 | `Mandatory argument PREFSFILE not specified` |
| crashgetnode | 10 | `Mandatory argument NODE not specified` |
| crashlist | 10 | `Failed to open ./cmnodelist.prefs for reading` |
| crashlistout | 0 | `CrashListOut 1.7` |
| crashmail | 10 | `Failed to read configuration file crashmail.prefs` |
| crashmaint | 0 | `Nothing to do.` |
| crashstats | 10 | `Mandatory argument FILE not specified` |
| crashwrite | 10 | `Mandatory argument DIR not specified` |

**8/8 全部真实执行，rc==126 的计数为 0。** 另用真实参数执行同样通过：
`crashmail settings crashmail.prefs` → rc=0 并打印
`CrashMail II 1.7 started successfully!`；`crashlist --help` → rc=0。

「无一为 126」是这些产物**未被 strip 破坏 `.codesign`** 的正面证据。
对照实测（同一设备）：clang 编译一个最小程序 → 执行 rc=0；
`cp` 一份并对其执行 GNU `strip`（binutils 2.45）或 `llvm-strip` 后
执行即 `Operation not permitted` / rc=126，文件从 18816 字节缩到 10072 字节。
这也是配方传 `STRIP=:` 的直接依据（详见 `notes.md` 问题 4）。

## L5 补测：产物基线

### 关键前提：本包并非逐字节可复现

`src/crashmail/crashmail.c:321-322` 无条件内嵌编译期时间戳：

```c
printf("Compilation date: %s\n",__DATE__);
printf("Compilation time: %s\n",__TIME__);
```

因此 **`bin/crashmail` 每次干净构建的 sha256 都不同**，而其余 7 个产物不含
该宏。实测证据：本轮 `strings <pkg>/bin/crashmail` 命中两个字面量
`Sep 11 2026` 与 `03:38:18`（即该轮的编译日期与时刻，逐轮不同）；
而 `strings <pkg>/bin/crashlist` 匹配同类日期模式 **0 次**。

六轮**独立清缓存干净构建**的逐产物比对：

| 产物 | 轮1 | 轮2 | 轮3 | 轮4 | 轮5 | 轮6（本轮） | 跨轮一致 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| crashexport | `8c71774d…` | `8c71774d…` | `8c71774d…` | `8c71774d…` | `8c71774d…` | `8c71774d…` | ✅ |
| crashgetnode | `8b6bb272…` | `8b6bb272…` | `8b6bb272…` | `8b6bb272…` | `8b6bb272…` | `8b6bb272…` | ✅ |
| crashlist | `e96ad702…` | `e96ad702…` | `e96ad702…` | `e96ad702…` | `e96ad702…` | `e96ad702…` | ✅ |
| crashlistout | `c081a014…` | `c081a014…` | `c081a014…` | `c081a014…` | `c081a014…` | `c081a014…` | ✅ |
| crashmaint | `af0a6425…` | `af0a6425…` | `af0a6425…` | `af0a6425…` | `af0a6425…` | `af0a6425…` | ✅ |
| crashstats | `87f43325…` | `87f43325…` | `87f43325…` | `87f43325…` | `87f43325…` | `87f43325…` | ✅ |
| crashwrite | `3ae44403…` | `3ae44403…` | `3ae44403…` | `3ae44403…` | `3ae44403…` | `3ae44403…` | ✅ |
| **crashmail** | `9c148234…` | `dd38680f…` | `0a85b578…` | `406e003c…` | `a8d61e66…` | 逐轮变 | ❌（内嵌 `__DATE__`/`__TIME__`） |

即 **7/8 可复现，1/8 因上游内嵌编译时间戳而不可复现**（原始设计者把它当
"编译信息"打印，属上游行为，不修补）。

### 基线值

全部命令在 `$PKG` 内用相对路径执行（否则 `p/b/<hash>/` 会进输出导致漂移）。

| 聚合 | 命令 | 值 | 跨轮稳定性 |
| --- | --- | --- | --- |
| ① **可复现产物子集**（7 个） | `cd "$PKG/bin" && sha256sum crashexport crashgetnode crashlist crashlistout crashmaint crashstats crashwrite \| sha256sum` | `facf968b9eb7a3ba2040d2d40652350dbee48996445f6a0bb4b59f7b5b77e6ab` | ✅ 六轮一致（建议作为 L5 基线） |
| ② 文档/许可证 | `cd "$PKG" && find share licenses -type f \| sort \| xargs sha256sum \| sha256sum` | `59ac41cb459b722b49317e9125c70ff665f5af80bc5eee8299947256ad80497b` | ✅ 六轮一致 |
| ③ 全 8 产物（含 crashmail） | `cd "$PKG/bin" && sha256sum * \| sha256sum` | 逐轮变 | ❌ 必漂移（crashmail 时间戳） |
| ④ 全包（含 conanmanifest 时间戳） | `cd "$PKG" && find . -type f \| sort \| xargs sha256sum \| sha256sum` | 逐轮变 | ❌ 必漂移（`conanmanifest.txt` 首行 = 打包时间戳） |

③④ 按设计就是轮次相关的，故不记录具体值（记录一个必然失效的数字没有意义）。
① 与 ② 是本报告提供的稳定基线，复核者可在任意一轮的包目录上重算比对。

本轮逐产物 sha256（`cd "$PKG/bin" && sha256sum *`）：

```text
8c71774d4b78ac4a305982fbe9feb33a20f3ec24142f760e000d1522b0474a26  crashexport
8b6bb272b0dd81b206b116babeff2c198b58d389eecee159027acffecc41d7ce  crashgetnode
e96ad7027664a9b22532ee3c2b3d58a45fcee8243d0b76a997f0349f771fd094  crashlist
c081a014f5c407644d23d8246468c996fdc5caef1054c79643905febbc20db2d  crashlistout
02097970219394b5b3c12bf2246da1d126b62fd15af9d82882009e567cda6b55  crashmail   ← 含编译时间戳，逐轮变
af0a6425aececaac441205c3445ea0392bd8dd07d8a89ef7612dc23b6fa4b9f9  crashmaint
87f433258a9ed2f4810219fc68d5c1fa3aebd7469e2a69e56da4fd80da74837a  crashstats
3ae44403c4f9cd5167290899c530b813247833a569789d58aa41429cb20559bd  crashwrite
```

### 该缺陷未覆盖的检查（人工判据）

§17 记载 conan-verify 的 L5「未实现 build-tree 与打包副本的 sha256 对比」
（meson 改写 `.dynstr` 破坏 `.codesign` 的路径）。本包：

- 无 `.so`，不存在 `meson install --destdir` 改写 `.dynstr` 的场景；
- 不使用上游 makefile 的 `install` 目标（配方 `package()` 用
  `conan.tools.files.copy` 直接复制），不存在安装期二进制改写；
- **最强正面证据**：打包副本 8/8 真实执行、无一返回 126。
  若打包过程改写了任何字节导致 `.codesign` 失效，这 8 个程序都会以
  退出码 126 失败而不是打印各自的用法信息。

因此该未覆盖项对本包不构成风险，结论以「打包副本无一为 126」为准。

## 结论

`conan-verify` 的 G4/L2/L4/L5 四个跳过项已按 §7.2 全部人工补测并留证：

- G4：产物清单 23 个文件与 `package_info()` 声明逐项一致；
- L2：`test_package` 8 条断言在本轮通过，另在包缓存目录上独立复跑
  完整 toss 周期 7 项全过；
- L4：8 个产物 PIE + NX + RELRO + BIND_NOW 齐备，且 8/8 真实执行、
  无一返回 126（`.codesign` 未被破坏）；
- L5：给出两条跨六轮稳定的基线（7 产物子集 `facf968b…`、文档/许可证
  `59ac41cb…`）与逐产物 sha256，并明确记录 `bin/crashmail` 因上游内嵌
  `__DATE__`/`__TIME__` 而**逐轮不可复现**这一事实。

无未覆盖的验证缺口。
