# dicom3tools 1.00-20240118131615 — 上游测试可运行性取证

> 采集时间：2026-09-11（设备本地时间）
> 命令：`make IMAKE_DEFINES="-DStripCmd=true -DAnsiCCmd=clang -DCPlusPlusCmd=clang++" test`
> 工作目录：补丁后的源码树
> 原始日志：`reports/upstream-make-test-evidence.md`（逐字留档，1076 行）
> 网络探测原始输出：`reports/upstream-test-probe.md`

> **本结论对后续 delta 的有效性**：本次上游测试不经 Conan，是在「基线源码 + `patches/` 全部补丁」
> 的原生源码树上直接跑 `make test`，因此其输入只有 `patches/` 与 `conandata.yml`（补丁清单与
> `patch_file` 引用）两类。这两类在采集之后逐字节未变：
>
> ```sh
> git diff --name-only 586b8af8..HEAD -- 'archives/*/*/*/patches/**' 'archives/*/*/*/conandata.yml'
> # 无输出
> ```
>
> 其后唯一影响上游源码树的 delta 是 `test_package/conanfile.py`（测试脚本路径解析，
> 属消费者测试而非上游测试）与 `conanfile.py` 的 `package_info()` 声明（打包元数据，
> 不参与原生编译）。两者都不改变上游源码树，故本文件的计数与归因继续有效。

## 结论

上游测试**一个都无法产生通过结果**：其断言全部依赖 `$(TOP)/images/` 与 `$(TOP)/test/`
两份夹具树，而上游把这两棵树作为独立归档分发，该归档在官方站点上**不存在**。
另有 1 个驱动（`appsrc/misc/binpatch.test.sh`）**被测二进制确实被调用过**，但因脚本硬编码 `/tmp` 而在比对前 abort（见下方「FAIL / NOT_RUN 的判定口径」）。

## 分母 N 的候选值、取数命令与归因

按 §7.3「N 取候选数法中的最大值 + 逐项归因差额」。上游无单元测试框架、无 case 注册机制，
因此把**测试驱动调用点**作为口径。全部候选值实测如下（在 sha256 已核对的上游 tarball 解包树中）：

| 候选口径 | 值 | 取数命令 | 语义 |
| --- | --- | --- | --- |
| 上游单元测试框架注册 case | 0 | — | 上游无单元测试框架 |
| `test::` 目标数 | 21 | `grep -rh '^test::' --include=Imakefile . \| wc -l` | 测试入口（`make test` 遍历的对象） |
| `test.create::` 目标数 | 21 | `grep -rh '^test.create::' --include=Imakefile . \| wc -l` | 比对基准生成入口 |
| `test::` 行内具名子目标数 | 16 | `grep -rhoE '^test::[[:space:]]+[a-zA-Z0-9_ ]+' --include=Imakefile . \| sed 's/^test:://' \| tr ' ' '\n' \| grep -c .` | 一行 `test::` 可展开多个子目标 |
| `test.create::` 行内具名子目标数 | 2 | `grep -rhoE '^test\.create::[[:space:]]+[a-zA-Z0-9_ ]+' --include=Imakefile . \| sed 's/^test\.create:://' \| tr ' ' '\n' \| grep -c .` | 同上，create 侧 |
| `support/testapp` 调用（compare） | 148 | `grep -rh 'support/testapp' --include=Imakefile . \| grep -c ' compare '` | `make test` 实际驱动的子集 |
| `support/testapp` 调用（create） | 148 | `grep -rh 'support/testapp' --include=Imakefile . \| grep -c ' create '` | 比对基准生成侧 |
| `support/testapp` 调用（全部，词法口径） | 296 | `grep -rh 'support/testapp' --include=Imakefile . \| wc -l` | 含 `test.create::` 的 create 模式 |
| `support/testapp` 调用（仅 `test::`/`test.create::` 可达） | 288 | 见下「可达性」 | 排除未出现在前置列表里的 4 个死目标 |
| 脚本驱动调用点 | 12 | `grep -rnE '^[[:space:]]*(@)?\./[A-Za-z0-9_.-]+\.sh' --include=Imakefile . \| grep -v ':[[:space:]]*#' \| grep -v makedcdtchgheader \| wc -l` | 独立测试脚本的调用点 |
| 测试驱动调用点（testapp + 独立脚本） | **308** | 296 + 12 | **本次采纳的 N（候选最大值）** |

### 脚本驱动必须用「与脚本名无关」的枚举

这是本文件先前 N=304 的**少报根因**。按脚本名硬编码三个名字只能看到 8 处：

```sh
grep -rn 'binpatch.test.sh\|test.create.ut.sh\|testy2k.sh' --include=Imakefile . \
  | grep -v ':[[:space:]]*#'
# → 8 行
```

