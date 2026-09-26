# memlockd 1.3.1 适配笔记

## 编译环境

- 设备：HarmonyOS PC（aarch64，HongMeng Kernel 1.12.0，`uname -s` 返回 `HarmonyOS`）
- 工具链：clang/clang++ 15.0.4（`/data/service/hnp/bin/clang++`，由 CI profile 的
  `tools.build:compiler_executables` 指定），libc = musl（OHOS 变体），`-stdlib=libc++ -std=c++17 -O3`
- 构建器：conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（h/b 两侧同 profile）
- 会话形态：远程形态（Windows 侧起草与编排，构建/测试全部在鸿蒙 PC 真机执行）
- `CONAN_HOME=$HOME/tmp/ch/home-hw-3-memlockd`（独立 home，`global.conf` 含 `tools.build:jobs=2`）
- 资源纪律：`build-slot`（基准 2 槽）+ `memcap-run.py --mb 2500` 包裹，构建前过 `gate.sh`
  （本轮 `GATE_PASS`，MemAvailable 5457MB；fork+编译探针为决定性判据）

## 编译步骤

```bash
# 一次性命令（真机执行，逐字读数见 reports/conan-create.log）
conan create archives/m/memlockd/1.3.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

- 上游是**裸 Makefile 单 TU**：`Makefile:8` 一行 `$(CXX) $(WFLAGS) $(CXXFLAGS) $(LDFLAGS) memlockd.cpp -o memlockd`。
  配方按工作区规则显式传编译器（`create-6.log:101` 的 `make all -j1 CXX="/data/service/hnp/bin/clang++"`），
  不依赖 `$CXX` 是否被 buildenv 导出（R33）。
- 上游 **无 `install:` 目标**（Makefile 只有 `all`/`memlockd`/`clean`），因此 `package()` 逐条手工复现安装语义：
  可执行文件→`bin/`，样例配置→`res/`，手册→`share/man/man8/`，源码→`res/source/`（便于消费者核对锁页清单语义）。
- `package()` 用 `binary-sign-tool -selfSign 1` 对 `bin/memlockd` 自签，
  `create-6.log:109-110` 逐字 `add codesign section success` / `write code sign data success`。
- 交付身份绑定（三处同源）：
  配方 rev `3e0c3246c201156106a02c9f91eb8268`、
  包 `6b129b068851896169fae42d399fa922d239ce8a`、包 rev `f738a5035257fad8c30b398805f6a795`
  （`create-6.log:115-117`）。
- **本文件与各清单里 `create-6.log:NNN` 形式的行号**统一指真机
  `~/tmp/uc2/hw-3/memlockd/create-6.log`（17:27:45 那一次 `conan create` 的完整日志，176 行）。
  同一批读数在框架 W3 本地 CI 重跑（17:44，`archives/m/memlockd/1.3.1/reports/conan-create.log`，118 行）
  中**逐字复现**：`RLIMIT_MEMLOCK cur=-1 max=-1` 在前者 :152、后者 :96；
  `Locked: 31768 kB -> 39960 kB (delta=8192 kB)` 在前者 :163、后者 :107；
  `PASS=17 FAIL=0` 在前者 :173、后者 :117 ⇒ 两次独立运行同读数。
  按 AGENTS §9「工作流标记文件留盘不提交」，`reports/` 被仓库 `.gitignore` 覆盖（实测 `git add` 被拦），
  故两份日志都不随 PR 提交，行号只在真机上复核用。
- **W4 之后的 T3 复跑（`create-7.log`，18:58）**：W4 独立审计（verdict=pass，P0=0/P1=0/P2=5）后按整改意见
  改了 `test_package/conanfile.py`（工作目录兜底清理）与三处文档行号引用 ⇒ 属构建输入变更，重跑一次
  `conan create`。导出后**配方 rev 仍为 `3e0c3246c201156106a02c9f91eb8268`**（notes/manifest/knowledge 不在
  recipe rev 的输入集内），因此 conan 复用已存在的二进制包 `6b129b06…`，本包编译/签名的逐字读数仍以
  `create-6.log` 为绑定载体；`create-7.log` 提供的是改后 test_package 的第三次独立执行：
  `PASS=17 FAIL=0`（:120）、`MEMCAP[run] peak=94MB budget=2500MB rc=0 用时2.2s`（:122）、
  `RLIMIT_MEMLOCK cur=-1 max=-1`（:99）、`Locked: 31768 kB -> 39960 kB`（:110）⇒ 与 :152/:163 三度同读数。

## 源码修改

**零补丁**（`patches_applied: []`）。三点核实：

1. 上游 `WFLAGS` 含 gcc 早已移除、clang 也常被认定不支持的 `-ffor-scope`。真机按**上游原始整条命令行**
   实测 rc=0 且零诊断；conan 追加 `-stdlib=libc++ -std=c++17 -O3` 后（`create-6.log:102` 逐字命令行）
   同样零告警通过。⇒ 不为"看着像 gcc 专属"的旗标名打补丁，先跑合并后的真实命令行。
2. `-O3` 与 `-O0` 两版产物在 `$ARCH` 展开行为上一致（非优化相关）。
3. 上游只 `#include <assert.h>`（`memlockd.cpp:5`），全文 `assert()` 调用点为 **0**（逐行检索确认），
   因此 `NDEBUG` / Release 与断言副作用在本包不构成任何变量——没有断言可被静默掉。

