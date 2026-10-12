# DRAFT-tnftpd-20231001-autotools-ohos-triplet-and-hmdfs-shim-adaptation
> autotools 栈在 OHOS 真机的平台微载适配：config.guess/sub 缺 ohos 三元组 + HMDFS 只读/tmp、mktemp fork 不可用、CONFIG_SHELL 重执行 getcwd 失败、install shim 多源 EX_USAGE 的统一修复套路
## 问题特征（真实日志片段/标记）
`HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/6f38303cf380/runtime/tnftpd-20231001/tmp","jobs":1,"install_shim":true,"hardlink":0,"symlink":1,"chmod":0,"local_mktemp":1}`

- config.sub：`KERNEL-OS 组合表与 OS 后缀表均不含 ohos，会把 aarch64-unknown-linux-ohos 判为 "Invalid configuration ... system `ohos' not recognized"`。
- configured failure（HMDFS 只读/tmp）：`写 subs1.awk 报 Permission denied ⇒ "config.status: error: could not setup config files machinery"`（E011/E112/E114 家族；radvd/tarsnap 同法）。
- CONFIG_SHELL 重执行：profile 设 `CONFIG_SHELL=/data/service/hnp/bin/bash`，前导重执行块切换后 `ac_pwd=\`pwd\`` 告崩 `working directory cannot be determined`。
- mktemp fork 不可用：`configure[38]: can't fork - try again`，HMBS 平台诊断为 `unsafe_local_mktemp`。
- install shim 多源 EX_USAGE：`make[2]: *** [Makefile:322: install-dist_exampleDATA] Error 64`；`install -c -m 644 ftpd.conf ftpusers dir/` 触发 `Error 64 (EX_USAGE)`；`ERROR: tnftpd/20231001: Error in package() method, line 198`，`ConanException: Error 2 while executing`。
- 环境性故障（不计入本条增量）：`can't fork - try again`、`sh: /usr/bin/rm: Out of memory`（fork EAGAIN/ENOMEM），与 DRAFT-11327 / ci-worker-gate-fork-oom 同型。
## 根因
autotools 配置链在 OHOS 真机的 HMDFS 与受限 shell 上逐环暴露四个独立平台微载缺口：
1. `config.guess`/`config.sub`（本仓 KERNEL-OS 组合表与 OS 后缀表 timestamp 2018-05-05）不含 ohos 三元组，直接拒绝 `aarch64-unknown-linux-ohos`。
2. HMDFS 只读 `/tmp`，configure/config.status 以 `umask 077` + `mktemp -d ./confXXXXXX` 建的临时目录不可写；且该 FS 下 mktemp 的 fork/建目录能力不可用（`can't fork`），即使 mktemp 成功目录也不可写——原 patch 仅 umask 077→022 仍依赖 mktemp 成功，恰是 FS 不支持的子能力。
3. configure（autoconf 2.69）前导 CONFIG_SHELL 重执行块按 profile 把进程切到 getcwd 失败的 hnp bash，`ac_pwd=\`pwd\`` 失败告崩。
4. HMBS 注入的 `install` shim（`install_shim:true` 能力）只接受单文件两参调用；automake 批量安装 `install -c -m 644 f1..fN dir/` 该 shim 直接 exit 64 (EX_USAGE)，configure 已把探测到的 install 路径写死进生成 Makefile。
另有若干轮为共享真机瞬时 fork EAGAIN/ENOMEM 环境故障，配方已处最低 fork 开销（发行包自带 configure、`-j1`、`/bin/sh`、无 conan 依赖），不构成新增。
## 修复方案（rec）
1. **补 ohos 三元组**：`patches/0001-config.guess-ohos.patch`、`patches/0002-config.sub-ohos.patch` 补 `linux-ohos*` / `-linux-ohos*`，使 `.config.sub` 对 ohos 三元组原样输出、RC=0。
2. **HMDFS 临时目录 mkdir fallback + umask 022**：`patches/0003-configure-hmdfs-umask.patch` 把临时目录块从 `(umask 077 && mktemp -d ./confXXXXXX)` 改为 `mktemp→false` 强制走 mkdir fallback 且两处 umask 077→022（radvd/tarsnap 同法）。
3. **CONFIG_SHELL/SHELL 强制 /bin/sh 直驱**：OHOS 分支用 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh configure` 压过 buildenv，给 make/install 追加 `SHELL=/bin/sh`；`_setup_fs_env()` 置可写 TMPDIR/PWD/SHELL（与 libradsec/radvd 成功先例一致）。
4. **install shim 多源重定向**：`package()` 内写 cp/mkdir install shim，递归把 configure 生成的各 Makefile（`build-release/` 下，含 `build-release/examples/Makefile`）的 `INSTALL = .../install` 重定向到该 shim（`INSTALL_DATA/INSTALL_PROGRAM` 引用 `${INSTALL}` 自动重算），随后 `autotools.install()` 全程走 shim。
5. **验证**：patch 在官方 configure 上 dry-run 校验可干净应用（hunk 行数正确，避免 patch stream is incomplete）；conanfile.py `py_compile`、test.sh `bash -n` 语法校验。
## 禁止策略
- 禁止在 `Invalid configuration ... not recognized` 或 `working directory cannot be determined` 未修复时以 `"status":"passed"` 放行——真机预检 evidence incomplete，任务退回修复循环。
- 禁止把共享真机 fork EAGAIN/ENOMEM 环境故障（`can't fork`、`Out of memory`）伪造为配方改动；应保持配方零改动、仅留 notes.md 证据等待复跑。
- 禁止用 mktemp 成功假设替代 FS 不支持的 mkdir fallback（只改 umask 不强制 fallback 仍会失败）。
- 禁止以 malformed hunk 行数提交补丁（`patch stream is incomplete` / `Failed to parse patch`）。
## 与相近条目的边界（查重）
查重命中表逐条判读为靶向命中但语义相邻不相同：均属平台能力样板（`hmbs_platform_capabilities`/`tmpdir`/`readonly_tmp`）或单点病因条目，无一条命中本条的 ohos 三元组缺失 + CONFIG_SHELL 重执行 + install shim EX_USAGE 组合。本条目为强增量，属可跨库复用的统一套路（radvd/tarsnap/avahi/xeyes/libfec/libdisasm 同类 autotools 库）。
## 适用判断
对依赖完整 autotools 栈（config.guess/sub + autoconf 2.6x configure + automake install 规则）在 OHOS 真机（HMDFS、/bin/sh 受限、install_shim:true）构建的 C/C++ 库适用：缺 ohos 三元组、HMDFS 只读/tmp、mktemp fork 不可用、CONFIG_SHELL getcwd 失败、install 多源 EX_USAGE 任一或组合出现时，采用本条目四环统一修复套路。共享真机 fork/exec 瞬时资源耗尽（`can't fork`、`Out of memory`、EAGAIN/ENOMEM）不适用本条目，归 DRAFT-11327/ci-worker-gate-fork-oom。
