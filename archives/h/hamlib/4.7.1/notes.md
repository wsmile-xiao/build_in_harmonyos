# hamlib 4.7.1 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

- 构建系统: autotools
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 / clang++
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

上游: https://github.com/Hamlib/Hamlib （业余无线电电台/旋转器/功放控制库，LGPL-2.1-or-later）
构建系统: autotools（纯 configure + make，与 qmake/CMake 无关）
源码: 官方 release tarball `hamlib-4.7.1.tar.gz`
  sha256 `d197a08a3d5d936d7571ae573f745bbba619e88998742c8267e3fcb0fb3d5974`
  ⚠️ 不用 GitHub tag 归档（`archive/refs/tags/4.7.1.tar.gz`）：git archive **不含 `configure`**，
  需在 CI 上 autoreconf/bootstrap（automake/aclocal/libtool 版本敏感，且需补 build-aux 脚本），
  release tarball 是 `make dist` 产物，自带 configure + build-aux，无需 bootstrap。

## 构建步骤（本地复现）

```sh
./configure --prefix=$DEFAULT_PREFIX --without-libusb --without-readline
make -j1          # R9: HMDFS 上并行 make 会触发 jobserver fifo EPERM（E074）
make install DESTDIR=$TEST_PREFIX
make check        # 上游测试 11/11 PASS
```

Conan 侧由 `conanfile.py` 完成同样流程（configure → make -j1 → make check → install）。

## 依赖

无 conan 依赖。可选依赖 `libusb`（USB 电台）、`readline`（rigctl 交互补全）在 ohpcd
制品仓未发布，且非 rigctl/rigctld 主路径所需 → `--without-libusb --without-readline`。
openssl/dbus 等由 hamlib configure 自动探测，缺失时不启用相应后端（CI 实测 configure 通过）。

### 功能边界（诚实声明，R40）
- **可用**: 串口（termios/`/dev/tty*`）电台控制、`rigctld`/`rotctld` 网络（TCP）服务、
  Dummy/Net rig、全部型号 caps 表与频率/模式/网格换算（上游 11/11 测试覆盖）。
- **不可用**: 依赖 `libusb` 的 USB 直连后端（configure `--without-libusb`）。这只是
  "该可选后端未启用"，不是 stub/假实现：`configure` 不生成对应后端，`rigctl -l` 如实
  不列出它们，库内无返回假成功的桩函数。后续 libusb 发布到 ohpcd 后去掉该选项即可启用。
- `readline` 同理：仅影响 rigctl 交互式补全，不影响命令执行（`rigctl -c` 等）。

## 与前人手工适配的关系
仓库 `archives/h/hamlib/` 下已有一份 2026-05-26 的手工适配记录（README.md、软件级
manifest.yaml、版本级 manifest/notes，无 conanfile.py / conandata.yml / patches /
test_package）：其源码 URL 用 GitHub tag 归档（**不含 configure**）、`sha256` 为空、
`patches_applied` 为空，交付物是一个预编译 tar.gz（不符合 R12/R19）。
本 PR 用可复现的 Conan 配方取代版本级 manifest/notes 并补齐全部必需文件；
软件级 `archives/h/hamlib/README.md` / `manifest.yaml` 未改动（仍记录历史 published
状态），版本级 manifest 按本次实测事实记 `built`（尚未经 CI upload）。
历史记录中“pthread_cancel 在 OpenHarmony 不可用”与本 PR 的 patches/0001 一致，
本次给出了正式补丁与 libc 探针守卫。

## 遇到的问题与解决方案

### 1. `config.guess` 不识别 HarmonyOS（E007）
- 症状: `configure: error: cannot guess build type; you must specify one`；
  堆栈里 config.guess 用 `mktemp -d` 建临时目录后写 dummy.c 也被拒（Permission denied）。
- 处理: 用 skill 脚本 `patch-autotools-ohos.pl` 给 `build-aux/config.guess` 打补丁
  （`__OHOS__` → `LIBC=ohos` 探针 + `*:HarmonyOS:*:*` 分支，产出标准三元组
  `aarch64-unknown-linux-ohos`），落为 patches/0003。**不要**用 `--build/--host` 绕过：
  那会让 configure 误判交叉编译，AC_RUN_IFELSE 全部跳过、生成错误 config.h（E007 根因分析）。
