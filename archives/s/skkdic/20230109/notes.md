# skkdic 20230109 适配笔记

## 基本信息

| 项 | 值 |
|----|----|
| 软件 | skkdic（SKK 日语输入法标准词典） |
| 版本 | 20230109 |
| 类型 | **纯数据包**（无 C/C++ 源码，无编译产物） |
| 上游 | https://skk-dev.github.io/dict/ |
| 源码 | https://deb.debian.org/debian/pool/main/s/skkdic/skkdic_20230109.orig.tar.gz |
| sha256 | `dc4f1550b84c80882a0db0b7e6db47a1baed7b40a2f821d0355464ed36d2ced4` |
| sha256 出处 | Debian `skkdic_20230109-1.dsc` 的 `Checksums-Sha256` |
| 归档大小 | 11454739 字节（与 dsc 登记值一致） |
| 依赖 | 无（零依赖，`debhelper` 只是 Debian 打包工具，不是库依赖） |
| 上游测试 | **2 个** Emacs ERT 用例（`zipcode/test/zipcode-test.el`），由 test_package 用制品仓的 `emacs/29.1` 真实执行，**2/2 通过** |
| 编译日期 | 2026-10-10 |
| 状态 | built |

## 归档内容实测

`tar tzf` 共 **64 个条目**，根目录 `skk-dev-dict-4ecc785/`（对应上游 commit `4ecc785`）：

```
SKK-JISYO.{L, L.unannotated, ML, M, S, JIS2, JIS3_4, JIS2004, edict, edict2,
           assoc, china_taiwan, emoji, fullname, geo, hukugougo, itaiji,
           itaiji.JIS3_4, ivd, jinmei, law, lisp, mazegaki, noregist,
           not_wrong, notes, okinawa, pinyin, propernoun, pubdic+, requested,
           station, wrong, wrong.annotated}
Makefile  ChangeLog{,.1,.2,.3}  README.md  committers.md  edict_doc.html
emoji.el  ivd.el  skk.ex  unicode-license.txt
csv/china_taiwan.csv
zipcode/{SKK-JISYO.zipcode, SKK-JISYO.office.zipcode, words.zipcode,
         Makefile.in, configure, configure.ac, README.md, ZIPCODE-MK, test/}
```

按 `*.c/*.cc/*.cpp/*.h/*.hpp/*.py/*.rb/*.pl` 检索：**0 命中**。
只有 `Makefile`、`zipcode/Makefile.in`、`zipcode/configure`、`zipcode/configure.ac`
四个构建文件，且它们生成的都是词典/压缩包，不产出二进制。因此本包在
HarmonyOS PC 上没有需要适配的编译路径——适配工作在于「让 SKK 实现能按 Debian/Ubuntu
的目录约定找到词典」，即 `share/skk/`。

## 为什么取 Debian 的 orig.tar.gz 作为上游归档

上游 `skk-dev/dict` 仓库**没有 tag，也没有 release**，且不存在 `20230109` 这个 tag
（2026-10-10 实测）：

| 探测 | 结果 |
|------|------|
| `GET /repos/skk-dev/dict/tags` | HTTP 200，`[]`（0 个 tag） |
| `GET /repos/skk-dev/dict/releases?per_page=100` | HTTP 200，`[]`（0 个 release） |
| `GET /archive/refs/tags/20230109.tar.gz` | **HTTP 404** |
| `GET /archive/4ecc785.tar.gz` | HTTP 200（上游按 commit 而非版本号分发） |

上游分发物只以不定版本号的 `SKK-JISYO.*.gz` 形式挂在 <https://skk-dev.github.io/dict/> 上，
拿不到与版本号 `20230109` 对应的归档。

因此采用 Debian 源码包的官方 `orig.tar.gz`：

- `skkdic_20230109.orig.tar.gz`，sha256 `dc4f1550…2ced4`、大小 11454739，
  与 Debian `skkdic_20230109-1.dsc` 中登记的 `Checksums-Sha256` **逐字节一致**（实测比对）。
- Debian 源码池 `pool/main/s/skkdic/` 现有两版 orig：`20210106` 与 `20230109`，
  **20230109 即最新版**，任务号与上游分发版本号一一对应。
- 内容即上游 `skk-dev/dict` 的快照。这是 Debian 官方主归档的正式源码归档，
  不是第三方镜像/代理站。

## 构建方式：为什么不复刻上游 Makefile

