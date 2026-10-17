# E692（草稿）：COIN-OR 顶层编排型 tarball 在 HMDFS 的 configure 两关——老 config.sub 拒 musl 三元组（第一关）与 `umask 077`/`confstatXXXXXX` 临时目录不可写（第二关）必须成对处理

> Draft: DRAFT-E692-COINOR-SYMPHONY-572-CONFIGURE-TRIPLET-AND-CONFSTAT-HMDFS
> Stem: `DRAFT-E692-coinor-symphony-5.7.2-configure-triplet-confstat-hmdfs` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-E692-COINOR-SYMPHONY-572-CONFIGURE-TRIPLET-AND-CONFSTAT-HMDFS
- **严重度**: 2
- **类别**: platform | portability | autotools | hmdfs-permission
- **触发工具**: configure | make | conan
- **阶段**: compilation | configuration
- **来源任务**: coinor-symphony 5.7.2（任务卡 6552，积分赛）断点续跑：原生探索 R1→R3 + W3 本地 `conan create` 全链
- **关联既有条目**: **E114**（HMDFS `umask 077`/`0700` → `drwx--S---`）、**DRAFT-E678**（sollya 同族双杀正解与「生成物免 refresh-patch 登记」口径）、**E646**（COIN-OR flags 模式/合并 incdir/直接 .a 闭包）、`device-facts §一.10/§一.12/§一.13`；与 bcp 的「补 config.sub 词表」修法**互为对照样本**

## 错误特征（逐字，`error_signature` 5 条子模式对 5 处实测）

**第一关（`config.sub` 拒 musl 三元组，`explore-configure.log`）**：

```
checking build system type... Invalid configuration `aarch64-unknown-linux-musl': machine `aarch64-unknown-linux' not recognized
configure: error: /data/service/hnp/bin/bash ./config.sub aarch64-unknown-linux-musl failed
CONFIGURE_RC=1
```

**第二关（`config.status` 的 confstat 临时目录，`explore-configure2.log` 尾部逐字）**：

```
config.status: creating include/config.h
./config.status: line 1130: ./confstatPNkMNn/in: Permission denied
./config.status: line 1179: ./confstatPNkMNn/undefs.sed: Permission denied
mv: bad './confstatPNkMNn/out': Permission denied
rm: ./confstatPNkMNn/config.h: Permission denied
```

**第二关的假绿形态（关键）**：同一份 `explore-configure2.log` 里上述 Permission denied **与**下面的成功行并存，`CONFIGURE_RC=0`：

```
configure: In case of trouble, first consult the troubleshooting page at https://github.com/coin-or-tools/build-tools/wiki/user-troubleshooting
configure: Configuration of SYMPHONY successful
CONFIGURE_RC=1→0（手工收敛后）
```

（即：config.status 段的错误不回传给 configure 的退出码，只看 rc=0 会漏掉 config.h/Makefile 残缺。）

**修复过程的两处次生报错（`config-status-fix.log`/`fix2.log`）**：

```
sed: bad regex 'tmp=\./confstat\$…': Invalid back reference      ← 照抄兄弟包 sed 时转义没对上本包形态
mkdir: './conftmp': File exists
: cannot create a temporary directory in .                        ← mktemp fallback 未改净
```

修复收敛（`config-status-fix3.log` 无错误收尾）：

```
config.status: creating Makefile
…
config.status: creating include/config_sym.h
config.status: executing depfiles commands
```

**伴随（同任务非两关，供审核裁剪）**：CLI 格式错配 `-F model.lp`：

```
Coin6002E Unknown image \ consumer model at line 1 of file …/t.lp
Errors in reading mps file
Fatal errors encountered. Exiting with code -122.
```

## 根因分析

两个失败点在「COIN-OR BuildTools 顶层编排 + 子包预生成 configure」形态的 tarball 上**串联**出现，但根因各自独立：

1. **第一关 · 三元组词表年代差**：本包两份 `config.sub`（顶层与 `SYMPHONY/`）`grep -c musl` = **0**——词表早于 2013 年 `linux-musl` 进入 config.sub 的年代。`--build=aarch64-unknown-linux-musl` 是 **coinor-cbc 2.10.13 可用**的同名同值（其 config.sub 较新），在本包直接被拒。**结论：三元组能不能用，判据只能是各包自己的 config.sub 词表实测，禁止沿抄兄弟包**。`aarch64-unknown-linux-gnu` 在词表内（CONFIGURE_RC=0 实证）；`aarch64-unknown-linux-ohos` 亦可（DRAFT-E678 实测），三者是「词表内取值」的三种合法解。

2. **第二关 · HMDFS umask 属主映射（E114 同族）**：autoconf 2.59 生成器内嵌三处临时目录逻辑——
   `tmp=\`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null\``、
   fallback `tmp=./confstat$$-$RANDOM`、`(umask 077 && mkdir $tmp)`
   （本包 `configure:30923/30927/30928` 实测）。HMDFS 强制 setgid 并按共享属主映射：umask 077 的目录落盘 2700，进程 euid 非属主、other 位无 w ⇒ 后续 subs/stdout/mv/rm 全部 Permission denied（与 DRAFT-E678 的 A/B 对照表同机制）。**该逻辑在 configure 里存在两份**：AC_OUTPUT 内联执行的一份 + 复制生成 `config.status` 的一份——只修其一，另一份照炸（fix1/fix2 两轮次生报错正是「只修一半」的现场）。