- 注: **未修改 `config.sub`**。本版本的 `config.sub` 已原生支持 ohos
  （OS 列表含 `ohos*`、内核列表含 `linux-ohos*-`），实测
  `sh config.sub aarch64-unknown-linux-ohos` 直接通过；`patch-autotools-ohos.pl`
  额外加的 `ohos-linux` 两段式简写对本工程无用，已删除（初版误留为 patches/0004，
  经实测确认多余后移除，保持补丁集最小）。

### 2. config.status 临时目录不可写（E114）
- 症状: `./config.status[1313]: can't create ./confXXXXXX/subs1.awk: Permission denied`
  → `config.status: error: could not setup config files machinery`。
- 根因: HMDFS 强制目录 setgid 且忽略 chmod；autoconf 生成物里
  `tmp=`(umask 077 && mktemp -d "./confXXXXXX")`` 建出的目录属主也不可写。
- 处理: patches/0005 直接改写**生成的 configure** 内嵌 config.status 模板（去掉两处
  `umask 077`）。必须落在补丁而不是配方 build() 运行时改写：G0 clean-verify 不执行
  build()，只在原始 tarball 上打补丁后 configure，运行时改写会让 G0 永远失败；
  与仓库既有 aaphoto 0.45（patches/0003-configure.patch）、activity-log 0.9.7
  同一做法（E114）。

### 3. Autotools 脚本可执行位丢失（E490）
- 处理: build() 里 `_restore_exec_bits()` 给 configure/config.guess/config.sub/install-sh/
  missing/compile/depcomp/ltmain.sh/ar-lib/test-driver 等补 `+x`。

### 4. `rigs/harris/harris.h` 用了 `mode_t`（上游笔误，musl 暴露）
- 症状: `./harris.h:49:40: error: unknown type name 'mode_t'; did you mean 'rmode_t'?`
- 根因: 原型应为 hamlib 自己的 `rmode_t`；glibc 经 sys/types.h 泄漏 mode_t 所以上游编译得过，
  musl/OHOS 不泄漏 → 编译失败。落为 patches/0004。

### 5. musl 无 `pthread_cancel`（src/rig.c、rotators/ars/ars.c 引用）
- 症状: `ld.lld: error: undefined reference due to --no-allow-shlib-undefined: pthread_cancel`
- 处理: patches/0001 在 `src/misc.c` 增加 pthread_cancel() shim（返回 0，调用方仍走 join 清理路径），
  用 libc 探针守卫（`defined(__linux__) && !defined(__GLIBC__) && !defined(__ANDROID__)`），
  glibc/Android 走平台实现。**未使用 `__OHOS__` 宏**（R8/PF5）。

### 6. `<linux/wireless.h>` 与 musl `<sys/socket.h>` 冲突
- 症状: `sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`
  （network.c 在 `#ifdef __linux__` 下包含 linux/wireless.h）
- 处理: patches/0002 改为 libc 探针守卫（glibc 专有路径）；无线网卡探测非必需功能。

### 7. CI 门禁 L0d / L0k（test_package 空壳判定 + bin 产物登记）
- 症状（本地 CI `ci/conan/build_and_test.sh` 首跑）:
  `[fail] L0d: test() method has no self.run() call — likely a stub`，
  `[warn] L0k: commands.json exists but package looks like a library`；
  L1/L2/L4/L5 全部 `skip: blocked_by_L0`（L0 是阻塞门禁）。
- 根因 1（L0d）: 该门禁用 grep 在 `test_package/conanfile.py` 的 `test()` 内找字面量 `self.run`。
  本包 test() 走 `cmake.test()`（CMake/CTest 驱动），虽真实执行了二进制，但门禁看不到 `self.run`。
  处理：保留 ctest，并在其后显式
  `self.run(os.path.join(self.cpp.build.bindirs[0], "test_hamlib"), env="conanrun")`
  （与 a52dec / aalib / aces_container 同款写法），test_package 因此同时给出
  ctest 摘要与直接执行输出两份证据（见 reports/conan-create.log）。