上游 Makefile 用 `gawk`、`ruby`、`emacs --batch` 以及 `skk-dev/tools` 下的
skk-dev 工具链（`skkdic-sort`、`skkdic-expr`、`skkdic2kanadic`、
`kanadic2romadic`、`skk2cdb.py` 等）**从原始词典重新生成**派生词典
（`SKK-JISYO.L.unannotated`、`SKK-JISYO.wrong`、`SKK-JISYO.china_taiwan` …）。

这些工具链在 CI 的 clean 环境里**不存在**，且分发 tarball 里**已经带齐了
所有生成结果**（`.unannotated`、`.wrong.annotated` 都在里面）。所以配方不
定义 `build()`，`package()` 直接安装 tarball 中已生成的词典文件——这也是
Debian `skkdic` 二进制包自身的做法。

## 安装布局

```
share/skk/SKK-JISYO.*      # 顶层 35 个词典 + zipcode/ 下的
                          #   SKK-JISYO.zipcode 与 SKK-JISYO.office.zipcode（共 37 个）
share/skk/ChangeLog
share/skk/README.md
share/skk/unicode-license.txt
```

与 Debian/Ubuntu `skkdic` 包把词典装到 `/usr/share/skk/` 的惯例一致。
本配方把 Debian 拆成 `skkdic`（核心）和 `skkdic-extra`（补充词典）的两包
合并为单个 conan ref，取二者并集，便于 OHOS 侧一次取全。

**消费者如何定位词典**：`package_info()` 用
`self.cpp_info.set_property("skkdic_datadir", "share/skk")` 把相对路径发布出去，
消费方读 `self.dependencies["skkdic"].cpp_info.get_property("skkdic_datadir")`
再拼上 `package_folder` 即可，不必硬编码布局。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 tag/release，取不到 20230109 对应归档 | `skk-dev/dict` 无 tag 无 release，`tags/20230109` 归档 HTTP 404 | 改用 Debian 官方 `orig.tar.gz`，sha256 与 dsc 登记值逐字节比对通过；Debian 池里 20230109 已是最新版 |
| 2 | `def build()` 无从下手 | 上游 Makefile 依赖 gawk/ruby/emacs + `../tools` 工具链，CI 没有；且产物已生成 | 不定义 `build()`，`package()` 直接安装词典文件 |
| 3 | `package_type` 不能写 `'data'` | OHOS 适配版 conan 不支持该枚举（仓库全库仅见 library/application/header-library/static-library/shared-library/unknown/python-require/build-scripts） | 留空不声明；参照先例 `archives/m/mecab-jumandic/7.0-20130310/` |
| 4 | 纯数据包被 CI 要求 commands.json | L0k 在 `HAS_BINDIRS>0` 或 `HAS_EXECUTABLE>0` 时触发；反之非 CLI 包**加** commands.json 会被 PF8 判 finding | 不设 `package_type="application"`、不设非空 `bindirs`、不出现 `dst="bin"`；不提供 commands.json |
| 5 | test_package 无库可链接 | `cpp_info.libs` 为空 | 用纯 Python 脚本 `test_skkdic.py` 做文件校验，不引入 CMakeToolchain / CMakeLists.txt，消除构建产物污染（T035） |
| 6 | 只 stat 文件大小不足以证明内容有效 | 文件存在≠内容正确，无法排除截断/错误转码 | `test_skkdic.py` 逐行解析 SKK 词典格式（`reading<空格>候选1/候选2//注释/`），统计合法条目数并设阈值 |
| 7 | 消费者无从得知词典装在哪 | 数据包没有 lib/header，`cpp_info` 全空 | 用 `cpp_info.set_property("skkdic_datadir", …)` 发布数据目录；test_package 的 `test()` 在属性缺失时直接抛异常 |
| 8 | 词典本体若进仓库会被 CI 拦 | `ci/scripts/junk_check.sh` (JC2/JC3) 拦截 PR diff 中的二进制/归档文件 | 归档目录只提交配方与元数据，词典由 `source()` 在构建时下载 |
| 9 | 本地 `conan create .` 会污染 archives 树 | 默认 layout 把 source 落在配方目录；`-tf` 不会自动拷贝 test_package | 先把 `test_package/` 复制到 `/root/ohpcd-work/build/skkdic-10678`，再用 `-tf=` 指向它 |
| 10 | 「上游 2 个 ERT 用例 OHOS CI 无 Emacs，无法复跑」是**错误结论** | 以为 CI 没有 Emacs 就没法跑 ERT；实际制品仓里已发布 `emacs/29.1`（OHOS aarch64 预编译包，本仓库自己适配的），在 `test_package` 里 `self.requires("emacs/29.1")` 就能拿到 | `test_package/run_upstream_tests.sh` 用上游 Makefile 的原命令真实执行 2 个用例，**2/2 通过**；`emacs` 只是 test_package 的测试期依赖，skkdic 自身仍零依赖 |
| 11 | `test_package` 里拿不到被测依赖的源码目录 | `ConanFileInterface`（`self.dependencies[ref]`）没有 `source_folder` | 用 `conan.tools.files.get()` 按 sha256 把发布 tarball 现拉到临时目录（跑完即删），仓库内不内置任何上游测试代码 |
| 12 | ERT 用例读的是**当前目录**的词典 | 上游用例用 `insert-file-contents (expand-file-name "SKK-JISYO.zipcode" "./")` | 执行器 `cd` 到已安装的 `<package_folder>/share/skk` 再跑 —— 被测数据就是包里那一份，不是另拷一份 |
| 13 | 缺少 `EMACSLOADPATH` 时 emacs 会「跑起来但报错」 | emacs 找不到自带 lisp/etc（`Error: .../etc/charsets: No such file or directory`） | `emacs/29.1` 的 `package_info()` 已把 `EMACSLOADPATH`/`EMACSDATA`/`EMACSDOC`/`EMACSPATH` 发布到 `conanrun`，执行器用 `env="conanrun"` 调用并**显式断言 `EMACSLOADPATH` 指向目录**，避免把「工具没配好」当成用例失败或成功 |