3. **假绿风险（本条最值钱的判读）**：configure 的退出码不吸收 config.status 段的错误。`CONFIGURE_RC=0` + 满屏 Permission denied 并存 ⇒ 判 configure 成功必须 **grep config.status 段输出**，不能只看 rc。

4. **伴随增量**（同任务，审核可裁剪）：
   - 测试面：`--with-sample-datadir=<Data-Sample 1.2.13 解包目录>` 置 `COIN_HAS_SAMPLE` 后，`make test` 的 `unitTest -miplib3Dir= -mpsDir=<dir>` 才进数据驱动断言面（412 PASSED/0 ERROR 实测）；漏传则 OsiCppUnit 面大面积静默缩水——**上游 N 清点的前置**。
   - CLI 格式语义：`-F` 读 **MPS**、`-L` 读 **LP**（`-h` help 与实测双证），错配以 `Errors in reading mps file` 退出 **-122**；test_package 驱动 LP 模型必须用 `-L`。

## 解法（rec_approach = `gnu-triplet-plus-pre-configure-umask-strip-in-build`）

**两步都在 conanfile `build()` 内，顺序=先修生成器、再跑 configure**（生成物不进 git ⇒ 按 DRAFT-E678 正解留同名函数每次执行，**免 refresh-patch 登记**；`patches: {}` 同时结构性绕开 refresh_patch 改补丁名不同步 conandata 的缺陷）：

1. **过第一关**：`--build=aarch64-unknown-linux-gnu`（本包词表实测值）。与 bcp 先例互为对照——bcp 走「补 config.sub 词表」侧，本条走「换词表内三元组」侧；词表老但存在可选合法值时，**换值是零改动最短路径**，两法都必须逐包实测。
2. **过第二关**：configure **之前**对生成器 `configure` 四处精确文本替换（`replace_in_file` 严格模式 + 未命中跳过 = 跨 autoconf 版本幂等）：

   ```python
   ('umask 077 && mktemp -d -q "./confstatXXXXXX"', 'umask 022 && mkdir -p ./conftmp')
   ("tmp=./confstat$$-$RANDOM",                     "tmp=./conftmp")
   ("umask 077 && mkdir $tmp",                      "umask 022 && mkdir -p $tmp")
   ("umask 077",                                    "umask 022")   # 残余兜底
   ```

   外加 configure 前 `rm -rf conftmp confstat*` 清残留；AC_OUTPUT 内联与生成出的 `config.status` 从这份 configure 复制，**自动继承**，configure 之后对 `config.status` strict=False 幂等补一遍即可（本包实测修后 configure 全程零 Permission denied、`Configuration of SYMPHONY successful`）。
3. **防假绿**：configure 成功判据 = rc **且** `grep -cE 'confstat.*/(out|stdin): Permission denied' <log> == 0`。
4. **测试面配套**：`--with-sample-datadir` 传全，否则断言面静默缩水。

## 自证（verification_cmd，设备可直接执行、路径落 `$TASK_DIR`）

```bash
T=/storage/Users/currentUser/tmp/coinor-symphony-5.7.2
W=/storage/Users/currentUser/ws/tmp/builds/coinor-symphony-5.7.2.work/SYMPHONY
grep -c musl "$W/config.sub"                                        # 0 = 词表缺失（第一关命中面）
grep -n "umask 077 && mktemp" "$W/configure" | head -3              # 生成器原样（未修面）
grep -n "confstat.*/out: Permission denied" "$T/explore-configure2.log" | head -3   # 逐字复现
grep -n "Configuration of SYMPHONY successful" "$T/explore-configure2.log"          # 假绿并存证据
grep -c "umask 077" "$W/config.status"                               # 修后：0 = 生成链已继承
sh "$T/w0-checks.sh" >/dev/null 2>&1; echo "w0 rc=$?"                # W0 全套秒级复跑
```

## 禁止（forbid）

1. 未合并未 release upload 前把 `manifest.status` 写 `published`（O5 假绿）。
2. 用 `OHC_PREFLIGHT=0` / 无闸号 `--no-preflight` 绕门禁——本包「rc=0 与 Permission denied 并存」正是会被带进 PR 的假绿形态。

## 证据路径

- `$TASK_DIR/w0-checks.md`（W0 三段命令+rc 逐字）、`$TASK_DIR/explore-configure{,2}.log`、`$TASK_DIR/config-status-fix{,2,3}.log`、`$TASK_DIR/explore-make.log`（MAKE_RC=0）、`$TASK_DIR/explore-test.log`（PASSED 412 / ERROR 0）、`$TASK_DIR/local-create.log`（W3 conan create 全链）
- 配方落点：`archives/c/coinor-symphony/5.7.2/conanfile.py`（`_fix_config_tmp_mechanism` / `_fix_hmdfs_scripts` / CFLAGS pin / `--build` 值）与 `notes.md` 问题表 #1–#5