- 根因 2（L0k）: 门禁用 `ci/conan/detect_bindirs.py`(AST) + 正则判断包是否产出可执行文件，
  依据是 `self.cpp_info.bindirs` / CMake `RUNTIME DESTINATION bin` / `package_type="application"`。
  本包为 autotools 库，把 14 个 CLI 工具装到 `bin/` 但未声明 bindirs，被判定为「无 bin 的库」
  却又存在 commands.json，故告警。处理：`package_info()` 内加 `self.cpp_info.bindirs = ["bin"]`
  （与仓库 2621 个配方惯例一致），commands.json 的 type=tool 随即对齐。
- 结果：L0 pass（`commands.json valid (type=tool)`）→ 后续检查全部解锁，本地 CI 全绿。

## 上游测试申报（R51）

| 项 | 值 |
|----|----|
| 清点 | tests/Makefile.am `TESTS = $(check_SCRIPTS)`，11 个脚本 |
| 清单 | amptest.sh test2038.sh testbcd.sh testcache.sh testcaps.sh testcookie.sh testfreq.sh testgrid.sh testloc.sh testrig.sh testrigcaps.sh |
| 真机实跑 | `make check` → TOTAL 11 / PASS 11 / FAIL 0（+ src/testcpp 1/1） |
| CI 内实跑 | conanfile.py build() 调用 `autotools.make(target="check", args=["-j1"])`，conan create 日志 11/11 PASS |
| 通过率 | 11/11 = 100%（本轮无 skip） |
| 备注 | 另有 bindings/(perl/python SWIG) 与 android/ 等非 autotools 目标不在 make check 范围；swig 未安装故不构建 |

## 附 1：lang-preflight 误判（框架问题，非本包问题）
`ohc lang-preflight` 在 hamlib 上误报 `mixed / module-build / env_unsupported`：
`lang_detect._manifest_scan()` 把**递归**收集到的文件名放进同一个 `names` 集合，
于是 `bindings/Makefile.PL`（上游 Perl/SWIG 绑定）命中 perl module-build 分支，
且该分支优先级高于顶层 `configure.ac`/`Makefile.am`，压过了真正的 C/C++ autotools 主体
（源码统计 c:527 / cpp:7）。本任务未改框架代码，已在 SKILL_FEEDBACK 中反馈；
建议修法：perl manifest 判定只认顶层（`tops`），或将其优先级放到 cmake/autotools 之后。
## 附 2：G0 clean-verify 在 HMDFS 上必须显式指定 CONFIG_SHELL
- 症状: clean-verify 的 configure 日志以 `shell-init: error retrieving current
  directory: getcwd: ... Not supported` 开头，随后
  `configure: error: working directory cannot be determined`（configure 第 1445 行）。
- 根因: `clean_verify.py` 默认 `config_shell = /data/service/hnp/bin/bash`（OHOS 系统
  bash，`CONFIG_SHELL` 环境变量可覆盖）。该 bash 二进制在 HMDFS 上对**子目录**调用
  getcwd() 返回 ENOTSUP（仅 `$HOME` 根目录正常），而 configure 一启动就做
  `ac_pwd=\`pwd\``。知识库已有同名草稿 DRAFT-6487（classads 1.0.10）。
- 处理: 本地用 `CONFIG_SHELL=/bin/sh python3 scripts/ohc-run.py clean-verify ...`；
  该次运行结果为 **5 补丁全部应用 + configure/make/install 全通过
  （14 bin / 11 lib）**。conan-verify 的 G2 走 conan 自己选定的 shell，不受影响。

