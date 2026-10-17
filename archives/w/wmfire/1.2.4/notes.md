# wmfire 1.2.4 适配说明

状态：built
构建系统：autotools（tarball 只带 `configure.in` / `Makefile.am`，构建时 bootstrap）
目标平台：OHOS 6.0 / aarch64（clang 15，libc++）
最后更新：2026-09-30

## 适配内容

1. **移除硬编码 X11 路径**（补丁 `0001-remove-hardcoded-x11-paths.patch`）：
   `src/Makefile.am` 写死了 `-L/usr/X11R6/lib -L/usr/local/lib` 及对应 `-I`，这些目录
   在 OHOS 上不存在且会覆盖 Conan 注入的搜索路径，改为完全由
   `pkg-config gtk+-2.0` / `pkg-config libgtop-2.0` 决定。
2. **`draw_fire` 链接修复**：`src/wmfire.c` 把 `draw_fire` 声明为 `inline` 而非
   `static inline`，clang -O3 不为非 static 的 inline 函数生成外部符号，链接报
   undefined symbol。构建期改写为 `static inline`（`_patch_draw_fire_static`）。
3. **autotools bootstrap**：tarball 不含生成的 `configure`，`build()` 依次执行
   `aclocal --force` / `autoconf -o configure configure.in` / `automake --add-missing --copy`，
   并在 configure 前恢复 `configure`、`config.guess`、`install-sh` 等辅助脚本的可执行位。
4. **安装产物处理**：`bin/wmfire` 归一化为 0755、移除 build RPATH（改由 LD_LIBRARY_PATH
   决定），再先删旧 `.codesign` 段重新签名。
5. **上游测试入口**：`build()` 中执行 `make -j1 check`。上游 `Makefile.am` 未声明
   `TESTS`、也没有 test suite 目录，因此该目标是「成功的空操作」；保留它是为了证明
   这个入口在 OHOS 上确实可运行。

## 依赖与版本冲突

运行期依赖 `gtk2/2.24.33`、`libgtop/2.41.3`、`libx11/6.4.0`、`libxext/6.4.0`。

gtk2 精确 pin `glib/2.84.0.1`（pango/atk/gdk-pixbuf 同代），因此整张图必须留在
glib 2.84 轨道，本配方显式 `glib/2.84.0.1 force=True`。

仓库里同一份上游 libgtop tarball（sha256 `775676df…`）被打成两个包，分属两条轨道：

| 包 | glib 轨道 | `cpp_info.libs` | 可用性 |
|---|---|---|---|
| `libgtop/2.41.3` | **2.84.0.1**（与 gtk2 一致） | `gtop-2.0`, `intl` | 发布二进制匹配，直接下载 |
| `libgtop2/2.41.3` | 2.88.3 | `gtop-2.0`（缺 `intl`） | 与本图不匹配，会触发源码重建 |

本配方因此依赖 `libgtop/2.41.3`：它与 gtk2 同轨道（发布二进制 requires
`glib/2.84.Z`）、已被同仓的 `das-watchdog/0.9.0` 使用，且已正确声明静态归档所需
的 `intl` 库。两者暴露的 pkg-config 名同为 `libgtop-2.0`、库名同为 `gtop-2.0`，
对 wmfire 的 autotools 构建完全透明。

## 功能验证

- 上游 `make check`：入口可执行，无用例（上游无测试套件）。
- 鸿蒙具名端到端消费者用例 `test_package/src/hc_consumer.c`（HC-1..HC-4，共 21 项判定）：
  HC-1 产物 ELF 契约（ELF64/AArch64/PIE + `.codesign` + DT_NEEDED）；
  HC-2 **端到端**：无 `DISPLAY` 下 exec 已安装的 `bin/wmfire`，要求 OHOS 加载器解析完整
  DT_NEEDED 闭包且 `main()` 被真正执行到（stderr 出现 `GDK init failed`、退出码 255），
  出现任何加载器诊断即失败；
  HC-3 真实调用 `XParseGeometry()`（wmfire `-g` 选项同一入口）；
  HC-4 真实调用 `glibtop_init()` + `glibtop_get_cpu()`（wmfire 每次刷新同一入口）。
  全部用例只走 exec-time DT_NEEDED 加载路径，不使用 `dlopen`（OHOS CI 拒绝 dlopen
  用户目录 .so，见 knowledge E502）。

## 依赖阻塞的根因与解除