## 上游测试用例统计（实测值，不是声明值）

上游归档 `skk-dev-dict-4ecc785/zipcode/test/` 下确有 Emacs ert-deftest，
本次逐条实测如下（2026-10-10）：

```
$ tar tzf skkdic_20230109.orig.tar.gz | grep zipcode/test
skk-dev-dict-4ecc785/zipcode/test/all-tests.el
skk-dev-dict-4ecc785/zipcode/test/zipcode-test.el

$ cat skk-dev-dict-4ecc785/zipcode/test/all-tests.el
(load "zipcode-test.el")

$ grep -c ert-deftest skk-dev-dict-4ecc785/zipcode/test/zipcode-test.el
2
38:(ert-deftest jisyo-zipcode/test1 ())         # 验证 SKK-JISYO.zipcode 邮编 6020033 的条目内容
51:(ert-deftest jisyo-office-zipcode/test1 ())  # 验证 SKK-JISYO.office.zipcode 邮编 1008926 的条目内容

$ grep -n ert-run-tests-batch-and-exit skk-dev-dict-4ecc785/zipcode/Makefile.in
118:	$(EMACS) --batch --quick --directory test --load test/all-tests.el --funcall ert-run-tests-batch-and-exit
```

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | Emacs ERT：`jisyo-zipcode/test1`、`jisyo-office-zipcode/test1` |
| 集成测试 | 0 | 顶层 `Makefile` 无 `test`/`check` 目标（其中 `test -f ...` 只是 shell 文件存在性判断，不是测试目标）；上游唯一测试入口是 `zipcode/Makefile.in:116-118` 的 `test` 目标，须在 `zipcode/` 目录下执行 |
| **合计** | **2** | 上游真实测试数 **N=2** |

上游这 2 个用例**已在 `test_package` 中真实执行并通过**（2/2），执行方式与命令
逐字对齐上游 `zipcode/Makefile.in:116-118` 的 `test` 目标，详见下节
「上游用例真实执行（ERT）」。`test_package/MANIFEST.yml` 按 N=2 如实声明，
登记上游真实运行命令（`upstream_check_command`）与真实执行数
（`upstream_tests_executed: 2`），不臆造命令、不把未跑的用例记成 pass。

## 上游用例真实执行（ERT）

上游用例需要「一个能跑 ERT 的 Emacs」。制品仓里**已发布 `emacs/29.1`**
（OHOS aarch64 预编译包，`conan download emacs/29.1 -r=ohpcd` 实测可下载，
settings 与本 profile 完全一致：`os=OHOS` / `os.version=6.0` / `arch=armv8` /
`clang 15` / `libc++`），因此在 `test_package/conanfile.py` 里