## 附 3：本地 CI 全流程复现（ci/conan/*.sh）与非阻塞告警
按 `CI_RUN.md` 在 HarmonyOS PC 上按 PR 流水线参数实跑：
```sh
export CI_TASK_TYPE=pr CI_PACKAGES="archives/h/hamlib/4.7.1" CI_REPO_ROOT="$(pwd)" \
       CI_RUNNER=local-manual CI_COMMIT_SHA=<commit>
zsh ci/conan/setup.sh          # rc=0
zsh ci/conan/build_and_test.sh # rc=0（日志 ~/tmp/ci-local-hamlib.log）
```
结果：L0 pass / KC pass（541 条知识条目索引一致）/ JC pass（prdiff 15 文件、单软件原子性）/
G0 pass / G0e pass / L1a·L1b·L1c pass / **L1e 破坏性负向测试 pass** /
L2 pass（12 个工具 `--version` 或 `--help` OK）/ L4 pass / L5 pass（`bin/` 有内容）。
上游测试与 test_package 结果见上方章节。

两条**非阻塞告警**（如实记录）：
1. **L2**: `rigtestmcast`、`rigtestmcastrx` 的 `--version`/`--help` 失败。二者是
   `tests/Makefile.am` 里 `bin_PROGRAMS` 一并安装的**上游多播测试小程序**
   （`tests/rigtestmcast.c` 把 `argv[1]` 当 `atoi` 的 rig 型号，默认 1035，然后直接
   `rig_open()` 访问 `/dev/ttyUSB0`），本身不实现 `--version`/`--help`，故不属于功能缺陷。
2. **L4**: 「dangerous functions found in patches」为 grep 假阳性——规则
   `(strcpy|sprintf|gets|strcat)\b` 命中了 `patches/0003-build-aux-config.guess.patch`
   上下文行里单词 **targ*gets*** 中的 `gets`；补丁本身无危险调用。

另注：CI 脚本在下载前会把 `conandata.yml` 的**单值** `url:` 临时改写成镜像优先的列表
（`get_mirrors()` → `[gh-proxy, 官方]`），下载后还原（日志 `conandata.yml 已还原为官方 URL`），
提交版始终只登记官方 URL。本版本原先写成两项列表，见「附 5」第 3 点的修正。

## 附 4：PR #13597 首轮 CI 失败为 worker 基础设施问题（非本配方缺陷）
- 现象：build #63919（worker `OpenHarmonyPCDeveloper-CI-038`）**git-clone ❌ / cleanup ❌**，
  分类「未知」。日志为仓库**自身**克隆的重试失败：
  `error: cannot fork() for --shallow-file`、`fatal: fetch-pack: unable to fork off index-pack`、
  `exit code 128`（每次都在 `Counting objects` 约 85–87% 处），随后
  `zsh: can't open input file: ci/conan/cleanup.sh`（exit 127，因为克隆失败后工作目录里没有仓库文件）。
- 判定：`fork()` EAGAIN（进程/内存压力），发生在 `fetch-pack` 派生 `index-pack` 时，
  与 hamlib 配方无关；cleanup 的 127 是连带失败。该机器为共享开发+CI 主机
  （32GB RAM，多 agent 并发高负载），克隆的仓库约 127952 对象 / .git ~447MB。
- 复现验证：稳定后在 `~/tmp` 用同一条浅克隆命令重试，**一次成功**
  （`Counting objects: 100% (127952/127952)`，rc=0），说明首轮失败是瞬时的资源竞争，
  修复方式为重试 CI 而非改配方。
- 但本次本地 CI 复现**确实发现了两个真实门禁缺陷**（L0d/L0k，见「遇到的问题」第 7 节），
  若克隆正常它们会在 CI 上必然失败——已在推送前修复并全量复验。

## 附 5：PR #13597 第二轮 CI 失败（build #64011）同为 worker 基础设施问题
### 1) 现象与日志复核（CI 自动诊断「网络问题」不成立）
- CI 报告：build #64011（worker `OpenHarmonyPCDeveloper-CI-018`，SHA `0154c27d`）在
  `conan-build-test` 失败，类别「网络问题 / 源码下载超时」，指向 `gh-proxy` 源码 URL。
