# samba 4.21.0 适配笔记

## 基本状态

- 构建系统: waf（`configure` 是 wrapper，调用 `buildtools/bin/waf`；顶层 `wscript`）
- 编译器: clang 15.0.4 / clang++
- 目标: 鸿蒙 PC (arm64) 交叉编译 → conan 配方（branch `feat/samba-4.21.0`）
- 依赖: 制品仓 gnutls/3.8.10、zlib/1.3.1（waf configure 强制检查）；perl/5.42.2 tool_requires

## ✅ 核心适配状态（79 ~ 80%：编译层完成）

- **conan create 端到端编绿**：包本体 `Package '74581ffb...' created`
  （waf configure 通过 → waf build 完成 [3571/3571] → waf install 完成）
- **消费者用例（test_package）通过**：conftest（libwbclient 编译+链接+运行，
  SID 字符串往返 OK）+ smbd --version（`Version 4.21.0`）
- **与 resolv-wrapper 完全解耦**：selftest 默认关闭（`--enable-selftest`
  默认 no），resolv/socket/nss/uid/pam_wrapper 等 wrapper 依赖全被
  `ENABLE_SELFTEST` 分支包住，configure/build 根本不触碰。

## waf configure 裁剪参数（conanfile build()）

`--prefix=/ --without-ad-dc --without-ldap --without-json
--without-acl-support --without-ads --without-pam
--without-quotas --disable-cups --without-systemd --without-lttng --without-gettext`

- `--disable-python` 仅**默认变体**（with_selftest=False）传入（鸿蒙无 python
  embedding，同 ldb 2.9.2 适配）；selftest 变体启用 python 绑定（selftest python
  管线依赖 samba/_glue/_ldb/param 等编译扩展，见「selftest 设计」段）
- `--without-libarchive` 仅**默认变体**（with_selftest=False）传入：libarchive 仅
  smbclient tar 模式使用；selftest 开启时 libarchive 是 source3/wscript:204 的
  硬依赖（--without-libarchive + selftest → 直接 WafError），故不传并经
  CPATH/LIBRARY_PATH 消费制品仓 libarchive/3.8.7
- selftest 开启时另加 `--enable-selftest`（见下文「selftest 设计」段）

## 11 个 bugfix 补丁（patches/，配置式/符号级探测，0 处 __OHOS__）

