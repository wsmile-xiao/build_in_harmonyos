# pipemeter 1.1.5 适配笔记

## 编译环境
- 构建系统: autotools（autoconf `configure` + 手写 `Makefile.in`，**无 automake**）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4（OHOS 原生 `/data/service/hnp/bin/clang`，profile `ohos-aarch64`）
- 平台: HarmonyOS / OpenHarmony PC aarch64，musl libc，HongMeng Kernel 1.12.0
- 状态: built（conan-verify 全门禁通过，待发布流水线 upload）

## 上游与源码核验

| 项 | 结果 |
|---|---|
| 官方发布页 | https://launchpad.net/pipemeter/trunk/1.1.5 （HTTP 200） |
| 源码 URL（R39 官方源） | `https://launchpad.net/pipemeter/trunk/1.1.5/+download/pipemeter-1.1.5.tar.gz` → 实际落地 `launchpadlibrarian.net/516365027/pipemeter-1.1.5.tar.gz`（HTTP 200） |
| tarball sha256 | `e470ac5f3e71b5eee1a925d7174a6fa8f0753f2107e067fbca3f383fab2e87d8`（149052 B） |
| tarball 文件数 | 21（含 autom4te.cache 5 个） |
| 源码构成 | `pipemeter.c` 904 行单文件 + `configure`(autoconf 2.59+ 生成) + `configure.in` + `Makefile.in` + `install-sh` + man/spec/脚本 |
| 许可证 | GPL-2.0-or-later（`LICENSE` 为 GPL-2 正文，`pipemeter.c` 头注释 "either version 2 ... or any later version"） |
| 语言预检（R47） | `detected_language=c`（源文件 1 个 c，占比 100%）↔ 任务语言 cpp 兼容族 → PASS |
| 历史归档（W0b） | `grep -ril pipemeter archives knowledge` 无命中 → 本仓库首次适配，无历史 notes 需比对 |
| ConanCenter | `recipes/pipemeter/` 不存在（HTTP 404）→ 无上游社区配方参考 |
| cmd-pkgs 预编译索引（R18） | 无同名包 |

## 依赖核验（W0 / R35 / R36）

`configure.in` 的 `# Checks for libraries` 段为空；`configure` 里唯一的库探测是
`checking for pow in -lm`（结果存入 `POW_LIB`，而 **`Makefile.in` 从不引用 `@POW_LIB@`**，
`LDFLAGS=@LDFLAGS@ @LIBS@` 中 `LIBS` 未被追加 `-lm`）。因此 pipemeter 的链接需求只有
OHOS musl sysroot 提供的 libc（+ clang 内建解析的 `pow`）。

- **Conan 依赖集合 = 空**（`requirements()` 为 `pass`）→ 不存在必选依赖不可消费的 R36 阻塞。
- registry 通道本身已用对照组实测可用：`conan download zlib/1.3.1 -r=ohpcd --only-recipe` → exit 0（拉到 revision `2ee7c0eeb8f4dfef8982d0c5c1551a61`）。
- `preflight_check.sh pipemeter/1.1.5` → "预检通过（无依赖需要检查）"。
- 全程未使用 `--build=missing` 绕过、未使用本地缓存顶替缺失依赖。

## 编译步骤（实际执行顺序）