而按 recipe 里的 `./<name>.sh` 形态枚举（与名字无关）能看到 13 行，其中 12 行是测试驱动：

```sh
grep -rnE '^[[:space:]]*(@)?\./[A-Za-z0-9_.-]+\.sh' --include=Imakefile . | grep -v ':[[:space:]]*#'
# ./appsrc/misc/Imakefile:152             ./binpatch.test.sh ... compare
# ./appsrc/misc/Imakefile:155             ./binpatch.test.sh ... create
# ./appsrc/acrnema/Imakefile:38           @./test.create.ut.sh compare
# ./appsrc/acrnema/Imakefile:39           @./test.create.private.un.sh compare   ← 此前漏计
# ./appsrc/acrnema/Imakefile:51           @./test.create.ut.sh create
# ./appsrc/acrnema/Imakefile:52           @./test.create.private.un.sh create    ← 此前漏计
# ./appsrc/dconvert/gen/Imakefile:30      ./testy2k.sh ... compare
# ./appsrc/dconvert/gen/Imakefile:35      ./testy2k.sh ... create
# ./appsrc/dcfile/Imakefile:190           ./makedcdtchgheader.sh ...   ← 构建步骤，非测试驱动，排除
# ./appsrc/dcfile/Imakefile:529           ./testy2k.sh ... compare
# ./appsrc/dcfile/Imakefile:530           ./testy2k.antodc.sh ... compare        ← 此前漏计
# ./appsrc/dcfile/Imakefile:672           ./testy2k.sh ... create
# ./appsrc/dcfile/Imakefile:673           ./testy2k.antodc.sh ... create         ← 此前漏计
```

12 个驱动点按脚本归并：`binpatch.test.sh` 2、`test.create.ut.sh` 2、
`test.create.private.un.sh` 2、`testy2k.sh` 4（dconvert/gen 2 + dcfile 2）、
`testy2k.antodc.sh` 2（dcfile）。

（`appsrc/dconvert/signa/Imakefile:27,32` 的同名调用被上游以 `#` 注释掉，不计入。）

### 差额逐项归因

| 差额 | 数量 | 归因 |
| --- | --- | --- |
| 308 − 296 | 12 | 独立测试脚本驱动点（见上表；其中 4 处若不按名字无关枚举会漏计） |
| 296 − 288 | 8 | `testdctopnm` / `testdctopgx` / `testdctopnm.create` / `testdctopgx.create` 四个目标内的 testapp 调用（`appsrc/dcfile/Imakefile:634,635,638,639,780,781,784,785`）；这四个目标**未出现在** `appsrc/dcfile/Imakefile:523` 的 `test::` 前置列表里，`make test` 不会触达——按最大口径仍计入 N |
| 296 − 148 | 148 | `create` 模式的 testapp 调用：**生成比对基准**，不是比对本身；取最大口径仍计入 N |
| 148 − 21 | 127 | 每个 `test::` 目标展开多个 testapp 调用（`appsrc/dcfile/Imakefile:523` 一行 `test::` 即展开 15 个具名子目标） |
| 21 − 16 | 5 | `test::` 目标中不带具名子目标（recipe 直接内联） |

候选值中的最大值即 **308**；「仅可达」口径给出 288 + 12 = 300，比 308 小。

**真实断言数不可得**：`support/testapp` 按 `images/<dir>/testlist` 文件逐行展开，每个镜像文件
产生一次比对；这些 `testlist` 就在未分发的夹具归档内，因此无法给出上游口径的断言总数。
同理，`appsrc/acrnema/Imakefile:62` 的独立目标 `testcompareandcwithoriginal` 未被 `test::`
或任何目标引用、不在 `make test` 路径上，其 `andiff` 调用数也取决于同一批 `testlist`，
故不计入 N（已在 `MANIFEST.yml` 的 attribution 中声明）。
本表以「驱动调用点」为口径并取候选最大值 308，避免少报。

## FAIL / NOT_RUN 的判定口径

先定口径再计数，避免把「环境阻断」写成「测试失败」：

| 分类 | 判定条件 |
| --- | --- |
| `PASS` | 驱动真的执行了比对，且比对通过 |
| `FAIL` | 驱动**真的执行了比对**，并给出不符结论（mismatch） |
| `SKIP` | 测试框架主动跳过（本包上游无该机制） |
| `NOT_RUN` | 驱动在**达到比对之前**即被阻断——夹具缺失、临时目录不可用、被测程序 abort 等 |

本包 308 个驱动点**全部**落在 `NOT_RUN`，两个具体阻断原因：

1. **夹具目录不存在**（296 个 testapp 调用）：`support/testapp` 的镜像目录参数指向
   未分发的 `$(TOP)/images/*`，中止于 `no such image directory` 判据。
   日志中该提示出现 **19 次**，涉及 19 个目录。