## 发现与知识（使用记录，逐条对应 `manifest.yaml` 的 `knowledge_gained`）

- ✅ **OHOS 非特权锁页能力面（本条新增，申报路径 B）**：`RLIMIT_MEMLOCK cur=-1 max=-1`（＝RLIM_INFINITY，
  `create-6.log:152` 逐字读数）；`mlockall(MCL_CURRENT|MCL_FUTURE)` 与 `mmap+mlock` 在 uid=20020084
  （非 root、无 CAP_IPC_LOCK）下全部成功；`/proc/<pid>/smaps_rollup` 的 `Locked:` 从 31768 kB 升到
  39960 kB，**恰好 +8192 kB**（`create-6.log:163`），与追加映射的 8 MiB 文件同量。
  ⇒ 见 `DRAFT-memlockd-1.3.1-ohos-unprivileged-mlock-capability-plane`。
- ✅ **`/proc/<pid>/maps` 的双路径形态**：同一文件在 maps 里打印为
  `/data/service/el2/100/hmdfs/account/files/Docs/tmp/ch/...`，而调用方持有 `/storage/Users/currentUser/...`
  （`create-6.log:161` 逐字），且两侧 **inode 也不一致**（HMDFS 把 st_ino 虚拟化为本机 2305843009227425945，
  maps 里是 13731993）⇒ 按路径串或 inode 直接匹配 maps 的测试必然假阴。本包改为按路径尾段
  （含 conan 包哈希，唯一）匹配，并用权限串 `r--s` 把 memlockd 自己的 `PROT_READ|MAP_SHARED`
  映射与可执行文件自身的 `r--p`/`r-xp` 段区分（否则"打包二进制自身"会让断言无条件成立）。
- ✅ **上游零 RPC（更正工单前提）**：对整个发布树 `grep -ri rpc` 零命中；`memlockd.cpp` 的 include 列表
  无 `rpc/*`，源码内无 `socket/bind/listen/accept/clnt_*/svc_*/xdr_*`，进程不开任何套接字。
  派单里"SunRPC/xdr 走 libc，OHOS 下 rpc 可用性是前置风险"的判定**不成立**，本包不需要 `libtirpc`
  （仓库确有 `archives/l/libtirpc/1.3.7` 归档，但本包用不到）。
- ✅ **`/etc` 只读与 `/var/run` 缺失的实际影响**：上游硬编码 `/etc/memlockd.cfg`（`memlockd.cpp:39`）与
  `/var/run/memlockd.pid`（`:24`）。本机 `/etc` 是指向只读 `/system/etc` 的符号链接、`/var/run` 不存在
  （实测 `ls: /var/run: No such file or directory`）。pidfile 分支只在 `getuid()==0` 且非 debug/foreground
  时才写（`:424` 的 `write_pidfile` 判定），所以非特权 `-d`/`-f` 运行根本不触及缺失目录；
  配置则必须走 `-c` 运行期选路 ⇒ 样例配置以数据形态交付到 `res/`。
- ✅ **`-d`/`-f` 会 `chdir("/")`（`memlockd.cpp:430`）**：因此 `-c` 传相对路径必然在 chdir 之后
  `Can't stat` ——开发期第一条测试就撞在这上面（`sh memlockd -d -c arch.cfg` 复现），
  交付的测试一律使用绝对路径。这是使用侧约束，不改上游。

## 依赖版本

无外部依赖（`requires()` 为空）。`ldd` 型依赖展开只在 `-u <user>` 时触发
（`map_file_dependencies()` 首行 `if(!uid || !gid) return;`），本包不新增该依赖面。

## 验证结果

| 维度 | 读数 | 出处 |
|---|---|---|
| 编译（G0–G4 / conan create） | 通过（`CREATE_RC=0` 出自 `run-create.sh` 包装层 stdout，不是日志行；日志内终态为 :104 `Package '6b129b06…' built` 与 :116 `…created`） | `create-6.log:101-117` |
| 上游静态声明 `N_static` | **0**（Makefile 仅 all/memlockd/clean，无 check/test 注册） | `test_package/MANIFEST.yml` 说明段 |
| 上游注册/执行 | 0 / 0（不存在测试入口，非"有测试未跑"） | 同上 |
| 平台受限未执行 | 0 项 | 本机非特权即可跑完整行为面 |
| 消费者断言 `N_consumer` | **17**（1 个测试程序 `test_memlockd.py`，4 层） | `create-6.log:153-173`（终态行 `PASS=17 FAIL=0` 在框架 W3 重跑日志 `reports/conan-create.log:117` 同读数） |
| 内存峰值 | `MEMCAP[run] peak=97MB budget=2500MB rc=0 用时4.1s` | `create-6.log:175` |
| 签名 | codesign 段写入成功 | `create-6.log:109-110` |