**现象**：早期版本依赖 `libgtop2/2.41.3`。在冷缓存（CI 语义）下该包因 glib 轨道
不匹配被判定为 `Missing`，必须源码重建，而重建在**链接阶段失败**：
`src/daemon/Makefile` 与 `examples/Makefile` 的链接变量只带 `-lgtop-2.0`，而
`lib/read.c`、`lib/write.c` 经 `gi18n-lib.h` 调用 `ngettext` →
`g_libintl_ngettext`，该符号 glib/2.88.3 的 `libglib-2.0.so` 导出、
glib/2.84.0.1 **不导出**。

**根因**：`libgtop2` 的 `cpp_info.libs` 只有 `["gtop-2.0"]`，缺少 `intl`；
glib 2.84 轨道上提供 `g_libintl_ngettext` 的是 **glib 包自带的 `lib/libintl.so`**
（glib 内嵌 proxy-libintl），因此凡是静态链接 `libgtop-2.0.a` 的消费者都必须
额外链接 `-lintl`。

**解除方式**：改用同轨道的 `libgtop/2.41.3`，其 `cpp_info.libs = ["gtop-2.0","intl"]`
已正确携带该标志。实测：`conan graph info` 中 `libgtop/2.41.3` 为可下载、
不再源码重建；手工以 `-lgtop-2.0 -lglib-2.0 -lintl` 链接静态归档成功且可运行
（`glibtop_init()` / `glibtop_get_cpu()` 返回非零计数）。修改完全落在
`archives/w/wmfire/` 内；`libgtop2` 包自身 `cpp_info.libs` 缺 `intl` 属该包
（属主目录）的问题，不在本次变更集。

已实测的另一条路（不改依赖、给 libgtop2 的 daemon/examples 补
`-L<proxy-libintl>/lib -lintl`）虽可链接成功，但需要修改 `libgtop2` 的 recipe，
属**非本软件目录改动**，故未采用；改为强制 `glib/2.88.3` 则引发 zlib/libpng
世代级联冲突，同样不可行。

## pango 依赖轨道的对齐

清掉 libgtop 阻塞后，冷缓存图仍会把 `pango` 判为 `Missing` 而触发源码构建。
根因是 **gtk2/2.24.33 仍钉 `pango/1.50.14.1.1`**，而该版本的 cairo 钉
（`cairo/1.18.4`）早于本图使用的 6.4.0 X11 轨道，于是其 package_id 在制品仓
没有对应二进制。仓库其实已经为这个问题准备了修复（提交 `094f30b664`
【依赖项】pango 1.50.14.1.1.1：cairo pin 对齐 gtk3 生态），把 pango 递增到
`1.50.14.1.1.1` 并改钉 `cairo/1.18.4.1`，ohpcd 上该版本的二进制
（`251915fe`，package_id `4739686b…`）与本图所需**完全一致**。

由于 gtk2 属其他软件目录（rule5），本配方改为显式
`pango/1.50.14.1.1.1 force=True` 对齐。实测效果：依赖图状态从
`Missing: pango, libxrender` 变为**零源码构建**——29 个 Cache + 1 个 Download，
`gtk2`/`cairo`/`libgtop`/`pango` 全部复用已发布二进制，只有 wmfire 自身需要构建。

## 对话记录

### 对话 #1 — 上游测试与鸿蒙特有测试
审计指出 test_package 原先只声明 `test_wmfire.sh`，其内容是纯断言清单
（ELF magic / 64 位 / ARM64 / codesign 存在），没有任何具名端到端用例，违反
「鸿蒙特有测试不能是断言」的要求；且该脚本的 `check()` 调用把管道写在函数外，
5 个 PASS 全是假阳性。改为编译型消费者 `src/hc_consumer.c` + CMake 构建，
用例从「断言清单」变为「真实 exec 产物 + 真实 API 调用」。

### 对话 #2 — 运行期验证必须走 exec-time 路径
第一版 HC-2/HC-3 用 `dlopen()` 遍历 DT_NEEDED 闭包、`dlsym()` 校验导入符号，
本地对已发布闭包可以跑通，但知识库 E502 表明 OHOS CI 运行器拒绝 dlopen
用户目录下的 .so（与签名无关），该设计在 CI 上必然假失败。于是整体改为
exec-time 探针：HC-2 直接 exec `bin/wmfire`，靠加载器是否解析完整闭包以及
`main()` 是否跑到 `gdk_init_check` 失败分支来判定。