2. **脚本驱动硬编码 `/tmp`**（12 个脚本驱动点中的 6 处；另 6 处同因夹具缺失而止）：
   - `appsrc/misc/binpatch.test.sh` 把临时目录写成 `/tmp/binpatch.test.sh.$$`，
     设备 `/tmp` 只读 → 被测程序 `binpatch` abort（`Abort - File open for write failed`），
     脚本随后报 `binpatch: nothing stored to compare binary` / `... compare od`；
   - `appsrc/acrnema/test.create.ut.sh`、`test.create.private.un.sh` 的
     `mkdir //tmp/<script>.$$` 失败 → 每条 `cmp`/`diff` 都提示
     `No such file or directory`。

   **两类都从未产出比对结论**，故同为 `NOT_RUN`。此前把 `binpatch.test.sh` 记作 `FAIL`
   属口径不一致（它的比对并未执行）。

值得保留的反证：`binpatch.test.sh` 是唯一**被测二进制真的被调用过**的驱动，
它的 abort 原始输出逐字保留在下方的日志留档里——这证明这些用例不是静默跳过，
而是在明确的平台限制（只读 `/tmp` + 夹具未分发）处中止。

**`make test` 的退出码恒为 0，不作为通过证据**——原因已实测定位（原始输出见
`reports/make-test-exit-code-probe.md`）：顶层 `test::` 的 recipe 是
`for i in $(SUBDIRS); do (cd $$i; $(MAKE) ... test); done`，**shell 循环的退出状态等于
最后一次迭代的状态**，因此子目录的失败不会传递到顶层。实测同一次运行里
**22 条 `*** Error` 与 `rc=0` 并存**，可见退出码与「有没有失败」无关。
（此前的说明写成「夹具缺失时只打印提示就继续」并不准确：日志里确有
`make[2]: *** [makefile:282: test] Error 1` 一类失败，只是未向上传递。）
本 PR 未把该退出码记为 PASS，PASS 计为 0。

## 用例计数（口径：测试驱动调用点）

```text
TOTAL = PASS + FAIL + SKIP + NOT_RUN = 0 + 0 + 0 + 308 = 308
```

| 指标 | 值 |
| --- | --- |
| TOTAL | 308 |
| PASS | 0 |
| FAIL | 0 |
| SKIP | 0 |
| NOT_RUN | 308 |

**被调用过但未产出结论的驱动（记 NOT_RUN，共 4 处）**：`appsrc/misc/binpatch.test.sh`（`test::` →
`testbinpatch`，compare 模式）是唯一**被测二进制真的被调用过**的驱动——脚本硬编码
`TMPROOT=/tmp/`basename $0`.$$`，设备 `/tmp` 为只读挂载，实测
`can't create /tmp/binpatch.test.sh.65157.src: Read-only file system`，
被测程序 `binpatch` 随即 `Abort - File open for read/write failed`，脚本报
`binpatch: nothing stored to compare binary` / `... compare od`。
`appsrc/acrnema/test.create.ut.sh` 与 `test.create.private.un.sh` 同理（`mkdir //tmp/...` 失败）。
**四者都从未产出比对结论**，按判定口径记 NOT_RUN 而非 FAIL。

**NOT_RUN 明细（308 项）**：全部驱动点都在**比对执行之前**被阻断。阻断原因有两类
（夹具缺失 / 脚本硬编码 `/tmp`），落到驱动点上分三行（与前述判定口径一一对应）：

| 类别 | 数量 | 阻断点 | 日志证据 |
| --- | --- | --- | --- |
| testapp 调用因夹具目录不存在而中止 | 296 | `support/testapp: no such image directory as ...` | 该提示 **19 次**，涉及 19 个目录 |
| 脚本驱动因硬编码 `/tmp`（设备只读）而中止 | 6 | `binpatch.test.sh` 2 处、`test.create.ut.sh` 2 处、`test.create.private.un.sh` 2 处 | `can't create /tmp/<script>.<pid>...` 共 120 行，**仅来自这三个脚本**（45 / 30 / 45） |
| 脚本驱动因夹具缺失而中止 | 6 | `testy2k.sh` 4 处（`dconvert/gen` 2 + `dcfile` 2）、`testy2k.antodc.sh` 2 处（`dcfile`） | 这两个脚本**没有**任何 `/tmp` 错误行，只报 `no such image directory` |
| **合计** | **308** | | PASS 0、FAIL 0 |

其中 4 处脚本驱动**被测程序确实被调用过**（`binpatch.test.sh`），其 abort 原始输出
逐字保留在下方的日志留档中，可佐证这些用例不是静默跳过。

## 证据 1：夹具目录缺失与涉及的 19 个目录

`support/testapp` 的参数第 4 项就是镜像目录：

```
Usage: testapp testlist appname options imagedir testlogdir create|compare dump|cp|todc|ancp|filter
```