| 补丁 | 内容 |
| --- | --- |
| 0001-lib-replace-wscript | mkstemp 探针修复：用 TMPDIR 而非硬编码 /tmp（/tmp 只读文件系统上失败），安全判定从『恰好 0600』放宽为『属主可读写且组/其他无写权限』，mode 0660 这类真实安全 mkstemp 也能获得 HAVE_SECURE_MKSTEMP，不落入不安全的 rep_mkstemp(mktemp)；探针改为非强制 |
| 0002-lib-socket-interfaces.c | 链路速率查询按 HAVE_ETHTOOL_CMD_SPEED 分支：符号可用走 ethtool_cmd_speed()，否则 *speed=0 兜底 |
| 0003-lib-socket-wscript | 符号级链接探测 ethtool_cmd_speed()（glibc 提供、部分 libc 不提供），define HAVE_ETHTOOL_CMD_SPEED 由工具链真实链接结果决定 |
| 0004-pidl-wscript | yapp 二进制缺失降级为警告（Parse::Yapp::Driver 由配方 vendored 注入，release tarball 带 pre-generated 解析器），不再硬失败 |
| 0005-third_party-cmocka-cmocka.h | cmocka.h uintptr_t typedef 冲突修复：libc 已通过编译器内建宏 __UINTPTR_TYPE__ 提供 uintptr_t 时跳过重复 typedef（__UINTPTR_TYPE__ 为编译器内建宏，非平台宏） |
| 0006-buildtools-wafsamba-samba_third_party.py | uid_wrapper minversion 1.3.1→1.2.5（制品仓仅 1.2.5）：nm 实证 1.2.5 导出符号覆盖 1.3.1 源码全部 selftest 相关截获函数（setuid/setgid/setre*/setres*/getres*/setgroups/getgroups/pthread_create/pthread_exit/uid_wrapper_enabled/uwrap_*），唯一差异 __getgroups_chk 为 glibc fortify 符号、musl 不存在；selftest 经 LD_PRELOAD+UID_WRAPPER=1 环境变量协议工作，不直接调用 wrapper 符号 API |
| 0007-source3-modules-wscript_build | vfs_nfs4acl_xattr 模块按 rpcgen 可用性门控：设备无 rpcgen 二进制（rpc/xdr.h 亦缺失），默认构建本就不启用该模块；无 rpcgen 时跳过 nfs41acl.x→nfs41acl.h 生成任务且不声明该模块（selftest 构建对齐默认构建模块集，无 selftest 套件依赖该模块）；有 rpcgen 的上游构建不受影响 |
| 0008-source3-modules-wscript_build（同文件第二段） | test_vfs_posixacl 自测二进制按 acl 头可用性门控：该测试直接 include vfs_posixacl.c 源文件，需 acl_t 等类型（filesys.h 按 HAVE_SYS_ACL_H/HAVE_ACL_LIBACL_H 条件 include sys/acl.h 或 acl/libacl.h）；OHOS sysroot 无 libacl（两头均不存在，--without-acl-support）→ 无 acl 时不构建该测试二进制（无 selftest 套件运行它，vfs_posixacl 模块无 acl 时本就不构建）；有 acl 平台行为不变 |
| 0009-selftest-wscript | cmd_testonly 对 6 个 wrapper .so 路径变量做 None 防御：pam/pam_matrix 在 --without-pam（OHOS 无 PAM 头）时 configure 整体跳过、变量未定义，原代码 `str + NoneType` 直接崩溃（SELFTEST_EXIT=2，selftest.pl 未启动）；改为逐变量判空、仅已设置项拼入 selftest.pl 选项（nss/resolv/uid/socket 四值实测已设置为裸 .so 名，经 LD_LIBRARY_PATH 解析）；有 PAM 平台行为不变，pam 相关套件按环境受限如实归类 |
| 0010-selftest-optional-python-modules | python/wscript selftest_pkgs（cryptography/pyasn1）缺失模块由 fatal 降级为跳过（required=False）：两模块仅被 AD-DC GPO/GPDI/krb5 加密相关套件运行时 import（gkdi、gp_cert_auto_enroll_ext、krb5 kcrypto/lockout/pkinit），设备 python 无对应系统包（python3-cryptography/python3-pyasn1 不可安装，import 实测 MISSING）；缺失时 COMPOUND_END(False) 跳过、受影响套件运行时 ImportError 按环境受限如实归类；dateutil.parser 实测可用（与 iso8601 二选一检查天然满足）；模块在场时行为不变 |
| 0011-source3-selftest-tests.py | kernel oplocks 判定 None 守卫：非 Linux 平台（OHOS 实测 platform.system()='HarmonyOS'）linux_kernel_version 保持 None，config.h 有 HAVE_KERNEL_OPLOCKS_LINUX 时原代码无条件 compare_versions(None, [5,3,1]) → TypeError 崩溃（selftest.pl 0 tests）；None 时视同无 kernel oplocks，依赖套件按环境受限如实归类；Linux 平台行为不变 |

注：全程 0 处 `__OHOS__`（无平台宏，符合 R8/PF5）；修补均走配置式/符号级/
编译器内建宏探测，CI 可迁移。

## ⚠️ lang-preflight 误判记录（R47 工具缺陷，勿据此终止）

- 误判 `mixed → env_unsupported`。证据：顶层仅 setup.cfg（pycodestyle 样式，
  非打包 manifest），无 setup.py/pyproject.toml；构建系统 waf；主体 C（3969 个
  .c，>78%）。同源 ldb/2.9.2 以 C 库 published 作参照。**判定为误判，继续 C 适配。**