上游 86 例那类"平台受限单列"在本包不存在：`N_static=0` 是发布源的真实形态，
因此适配后合计 17 ≥ 上游合计 0 成立，且 17 条全部真实执行、逐条判定。

### `N_static = 0` 的取证方式（不拿日志反填）

对解包后的 1.3.1 发布源逐项核对：`debian/` 之外仅 `Makefile`(235B)、`memlockd.cpp`(10731B)、
`memlockd.8`(2328B)、`memlockd.cfg`(496B)；`Makefile` 全文三条规则 `all:`、`memlockd:`、`clean:`，
对 `check`/`TESTS`/`add_test`/`test` 的检索零命中；`memlockd.cpp` 无测试注册宏。
⇒ 静态声明数按真实注册入口计为 0，与运行日志无关。

## 知识使用记录

- 复用：E543（HMDFS 默认 660 影响产物可执行位，故 `package()` 显式 `chmod 0755`）、
  abx/0.1 与 plocate 的 `binary-sign-tool -selfSign 1` 自签流程、
  R26（系统同名库静态优先，本包无库产物不适用）、R33（编译器不靠 `$CC/$CXX` 环境变量）、
  R51/§10.1 五维账本口径、§12.22「上游官方站不可达时的替代源判定」（本包最终**不需要**退到池件，见下）。
- 新增：`DRAFT-memlockd-1.3.1-ohos-unprivileged-mlock-capability-plane`（同 stem `.kv`/`.md` 成对，同一原子 PR）。
- 另有一条通用机制（procfs 对 HMDFS 文件打印规范路径且 inode 两侧不一致）不属本包主线，
  按"一 PR 一知识"规则转入通用草稿池 `经验文档/B草稿库/DRAFT-PKG-VER-proc-maps-hmdfs-canonical-path.*`
  供任何以 `/proc/<pid>/maps` 作测试载体的包取用（本 PR 只在 notes 与 manifest 记录事实）。

## 上游取包判定（url 与 sha256 同物）

- 官方站 `www.syselements.us` 实测已死：设备侧 `curl` 报 `Could not resolve host`，Windows 侧 TLS 握手失败。
  该域名是本包旧维护页面上的历史地址（`debian/watch` 指向 `http://www.coker.com.au/memlockd/`）。
- 按 `debian/watch` 与上游文档页 `https://doc.coker.com.au/projects/memlockd/` 实测取到
  **官方 HTTPS 原件**：`https://www.coker.com.au/memlockd/memlockd_1.3.1.tar.xz`
  → HTTP 200，10072 B，`sha256 = 8534e586eac0060be78a92d6d1c0b8cbfc3bb4360627faf0ab60ca20c90f0603`。
- 同哈希与 `archive.ubuntu.com` 池件 `memlockd_1.3.1.orig.tar.xz` 逐字节一致（两处分别下载分别求哈希），
  即"官方同物"已坐实 ⇒ `conandata.yml` 写官方 URL，**不写任何镜像/池件地址**（§12.3、§9 硬门）。

## 注意事项

- memlockd 是**守护进程**，且它的"功能"就是把文件锁进内存。本机非 root 即可完整跑通这条链，
  所以消费者测试不是"能启动"级别的冒烟，而是拿 procfs 的 `Locked:` 差分证明页真的被钉住了。
- 上游样例配置 `memlockd.cfg` 原样交付在 `res/`，但**它是 Linux 路径清单**：本机只有 4 项存在
  （`/bin/login`、`/etc/passwd`、`/etc/group`、`/etc/resolv.conf`），且尾行 `%/etc/memlockd.d`
  在本机不可 `stat()`，按 `parse_config_file()` 的语义是**致命** `exit(1)`（不是跳过）。
  两条都写成断言固定下来，免得后来者把样例配置当可直接运行的默认值。
- 本包不申报 M13：无 `install` 目标是**上游没有该目标**（裸 Makefile），不是"install 命令缺失"，
  也不属于 `PREFIX?=` 可覆盖类；配方自己完成安装动作。
- `make -j1`：体量单文件，且设备多窗口共用，按 §14.1 资源纪律不开并发。
- 平台任务 8789 声明语言 `cpp`，上游确为单个 `.cpp`＋裸 Makefile ⇒ 语言匹配，不走语言例外通道。
---

**编译结束**: 2026-09-25 19:41
**最终状态**: built