按 `testing in` 行归因，**合计 19 个目录**（早期版本误记为 17，漏了 `appsrc/acrnema`
与 `appsrc/dconvert/gen`）：

```sh
awk '/^testing in /{cur=$0} /no such image directory/{print cur}' upstream-make-test.log | sort -u | wc -l
# → 19
```

1. `appsrc/acrnema`
2. `appsrc/dcdisp`
3. `appsrc/dcfile`
4. `appsrc/dconvert/gaw`
5. `appsrc/dconvert/ge9800`
6. `appsrc/dconvert/gen`
7. `appsrc/dconvert/himr`
8. `appsrc/dconvert/imtn`
9. `appsrc/dconvert/pace`
10. `appsrc/dconvert/pq`
11. `appsrc/dconvert/shim`
12. `appsrc/dconvert/somp`
13. `appsrc/simple/ge9800`
14. `appsrc/simple/genesis`
15. `appsrc/simple/pace`
16. `appsrc/simple/signa`
17. `appsrc/simple/somatom`
18. `appsrc/simple/sytec`
19. `appsrc/simple/vision`

日志中该消息**合计出现 19 次**；其中指向 `images/acrnema` 的那一条具体行出现 **2 次**：

```sh
grep -c 'no such image directory' upstream-make-test.log                              # → 19（全部合计）
grep -c 'no such image directory as "../.././images/acrnema"' upstream-make-test.log  # → 2（单条示例）
```

`appsrc/dcfile/Imakefile` 中 `images/` 出现 214 次，`appsrc/acrnema/Imakefile` 20 次。

其他复算一致的计数：`grep -c 'Read-only file system'` → 47；`grep -c '^testing in'` → 66；
日志总行数 → 1076。

## 证据 2：夹具归档在官方站点不存在

`INSTALL` 原文（第 104–110 行，完整摘录见 `reports/upstream-test-probe.md` 第 6 节）：

> 4. To test the conversion routines, and some of the dicom and miscellaneous utilities,
> **if you have the sample images, which are distributed separately**, having set the PATH, correctly, do: `make test`

对上游归档命名规则做穷举探测（2026-09-11 实测，**原始 curl 响应码留档见
`reports/upstream-test-probe.md`**，未加工）：

| URL 形态 | 状态 |
| --- | --- |
| `https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20240118131615.tar.bz2` | 404 |
| `https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_test_1.00.snapshot.20240118131615.tar.bz2` | 404 |
| 上述两文件 `.tar.gz` 变体 | 404 |
| `https://www.dclunie.com/dicom3tools/dicom3tools/dicom3tools_{images,test}_<version>.{tar.bz2,tar.gz}` | 404 |
| `https://www.dclunie.com/dicom3tools/{images,test}/dicom3tools_{images,test}_<version>.{tar.bz2,tar.gz}` | 404 |
| 上述形态 + 20231221101722 / 20220120135102 / 20200418151316 / 20200101000000 四个历史日期 | 全部 404 |

站点索引同样没有：`workinprogress/index.html` 只有 **68 个源码快照**
（`dicom3tools_1.00.snapshot.<时间戳>.tar.bz2`）以及 `macexe/`、`winexe/` 两个可执行归档目录，
`grep -iE "image|test"` 命中 **0** 行；`dicom3tools/old/index.html` 只有 `dicom3tools_0.15.tar.gz`。

第三方镜像亦无：`fedorov/dicom3tools`（GitHub 上的 2004 年快照克隆）顶层只有
`appsrc config libsrc support` 与文档文件，无 `images/` 或 `test/`。
Debian/Ubuntu 打包 `dicom3tools` 时同样不运行上游 `make test`（仅构建二进制）。

## 证据 3：`make test` 不传递失败，退出码不能当通过证据

```sh
make ... test ; echo $?
# → 0
```

原因见上「`make test` 的退出码恒为 0」一段：顶层 `test::` 的 recipe 是
**`for i in $(SUBDIRS)` 循环，退出状态取末次迭代**，子目录失败不向上传递
（实测同轮 22 条 `*** Error` 与 `rc=0` 并存）。
注意 `@` 前缀只影响命令是否回显，**与退出码无关**。
因此 **退出码 0 不能作为上游测试通过的证据**。本 PR 未把该退出码记为 PASS，PASS 计为 0。

## 对适配结果的替代验证

上游测试不可执行属上游分发事实，与本包构建无关。本 PR 对**同一批已安装产物**做端到端验证：

| 测试 | 断言数 | 结果 | 证据 |
| --- | --- | --- | --- |
| `test_package/test.sh` | 22 | 22/22 PASS | `reports/test-package-evidence.md` |
| `reports/l2-consumer-test.sh` | 36 | 36/36 PASS | `reports/l2-consumer-test-evidence.md` |
| 合计（"鸿蒙特有测试"行） | 58 | 58/58 PASS | — |