```sh
# 探索阶段（模式 B，原生 OHOS 工具链）
export CC=clang CXX=clang++ CFLAGS="-fPIC -O2"
./configure --prefix=/storage/Users/currentUser/usr/local     # 首轮失败，见问题 #1
make -j2                                                       # 通过
make install DESTDIR=$TEST_PREFIX                              # 首轮失败，见问题 #2
sh ./testscript.sh                                             # 上游测试，见「上游测试」节

# Conan 阶段
conan create archives/p/pipemeter/1.1.5 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 现象（首个错误原文） | 根因 | 解决方案 | 重新验证 |
|---|---|---|---|---|
| 1 | `./config.status[693]: can't create ./confBJIjCa/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（configure exit 1） | HMDFS 忽略 `umask`/`chmod`：`(umask 077 && mktemp -d ./confXXXXXX)` 出来的目录权限归一化为 `drwx--S---`(2700)，属主同样无法在其中建文件（实测 `echo x > confGfPAbL/subs1.awk` → Permission denied）。知识图谱 **E114** 命中（推荐方案 bypass-mktemp） | `patches/0002-configure.patch`：把 mktemp 引导换成 `tmp=./conf$$-ohc; mkdir -p "$tmp"`，fallback 分支同样改 `mkdir -p`（普通 `mkdir -p` 实测可写） | `./configure` exit 0，生成 Makefile/config.h/config.status；`config.status Makefile` 复跑 exit 0；`grep mktemp configure` 无残留 |
| 2 | `make: install: No such file or directory` / `Makefile:27: install] Error 127`（make install exit 2） | OHOS 无可用 `install`：`/bin` 不在 PATH（PATH 只有 `/usr/bin`、`/vendor/bin` 等）；`/bin/install` 是 toybox 0.8.12 applet，实测 **不支持 GNU `-D`/`-t`**（`install: -D '/tmp/x': Read-only file system`），且 `/tmp` 只读（E002） | `patches/0001-Makefile.in.patch`：安装规则改用 tarball 自带的 autoconf 可移植脚本 `install-sh` —— `sh ./install-sh -d <dir>` + `sh ./install-sh -c -m 755/644 <src> <dst>`（先实测 `install-sh` 在 OHOS 可正常建目录、装文件且产物可执行） | `make install DESTDIR=$TEST_PREFIX` exit 0，staging 出现 `…/usr/local/bin/pipemeter` 与 `…/man/man1/pipemeter.1`，二进制执行输出 `pipemeter v1.1.5` |
| 3 | `make: *** No rule to make target 'pipemeter.c', needed by 'pipemeter'. Stop.`（conan create 的 `autotools.make` exit 2） | 上游 `Makefile.in` 是手写的，没有 VPATH 也没有 `@srcdir@`；conan2 `basic_layout` 把 build 目录与 src 目录分开，configure 在 build 目录里生成的 Makefile 找不到同级的 `pipemeter.c`。同型先例：`bandwidthd/2.0.1-cvs20090917`、`audtty/0.1.12` | 配方 `layout()` 里 `basic_layout(self)` 之后追加 `self.folders.build = self.folders.source` 强制 in-tree 构建 | 重跑 conan-verify：G2 PASS，产物 `bin/pipemeter` + `man/man1/pipemeter.1` + `licenses/LICENSE` |

## 源码修改

两个补丁均由 `ohc-run.py refresh-patch --auto pipemeter 1.1.5` 生成（R1），
**不含任何 `__OHOS__` 平台宏**（R8 / PF5），不引入 `/usr/local` 等共享前缀字面量（R49 / PF6）：

- `patches/0001-Makefile.in.patch`（+5/−3，portability）— install 规则改走 `install-sh`
- `patches/0002-configure.patch`（+3/−2，portability）— `mktemp -d` 换 `mkdir -p`

未改动 `pipemeter.c`（源码零介入，6 条 clang warning 全部是上游既有代码风格问题，
不涉及 OHOS 正确性：`-Wpointer-to-int-cast` / `-Wparentheses` 各 1 处（第 577 行 fgets 赋值）、
`-Wswitch` 3 处 + `-Wtautological-constant-out-of-range-compare` 1 处（`case -1` 与 `char` 比较）。
按「bug 修复不需要清理周围代码」原则不做顺手修改）。

## 发现与知识

本次 4 个障碍全部命中知识图谱既有条目（R30 命中即复用，R31 未命中才需草稿 → 本次无需新增草稿）：