## PIDL 非致命告警说明

`source3/librpc/idl/*.idl: Unable to determine origin of type ...` 是 python
绑定生成器（默认变体 --disable-python 下未参与构建；selftest 变体下 python
启用后若再现同属生成器提示，不影响核心 C 编译与链接）的非致命提示，可忽略。

## ✅ R51 两段式测试申报（诚实口径）

### 第一段（当前，可运行子集 — 已实际执行并验证）

| 项目 | 数量 | 说明 |
| --- | --- | --- |
| 消费者用例（test_package） | 2/2 通过 | ①conftest：libwbclient 编译+链接+运行，wbcStringToSid/wbcSidToString 往返 OK；②smbd --version 输出 Version 4.21.0 |
| waf 编译任务 | 3571/3571 | 全部编译/链接任务完成（含 heimdal、cmocka、popt） |
| 包本体 | created | `Package '74581ffb...' created` |

- 测试命令与日志：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=...`，真实日志在
  `/storage/Users/currentUser/tmp/samba-c27.log`（waf build [3571/3571] +
  install + Package created）与 `.../samba-tp9.log`（test_package 消费者用例
  2/2 通过，含 `Version 4.21.0`）。

### 第二段（全量 selftest — 构建全绿，运行判定环境受限（root/能力集），闭环）

- **5 个 wrapper 全部已发布制品仓**（OHOS armv8 二进制已核验）：
  resolv-wrapper/1.1.8、nss-wrapper/1.1.16、socket-wrapper/1.5.2、
  uid-wrapper/1.2.5、pam-wrapper/1.1.8
- **侦查结论（100% 闭环）**：
  - runner = selftest/selftest.pl（Perl 5.44 设备在位，依赖全为 perl 核心模块 +
    本地 Subunit.pm/SocketWrapper.pm）
  - wrapper 机制走 cwrap LD_PRELOAD（selftest.pl 拼 5 个 --*_wrapper_so_path 进
    LD_PRELOAD，裸 .so 名经 LD_LIBRARY_PATH 解析）
  - **wrapper bundled 版在 OHOS 不可编**：socket_wrapper.c 无条件
    `#include <rpc/rpc.h>` 且 deps 含 tirpc（musl 无 libtirpc）→ 改走
    **系统 wrapper** 路线（见「selftest 设计」段 .pc shim）
  - /tmp 只读 erofs → TMPDIR 指向构建树下可写目录
  - 跑起来才暴露的新硬依赖/阻塞（逐一已解）：libarchive 硬依赖
    （source3/wscript:204 WafError；制品仓 3.8.7）、uid minversion 1.3.1 门限
    （0006 补丁，nm 实证）、libarchive 钉死 zlib/1.3.1.1 与本配方 1.3.1 冲突
    （zlib require force=True 统一整图，默认变体无操作）、rpcgen 缺失
    （0007 补丁）
- **当前状态**：with_selftest=True 构建全绿（configure：socket/nss/resolv/
  uid(>=1.2.5) 五查全 yes + libarchive ok + pyext/pyembed yes；build 4192/4192，
  含 86 个 python 扩展 .so，bin/python/samba/ 实证）；配方端到端 conan create
  复验（verify3）：configure/build 全绿，waf test 真实执行（R9 门禁 `exit $ec`
  生效，SELFTEST_EXIT=255 传播、create 按预期失败）；全量 selftest 运行
  判定**环境受限**（四层独立实测：非 root 能力集层 + root 层设备策略层
  socket() 创建封锁 + 设备工具链/umask/socket wrapper 语义差异）任何可用
  上下文均不可运行，证据链见下