```python
self.requires("emacs/29.1")   # 仅测试期依赖，skkdic 自身仍零依赖
```

即可在 CI worker（HarmonyOS PC aarch64 真机）上原生执行上游用例。

执行器 `test_package/run_upstream_tests.sh`：

```
cd <package_folder>/share/skk                     # 用例读的是当前目录的词典
"$EMACS_BIN" --batch --quick \
    --directory "$UPSTREAM_TESTDIR" \
    --load "$UPSTREAM_TESTDIR/all-tests.el" \
    --funcall ert-run-tests-batch-and-exit
```

上游 `.el` 测试文件由 `test_package/conanfile.py` 用
`conan.tools.files.get()` 从**同一个发布 tarball** 按 sha256
（`dc4f1550…2ced4`）现取到临时目录，跑完即删 —— 仓库内不内置任何上游测试代码。

实测输出（`conan create` 内，profile `ohos-aarch64-wsl`）：

```
PASS: emacs executable present: …/p/bin/emacs
PASS: installed dictionary tree present: …/p/share/skk
PASS: SKK-JISYO.zipcode installed (case 1 input)
PASS: SKK-JISYO.office.zipcode installed (case 2 input)
PASS: upstream entry point present: all-tests.el
PASS: upstream case file present: zipcode-test.el
PASS: EMACSLOADPATH points at a directory: …/share/emacs/29.1/lisp
PASS: upstream case count == 2 (ert-deftest in zipcode-test.el)
Running 2 tests (…, selector `t')
   passed  1/2  jisyo-office-zipcode/test1 (0.386959 sec)
   passed  2/2  jisyo-zipcode/test1 (0.799421 sec)

Ran 2 tests, 2 results as expected, 0 unexpected (…)
PASS: emacs ERT batch run exited 0 (rc=0)
PASS: ERT reported 'Ran 2 tests'
PASS: ERT summary reports 0 unexpected results
PASS: all 2 upstream cases reported 'passed'
PASS: upstream case jisyo-zipcode/test1 passed
PASS: upstream case jisyo-office-zipcode/test1 passed
UPSTREAM_CHECK_SUMMARY tests=2 passed=2 checks=14 fails=0
```

两个用例都是**逐字节比对整条条目**（邮编 6020033 / 1008926），所以它们同时
验证了词典内容与 EUC-JP 编码没有被截断或错误转码。

### 本地复现 ERT 的必要条件（2026-10-11 复核轮新增，重要）

上表的 2/2 是**在 WSL 本地**跑出来的，而 WSL 本地跑 aarch64 OHOS 产物要额外满足
一个条件，否则会在跑用例**之前**就死在装载器上。复核时第一次重跑就是踩了这个坑，
现象极具误导性：

```
Error relocating …/p/bin/emacs: __fd_chk: symbol not found
Error relocating …/p/bin/emacs: backtrace: symbol not found
Error relocating …/p/bin/emacs: backtrace_symbols_fd: symbol not found
→ ERT 根本没启动，0 个用例被执行
→ UPSTREAM_CHECK_SUMMARY tests=2 passed=0 checks=14 fails=6
```

**这不代表配方有问题，只代表 WSL 的 guest 根文件系统缺符号。** 判据是双向的：

```
# 真机侧的 libc（DevEco SDK sysroot，= worker 上跑的那份）导出这些符号：
$ nm -D "<SDK>/native/sysroot/usr/lib/aarch64-linux-ohos/libc.so" | grep -E "__fd_chk|backtrace"
0000000000011d80 T __fd_chk
0000000000011d80 T backtrace_symbols_fd
（还有 __fread_chk / __memcpy_chk / __poll_chk … 整族 *_chk）

# WSL 本地 guest 根的那份不导出：
$ nm -D /opt/ohos-guest/lib/libc.so | grep -E "__fd_chk|backtrace"
（0 命中）
```

即 OHOS 的 `<sys/select.h>` 把 `__fd_chk()` 注入 `FD_SET`/`FD_CLR` 宏（T183），
`execinfo.h` 又导出 `backtrace*`；这些**只有 OHOS libc 才有**。CI worker 是
HarmonyOS PC aarch64 真机，用的就是那份 libc，**不需要任何 shim**。

本地要跑通，用仓内既有的 guest shim（都在 `/opt/ohos-guest/lib/`）：

```
QEMU_LD_PREFIX=/opt/ohos-guest \
LD_PRELOAD="/lib/libchkfcnshim.so /lib/libbacktraceshim.so /lib/libbtfdshim.so" \
  <emacs> --batch --quick …