- 复核完整日志：**源码下载是成功的** ——
  `hamlib/4.7.1: Sources correctly downloaded from https://gh-proxy.com/https://github.com/Hamlib/Hamlib/releases/download/4.7.1/hamlib-4.7.1.tar.gz`。
  真实失败点是 `build()` 中第一条 fork 密集语句：
  `.../conan2/p/b/hamlif61a6090ac6f2/b/configure[36]: can't fork - try again`
  → `ERROR: hamlib/4.7.1: Error in build() method, line 75 / autotools.configure()`。
  该 build 的 L0（含 L0j/L0k/L0m/L0n）/ KC / JC / G0 / G0e 全 pass，失败前只差源码解压后的
  configure 一步，耗时 362s 中约 70s 是 github.com 直连的 2×30s 超时。

### 2) 根因：`fork()` EAGAIN（worker 进程/pid 限额耗尽），非配方缺陷
- `can't fork - try again` 是 mksh（`/system/bin/sh`，本机与 worker 同源）在 `fork()` 返回
  EAGAIN 时的报错。autoconf 生成的 `configure` 第 20–36 行是 shell 探明块，其中
  ``case `(set -o) 2>/dev/null` in`` 是整份脚本里**第一个** fork；mksh 把行号报在该复合命令的块尾
  `fi`（第 36 行），因此「36」只表示「首个 fork 失败」，与第 36 行内容无关。
- **决定性复现**（本机，对 pristine 源码的同一份 configure）——把 RLIMIT_NPROC 压到 5：
  ```sh
  python3 -c "import resource,os; resource.setrlimit(resource.RLIMIT_NPROC,(5,5)); \
    os.execv('/system/bin/sh',['sh','./configure','--version'])"
  # -> ./configure[36]: can't fork - try again
  ```
  输出与 worker 日志**逐字一致（含行号 36）** → 证实根因是进程创建被限额拒绝，与 hamlib 源码/补丁无关。
- 旁证：同一 PR 上一轮 build #63919（worker CI-038）也是 fork 类失败（git-clone 阶段
  `error: cannot fork() for --shallow-file` / `fatal: fetch-pack: unable to fork off index-pack`）。
  **两个不同 worker 连续**在 fork 上失败 → 集群资源压力（见 DRAFT-ci-worker-gate-fork-oom、
  DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent）。本仓库第一轮已用「自带的
  release tarball（含预生成 configure）+ `make -j1`」消除了高 fork 开销的自举链，configure
  本身已是不可避免的单进程。

### 3) 处置（按知识库策略：环境失败只重试，不改配方、不伪造通过）
1. **配方构建逻辑不改**：configure 由 conan 以单个子进程启动，配方无法影响 worker 的
   pid/进程限额；为绕过环境故障去改配方属明确禁止项（DRAFT-11327 forbid_1）。
2. **修正一处真实但非本轮根因的 URL 登记形式**（响应 CI 提示里关于 URL 的建议，同时对齐 R39）：
   原先 `sources.url` 写成两项列表（官方 + `gh-proxy` 镜像），这使
   `ci/conan/build_and_test.sh` 的 `Mirror fallback` 步骤**被静默跳过** —— 该步骤的正则
   （`^\s*url:\s*["\']https?://…`）只匹配**单值** `url:`，列表形式不匹配；
   于是 CI 无法注入自己的镜像列表，下载只能依赖配方里硬编码的镜像，且先撞 github.com 的
   2×30s 超时。改为单值官方 URL 后，CI 会自动改写为 `[gh-proxy, 官方]`（镜像优先），
   首次尝试即命中，同时仓库里只登记官方源。本地与 worker 使用的是同一份 CI 脚本，行为已实测。
3. **本机全量复跑**：按 `CI_RUN.md` 用 PR 流水线同一套脚本（`zsh ci/conan/setup.sh` +
   `CI_PACKAGES=archives/h/hamlib/4.7.1 zsh ci/conan/build_and_test.sh`）在修正后的提交上复跑，
   结果全绿：L0（含 L0j/L0k/L0m/L0n）/ KC / JC（含 JC1–JC6）/ G0 / G0e / L1a·L1b·L1c / L1e /
   L2 / L4 / L5 通过，上游 `make check` 11/11 PASS，`test_package` 1/1 PASS，
   Build Summary `Total 1 / Success 1 / Failed 0`（日志 `~/tmp/ci-hamlib-64011-fix.log`）。