### 对话 #3 — 依赖图阻塞与幽灵缓存
发现本机 conan 缓存里存在一个**未提交**的 libgtop2 recipe revision（`5010789f`，
`shared=True` 且带 daemon 链接修复），此前 conan create / W3 / finish 的「全绿」
都建立在这个幽灵条目上（W3 日志中 libgtop2 显示 `- Cache` / `Already installed!`）。
清理该污染后按 CI 语义重跑，暴露出上述 `g_libintl_ngettext` 阻塞：远端只有一个
libgtop2 版本、一个二进制、且发布版 recipe 不含该修复，也没有可跳过 daemon 的选项；
改强制 `glib/2.88.3` 会引发 zlib/libpng 世代级联冲突，不可行。

### 对话 #4 — 依赖轨道切换与阻塞闭环
在明确「修复必须只落在 wmfire 变更集内」这一约束后，逐一排除了三条路：
改 `libgtop2` 的 recipe（跨目录）、改 gtk2 的 glib pin（跨目录）、强制
`glib/2.88.3`（世代级联冲突）。随后发现仓库里存在同一上游源码的第二个包
`libgtop/2.41.3`，它就在 glib 2.84 轨道上、发布二进制可直接下载，且
`cpp_info.libs` 已带 `intl`。切到该包后：干净缓存下的依赖图不再要求任何
libgtop 源码构建（`libgtop/2.41.3: Already installed!`），消费者链接与
`glibtop_get_cpu()` 运行实测均通过。这是本次变更集中除测试包之外的第二处
实质修复。

### 对话 #5 — pango 轨道对齐与「零源码构建」图
清掉 libgtop 障碍后继续按 CI 语义验证，暴露第二处源码构建：`pango` 因
gtk2 钉的 `1.50.14.1.1` 与本图 cairo 轨道不匹配而 `Missing`；该包源码构建
可编译但在其自身 `meson test` 阶段因 E505（构建树与依赖包中 soname 为符号
链接）无法通过。排查确认仓库已合入修复版 `pango/1.50.14.1.1.1`，且 ohpcd
上其二进制 package_id（`4739686b…`）与本图所需完全相同。于是本配方加
`pango/1.50.14.1.1.1 force=True` 对齐（改 gtk2 属其他目录，rule5 不允许）。
对齐后依赖图**再无任何 Missing 节点**，全部依赖复用已发布二进制。

### 对话 #6 — 运行期闭包的三个 OHOS 陷阱

HC-2 在 CI 对齐 `conan create` 上继续失败，报错几经变化，最终定位到三个**互相独立**的 OHOS 陷阱，且每一层都会伪装成另一层：

1. **E505 摊平**：OHOS musl 不跟随符号链接解析 DT_NEEDED，`Error loading shared library libXrender.so.1`。
   已在 `test_package/conanfile.py` 中用 `cp -L` 摊平依赖闭包解决。

2. **E508 CMakeDeps 限制**：`find_package(libgtop CONFIG REQUIRED)` 永远 configure 失败。
   libgtop 的 `cpp_info.libs = ["gtop-2.0","intl"]`，而 `libintl.so` 在 glib 包里；CMakeDeps
   的 `conan_package_library_targets()` 只在声明包自己的 libdir 内 `find_library(NO_DEFAULT_PATH)`，
   找不到 `intl` 就直接 `message(FATAL_ERROR "Library 'intl' not found in package")`。
   修法：`generate()` 把 libgtop 静态归档按路径喂给 CMake（`hc_libgtop` IMPORTED），
   并显式 `-lintl`（A/B 证明不加就 `undefined symbol: g_libintl_ngettext`）。