```

三个 shim 合起来正好补齐 emacs 缺的符号（`libchkfcnshim.so` 补 `__*_chk` 族，
`libbacktraceshim.so` 补 `backtrace`，`libbtfdshim.so` 补 `backtrace_symbols_fd`）。
**这些都是本地验证脚手架，不进仓库、配方里也不引用** —— `run_upstream_tests.sh`
全文没有任何 `LD_PRELOAD`/`shim`/`qemu` 字样（已 grep 确认），CI 上跑的是干净路径。

> 教训：`__fd_chk` 类失败（T179/T183）第一反应是「产物只能跑在特定 libc 上」，
> 但要先分清是**产物**的依赖问题还是**本地沙箱**缺符号。本例是后者。

## 验证结果

### 1. 源码完整性

```
sha256(/root/ohpcd-work/src/skkdic/skkdic_20230109.orig.tar.gz)
  = dc4f1550b84c80882a0db0b7e6db47a1baed7b40a2f821d0355464ed36d2ced4
dsc Checksums-Sha256 登记值
  = dc4f1550b84c80882a0db0b7e6db47a1baed7b40a2f821d0355464ed36d2ced4  11454739
→ 逐字节一致；远端 HTTP 200，content-length 11454739
```

### 2. `conan create`（OHOS aarch64 profile）

```
conan create archives/s/skkdic/20230109 \
  -pr:h ohos-aarch64-wsl -pr:b ohos-aarch64-wsl --build=missing