- ✅ HMDFS 忽略 umask/chmod，`mktemp -d` 临时目录属主不可写，configure 崩在 `could not setup config files machinery` → 知识图谱 E114（方案 bypass-mktemp），已按处方落 `patches/0002-configure.patch` 复验通过
- ✅ OHOS 无可用 `install`（`/bin` 不在 PATH + toybox install 无 GNU `-D`/`-t`），`make install` 退 127 → 知识图谱 E174（方案 manual-install / makefile-patch），本次取 makefile-patch 改走包内 `install-sh`，落 `patches/0001-Makefile.in.patch`
- ✅ 手写 `Makefile.in` 无 VPATH/@srcdir@，conan2 `basic_layout` out-of-tree 构建报 `No rule to make target 'pipemeter.c'` → 知识图谱 E519，配方 `self.folders.build = self.folders.source` 强制 in-tree（同型先例 bandwidthd/2.0.1-cvs20090917、audtty/0.1.12）
- ✅ OHOS toybox applet 不支持 GNU 长/扩展选项 → 知识图谱 E402 同族（该条目记录 toybox gzip 不认 `--force`）；本次实证补充 `/usr/bin/time` 只支持 `-p`/`-v`，上游 `testscript.sh` 依赖的 `-a`/`-o` 全部失效且静默（除开头 `[ ! -x ./pipemeter ] → exit 1` 守卫外无任何失败判定，计时报错不改退出码），须按步骤用 `time -p … 2>>file` 等价实跑
- ✅ pipemeter 在 elapsed < 1 s 时速率列显示 `-1.00B/s` 而字节计量列仍精确无误 → 上游显示行为（`avg_bytes()` 除法窗口），非 OHOS 缺陷；拉长样本到 >1 s 后速率正常（12.00M/s / 10.67M/s），排查此类现象应先看字节计量列而非速率列
- ✅ finish Step 3 的 G0 干净构建验证（不走 conan，直接在 `$TMPDIR` 解压后跑原生 `./configure`）在 OHOS 上必然失败：`shell-init: error retrieving current directory: getcwd: cannot access parent directories` → `configure: error: working directory cannot be determined` → 知识图谱 **E386**（HMDFS getcwd 平台限制）。该步在 SKILL 中为非阻塞；本包的权威构建路径 `conan create`（G2 + W3 本地 CI 模拟）已 3 次实跑通过，不受影响。若要让原生 configure 也能跑，需按 E386/nmh 先例把工作根迁到 `/data/storage/el2/base`
- ✅ 本地 W3 的 junk_check 在无 commit 的开发分支上会 fallback 到 full 模式扫全仓，从而被 main 上存量的他人目录违规文件（`archives/u/util-linux-login/2.42.2/.ci-trigger`，JC5 未登记隐藏文件）误伤；与 CI 同源的权威口径是 PR 文件清单（`JUNK_PR_DIFF` prdiff 模式）→ 已用 prdiff 模式复验 JC1–JC6 全 pass、涉及软件数 1

## 上游测试（R51 三步法）

### 第 1 步：清点

| 检查项 | 结果 |
|---|---|
| `tests/` 目录 | 不存在 |
| `make check` 目标 | 不存在（`Makefile.in` 只有 all/debug/clean/distclean/install/dist） |
| CTest / automake `TESTS` 注册 | 0（无 automake） |
| pytest / spec 测试 | 0 |
| 唯一测试入口 | 根目录 `testscript.sh`（28 行） |

`testscript.sh` 性质：`dd` 造 200M 样本 → 用 `/usr/bin/time -a -o results.txt` 对
裸 `cat` 计时 ×2、对 `cat | ./pipemeter` 计时 ×2 → 追加 `/proc/cpuinfo`、`free -m`、
`uname -a` → 打印 "Please mail the file results.txt to spamaps@spamaps.org"。
**脚本内 0 条断言；除开头 `[ ! -x ./pipemeter ] → exit 1` 这一条前置守卫外没有任何失败判定，
计时命令报错既不中断也不改退出码**（实测原样执行 exit 0） —— 是回寄作者的性能采样
采集器，不是回归测试。上游自动化断言测试：**没有**。

### 第 2 步：实际执行（OHOS 原生，两轮）

**2a. 原样执行** `sh ./testscript.sh`（日志 `$HOME/tmp/ohc-logs/07_upstream_testscript_as_is.log`）
→ exit 0，但 4 个计时步骤全部打印 `time: Unknown option 'a'`：OHOS `/usr/bin/time` 是
toybox applet，实测只支持 `-p`/`-v`（`/usr/bin/time --help` 原文 `usage: time [-pv] COMMAND...`），
不支持脚本用的 GNU `-a`/`-o`。results.txt 因此丢掉全部计时行，`cat` 未执行导致
pipemeter 读到空输入，只留下 `-1.00B/s 0.00B`。

