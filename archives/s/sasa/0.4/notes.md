# sasa 0.4 适配笔记

## 基本信息

- **适配状态**: built (待真机预检确认)
- **适配版本**: 0.4
- **用户名**: dIT8Zv
- **队伍**: NebulaAGI
- **构建系统**: Makefile（纯 make，无 configure/cmake）
- **语言**: C
- **上游仓库**: https://git.devuan.org/leepen/standalone-socket-activate
- **源码归档**: https://deb.debian.org/debian/pool/main/s/sasa/sasa_0.4.orig.tar.gz
  （sha256 adbfbcd2aea5ff6951707f04b26f5cbca850ed5801d2bfee45470b75313ced7c，
  内容为纯上游 0.4 源码，无 Debian 打包文件）

## 编译环境

- 构建系统: makefile
- 编译日期: 2026-09-18
- 编译器: clang
- 状态: built

## 项目概况

sasa（standalone socket-activate）是对无 systemd 的 Unix 系提供独立
systemd 风格 socket-activation 实现的小型 C 工具。生成单个 CLI 二进制
`socket-activate`，遵循系统 `sd_listen_fds` 环境变量 + 文件描述符约定，
不依赖 systemd 源码。GPL-3.0-or-later 许可。

## 编译步骤

```bash
conan create . --profile:host <OHOS-profile> --profile:build <native-profile>
```

配方内 build() 实际命令：
1. `make -C <src> CC=<clang> CPPFLAGS='-D_POSIX_C_SOURCE=200809L
   -D_XOPEN_SOURCE=700 -D_DEFAULT_SOURCE -D_GNU_SOURCE'
   CFLAGS='-O2 -g -pipe -std=c99 -Wall -W -Wextra' src/socket-activate -j1`
   —— 只构建二进制目标，规避 man 页目标对 pandoc 的依赖（工具链无 pandoc）。
2. `_run_upstream_tests()`：运行上游 `make check` 的 5 个 bash 脚本
   （tests/basic、options、cmdline、unix、inet），逐脚本统计 PASS/FAIL，
   输出 `HMBS_UPSTREAM_TEST_RESULT` 硬门禁标记。
3. `package()`：把 `src/socket-activate` 复制到 `bin/`。

## 设计要点

- **package_type = "application"**：sasa 产出 CLI 二进制（socket-activate），
  非库。`package_info()` 声明 `cpp_info.bindirs = ["bin"]`（R38 工具类约定）。
- **software 级 commands.json**：工具型包必须提供（R38），
  `archives/s/sasa/commands.json`，type=tool。
- **R33**：编译器从 Conan conf `tools.build:compiler_executables`（dict）获取，
  不裸用 shell 环境变量 CC/CFLAGS。
  - 坑：`self.conf.get("tools.build:compiler_executables:c", ...)` 在 conf 未配置时
    抛 `[conf] '...:c' does not exist in configuration list`，导致 conan create
    build() 直接失败。正确做法是读取整个父键
    `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)`
    再自行索引 `.get("c", "clang")`（与仓库内已验证配方 adolc/abuild-sudo 一致；
    亦见 knowledge/drafts/E6340 dict-form-conf-read）。
  - 加固：`_compiler_c()` 对 `self.conf.get` 整体 try/except 包裹（读 conf 出任何
    异常都不让 build() 失败），并回退 `CC` 环境变量、最后才是裸 `clang`。
    `_run_upstream_tests()` 注入 `env["SOCKET_ACTIVATE"]=` 内置二进制绝对路径
    （测试脚本缺省 `socket-activate` 不在 PATH 上，不注入必然全 FAIL）。
- **R9**：make 用 `-j1`。
- make 用 hmbs 注入的 `HMBS_MAKE` 绝对路径（缺省回退 `make`）。

## 上游测试

上游 `make check` 目标运行 tests/ 下 5 个 bash 脚本，每个脚本用 `set -e`，
内部任一断言失败即非零退出，因此逐脚本统计通过/失败：