3. **平铺舞台摧毁 `LD_LIBRARY_PATH` 优先级**（本轮最阴的一个）：
   `VirtualRunEnv` 写的是 `<conan libdirs>:<环境原有 LD_LIBRARY_PATH>`，
   本机尾巴含 `/data/storage/el1/bundle/libs/arm64`——该目录里有个**同名 7.5 MB 的应用包
   libc++_shared.so（0755 缺 .codesign）**。原写法 `cp -L` 后到者覆盖，于是它把工具链
   那份可加载的 1.27 MB 副本（带 .codesign）覆盖掉了，加载器对用户目录可执行文件
   拒绝加载它 → HC-2 报了一个**假的** `Error loading shared library libc++_shared.so`。
   **8 组对照**（A/B/C/D/E/F/G/H）钉死根因：
   - `stage` 单独用坏副本 → exit 127；`stage:SDK` → 127；**`SDK:stage` → 255 通过**；
   - 把 SDK 那份覆盖进 stage → 255；换回坏副本 → 127；
   - **原始 `/data/storage/el1/bundle/libs/arm64` 置首 → 同样 127**（证明是那份文件本身不可加载，不是拷贝坏了）。
   修法：舞台**先播工具链自带的 libc++_shared.so**，再把 sweep 改用 **`cp -nL`（先到先得）**。
   可用运行时三处：SDK `llvm/lib/aarch64-linux-ohos/libc++_shared.so`（1267392，带 .codesign）、
   `/system/lib64`（1289544）、bundle 那份（7519624）不可用。平台 `cp` 支持 `-n`。

4. **`/proc` MAC 行为**：`/proc` 挂载 `hidepid=invisible,hmmac=genfs`，用户目录
   可执行文件被拒绝读取 `/proc/stat`（同 uid 的系统二进制可读，签名不改变）；
   `glibtop_init()` 自身读 `/proc/stat` → 所有 glibtop API 在用户目录二进制上
   都 SIGABRT。HC-4 据此改为**平台能力交叉校验的蕴含式**：本进程能读 `/proc/stat`
   → 必须采到递增 jiffies；被拒绝 → 必须按 `/proc/stat + Permission denied` 显性拒绝且不上报伪造计数。
   对应知识库 E031——E031 写「SELinux 限制普通用户访问 /proc」；本次实测结论更精确：
   **不是 uid 而是可执行文件的安全标签**（系统二进制同 uid 可读 `/proc/stat`）。

CI 对齐 `conan create` 结果：`EXIT=0` / `=== Results: PASS=4 FAIL=0 ===`
（HC-1 ELF 契约 .codesign=yes 4096B / DT_NEEDED=64；HC-2 exit=255 / GDK init failed /
loader-error=none / mapped objects=10；HC-3 XParseGeometry 120x48+16-12；
HC-4 /proc/stat denied → sampler aborted as required, counters=0）。
---

## 对话 #7：CI 构建失败 → config.status 私有临时目录（E011）

**现象**：PR #14133 CI（构建 #66145）`conan-build-test` 失败：