**2b. 语义等价逐步执行**（日志 `$HOME/tmp/ohc-logs/08_upstream_testscript_stepwise.log`，
计时数据 `$HOME/tmp/ohc-logs/08_upstream_results.txt`）：把 `$TIME -a -o $RESULTS CMD`
换成 POSIX 等价的 `$TIME -p CMD 2>>$RESULTS`，其余步骤、数据量、顺序与上游脚本逐字一致。
**11 个步骤全部 exit 0，0 失败 0 跳过**：

| 用例 | 步骤 | 结果 | 实测数据 |
|---|---|---|---|
| T-01 | `./pipemeter -V` 版本自检 | PASS | `pipemeter v1.1.5` |
| T-02 | `dd if=/dev/zero of=./200M bs=200M count=1` | PASS | 209715200 B，952 M/s |
| T-03 | `cat ./200M > /dev/null` 预热 cache | PASS | rc=0 |
| T-04 | 裸 `cat` 计时 #1 | PASS | real 0.139355 / user 0.007109 / sys 0.122758 |
| T-05 | 裸 `cat` 计时 #2 | PASS | real 0.160585 / user 0.023275 / sys 0.127297 |
| T-06 | `cat ./200M \| ./pipemeter` #1 | PASS | 计量 `200.00M`；`real 0.309227` |
| T-07 | `cat ./200M \| ./pipemeter` #2 | PASS | 计量 `200.00M 200.00M/s`；`real 0.331516` |
| T-08 | `cat /proc/cpuinfo >> results` | PASS | 采集到 KirinX90 AArch64 20 核 |
| T-09 | `free -m >> results` | PASS | Mem 31914/29769 free 2144 |
| T-10 | `uname -a >> results` | PASS | `HarmonyOS localhost HongMeng Kernel 1.12.0 ... aarch64 Toybox` |
| T-11 | `rm -f ./200M` 清理 | PASS | 文件确认不存在 |

统计：**用例 11，通过 11，失败 0，跳过 0**（上游脚本步骤语义 100% 覆盖；断言数 0 —— 上游本身无断言）。
正确性判据取 pipemeter 的字节计量列：两次均精确等于输入 200.00M。

补充定位 `-1.00B/s`：这是上游在单次传输 elapsed < 1 s 时速率列的显示行为（非 OHOS 缺陷）。
用 32M + `sleep 0.3` ×8 拉长到 ~2.4 s 后，速率列正常显示
`12.00M/s 32.00M 8.00k 0:00:03` / `10.67M/s … 0:00:03`（日志同目录）。

### 第 3 步：回填

申报表与逐项结果已写入 `test_package/MANIFEST.yml`（`assertion_count: 8`，
上游 `testscript.sh` 声明 `assertion_count: 0` 并记录 OHOS `time` 兼容告警）。

## 适配层补充测试（test_package，不用于替代上游统计）

`test_package/` 为标准三件套结构：`conanfile.py`（`can_run` 守卫 + CMake 构建 + OHOS 签名
staging）、`CMakeLists.txt` + `pump.c`（测试源码，编译出精确产字的管道生产者）、
`smoke.sh`（8 条断言）。conan create 日志原文：
`Building C object CMakeFiles/pump.dir/pump.c.obj` → `Linking C executable pump` →
`RUN: sh ".../smoke.sh" ".../p/bin/pipemeter" "/data/storage/el2/base/cache/pipemeter-test-*/pump" 524288`
→ `pump: wrote 524288 bytes` → `pipemeter-test-ok 8/8`：

| 用例 | 断言 | 实测 |
|---|---|---|
| T1 | `-V` 输出 `pipemeter v1.1.5` | PASS |
| T2 | 512 KiB 流经管道后计量列为 `512.00k` | PASS |
| T3 | stdout 透传字节精确 65536（不吞不改数据面） | PASS |
| T4 | `-f a.bin -f b.bin`（1M+512k）累加报 `1.50M` | PASS |
| T5 | `-b 64k` 块大小回显 `64.00k` | PASS |
| T6 | `-i 0` 非法间隔退出码 1（`Bad interval: 0`） | PASS |
| T7 | `-f <缺失文件>` 退出码 2 | PASS |
| T8 | `pump` 自报字节 == 文件字节 == pipemeter 计量列 `512.00k` == stdout 透传字节（端到端三方一致） | PASS |