| 脚本 | 内容 |
|------|------|
| basic | UNIX socket 激活，验证 LISTEN_FDS/LISTEN_PID/LISTEN_FDNAMES 环境变量 |
| options | socket mode 选项应用到生成的 UNIX socket |
| cmdline | --help / --version / --features 输出与退出码 |
| unix | UNIX 双 socket 激活（test_python.py 消费者），mellon/friend |
| inet | TCP/UDP socket 激活（test_python.py 消费者） |

每个脚本计 1 个测试用例，共 5 个。测试依赖：bash、diff、python3
（unix/inet 用 test_python.py）、netcat openbsd（nc -U 等）。python3 优先用
hmbs 注入的 `HMBS_PYTHON3` 并把其目录前置到 PATH；bash 用 CONFIG_SHELL/
BASH（OHOS 上为 /data/service/hnp/bin/bash），缺省回退 `bash`。

HMBS 硬门禁标记：
- `HMBS_UPSTREAM_TEST_RESULT`：build() 内 `_run_upstream_tests()` 逐脚本跑完
  上游 5 个测试后输出（status/framework/discovered/executed/passed/failed/
  skipped），数字来自真实 harness 输出，不硬编码。
- `HMBS_TEST_PACKAGE_RESULT`：test_package/conanfile.py 内执行 test_sasa
  （--version / --help 两检查）后输出，discovered/passedCount=2。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | all/man 目标需要 pandoc | 工具链无 pandoc，man 页生成依赖 pandoc | 只构建 `src/socket-activate` 二进制目标，跳过 man 页 |
| 2 | 纯 Makefile 项目无 configure | 项目无 configure/cmake 脚本 | 直接 make + 显式传 CPPFLAGS/CFLAGS（保留 POSIX/GNU feature 宏） |
| 3 | conan create build() 抛 `[conf] 'tools.build:compiler_executables:c' does not exist in configuration list`（compile 阶段失败） | 对 `tools.build:compiler_executables` 的子键 `:c` 做 `self.conf.get` 标量读取；conf 未配置时 Conan 抛异常而非返回默认值 | 改读整个父键 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 再 `.get("c","clang")`（与仓库已验证配方 adolc/abuild-sudo 一致） |

## 待真机确认项（非本轮可决）

- 上游测试脚本依赖 `nc`（openbsd netcat，-U 等选项）与 `bash`；
  unix/inet 依赖 `python3`。若真机缺 nc 或 bash 行为有差异，需在后续轮次
  适配（如 vendor/替换），或以如实结果在 PR「补充说明」注明。
- 测试脚本使用 bash 进程替换 `<(...)`、`env -i`、`jobs -p` 等特性，需真机
  bash 支持；若有差异按真机日志最小适配。

## 真机预检记录

- 首轮：工作树已完成（conanfile/conandata/manifest/test_package/notes/
  commands.json/pr-body 草稿），待 hmbs 真机预检。
- 首轮预检结果：failed（compile 阶段）——根因即上面 #3 的
  `tools.build:compiler_executables:c` conf 异常，已修复（读取整个父键 dict）。