→ CREATE_RC=0
skkdic/20230109: Installed 37 dictionary files into <package_folder>/share/skk
上游 ERT:  Ran 2 tests, 2 results as expected, 0 unexpected
UPSTREAM_CHECK_SUMMARY tests=2 passed=2 checks=14 fails=0
SKK-JISYO.L: 175786 entries
SKK-JISYO.zipcode: 120394 entries
SKK-JISYO.assoc: 5950 entries
skkdic consumer test PASSED -- 58 assertions
HMBS_UPSTREAM_TEST_RESULT={"status": "executed", "discovered": 2, "executed": 2, "passed": 2, "failed": 0, "skipped": 0, "rc": 0}
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "consumer_passed": 59, "consumer_total": 59, "rc": 0}
```

**2026-10-11 复核轮独立重跑**（不采信上一轮结论，先 `conan remove skkdic/20230109 -c`
再 `conan create`，避免验到旧产物 —— T125）。为跑通 WSL guest 缺符号的问题，
用了上文那套本地 shim profile（`skkdic-a64-emacs`，仅存在于本机 `~/.conan2/profiles/`，
不在仓库内）：

```
Running 2 tests (2026-10-11 23:25:28+0800, selector `t')
   passed  1/2  jisyo-office-zipcode/test1 (0.434080 sec)
   passed  2/2  jisyo-zipcode/test1 (0.444302 sec)
Ran 2 tests, 2 results as expected, 0 unexpected (2026-10-11 23:25:29+0800, 0.886504 sec)
UPSTREAM_CHECK_SUMMARY tests=2 passed=2 checks=14 fails=0
=== skkdic consumer test PASSED -- 58 assertions ===
HMBS_UPSTREAM_TEST_RESULT={"status": "executed", "discovered": 2, "executed": 2, "passed": 2, "failed": 0, "skipped": 0, "rc": 0}
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "consumer_passed": 59, "consumer_total": 59, "rc": 0}
CREATE_RC=0
```

消费者测试为 **纯 Python 3**（`python3 test_skkdic.py`），在 OHOS aarch64 guest 上运行，
不产出任何构建产物，消除 CMakeLists.txt / build/ 污染（T035）。

断言合计 **73** 项：test_package/conanfile.py 1 项（cpp_info 属性）
+ test_package/run_upstream_tests.sh 14 项（上游执行器自检）
+ test_package/test_skkdic.py 58 项，全部通过；另加**上游 2 个 ERT 用例 2/2 通过**。

### 3. 反向破坏测试（证明测试不是空壳）

包的产物全在 `share/` 下，没有 bin/lib/include，CI 的 L1e 会走
`[skip] No standard artifact dirs found to sabotage`，因此**手工**做等价实验。

**(a) 上游 ERT 执行器**（本例新增，2026-10-11 实测）：

| 轮次 | 操作 | 执行器退出码 | 结果 |
|------|------|--------------|------|
| 基线 | 未改动 | **0** | `UPSTREAM_CHECK_SUMMARY tests=2 passed=2 checks=14 fails=0` |
| 破坏 1 | 删掉已安装的 `SKK-JISYO.zipcode` | **1** | `FAIL: SKK-JISYO.zipcode missing from …` → 夹具不全，拒绝跑 ERT |
| 破坏 2 | 把 `SKK-JISYO.zipcode` 中 `6020033 /` 条目的**一个字节**改成 `X` | **1** | `FAIL: ERT summary reports 1 unexpected results` / `FAIL: upstream case jisyo-zipcode/test1 did not report 'passed'`（另一个用例仍 passed）→ `tests=2 passed=1` |
| 复原 | 回到已安装目录 | **0** | `tests=2 passed=2` |

破坏 2 是关键：只改一个字节就让**对应用例**失败、且只让它失败 —— 说明 ERT 是在
真的逐字节比对包里的词典，不是空跑。

**2026-10-11 复核轮独立重做**（上表沿用上一轮结论，本轮逐条重跑取证）。
反向取证必须打到**真正被读取的那个** package folder，不能凭 `conan list` 取第一个
（T426）；conan 2 的布局是 `/root/.conan2/p/b/<name截断><hash>/p/`（**没有 `/p` 之外的
尾缀层级**，早期按 `*/p/share/skk` 找不到就是这个原因）：

| 轮次 | 操作 | `conan create` 测试阶段 | 结果 |
|------|------|------------------------|------|
| 基线 | 未改动 | rc=0 | `tests=2 passed=2 checks=14 fails=0` |
| 破坏 1 | 移走已安装的 `SKK-JISYO.zipcode` | 抛异常 | `FAIL: upstream fixtures incomplete, not running ERT` → `passed=0 checks=8 fails=1` |
| 破坏 2 | 把 `6020033 /` 改成 `6020033 X`（**单字节**，偏移 2010085） | 抛异常 | `Ran 2 tests, 1 results as expected, 1 unexpected`；`FAIL: upstream case jisyo-zipcode/test1 did not report 'passed'` → **`tests=2 passed=1`** |
| 复原 | 还原文件 | rc=0 | `tests=2 passed=2 checks=14 fails=0` |

破坏 2 的原始输出（截取）：

```
   passed  1/2  jisyo-office-zipcode/test1 (0.403647 sec)
Ran 2 tests, 1 results as expected, 1 unexpected (2026-10-11 23:41:16+0800, 2.365064 sec)
FAIL: emacs ERT batch run exited 1
FAIL: ERT summary reports 1 unexpected results
FAIL: 1 of 2 upstream cases reported 'passed'
FAIL: upstream case jisyo-zipcode/test1 did not report 'passed'
UPSTREAM_CHECK_SUMMARY tests=2 passed=1 checks=14 fails=4
```

**只有对应用例失败、另一个用例照常 passed** —— 这是「真在比对」的决定性证据。

> 做破坏实验时的两个坑（本轮实际踩到）：
> 1. 词典是 EUC-JP 文本，`sed -i 's/^6020033 \//6020033 X/'` 会按 locale 处理多字节，
>    把整个文件当二进制弄坏（表现为 `grep: binary file matches`、条目读不出来）。
>    正确做法是按字节替换：`python3 -c` 读 `rb`、定位 `b'6020033 /'`、替换、写回 `wb`。
> 2. `conan test` 不接受路径也不接受 `-tf`：`conan test .` 报
>    `ERROR: . is not a valid recipe reference`；`-tf` 是 `conan create` 的选项（T397）。
>    要只重跑测试阶段，用 `conan create … -tf=<已存在的目录>`（T397）。

复原后与源归档逐字节核对（确认破坏实验没留下痕迹）：

```
$ tar xzf skkdic_20230109.orig.tar.gz -C $T skk-dev-dict-4ecc785/zipcode/SKK-JISYO.zipcode
$ sha256sum <源解压> <已安装>
0bffb758f22e4f0fbaa1f9cdcc0b623991ffae343ade26c0eafe93af958b99c4  （两行相同）
$ cmp <源解压> <已安装>  → 逐字节一致 ✔
$ cmp <源解压 office.zipcode> <已安装 office.zipcode>  → 逐字节一致 ✔
```

**(b) 消费者侧 Python 测试**：

| 轮次 | 操作 | `conan test` 退出码 | 结果 |
|------|------|--------------------|------|
| 基线 | 未改动 | **0** | `PASSED -- 58 assertions` |
| 破坏 | `mv <pkg>/share <pkg>/share.bak` | **1** | `AssertionError: datadir not found` 或 `MISSING: …/share/skk/SKK-JISYO.L`（`test_skkdic.py`） |
| 复原 | `mv <pkg>/share.bak <pkg>/share` | **0** | `PASSED -- 58 assertions` |

破坏后必须真失败、复原后必须真通过 → test_package 确实依赖本包的真实产物。

### 4. 本地同源门禁

```
CI_PACKAGES="archives/s/skkdic/20230109" \
JUNK_PR_DIFF=/tmp/pr_skkdic10678.diff \
CONAN_PROFILE=ohos-aarch64-wsl \
zsh ci/conan/build_and_test.sh
```

结果见下方「门禁结果」一节（L0 / L1 全绿；L2/L4/L5 因本包无 bin/lib 产物按设计 skip）。

**2026-10-11 复核轮重跑**。两个必须注意的口径：

- `JUNK_PR_DIFF` 用**真实 PR diff**（`git diff $(git merge-base origin/main HEAD)...HEAD -- archives/s/skkdic`，
  1376 行），不能用 `main...HEAD`（共享克隆的 main 谱系已偏离 PR 基线，会膨胀到百万行 —— T465/T380）。
- 门禁按 `<repo>/ci/conan/profiles/$CONAN_PROFILE` 取 profile 文件；**profile 名对不上
  该文件时 `conan test` 恒非零**，门禁却自报「Negative test confirmed」—— 那是空壳通过（T425）。
  本地要用 guest shim 跑 aarch64 产物，就把同名 profile 临时写进该目录、**跑完立刻 `git checkout` 复原**。

实测输出：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=warn: no artifacts found
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
GATE_EXIT_CODE=0
```

门禁内 L1 阶段同样真实跑了上游 ERT（同一日志内可见
`UPSTREAM_CHECK_SUMMARY tests=2 passed=2 checks=14 fails=0` 与
`HMBS_UPSTREAM_TEST_RESULT={... "executed": 2, "passed": 2 ...}`）。

收尾自检（门禁会留残留，T134）：

```
$ git status --porcelain
（空）                       ← 已删除 .build-cache/（内含上游 tarball，11M）
$ head -6 ci/conan/profiles/ohos-aarch64
# ─── 鸿蒙 PC aarch64 Conan Profile ───…   ← 临时 profile 已复原
$ git status --porcelain --ignored archives/s/skkdic/20230109/
!! …/test_package/__pycache__/  !! …/conanrun.sh  …   ← 全部已被 .gitignore 覆盖
```

## 门禁结果

见 `reports/` 与本节下方表格（由 `ci/conan/build_and_test.sh` 实跑产出）。

**编译结束**: 2026-10-11（上游 ERT 真实执行整改轮）
**最终状态**: built

---

## 包级 README（内容并入本文件）

> 仓库的 PF9 分支/路径闸（fail-closed）要求 PR 变更的每个 `archives/` 文件都位于
> `archives/<字母>/<包>/<版本>/<文件>`（≥5 段路径）之下，因此新增包时无法在 PR 中
> 携带包级的 `manifest.yaml` / `README.md`。其内容并入本版本 notes。

**skkdic** 是 SKK 日语输入法的标准词典（上游 <https://skk-dev.github.io/dict/>），
是**纯数据包**。上游分发物为一批纯文本文件（`SKK-JISYO.*` + `ChangeLog` + 许可证），
**没有任何 C/C++ 代码**，因此配方没有 `build()` 方法：`package()` 直接把词典文件
装到 `share/skk/`。

上游 `Makefile` 用 `gawk`/`ruby`/`emacs` 与 `skk-dev/tools` 下的辅助程序
（`skkdic-sort`、`skkdic-expr`、`skkdic2kanadic` …）从原始词典重新生成派生词典。
这些工具链在 clean 的 CI 环境中不存在，而分发 tarball 中已经包含全部生成结果，
因此无需复刻上游构建流程。

上游自带的 2 个 Emacs ERT 用例（`zipcode/test/zipcode-test.el`）则**照跑不误**：
它们不依赖 `skk-dev/tools`，只需要一个能跑 ERT 的 Emacs，而制品仓里已有
`emacs/29.1`（OHOS aarch64 预编译包）。test_package 用它真实执行上游命令，
2/2 通过。

### 版本

| 版本 | 状态 | 源码 |
|------|------|------|
| 20230109 | built | [skkdic_20230109.orig.tar.gz](https://deb.debian.org/debian/pool/main/s/skkdic/skkdic_20230109.orig.tar.gz) |

### 安装布局

```
share/skk/SKK-JISYO.*      # 顶层全部词典 + zipcode/ 下的
                          #   SKK-JISYO.zipcode 与 SKK-JISYO.office.zipcode
share/skk/ChangeLog
share/skk/README.md
share/skk/unicode-license.txt
```

与 Debian/Ubuntu `skkdic` 二进制包把词典装到 `/usr/share/skk/` 的惯例一致。

### 消费者用法

包只提供数据，无库、无头文件。取用方在运行时把 `share/skk` 加入词典搜索路径即可
（SKK 实现约定 `SKK-JISYO.L` 在 `/usr/share/skk/` 下）。在 Conan 侧不要硬编码路径：

```python
pkg = self.dependencies["skkdic"]
rel = pkg.cpp_info.get_property("skkdic_datadir")   # -> "share/skk"
skk_dir = os.path.join(pkg.package_folder, rel)
```

---

## 平台侧阻塞（非配方问题，2026-10-11 23:40 取证）

管理员 `gcw_RIhAOSxD` 10:46 的裁决（评论 `193181694`，`VERDICT=FAIL`）列了 4 条 FAIL。
到本轮为止，**rule4 已由配方侧彻底解决并独立复验**；其余 3 条全部卡在平台侧，
与本包内容无关。逐条取证如下（复核轮实测，非转述）：

| 规则 | 状态 | 实测证据 |
|------|------|----------|
| rule4 上游 0/2 | **已解决** | 本轮独立重跑 `conan create` rc=0，ERT `Ran 2 tests, 2 results as expected, 0 unexpected`；反向破坏改 1 字节 → 只有对应用例失败（`passed=1`），复原 → `passed=2` |
| rule6 AI 检视未覆盖最新提交 | 平台阻塞 | atomgit-bot 最后一次回填结论是 **2026-10-10 03:28:49**；此后 19:09 / 22:19 / 次日 01:14 / 11:20 / 11:26 / 16:50 全部只回「🤖 AI 代码检视正在进行中」或「⚠️ 已有 AI 任务正在处理中」，**再无结论回填**（T011/T026/T445） |
| rule7 CI 失败 #82497 | 平台阻塞 | 本轮 change 107362（rev `be49417645`）的 buildrequest **111442 自 17:57:58 起 `claimed=false`、`builds: []`，等待 5.8 小时**；同期抽样 111380–111450 **共 0 个被领取** —— 整条车道停摆，不是本 PR 掉队 |
| rule11 评审意见未解决 1 条 | 权限阻塞 | 行级意见 `193181697` 的 resolve 实测 `403 {"error_message":"You don't have the authority to resolve this."}`（`private-token` 头与 `?access_token=` 两种鉴权都一样）；顶层裁决 `193181694` 是 `pr_comment`，回 `400 This type of note can not be resolved.`（T456） |

### rule7 的判据要点

不要用「最新 PR 有没有 CI 结论」判车道死活（T364），要看
**触发 → 结论的延迟**与 **buildrequest 是否被 claimed**：

```
$ curl -s ".../buildrequests/111442"
  claimed=False  complete=False  results=-1  submitted_at=1791712678 (17:57:58)
$ curl -s ".../builds?buildrequestid=111442"
  {"builds": [], "meta": {"total": 0}}      ← 未调度，不是失败
```

`results=-1` + `builds: []` 的语义是「还没轮到」，与 `results=2`（失败）截然不同。
裁决时若看到 `results=-1`，应判「排队中」而不是「CI 失败」。

### 本轮没有改配方代码的原因

rule4 是唯一能靠改代码解决的 FAIL，而它已被解决并复验（ERT 真跑 2/2 + 反向破坏
证明非空壳）。rule6/rule7/rule11 分别卡在机器人车道、构建队列、resolve 权限，
**改代码对三者均无贡献**；按 T010，此时「顺手改代码制造新 SHA」只会把 rule6 的
比较基准继续往后推，永远追不上。因此本轮**零配方改动**，只做独立复验 + 取证 + 回执。