另在探索阶段跑过 15 项参数矩阵（P01–P15，日志 `$HOME/tmp/ohc-logs/09_param_matrix.log`），
覆盖 `-s/-b/-m/-r/-l/-a/-f/-F/-V/-i/getopt_long(--interval)` 与三类错误路径，全部符合预期。

## 验证结果

```text
$ conan create archives/p/pipemeter/1.1.5 -pr:h=…ohos-aarch64 -pr:b=…ohos-aarch64 --user=ohpcd --channel=stable
pipemeter/1.1.5@ohpcd/stable (test package): RUN: sh ".../test_package/smoke.sh" ".../p/bin/pipemeter" "/data/storage/el2/base/cache/pipemeter-test-*/pump" 524288
pump: wrote 524288 bytes
pipemeter-test-ok 8/8

$ conan-verify pipemeter 1.1.5   → EXIT=0
G1 PASS / G0 PASS / G2 PASS / G3 PASS / G4 PASS / L2 / L4 / L5
配方验证通过: pipemeter 1.1.5  →  可标记 status: published

$ file pipemeter
pipemeter: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

包内容（`conan create` 产物）：`bin/pipemeter`、`man/man1/pipemeter.1`、`licenses/LICENSE`。

## 软件类型判定（R38）

构建产物只有可执行文件 `bin/pipemeter`，`package_info()` 不设 `cpp_info.libs`
（`includedirs`/`libdirs` 显式清空）→ **CLI 工具**，已在软件级目录补
`archives/p/pipemeter/commands.json`（`type: tool`，`versions["1.1.5"].ref: "pipemeter/1.1.5"`）。

## 注意事项

- 上游 `pipemeter -h` 会打印 `unrecognized option: h` 后回落 usage（usage 文本里写了 `-ahlr`
  但 optstring 未把 `h` 注册为合法选项）—— 上游既有行为，OHOS 上表现一致，不改。
- `results.txt` 会被 `testscript.sh` 覆盖，属于运行时产物；本目录未纳入任何测试结果文件，
  补丁集也不含它（首轮 `refresh-patch` 曾把它带进 0003，已还原基线后重生成）。
- 发布（`conan upload`）必须等 CI 合并 main 后由流水线执行，本任务未在 PR 前上传任何制品。
## 会话决策记录

### 对话 #1 — 适配路径选择
- 依赖面判定：`configure.in` 的库检查段为空、`configure` 唯一库探测是
  `checking for pow in -lm`（结果只落到未被 `Makefile.in` 引用的 `POW_LIB`），
  实测 NEEDED 只有 `libc.so` → 判定零 Conan 依赖，不引入任何 requires，
  因此本包不存在 R36 依赖发布阻塞（registry 通道另用 zlib 对照组实测可用）。
- 补丁 vs 配方内改：install 缺失与 mktemp 陷阱都可以在 `build()` 里用 Python 改文件绕过，
  但两者都是上游源码自身的可移植性缺口，选择落成 `patches/0001`、`patches/0002`
  两个 portability 补丁（`refresh-patch --auto` 生成，不含平台宏），
  让上游 `make`/`make install` 语义在 OHOS 上保持完整，而非在配方里悄悄代跑。
- out-of-tree：`basic_layout` 失败后没有去给手写 Makefile 补 VPATH（改动面大且偏离上游），
  而是按仓库既有先例（bandwidthd、audtty）把 build 目录折回 source 目录。
- 上游测试：没有因为 `testscript.sh` 是 0 断言脚本就跳过，先原样执行留证（暴露 toybox
  `time` 不兼容），再逐步等价实跑取真实采样；未修改上游脚本本身，避免把环境兼容问题
  伪装成测试通过。

### 状态
- 状态: built
---

**编译结束**: 2026-09-07 22:40
**最终状态**: built