```
./config.status[878]: can't create ./confCioKch/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

包本体源码下载、patch、aclocal/autoconf/automake、依赖闭包（31 个节点）全部正常，
只死在生成 `config.status` 后的 subs 机制上——本地 W3 同一提交全绿。

**根因**（与知识库 E011/E114 一致）：autoconf 2.72 生成的 `config.status` 用
`(umask 077 && mktemp -d "./confXXXXXX")` 建私有临时目录。HMDFS 把该目录映射成
`drwx--S---`（2700 + setgid），**chmod 无效**，只有目录映射 owner 可写：

| 实验 | 命令 | 结果 |
|---|---|---|
| A | HMDFS 上 `umask 077; mkdir d1` | `drwxrws--x`（组可写），写文件 rc=0 |
| I | HMDFS 上 `umask 077; mktemp -d ./confXXXXXX` | **`drwx--S---`**（组/其他无权限），本地写 rc=0 |
| L | `umask 000; mktemp -d` | `drwxrws--x`（组可写） |
| L' | `umask 022; mktemp -d` | `drwxr-s--x`（组不可写） |
| H | `/tmp` 可写性 | `Read-only file system`（故 2.72 的第一分支在 CI 必然失败） |

本地 shell 恰好落在可写域（所以 W3 全绿是假绿），CI worker 落在另一个 uid 域，
对 `drwx--S---` 目录无写权限 → `subs1.awk` 创建被拒。

**修法**：`build()` 中 `autoconf -o configure` 之后调用 `_relax_config_status_umask()`，
把生成 `configure` 里的 `(umask 077 && mktemp -d "./confXXXXXX")` 与
`(umask 077 && mkdir "$tmp")` 放宽为 `umask 000`（显式取组可写，
不依赖 CI 环境 umask 具体值）。`configure` 与其派生出的 `config.status` 两处同时生效，
实测落地行：`configure:6696/6701`、`config.status:564/569`。

同类先例（仓库已入库）：`archives/a/abiword-plugin-clarisworks/3.0.8`（`_drop_umask_077`）、
`archives/a/aaphoto/0.45`。

**验证**：修改后本地 `conan create` 重跑 `EXIT=0` / `=== Results: PASS=4 FAIL=0 ===`，
日志出现 `configure: relaxed config.status temp-dir umask (E011/E114, HMDFS)`。
---

## 对话 #8：CI #66194 HC-4 失败 → /proc/stat「可读但无统计」（判据三态化）

**现象**：PR #14133 CI（构建 #66194）`conan-build-test` 再次失败。对话 #7 的修复已生效
（日志首行 `configure: relaxed config.status temp-dir umask (E011/E114, HMDFS)`，
`./configure`、`make -j1`、`make install`、package 全部成功），失败点前移到 test_package：

```
[PASS] HC-1   elf-contract        ELF64/LE/AArch64/PIE, .codesign=yes(4096 B), DT_NEEDED=64
[PASS] HC-2   loader-closure      exit=255, loader-error=none, mapped objects=11
[PASS] HC-3   x11-geometry-parse  XParseGeometry("120x48+16-12") -> 120x48+16-12 mask=0x2f
[FAIL] HC-4   cpu-sample          /proc/stat readable: jiffies 0->0, idle 0->0
=== Results: PASS=3 FAIL=1 ===
```

**根因**：HC-4 原判据是**二态**——`/proc/stat` 在本进程域可读 ⇒ 必须采到非零且非递减
的 jiffies；不可读 ⇒ 采样器必须显式拒绝。CI worker 容器给出**第三种形态**：文件可读、
`cpu` 行可解析，但所有字段恒为 0（同一容器里 CMake 也打印 `Problem parsing
/proc/meminfo`）。既不是 denied，也不是「有计数」，落进二态之外 → 判 FAIL。

**修法**：把判据锚定在**消费者自己读到的 /proc/stat 原始内容**上，而不是采样器自身
输出，形成三态交叉校验（防弱化：凭空造数仍判 FAIL）：

| 本进程域读到的 /proc/stat | 采样器必须 | 判定 |
|---|---|---|
| 打开/读取被拒（MAC） | 显式拒绝，且 stderr 同时命名 `/proc/stat` 与 `Permission denied` | `refused && total == 0` |
| 可读，聚合 `cpu` 行 total > 0 | 返回非零、非递减 jiffies | `sane` |
| 可读，但 total == 0 | 如实返回全零计数（或按上一条显式拒绝），**不得凭空造数** | `honest_zero \|\| refused` |

新增 `hc_procstat_read()`：在本进程直接 `open()/read()` `/proc/stat`，定位行首的聚合
`cpu ` 行（避免误匹配 `cpu0 `），`sscanf` 取前 10 个字段，返回
`readable/parsed/total/idle`。

**验证一：判定表 probe（7/7）**
`$CACHE/hc4-verdict-probe.c` 内嵌与生产代码**逐字相同**的判定表达式，把原始视图改为
路径参数以离线复放三种平台形态，用 fixture 文件喂入：

| 用例 | 原始文件 | 采样器结果 | 期望 | 实测 |
|---|---|---|---|---|
| denied + 显式拒绝 | 不存在 | 非零退出 + `/proc/stat ... Permission denied` | PASS | ✅ denied PASS |
| denied + 静默干净退出 | 不存在 | exit=0, 0/0 | FAIL | ✅ denied FAIL |
| 有计数 + 递增 | live fixture | 12345→12500 | PASS | ✅ live PASS |
| 有计数 + 全零 | live fixture | 0→0 | FAIL | ✅ live FAIL |
| **无计数 + 全零（CI 场景）** | zero fixture | exit=0, 0→0 | **PASS** | ✅ zero PASS |
| 无计数 + 伪造计数 | zero fixture | 50→80 | FAIL | ✅ zero FAIL |
| 无计数 + 显式拒绝 | zero fixture | 非零退出 + Permission denied | PASS | ✅ zero PASS |

**验证二：本地 conan create**（CI 同款命令）

```
conan create <pkg_dir> -pr:h=<prof> -pr:b=<prof> --build=missing --build="wmfire/*"
```
`EXIT=0` / `=== Results: PASS=4 FAIL=0 ===`；HC-4 走 denied 分支
（`/proc/stat denied to this binary (hmmac): sampler aborted as required, counters=0`，
child stderr 为 `glibtop(c=...): [ERROR] open (/proc/stat): Permission denied`）。

**验证三：conan-verify** `EXIT=0`，报告 Verdict PASS，G0/G1/G2/G3/G4 与 L2/L4/L5 全 ✅。
**验证四：finish W3** 通过（`✅ 本地 CI 模拟通过`）。注意 worktree 里跑 W3 必须给
`JUNK_PR_DIFF`：fork 的 `origin/main` 陈旧，`incremental` 模式会算出 2408 个文件
（140 个包）而误判 JC6；本包真实 diff 见 `git diff upstream/main...HEAD`（12 文件）。
**验证五：W3 内 conan create** 同日志 `Pass rate 100%`。
---

## 对话 #9：CI #66214 失败——HC-4 结果回传通道 bug（2026-10-01 16:15-16:35）

CI #66214（worker `OpenHarmonyPCDeveloper-CI-023`）失败点：

```
[FAIL] HC-4 cpu-sample  /proc/stat raw cpu: total=44933186 idle=35242322 -> sampler jiffies 0->0, idle 0->0
```

即**消费者本进程能读到真值，采样器却报 0**。此前三处形态各不相同：本地「全拒」、
CI-034「可读但全零」、CI-023「可读且带真值」——说明真值分支此前从未真正通过过。

**根因（用例自身的 C 缺陷，与平台无关）**：`hc_gtop_sample()` 的子进程先
`dup2(fds[1], STDOUT/STDERR)`，接着 `close(fds[1])`，之后才
`write(fds[1], "hc_gtop jiffies=…")` → **EBADF**，结果行被静默丢弃，
父进程 `sscanf` 不到 → `gt.total` 恒为 0。拒绝分支只看子进程退出状态与 stderr，
不受影响，因此本地 `PASS=4 FAIL=0` 属于**第三种本地假绿**：成功路径从未执行、
且失败被静默吞掉（前两种分别是缓存残留与 skip）。

**修法**：

| 项 | 改前 | 改后 |
|---|---|---|
| 结果回传 | 复用诊断管道，且写端已 close | **两条管道**：结果行走专用写端（dup2 之后不关，写完再 close），stdout/stderr 只作诊断证据、不参与解析 |
| 采样路径 | `glibtop_init()` + `glibtop_get_cpu()` | 对齐 wmfire 真实刷新：只调 `glibtop_get_cpu()`（wmfire 不调 `glibtop_init()`），并读 `glibtop_global_server->ncpu` |
| 真值形态判据 | 仅「非零、非递减」 | 追加与本进程 /proc/stat 原始读数的交叉校验：`idle` 取聚合行第 4 字段且只能增长；`total` 落在该行两种合法解析界定的窗口内 |
| 诊断 | 仅 denied 分支回显 | **任何结论都回显**子进程 exit/signal 与 libgtop 原文 |

**关键实测（本地 conan create，denied 形态）**：

```
[PASS] HC-4   cpu-sample              /proc/stat denied to this binary (hmmac): sampler aborted as required, counters=0
        --- glibtop child output ---