- 环境项：预检日志含
  `/preflight.sh[306]: can't open /proc/<pid>/cmdline` 与
  `can't create temporary file /tmp/shwdf5y9.tmp: Read-only file system`
  —— 来自 hmbs 预检 harness 自身 shell（其行 306），非本配方/上游测试。
  上游 tests/* 均不写 /tmp（只写 tests/stdout、tests/stderr 与 tests/ 下
  socket，都位于源码目录）；本配方也无硬编码 /tmp 写入。
  hmbs 注入 `TMPDIR/TMP/TEMP` 供临时文件使用。

## 交付物

- `archives/s/sasa/commands.json` — 工具声明（R38）
- `archives/s/sasa/manifest.yaml` — 软件级元数据
- `archives/s/sasa/0.4/conanfile.py` — Conan 配方
- `archives/s/sasa/0.4/conandata.yml` — 源码 URL + sha256
- `archives/s/sasa/0.4/manifest.yaml` — 版本级元数据
- `archives/s/sasa/0.4/notes.md` — 适配笔记
- `archives/s/sasa/0.4/test_package/conanfile.py` — 消费者测试入口
- `archives/s/sasa/0.4/test_package/test.c` — CLI 冒烟测试（--version/--help）
- `archives/s/sasa/0.4/test_package/CMakeLists.txt`
- `archives/s/sasa/0.4/test_package/MANIFEST.yml` — 上游测试声明


## 第二轮真机预检修复（2026-09-18）

- 上轮遗留：`_run_upstream_tests()` 用 `_bash_path()` 跑 `tests/<script>`，
  真机上 `_bash_path()` 解析成 `/bin/sh`（非 bash），导致：
  1) `nc: inaccessible or not found` —— OHOS 的 PATH 上没有 netcat。
  2) `syntax error: unexpected '('` —— tests/unix、tests/inet 用了 bash
     进程替换 `<(...)`，/bin/sh 不识别。
  3) `Path too long for a Unix-domain socket` —— conan 源码路径过长，
     `${PWD}/tests/sock` 超出 AF_UNIX 108 字节限长。
  4) `[readonly_tmp]` 诊断 —— /tmp 只读（来自 preflight harness），应使用
     hmbs 注入的可写 TMPDIR/TMP/TEMP。

- 根因确认：真机上 `nc` 不存在、无支持进程替换的 real bash、conan 构建/
  源码目录过长、/tmp 只读。这些是 OHOS 平台缺失项，并非产品 bug。

- 解决方案（keep every upstream assertion，只做真机最小适配）：
  * 在 hmbs 注入的可写 TMPDIR 下创建短路径 workdir，把 tests/ 复制进去，
    从该短目录运行，解决 AF_UNIX 108 字节限长。
  * 提供 python netcat 站替（NC_SHIM_SRC，内嵌于 conanfile），真正连接
    socket-activate 打开的 socket 并转发 child 输出，替代缺失的 `nc`。
    `nc -U <sock>`、`nc -4 -W<N> host port`、`nc -4 -W<N> -u host port`
    三种调用形态均已覆盖。
  * 把上游脚本的 bash 进程替换 `<(...)` 机械改为临时文件
    （如 `diff <(exp) <(sort ...)` -> 先写 tests/expected、tests/actual 再
    diff；`diff -u - <(echo x)` -> `printf '%s\n' x > tests/exp` 再 diff），
    断言含义逐字节保留。
  * 把 `jobpid="$(jobs -p)"` 改为 POSIX `$!`（非交互 sh 无作业控制）。
  * 用 hmbs 注入的 `SHELL=/bin/sh`（回退 /bin/sh）逐脚本运行，并给子进程
    设 TMPDIR/TMP/TEMP=workdir。

- 本机（Linux/dash）已做动态验证：真实 socket-activate 二进制下 5 个脚本
  全部 PASS（rc=0）；把被测二进制换成 `exit 1` 桩后 5 个脚本全部 FAIL——
  证明断言真实作用于被测二进制（非空文件比空文件、非静默跳过）。
- MANIFEST.yml 的 upstream_test_command 已同步为
  `SOCKET_ACTIVATE=<built>/src/socket-activate /bin/sh <TMPDIR>/tests/<script>`。


## 第三轮真机预检修复（2026-09-18）

- 上轮真机预检：upstream_test 失败，5 个用例 2 过 3 败（basic、options、unix FAIL；
  cmdline、inet PASS）。
- 失效分析：本地 Linux(dash+mksh) 在全新 workdir 下逐脚本 + 整个 5 脚本顺序执行
  均 PASS（真实 socket-activate 二进制）；但真机 OHOS 上 basic/options/unix 失败、
  inet 通过。失败集与通过集的关键差异是 **socket 类型**：basic/options/unix 都用
  AF_UNIX 监听 socket 并用 nc 站替 -U 连接，而 inet 用 TCP/UDP、cmdline 无网络。
  因此根因收敛到 OHOS 上 AF_UNIX 测试路径的真机特有差异，而非 shell 语法移植
  （POSIX 移植在 dash/mksh 均验证通过）。
- 本轮改动（不删除任何上游断言、不静默跳过）：
  1) nc 站替 (NC_SHIM_SRC) 新增 `connect_retry()`：对 AF_UNIX 与 TCP 的连接在
     短窗口（默认 2s，-W 指定则用之）内带 50ms 退避重试，容忍 OHOS 上 socket-activate
     启动/绑定慢于脚本 `sleep 0.1` 造成的连接竞态（真实 ENOENT/ECONNREFUSED
     可能是假失败）。若 socket 真不出现，重试耗尽仍以失败退出，断言不会被掩盖
     （用 exit 1 桩验证过：basic 在桩下 rc=1 正确判败）。
  2) `_run_upstream_tests()` 改为逐脚本独立捕获输出，失败脚本额外把其自身最近
     40 行输出以 `=== sasa failing script output: <name> ===` 打印到 conan 日志，
     供下一轮确认真实失败的断言内容（而不是只看到 PASS/FAIL 汇总行）。
- 本地回归：接 shim 改动后，dash 与 mksh 下 5 个脚本在全新 workdir 顺序执行全部
  PASS；exit 1 桩下 basic 正确 FAIL（rc=1）。conanfile 与 nc_shim 语法校验通过。
- 待下一轮真机结果确认根因（若仍失败将看到每个失败脚本的具体断言输出）。


## 第四轮真机预检修复（2026-09-18）— 换路线：探测 socket 能力、迁移工作目录

- 上轮真机预检仍失败：5 个用例 2 过 3 败，basic/options/unix 失败、cmdline/inet 通过。
  本轮关键证据（来自失败脚本自身输出）：
  - options/unix：`socket-activate: Could not bind the Unix-domain socket to
    tests/sock-options|tests/sock-mellon: Operation not permitted` —— 这是
    socket-activate 的 connect_unix() 在 bind(AF_UNIX) 时得到 errno=EPERM。
  - basic 的 bind 错误被脚本自身 2>tests/stderr 吸走，只在 nc 站替侧表现为
    `nc: connect tests/sock: No such file or directory`（socket 没 bind 出来）。
  - inet（TCP/UDP，AF_INET bind 成功）与 cmdline（无网络）通过。
- 结论：前 3 轮一直假设失败可经 shell/nc/路径/重试修复，但真正的根因是
  OHOS 沙箱/文件系统对 AF_UNIX(路径名) socket 的 bind() 拒绝（EPERM），且
  HMBS_PLATFORM_CAPABILITIES 显示运行时 tmp 挂载 chmod=0、hardlink=0 ——
  这是一个低 POSIX 能力的挂载，很可能不支持创建 AF_UNIX socket inode。
- 本轮采用与之前不同的实现路线（不再死磕单个 TMPDIR 工作目录）：
  1) 新增 `_afunix_bind_ok(path)`：真实调用 AF_UNIX bind() 探测某目录是否
     支持 socket；
  2) `_candidate_roots()` + `_writable_workdir()`：依次探测 hmbs TMPDIR、
     $HOME、conan build/source 区、tempfile.gettempdir() 等短可写根目录，
     选用第一个真正能 AF_UNIX bind() 的根来建测试工作目录（socket 路径仍
     控制在 108 字节限长内）；
  3) 若没有根支持 AF_UNIX，则 basic/options/unix 如实在日志计为
     `platform-blocked`（不运行、不冒充通过，skipped=3），cmdline/inet 照常
     真实执行；`HMBS_UPSTREAM_TEST_RESULT` 的 discovered/executed/passed/
     failed/skipped 按真实结果填，并打印平台 AF_UNIX 能力结论。
- 本地回归（关键）：用真实编译的 socket-activate + 上述完全相同的适配逻辑，
  从支持 socket 的 /tmp 工作目录运行全部 5 个脚本 → 全部 PASS（rc=0）；把被测
  二进制换成 `exit 1` 桩 → basic/options 正确判败（rc=1、"Connection refused"），
  证明断言真实作用于被测二进制、绝非静默通过。
  → 即只要真机上有任一文件系统支持 AF_UNIX bind，5 个上游用例就都能真实全过；
    若无，则如实按平台受限上报，不做任何伪装。


## 第六轮真机预检修复（2026-09-18）— 换路线：跨文件系统探测 socket 能力根

- 上轮真机预检仍失败：上游测试 5 个用例发现 5、执行 2、通过 2、跳过 3
  （basic/options/unix 因 AF_UNIX bind 平台受限被跳过），
  `HMBS_UPSTREAM_TEST_RESULT={"status":"skipped",...,"skipped":3}`。
  hmbs 硬门禁要求 status=passed、且 executed==discovered==passed、failed=0、skipped=0，
  因此 skipped 上报必然不通过。
- 根因确认（结合 knowledge/E461、E024）：OHOS PC 上写文件系统分为两类——
  1) HMDFS 用户数据区（$HOME 及整个 /storage/Users/...，含 hmbs 注入的
     runtime tmp 与 conan-home）对 AF_UNIX 路径名 socket 的 bind() 返回 EPERM，
     hmbs runtime tmp 还是低 POSIX 挂载（chmod=0/hardlink=0）；
  2) /tmp 为只读 erofs（EROFS）。
  上一轮 `_candidate_roots()` 只探测了 TMPDIR/HOME/conan 区/tempfile.gettempdir()，
  全部落在 HMDFS 或只读 /tmp 上，因此必然“找不到 socket 能力根”→ basic/options/unix
  全部跳过。也正因所有被探测根都是 HMDFS，上一轮“换路线”并未真正换出探测范围。
- 本轮修复：`_candidate_roots()` 在原有探测根基础上，追加 OHOS 上可能承载完整
  POSIX/AF_UNIX 能力的其他文件系统位置：/dev/shm（tmpfs）、/data/local/tmp
  （OHOS adb/系统测试常用，非 HMDFS）、/data、/cache、/sdcard、
  /storage/emulated/0、/mnt/user/0、/data/service/el2、/data/service/el1。
  探测顺序仍是“先 hmbs 注入的 TMPDIR，再其它根”，但任一候选根只要能真实
  bind() 一个 AF_UNIX socket，就把它作为测试工作目录 —— 这样三次 AF_UNIX
  上游测试（basic/options/unix）都能在真实 socket 上完整执行，`options` 的
  `stat -c '%a'` 文件权限断言也得以保留（因为用的是真实路径名 socket 文件）。
- `_writable_workdir()` 重构：
  * 用 `_short_workdir(root)` 在候选根下创建短名子目录（绝对路径 ≤80，保证
    `根/sasat_*/tests/sock-mellon` ≤108 限长）；
  * 无论根名长短都先真实探测 socket 能力（探测用短名，不受根长影响），
    只在探测成功后返回该工作目录；探测失败/Dir 缺失/路径过长都记录到
    failed 列表并在日志输出，不冒充成功；
  * 若无任何根支持 AF_UNIX，保留原“如实平台受限上报”回退（不伪造通过）。
- 本地回归（dash//bin/sh，真实编译的 socket-activate）：
  * 新探测逻辑能从支持 socket 的本地根选中工作目录；
  * 5 个上游脚本全部 PASS，`HMBS_UPSTREAM_TEST_RESULT`
    ={"status":"passed","discovered":5,"executed":5,"passed":5,"failed":0,"skipped":0}；
  * 把被测二进制换成 `exit 1` 桩重跑 → 5 个全部 FAIL（passed=0），
    证明断言真实作用于被测二进制、绝非静默跳过或空文件比空文件；
  * 抽查 basic：tests/stdout 52 字节非空，内容为
    LISTEN_PID=<child pid> / LISTEN_FDS=1 / LISTEN_FDNAMES=test，
    与上游断言逐项对应。
- 若真机上 /dev/shm、/data/local/tmp 等仍被 SELinux 域拒绝 AF_UNIX bind，
  本根因将再次失败并在日志中给出各候选根的 errno；届时再考虑 E461 推荐的
  abstract 命名空间（但 abstract 无文件 inode，会与 options 的 stat 权限断言
  冲突，属最后手段）。