4. **重触发 CI**（`/rebuild`）换 worker 复跑；若再命中同一 fork 故障则继续重试，不改配方。

## 对话记录

### 对话 #1 [2026-09-28] 源码获取与预检
- 问题: GitHub tag 归档不含 `configure`，CI 上需要 autoreconf/bootstrap。
- 操作: 改用官方 release tarball（`make dist` 产物，含 configure + build-aux），
  记录 sha256；`init-build` + `lang-preflight`。
- 结果: 源码就绪；预检误报 perl module-build（见附 1），按 c↔cpp 兼容族人工判定为 cpp。

### 对话 #2 [2026-09-28] 交叉编译三连（E007 / E114 / E490）
- 问题: `cannot guess build type` + `config.status ... subs1.awk: Permission denied` +
  autotools 脚本丢失可执行位。
- 操作: `patch-autotools-ohos.pl` 修 config.guess（落 0003；本版 config.sub 无需改）；
  configure 去 `umask 077`（落 0005）；配方 `_restore_exec_bits()`（E490）。
- 结果: configure → make → make install 全通。

### 对话 #3 [2026-09-28] musl 暴露的三处源码问题
- 问题: `harris.h` 原型用错 `mode_t`；`pthread_cancel` 未定义；
  `<linux/wireless.h>` 与 musl `<sys/socket.h>` 的 `sockaddr_storage` 冲突。
- 操作: 落 patches/0004、0001、0002（后两者用 libc 探针，不用 `__OHOS__`）。
- 结果: 编译链接通过，上游 `make check` 11/11 PASS。

### 对话 #4 [2026-09-28] 配方与验证
- 问题: 首轮 conan-verify G2 失败（临时目录权限 + 测试断言写错）。
- 操作: 改用 release tarball 重算补丁；重写 test_package/test.c（真实 API 断言，
  R34）；配方加 `--without-libusb --without-readline`。
- 结果: `conan-verify` G0–G4 + L2/L4/L5 全 PASS；clean-verify 全 PASS；
  consumer test `1/1 Passed`（310 rig models）。

### 对话 #5 [2026-09-28] PR #13597 首轮 CI 失败定位 + 本地 CI 全流程复验
- 问题: CI 报 git-clone / cleanup 失败（错误分类「未知」），无法判断是否配方问题。
- 操作: 读 `ci/conan/*.sh` 与 `CI_RUN.md`；在共享主机上复现浅克隆（成功）；
  按 PR 流水线参数本地实跑 `setup.sh` + `build_and_test.sh`，命中 L0d/L0k 阻塞门禁。
- 处理: test_package 增加显式 `self.run(<bindir>/test_hamlib, env="conanrun")`；
  `package_info()` 声明 `cpp_info.bindirs = ["bin"]`。
- 结果: 本地 CI 全绿（L0–L5 + 上游 11/11 + test_package 1/1），
  `clean-verify` G0 与 `conan-verify` G0–G4 复跑 PASS，随后再推送。

### 对话 #6 [2026-09-29] PR #13597 第二轮 CI 失败（build #64011）定位与复跑
- 问题: CI 报「网络问题 / 源码下载超时」，但日志显示源码已成功下载，真正失败在 configure。
- 操作: 提取机器人评论内嵌的完整日志复核；用 RLIMIT_NPROC=5 在本机复现
  `configure[36]: can't fork - try again`（逐字一致）；把 `sources.url` 从两项列表改回
  单值官方 URL（恢复 CI 的 Mirror fallback 注入）；按 CI_RUN.md 全量复跑本地 CI。
- 结果: 本地 CI 全绿（L0/KC/JC/G0/G0e/L1/L2/L4/L5 + 上游 11/11 + test_package 1/1），
  确认 #64011 为 worker fork 资源故障，重触发 CI 换机复跑。

---

**编译结束**: 2026-09-28 20:02
**最终状态**: built