glibtop(c=44249): [WARNING] Non-standard uts for running kernel:
release HongMeng Kernel 1.12.0=0.0.0 gives version code 0
glibtop(c=44249): [ERROR] open (/proc/stat): Permission denied
        --- glibtop child died on signal 6 ---
=== Results: PASS=4 FAIL=0 ===
```

由此确认两点：① 被 MAC 拒绝时 libgtop 走 `glibtop_error_io_r()` → SIGABRT（非静默返回零），
与本轮修掉的「静默丢结果」是两种完全不同的失败；② OHOS `uname()` 的 release 为
`HongMeng Kernel 1.12.0`，libgtop 的 `sscanf("%u.%u.%u")` 解析为 `0.0.0` →
`os_version_code = 0` → **`>= 2.6` 分支不执行**，`cpu.total` 只含 user+nice+sys+idle，
故 `total` 窗口的下界取该四字段之和（上界取该行全部字段之和 + 漂移余量）。

**本地复验**：`conan create` EXIT=0 / `=== Results: PASS=4 FAIL=0 ===`；
`conan-verify` EXIT=0（G0–G4 PASS）；`finish` 的 W3 阻塞门禁 ✅ 通过，
`EXIT_CODE: 0`，`STEP_FAILED: Step6` 仍为已知 packaging 框架缺陷
（step7 W5 的 E219/E253/E305 空字段、step9 W2 未吃 `JUNK_PR_DIFF` 而算出的
2407 文件假象，同为已知项）。
---

**编译结束**: 2026-10-01 16:36
**最终状态**: built