- **实测结果（已回填，不占位）**：
  - 默认变体（CI/制品）：conan create 3571/3571 构建任务全过 + test_package
    消费者用例 2/2（公开 API 编译/链接/运行）
  - selftest 变体：构建 4192/4192 全过（配方端到端 conan create 复验同结论）；
    全量 selftest 四层独立实测均**0 通过**、**0 构建适配问题失败项**：
    手工 run（tap4，非 root）smbpasswd -L root 检查拒绝，0 套件启动；
    配方端到端 run（verify3，非 root）权限 0771≠0755 + messaging context
    失败 + net setlocalsid 256，2 个 blackbox 用例 socket wrapper bind 拦截；
    root 预检（真 root+满能力集）socket() 创建即 EPERM（连 8080 亦拒，
    能力层之下的设备策略层）；root 直跑（run#2）权限层通过（root umask），
    死于 messaging context（IPC socket 被封）+ net setlocalsid 256；
    selftest.pl L896 上游 perl 崩溃（run#2/verify3 均现）；三分类明细见下
- **selftest 运行结论（R51 如实红线，证据链）**：
  1. 实测失败点：selftest.pl 环境创建阶段 `smbpasswd -L can only be used by
     root`（tap4 日志 L68）→ `Unable to create user at Samba3.pm line 3862`
     （L71）→ 环境创建失败，0/133 套件启动；
  2. agent 沙箱内核真值（/proc/self/status）：Uid=20020090、
     CapBnd=0000000000000000（限界能力集为空）→ 进程树无法获得
     CAP_SETUID/CAP_NET_BIND_SERVICE；cgroup=com.huawei.hmos.hishell/app_8174
     （HAP 沙箱标准安全策略）；
  3. uid wrapper 对照实验：LD_PRELOAD 机制本身生效（marker .so 构造器落盘
     实证），但 wrapper 提权（setresuid(0,0,0)）被空限界集挡死，getuid 不变，
     smbpasswd -L 仍拒（sudo 亦同——setuid exec 授 euid=0 但能力集被
     CapBnd=0 截空）；
  4. 用户终端（独立 HiShell 实例）前置检测：sudo 下绑定 445 乃至 socket
     创建均 PermissionError（2026-09-26 实测）→ 设备当前所有可用上下文均
     无完整 root；
  5. smbd 默认监听 445（生成的 server.conf 923 行无 port 覆盖项）；内核特权
     端口检查按能力集（CAP_NET_BIND_SERVICE）而非 uid——部分 root（euid=0、
     CapEff=0）亦无法通过。
  6. 配方端到端复验（verify3，conan create -o samba/*:with_selftest=True，
     日志 sha256 6d7a1dfa4309c2e4…）：configure 全 yes（含 pyext/pyembed）→
     build [4192/4192] 全过 → waf test 真实执行（conan 日志 RUN 行与配方
     源码逐字一致：`exit $ec` R9 门禁生效；SELFTEST_EXIT=255 → ConanException
     Error 255，create 按预期失败）。运行期路径修复前管线实测死于
     format-subunit ImportError（libtasn1.so.6 传递依赖缺失），LD_LIBRARY_PATH
     纳入整图 host 依赖 libdirs 后管线推进至环境 provisioning。
  7. verify3 TAP（sha256 73827eda0c390361…）真实失败点：fileserver/
     nt4_dc_smb1 环境 provisioning 失败——`stat: Unknown option
     'file-system'`（设备 stat 无该选项，非致命：provisioning 继续推进）、
     `invalid permissions ... has 0771 should be 0755`（设备 umask/fs 语义
     与上游 CI（umask 022）差异）→ `Unable to initialize messaging
     context!`（IPC 初始化失败）、`net setlocalsid failed: 256`（连带）；
     selftest.pl 计划 1084（skip/slow 排除后），仅 2 个 blackbox http 用例
     运行（http_server bind OSError Errno 99——socket wrapper LD_PRELOAD
     拦截，上游测试网络隔离设计），余下未运行；selftest.pl L896 perl 崩溃
     （getlog_env on undefined，上游错误处理 bug，仅环境未定义时触发）中止，
     SELFTEST_EXIT=255。
  8. root 上下文获取（2026-09-26 用户终端）：设备 CapBnd 已变为满集
     000000ffffffffff（非 09-25 记录的 0，HAP 沙箱策略变化）；root 终端
     直得 Uid=0 + CapEff=000000ffffffffff（su 不存在，OHOS sudo 需屏锁
     密码 E0003，agent 侧 pty 分配 TTY 成功仍止于认证边界）；root 同挂载
     可见构建树（smbd 符号链接可 ls）。
  9. root 预检（真 root+满能力集，用户终端）：socket() 创建即 EPERM——
     bind 445 与 bind 8080 双双在 socket 构造即 PermissionError（非 bind
     拒绝）→ 能力层之下的设备 seccomp/HAP 策略层封锁，root/满能力集不可解
     （对照：agent 非 root 上下文 socket 创建 OK、8080 bind OK、仅 445 按
     能力集 EPERM——两层封锁互证）。
  10. root 直跑（run#2，root-selftest-run.sh，TAP sha256
      272e3235b74a63d1…）：权限层通过（root umask 下无 0771 报错，第 7 点
      权限失败点消除）、smbpasswd 卡点消除（无 root 检查拒绝）；新首失败点
      `Unable to initialize messaging context!`（IPC socket 创建被第 9 点
      策略层封锁）→ `net setlocalsid failed: 256` → fileserver/nt4_dc_smb1
      环境 provisioning 失败；selftest.pl 计划 1084，blackbox 用例死于运行
      脚本 PATH 缺 python 别名（bash: python: command not found——运行环境
      项，非构建适配问题；补别名后按第 9 点预检证据仍死于 socket 策略层）；
      selftest.pl L896 上游 perl 崩溃（与 verify3 同），SELFTEST_EXIT=1。
      三分类：①环境受限（设备策略层 socket 封锁 → 2 环境 provisioning 失败
      → 1084 中环境依赖套件全部不可运行）②运行环境项（python 别名缺口，
      如实标注）③上游 bug（selftest.pl L896 崩溃）；0 构建适配问题失败项。
- **归属判定**：四层独立实测（非 root 手工 / 非 root 配方端到端 / root
  预检 / root 直跑）失败均卡在测试环境 provisioning 阶段：非 root 层 =
  能力集不足（smbpasswd root 检查、445 bind）；root 层 = 设备策略层
  socket() 创建封锁（messaging context IPC socket，满能力集不可解）+ 设备
  工具链/umask/socket-wrapper 语义与上游 CI（glibc coreutils、umask 022、
  wrapper 完整模拟）差异——均为环境受限、非 OHOS 适配层引入（全部二进制
  正确产出、4192/4192、消费者 2/2），0 构建适配问题失败项。
- 约束：不占位冒充全量，不把可运行子集包装成 CI 通过。

## selftest 设计（conanfile option with_selftest，默认 False）

- 默认变体（CI/制品）：with_selftest=False，不含 wrapper/libarchive 依赖，
  对发布产物零影响（回归门禁验证）。
- selftest 变体（with_selftest=True，R51 第二段，本地证据、非发布制品）：
  - 条件 requires 5 个 cwrap wrapper + libarchive/3.8.7；zlib/1.3.1
    force=True 统一整图，解决与 libarchive 钉死 zlib/1.3.1.1 的冲突
  - .pc shim：制品仓 wrapper 包自带 .pc 的 Libs 指向发布者机器绝对缓存路径
    （本机不存在），配方在 generators_folder 写本地 shim（含 Description
    字段）覆盖，waf CHECK_BUNDLED_SYSTEM（纯 pkg-config 探测）命中系统包、
    跳过 bundled 编译
  - 环境注入（_build_env 集中）：CPATH/LIBRARY_PATH 加 wrapper/libarchive
    include/lib；LD_LIBRARY_PATH = 整图 host 依赖 libdirs（含 libtasn1 等传递
    依赖——python 扩展 .so 链接 gnutls、dlopen 级联，实测缺传递依赖时
    selftest 管线 format-subunit 即 ImportError 死亡，SELFTEST_EXIT=255）+
    selftest.pl 拼装的 LD_PRELOAD 裸 .so 名（wrapper）解析；TMPDIR = 构建树
    selftest-tmp（/tmp 只读 erofs）
  - python 启用（仅 selftest 变体）：waf python 检查走 python_cross_compile
    环境变量旁路（配方构建期查询设备 python3 sysconfig，注入
    PYTHON_VERSION/PYTAG/pyext_PATTERN/PYTHON_PY*FLAGS——常规路径
    python3-config --ldflags --embed 输出 -lintl -ldl，OHOS/musl 无 libintl，
    ld.lld: unable to find library -lintl 实测；旁路后 pyext/pyembed 检查均
    yes 实测）；PERL5LIB 无需配方补 perl 包目录（perl/5.42.2 配方
    buildenv_info 已导出，ST2 实测 PERL_INC 含真实包目录）；PYTHONPATH =
    $B/bin/python:$B/python:$B/source4/selftest:$B/selftest（bin/python
    置前：构建期纯 python 复制进 bin/python/samba/ 并同置 86 个扩展
    .so，构成完整 samba 包；samba/__init__.py 硬 import _glue/_ldb/
    param 等扩展模块，源码 python/ 置前则无 .so 包胜出 → samba.param
    ModuleNotFoundError，实测）；可选模块 cryptography/pyasn1 缺失
    按 0010 降级
  - 执行：`waf test > selftest-tap.log`（末行 SELFTEST_EXIT=<code>）；
    selftest 失败阻断 conan create（R9：不强制通过——selftest 变体是本地
    证据非发布变体，root 受限环境下其 create 失败为预期行为，结论如实
    回填 PR，不占位不冒充）

## 待深入项
- R51 第二段：已闭环——构建全绿（4192/4192 + 86 个 python 扩展 .so）；运行
  判定环境受限（root/能力集）不可运行，证据链与实测数字见上文 R51 段
- manifest.yaml 的 build_system 等字段复核（conan-init/finish 阶段）
---

**编译结束**: 2026-09-20 19:18
**最终状态**: built

## Workaround 记录（诚实申报，非发布产物）

### packaging/samba-4.21.0-ohos-aarch64.tar.gz 仅为满足 submit 自检

- 该 tar.gz **仅用于通过 `submit`（submission.py `_check_packaging_present`）的本地自检**，
  打包自 conan create 生成的**真实产物树**（`conan cache path samba/4.21.0@ohpcd/stable:74581ffb.../p`，
  bin/lib/include/etc/libexec/sbin/private/bind-dns，含 smbd/smbclient 可执行，41MB）；
- 本配方是 **v3.0 新流程（conanfile.py 驱动）**，实际由 conan create 构建与发布，
  **packaging/ 非构建产物、非发布制品**，且已被 `.gitignore` 命中（不入 git / 不入 PR / 不触发 JC）；
- 该 tar.gz 已由 `git check-ignore` 验证命中 `.gitignore:2:packaging/`。

### 工具判标不一致（建议反馈 skill 侧，非本 PR 修改）

- `submit`（submission.py `_check_packaging_present`）在 status=published/built 时**无 v3.0
  conanfile.py 豁免**，强制要求 `packaging/*.tar.gz` 存在；
- 而 `finish`（finish.py）对「有 conanfile.py 的 v3.0 配方」**已豁免** packaging
  （`if conanfile.exists(): log_ok("conanfile.py ✅ (v3.0 配方)")`，不走 legacy 预编译包检查）；
- 两处判定**不一致**：submit 比 finish 严——导致本 v3.0 配方（有 conanfile.py）在 submit 自检
  被 packaging 卡点拦截。
- 建议：`_check_packaging_present` 增加 conanfile.py 存在时的豁免（与 finish 判标对齐），
  或在 skill 侧明确 v3.0 配方的 packaging 非必需；此项建议随 SKILL_FEEDBACK / 知识库反馈
  提交给 skill 维护方（协作方不改 scripts/，遵守铁律）。
