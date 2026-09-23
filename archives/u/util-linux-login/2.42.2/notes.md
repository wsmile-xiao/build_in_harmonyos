# util-linux-login 2.42.2 适配笔记

## 适配日期
2026-08-27

## 适配状态
prepared（前置配方完成，待真机验证）

## 概述

从 util-linux 2.42.2 源码中仅构建 `login` 和 `nologin` 两个可执行文件。

- `login`: PAM-based login program，用于用户认证和会话管理
- `nologin`: 拒绝登录的 shell 替代程序

## 上游源码

- 源码: `https://cdn.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.2.tar.xz`
- SHA256: `03a05d3adf9602ef128f2da05b84b3205ce60c351e5737c0370f74000679ce8a`
- 大小: ~10.2 MB
- 构建系统: Autotools (configure.ac + Makefile.am) 和 Meson 双支持

## 构建系统分析

util-linux 2.42.2 使用 Autotools 作为主构建系统（configure.ac + Makefile.am），
同时也支持 Meson（meson.build）。

### login 构建要求

从 `configure.ac` (行2469-2478) 分析：

```
UL_BUILD_INIT([login])
UL_REQUIRES_HAVE([login], [security_pam_appl_h], [PAM header file])
UL_REQUIRES_HAVE([login], [security_pam_misc_h, security_openpam_h], [PAM conversation functions])
UL_REQUIRES_HAVE([login], [utmpx_h], [utmpx.h header])
UL_REQUIRES_HAVE([login], [gnu_utmpx], [GNU utmpx functions])
```

**硬依赖**: PAM (libpam + libpam_misc)

### 配置策略

```
./configure \
  --disable-all-programs \
  --enable-login \
  --enable-nologin \
  --with-pam \
  --without-systemd \
  --without-selinux \
  --without-audit \
  --disable-bash-completion \
  --disable-nls
```

### 内部依赖

login 链接以下内部静态库：
- `lib_common` (通用工具函数)
- `lib_common_logindefs` (login 定义解析)
- `lib_common_shells` (shell 列表管理)

这些由 autotools 自动构建，无需外部 Conan 依赖。

## OHOS 平台适配

### config.sub
**无需补丁**: v2.42.2 的 config.sub 已原生包含：
- `ohos*` (行2075)
- `linux-ohos*-` (行2219)

### config.guess
**需要补丁**: config.guess 不含 HarmonyOS 检测分支。
补丁在 `*:NetBSD:*:*` case 之前插入 HarmonyOS 检测。

### 源码分析
- `login.c` 使用标准 POSIX 头文件 + PAM 头文件
- `<utmpx.h>` — HarmonyOS 支持
- `<path.h>` — util-linux 自带 (`include/path.h`)
- `<security/pam_appl.h>` — 由 linux-pam 提供
- `<memory.h>`, `<termios.h>`, `<sys/ioctl.h>` — 标准 POSIX

### 预期潜在问题

1. **PAM 模块配置**: login 运行时需要 `/etc/pam.d/login` 配置文件
   - 首次真机测试时需确认 PAM 配置路径
   - linux-pam 最小构建只含 pam_permit 模块

2. **utmpx 实现**: HarmonyOS 的 utmpx 实现可能与 GNU 有差异
   - configure 检查 `gnu_utmpx` 可能失败
   - 可能需要 patch 或 configure workaround

3. **SUID 位**: login 通常需要 SUID root 权限
   - Conan install 可能跳过 SUID 位设置
   - 真机测试时需要手动设置或在 root 下运行

## W0 依赖检查

| 依赖 | 状态 | 版本 | 说明 |
|------|------|------|------|
| linux-pam | ✅ 已构建 | 1.7.2 | L0/L1 通过，issue #1765 |
| autotools | ✅ 环境自带 | - | OHOS worker 自带 |

**阻塞**: linux-pam/1.7.2 需发布到 ohpcd 远端后，`conan create` 才能解析依赖。

## 文件清单

```
archives/u/util-linux-login/
├── manifest.yaml                             # 库级元数据（issue 待补）
└── 2.42.2/
    ├── conanfile.py                          # Autotools 配方（仅构建 login/nologin）
    ├── conandata.yml                         # 源码 URL + SHA256 + 4 个补丁
    ├── manifest.yaml                         # 版本级元数据
    ├── all.config                            # 全局配置占位
    ├── commands.json                         # 真机/shadow 验证命令清单
    ├── notes.md                              # 本文件
    ├── README.md                             # 库说明
    ├── .ci-trigger                           # CI 重建触发标记（空文件）
    ├── configs/
    │   └── util-linux-login.conf             # 运行时配置建议（PAM/SUID 说明）
    ├── patches/
    │   ├── 0001-config-guess-ohos-detection.patch   # config.guess HarmonyOS 检测
    │   ├── 0002-login-guard-updwtmpx-with-HAVE_UPDWTMPX.patch # updwtmpx 受 HAVE_UPDWTMPX 守卫（musl 兼容）
    │   ├── 0003-configure-allow-login-without-gnu-utmpx.patch # 允许 login 在无 GNU utmpx 时构建
    │   └── 0004-login-declare-utmpx-functions-for-OHOS.patch  # 声明 OHOS musl 缺失的 utmpx/getusershell 函数
    ├── reports/                              # 验证报告（待 CI 填充）
    └── test_package/
        ├── conanfile.py                     # L1 测试（编译 login/nologin + 校验 help 输出）
        ├── test.c                           # 最小编译验证源
        └── MANIFEST.yml                     # 测试声明
```

## 本机前置验证（W0 复验 + 静态校验）

> 本机环境说明：无 `ohos-aarch64` Conan profile、无 OHOS SDK 环境变量，且
> `cdn.kernel.org` 下载的 tarball 在本机被污染（sha256 与官方不符），故无法跑真实
> 交叉编译（conan create --profile:host=ohos-aarch64）。以下为静态/元数据层面的本机验证。

| 验证项 | 结果 | 说明 |
|--------|------|------|
| conanfile 语法 / 可解析 | ✅ 通过 | `conan export archives/u/util-linux-login/2.42.2` 成功，recipe 落本地 cache，4 个 patch 一并导出 |
| 源码 SHA256 与上游一致性 | ✅ 通过 | 配方记录的 `03a05d3a…79ce8a` 与 kernel.org `sha256sums.asc`（v2.42）逐字核对一致 |
| linux-pam 依赖可解析（本地） | ✅ 在本地 cache | `conan list "linux-pam/*"` 可见 `linux-pam/1.7.2`；但其 issue #1765 未合并，未发布到 ohpcd remote |
| 分支/目录原子性 | ✅ 通过 | 单库单分支 `feat/util-linux-login-2.42.2`，仅改动 `archives/u/util-linux-login/**` |
| 真实 OHOS 交叉编译 | ⚠️ 本机跳过 | 缺 ohos-aarch64 profile + OHOS SDK；且本机下载源被污染，无法 build |
| CI 端到端验证 | ⛔ 阻塞 | 见下节 |

## 已知限制

1. login 运行时需要 PAM 配置和真实终端
2. 真机上可能需要 root 权限或 SUID 位
3. 最小 PAM 构建（pam_permit only）可能限制实际登录功能

---

## CI 闭环状态与下一步命令

### 当前 CI 状态（2026-08-31 复验）

- 最新本地修复已推送至 `origin/feat/util-linux-login-2.42.2`（与远端 0/0 差异，commit
  `383abd8` "fix(util-linux-login): align conanfile with pipeline expectations…" + `.ci-trigger`）。
- **CI 触发已可用**：通过 `api.gitcode.com/api/v5` POST `/pulls/7031/comments` 发送 `/rebuild`
  成功（note_id 187447721）。`scripts/gitcode_pr.py` 的 `get-comments`/`ci-status`/`trigger-ci`
  子命令对该 token 返回空（疑似脚本仅处理 git push 或权限范围限制），但**直接 POST 评论有效**。
  因此 CI 修复循环可在本机闭环：读失败日志 → 修复 → 推 → POST `/rebuild`。

### 人工触发 / 修复循环命令（在 atomgit PR #7031 页面操作）

1. 若 CI 未自动跑：评论区回复 `/rebuild` 触发（平台已改为需主动评论才启动构建）。
2. 若 CI 失败：根据 `ohpcd-robot` 发的 `## CI 校验失败` 评论中的"失败步骤完整日志"定位：
   - `JC gate 失败` → 检查是否误提交本库外的杂项文件（本库只会动 `archives/u/util-linux-login/**`）。
   - `依赖缺失 / not found in remotes` → 确认 `linux-pam/1.7.2` 已发布到 ohpcd remote
     （依赖库 issue #1765 是否合并）；未发布则先拆 linux-pam 单独适配，**不混入本 PR**。
   - `链接失败 / 编译失败` → 对照 4 个 patch 与 configure 检查（PAM 头/库路径、utmpx、config.guess）。
3. 修复后 `git commit --amend` 或追加 commit + `git push`，再评论 `/rebuild`，循环至 `## CI 校验通过`。

### 真机 / shadow CI 验证命令（待真机空闲窗口）

- 提交 shadow 验证（单次排队）：在 PR 评论区回复 `/build-only` 或走 shadow 流水线，目标包
  `archives/u/util-linux-login/2.42.2`，profile `ohos-aarch64`。
- 真机单包测试（参考 `commands.json`）：
  - 预装依赖：`linux-pam/1.7.2`（提供 `/system/lib/libpam*.so` 与 `/etc/pam.d/` 骨架）
  - 部署 `login` 到 `/system/bin`，`nologin` 到 `/system/sbin`
  - 配置 `/etc/pam.d/login`（最小 pam_permit 策略，仅验证可加载）
  - 验证：`login --help` / `nologin` 退出码非 0（拒绝登录语义正确）
  - SUID：如 login 需 root 信道，真机 root 下或 `chmod u+s`（首次启动避坑见共性问题指南）

### issue 编号

- `manifest.yaml` 的 `issue:` 字段**待补**。本库 issue 编号未在会话/项目文件中明确给出；
  依赖库 linux-pam 的 issue 为 **#1765**（独立 PR，不混入本库）。本库 issue 需从 issue 跟踪系统
  或审核方确认后回填 `manifest.yaml` 与 PR 描述。

---

## CI 修复记录 #1（patch 0004 hunk 解析失败）

- **CI 构建**：PR #7031 / worker #35329 / `conan-build-test` 步骤失败
- **失败原因**：`0004-login-declare-utmpx-functions-for-OHOS.patch` 解析报错
  `extra lines for hunk no.1 at 26 for target login-utils/login.c`（补丁上下文与真实源码不符）。
- **根因**：原补丁在 `#include <utmpx.h>` 与声明块之间、声明块末尾各多插入了一个空行 context；
  而真实 `login-utils/login.c`（2.42.2）中 `#include <utmpx.h>` 之后**直接**是
  `#include <path.h>`（无空行），导致 hunk 上下文偏移累积在 `#ifdef HAVE_LASTLOG_H` 处溢出。
- **修复**：重写 0004，删除多余空行 context，使 hunk 上下文严格为
  `grp.h / pwd.h / utmpx.h / (插入声明) / path.h / (空行) / #ifdef HAVE_LASTLOG_H`；
  old=6, new=21。另修正 `endutxent` 拼写（原误写为 `endutxend`）。
- **本机验证**：用 Python 从 `cdn.kernel.org` 下载真实 tarball（sha256 与官方
  `sha256sums.asc` 一致），提取真实 `login.c`，`git apply --check` + 实际 `git apply` 均通过，
  插入位置正确。
- **提交**：`31891295da` "fix(util-linux-login): correct patch 0004 context to match login.c…"
- **触发**：已 POST `/rebuild` 评论至 PR #7031（note_id 187447721），等待 CI 重跑。

*适配完成时间: 2026-08-27 | 复验与前置验证记录: 2026-08-31 | CI 修复 #1: 2026-08-31*

---

## CI 修复记录 #2（Autotools configure 失败：PAM 头找不到）

- **CI 构建**：PR #7031 / `#33831` (14:34) 与 `#33842` (14:56) 均 `conan-build-test` 步骤失败
  （类别：编译失败 → Autotools configure 失败）。
- **失败原因**（从 `#33842` 完整日志定位）：
  ```
  checking for libuser >= 0.58... no
  configure: error: login selected, but required PAM header file not available
  ```
  configure 的 `AC_CHECK_HEADERS([security/pam_appl.h ...])` 找不到 PAM 头文件，
  导致 login 因 `UL_REQUIRES_HAVE([login], [security_pam_appl_h], ...)` 而报错退出。
- **根因**：原 `generate()` 仅通过 `tc.extra_cflags`（CFLAGS）注入 PAM 的 `-I` 路径，
  configure 检测头文件时用的是 **CPPFLAGS** 而非 CFLAGS；另有一处手动 `export CPPFLAGS`
  追加到 `conanbuildenv-*.sh` 的 hack，不可靠（脚本顺序/覆盖问题），实际未对 configure 生效。
- **修复**：改用标准 `AutotoolsDeps(self).generate()`，它会把 `linux-pam/1.7.2` 的
  `includedirs`/`libdirs` 自动注入到 `CPPFLAGS`/`LDFLAGS` 环境变量，`AC_CHECK_HEADERS`
  与链接阶段均可正确发现 `security/pam_appl.h` 与 `libpam`。保留 `extra_cflags`/`
  extra_ldflags` 作为冗余保险，移除手动 `conanbuildenv` 追加 hack。
- **改动文件**：`archives/u/util-linux-login/2.42.2/conanfile.py`（import 增加 `AutotoolsDeps`，
  `generate()` 末尾调用 `AutotoolsDeps(self).generate()`，删除 glob 改写 conanbuildenv 段）。
- **提交**：`e4ddf7a36f` "fix(util-linux-login): inject linux-pam paths via AutotoolsDeps…"
- **推送**：`f83f300e12..e4ddf7a36f` 已 push 到 `origin/feat/util-linux-login-2.42.2`。
- **触发**：POST `/rebuild` 至 PR #7031（note_id 187452571），等待 CI 重跑。
- **待确认**：下一轮若仍 configure 失败，需排查 (a) `linux-pam/1.7.2` 是否已发布到 ohpcd
  remote 可被解析；(b) `security/pam_misc.h` 是否同样被发现（login 还需 pam_misc conversation）。
  若 `gnu_utmpx` 检测失败（OHOS musl 无 GNU utmpx），`0003` patch 已强制 `ul_haveone_login=yes`
  绕过该 REQUIRES。

*CI 修复 #2: 2026-08-31*

---

## CI 修复记录 #3（源码下载超时：cdn.kernel.org Read timed out）

- **CI 构建**：PR #7031 / `#35419` 本次 `conan-build-test` 失败，但**不再是 configure 问题**
  （AutotoolsDeps 修复已生效，依赖图正常解析 `linux-pam/1.7.2` 并已下载安装）。
- **失败原因**：
  ```
  ERROR: util-linux-login/2.42.2: Error in source() method, line 45
  	get(self, **self.conan_data["sources"][self.version], strip_root=True)
  	ConanConnectionError: Download failed, check server, possibly try again
  HTTPSConnectionPool(host='cdn.kernel.org', port=443): Read timed out.
  ```
  CI worker 从 `cdn.kernel.org` 拉 `util-linux-2.42.2.tar.xz` 时读取超时（网络抖动/源站慢）。
  早期构建 `#33842` 曾成功下载并跑过 configure，故为偶发性源站超时，非配方逻辑错误。
- **修复**：在 `source()` 中为主 URL（`cdn.kernel.org`）增加两个 kernel.org 镜像 fallback，
  循环尝试直到下载成功；保留原 sha256 校验（镜像内容一致）。
  镜像：`mirrors.edge.kernel.org`、`www.kernel.org` 下相同路径。
- **提交**：`426c61a43e` "fix(util-linux-login): add kernel.org mirror fallback for source download…"
- **推送**：`3874428386..426c61a43e` → `origin/feat/util-linux-login-2.42.2`。
- **触发**：POST `/rebuild`（note_id 187453412），等待 CI 重跑。
- **若仍失败**：若镜像同样超时，则可能是 CI worker 整体出网受限，需考虑
  (a) 把 tarball 预置到 ohpcd `/data/cache` 或内部 mirror；(b) 临时重试 `/rebuild`
  等待网络恢复；(c) 确认 `linux-pam/1.7.2` 二进制确实已从 ohpcd 下载成功（本轮日志显示已 Downloaded）。

*CI 修复 #3: 2026-08-31*

---

## CI 修复记录 #4（编译错误：lib/shells.c getusershell 隐式声明）

- **CI 构建**：PR #7031 / `#35466` (2026-08-31) 与 `#35467` 进入**编译阶段**（下载/configure 均过），
  但 `make` 编译失败：
  ```
  lib/shells.c:71:2: warning: call to undeclared function 'setusershell'
  lib/shells.c:72:14: error: incompatible integer to pointer conversion
       assigning to 'char *' from 'int' [-Werror,-Wint-conversion]
     72 |         sp = getusershell();
  lib/shells.c:72:14: warning: call to undeclared function 'getusershell'
  lib/shells.c:74:2: warning: call to undeclared function 'endusershell'
  ```
- **根因**：`lib/shells.c`（`print_shells`/`is_known_shell`，被 login 链接）调用
  `setusershell`/`getusershell`/`endusershell`，这些是 **glibc 扩展**，OHOS 的 **musl libc
  既不声明也不实现**。clang 把隐式声明当 `int`，`getusershell()` 返回 `char *` 触发
  `-Werror=implicit-int-conversion`（实际报 `-Wint-conversion`）。
  之前 #2 的 `0004` patch 只给 `login.c` 加了这些函数的声明，但 `lib/shells.c` 同样需要。
- **修复**：扩展 `0004-login-declare-utmpx-functions-for-OHOS.patch`，新增对 `lib/shells.c` 的 hunk，
  在 `#include "shells.h"` 之后（文件顶部）加入 `__OHOS__` 护卫的 stub 实现：
  ```c
  #if defined(__OHOS__)
  char *getusershell(void) { return NULL; }
  void  setusershell(void) {}
  void  endusershell(void) {}
  #endif
  ```
  因定义即声明，调用点（文件后段）不再隐式声明；stub 提供符号解决链接期 `undefined reference`。
  getusershell 返回 NULL 表示“无额外已知 shell”，行为安全降级。
- **验证**：用真实 `util-linux-2.42.2.tar.xz` 跑 `git apply --check -p1` + 实际 apply，
  两个文件 hunk 均 rc=0 成功。
- **提交**：`d4c1e5ae0a` "fix(util-linux-login): add getusershell stubs in lib/shells.c for OHOS musl"
- **推送**：`acd7379254..d4c1e5ae0a` → `origin/feat/util-linux-login-2.42.2`。
- **触发**：POST `/rebuild`（note_id 187487985），等待 CI 重跑。
- **其它观察**：
  - 日志中 `login.c:617` 有 `vhangup` 未声明 **warning**（非 fatal，CI 未将其作 error），
    若后续成为 error 需另加声明/兼容处理。
  - 下载阶段 CI 出现了 `mirrors.ustc.edu.cn`/`mirrors.tuna.tsinghua.edu.cn` 的 404 噪声
    （CI 环境自带镜像，非本配方问题），最终回退主 URL 成功下载，无需处理。
  - 已成功 `Downloaded binary linux-pam/1.7.2`，PAM 头检测问题已解决。

*CI 修复 #4: 2026-09-01*

---

## CI 修复记录 #5（stub 未生效：护卫宏 __OHOS__ 未被定义）

- **CI 构建**：PR #7031 / `#35710` (2026-09-01 08:44) 由 /rebuild(187487985) 触发，`CI_BRANCH`
  正确为 `feat/util-linux-login-2.42.2`，但**仍报 `lib/shells.c` 的 getusershell 错误**。
- **根因**：#4 的 stub 用了 `#if defined(__OHOS__)` 护卫。OHOS 工具链的 clang **未定义
  `__OHOS__` 宏**（实际 OHOS 标准库为 musl 变体，定义的是 `__musl__`；glibc 平台定义
  `__GLIBC__`）。因此护卫块被跳过，stub 根本没编译进代码，shells.c 依旧隐式声明 int → error。
- **修复**：将 stub 护卫改为 `#if !defined(__GLIBC__)`——`__GLIBC__` 是 glibc 可靠定义的宏，
  非 glibc（musl/OHOS）下必然为 false，stub 一定编译进去；glibc 平台有真实 `getusershell`
  实现则不编译 stub，避免符号冲突。
  （注：login.c 的声明段保持无条件声明，C 允许重复一致声明，且 glibc/musl 下均安全。）
- **验证**：用真实 `util-linux-2.42.2.tar.xz` 跑 `git apply --check -p1` + 实际 apply，
  两个文件 hunk 均 rc=0；应用后 `lib/shells.c` 第17行起正确插入 `#if !defined(__GLIBC__)` stub。
  （过程中修复了 patch 末尾换行导致的 "corrupt patch at line 47" 与 hunk new 行计数 +15→+16。）
- **提交**：`13ddec3754` "fix(util-linux-login): gate getusershell stubs on !__GLIBC__…"
- **推送**：`4a41d1d7f1..13ddec3754` → `origin/feat/util-linux-login-2.42.2`。
- **触发**：POST `/rebuild`（note_id 187494549），等待 CI 重跑。
- **预判**：下一轮若编译通过，可能暴露链接期错误（`updwtmpx`/`logwtmp`/`vhangup`/`getutmp` 等
  utmpx/utmp 相关符号在 musl 缺失）。若如此，需在 0004 patch 中为这些函数补 stub（同 __GLIBC__ 护卫）。
  `login.c:617` 的 `vhangup` 未声明 warning 当前非 fatal，若升级 -Werror 需一并处理。

*CI 修复 #5: 2026-09-01*

---

## CI 修复记录 #6（链接期 undefined symbol：utmpx 系列 + vhangup）

- **CI 构建**：PR #7031 / `#35828` (2026-09-01 10:49→10:58, worker OpenHarmonyPCDeveloper-CI-039)
  由 /rebuild(note 187514679) 触发。分类「编译失败 / 编译错误 (make/gcc)」。
- **本次进展**：configure **完全通过**（`security/pam_appl.h` = yes、`security/pam_misc.h` = yes），
  `make` 编译阶段全部 .o 生成成功，`libcommon*.la` 与 `nologin` 链接成功；
  仅 `CCLD login` 失败。
- **根因**：OHOS 的 musl 变体**只有 utmpx 的声明、没有实现**，且没有 `vhangup`。
  上一版 0004 只补了**声明**（`struct utmpx *getutxent(void);` 之类），
  声明只能消掉 `-Wimplicit-function-declaration` 警告，**不产生符号**，
  因此链接期 `ld.lld` 报 8 个 undefined symbol：

  ```
  vhangup / utmpxname / setutxent / getutxent / getutxline / getutxid / pututxline / endutxent
  ```

  全部 `referenced by login.c (login-utils/login.o:(main))`。
- **修复**：把 0004 中 login.c 段的「声明」改为「**定义**」（no-op stub），并补充 `vhangup`：

  ```c
  #if !defined(__GLIBC__)
  struct utmpx *getutxent(void) { return NULL; }
  struct utmpx *getutxid(const struct utmpx *u) { (void)u; return NULL; }
  struct utmpx *getutxline(const struct utmpx *u) { (void)u; return NULL; }
  struct utmpx *pututxline(const struct utmpx *u) { (void)u; return NULL; }
  void          setutxent(void) {}
  void          endutxent(void) {}
  int           utmpxname(const char *n) { (void)n; return 0; }
  void          vhangup(void) {}
  #endif
  ```

  仍用 `#if !defined(__GLIBC__)` 护卫（沿用 #5 结论：OHOS clang 不定义 `__OHOS__`，
  `__GLIBC__` 才是可靠的 libc 判别宏）。glibc 平台保留真实实现，不产生符号冲突。
- **签名一致性核对**：对照 musl `include/utmpx.h` 的真实声明
  （`getutxent/getutxid/getutxline/pututxline` 返回 `struct utmpx *`，
  `setutxent/endutxent` 返回 `void`，`utmpxname` 返回 `int`），stub 签名逐条一致，
  不会出现 conflicting types；`vhangup` musl 未声明（与 CI 日志的
  "call to undeclared function 'vhangup'" 一致），无冲突风险。
- **补丁格式修复**：工作区里手工改写的 0004 把 shells.c 的 hunk 头写成
  `@@ -14,6 +14,17 @@`，但实际只有 16 行 → `git apply` 报
  `corrupt patch at line 43`，CI 会在 `build()` 的 `apply_conandata_patches()` 处就失败。
  改为**从真实 `util-linux-2.42.2.tar.xz` 源码用 `diff -u` 重新生成**，
  现为 `@@ -46,6 +46,19 @@` / `@@ -14,6 +14,16 @@`，计数自洽。
- **验证**：
  1. 下载真实源码，`sha256 = 03a05d3adf9602ef128f2da05b84b3205ce60c351e5737c0370f74000679ce8a` 与 conandata.yml 一致；
  2. 在干净源码树上按 0001→0002→0003→0004 顺序 `git apply --check` 全部 rc=0；
  3. 实际 apply 后确认 login.c:53-60 出现 8 个 stub 定义、lib/shells.c:22 出现 getusershell stub；
  4. 补丁文件统一 LF 行尾（避免 CRLF 导致 `git apply` 失败）。
- **预判**：链接通过后剩余步骤为 `make install` + `test_package`（L1：编译 `test.c`
  校验 login/nologin 存在且可执行，再跑 `login --help` 且 `ignore_errors=True`）。
  已确认 `test_package/test.c` 已入库且被 `git ls-files` 追踪，`MANIFEST.yml` 声明
  `assertion_count: 2`，预期可通过。

---

## CI 修复记录 #7（login.c 调用 getusershell 系列无声明 → -Wint-conversion 硬错误）

- **CI 构建**：PR #7031 / `#37306` (2026-09-03 10:19→10:32, worker OpenHarmonyPCDeveloper-CI-018)。
  分类「编译失败 / 编译错误 (make/gcc)」。
- **本次进展**：4 个 patch 全部应用成功（日志 `Apply patch (portability): ... 0004...`），
  上一轮的 8 个 utmpx/vhangup 链接错误**已消失**（stub 定义生效）。
  失败点前移到编译期，且只剩 **1 个 error**：

  ```
  login-utils/login.c:1564:2: warning: call to undeclared function 'setusershell'
  login-utils/login.c:1565:14: warning: call to undeclared function 'getusershell'
  login-utils/login.c:1565:12: error: incompatible integer to pointer conversion
                              assigning to 'char *' from 'int' [-Wint-conversion]
          while ((s = getusershell())) {
  login-utils/login.c:1569:2: warning: call to undeclared function 'endusershell'
  11 warnings and 1 error generated.
  ```
- **根因**：`configure` 判定 `checking for getusershell... no`（无 HAVE_GETUSERSHELL），
  而 util-linux 自带的 `include/shells.h` **只声明** `print_shells` / `is_known_shell`，
  **不声明** getusershell 系列——glibc 下它们来自 `<unistd.h>`（_GNU_SOURCE），
  OHOS/musl 下**既无声明也无实现**。
  于是 login.c 走到隐式声明（返回 int）→ `char *s = <int>` 触发 `-Wint-conversion` 硬错误。
  注意：#4/#5 那一版只把 stub **定义**放在 `lib/shells.c`，**没给 login.c 补声明**，
  所以当时即便编译过也会栽在这里。
- **修复**：在 `include/shells.h`（而不是逐个 .c）里补声明，一次性覆盖全部消费者：

  ```c
  #if !defined(__GLIBC__)
  char *getusershell(void);
  void  setusershell(void);
  void  endusershell(void);
  #endif
  ```

  选 `include/shells.h` 的原因：`login-utils/login.c:90`、`login-utils/su-common.c:71`、
  `lib/shells.c:15` 三处都 include 它；且 `lib/shells.c` 的 stub 定义在其 include 之后，
  声明天然先于定义，顺带消掉 `-Wmissing-prototypes` 警告。
- **验证**：重新从真实 tarball 生成 0004（现含 3 个 hunk：login.c / include/shells.h /
  lib/shells.c），在干净源码树上按 0001→0004 顺序 `git apply --check` 全部 rc=0，
  实际 apply 后确认声明在 `include/shells.h:9-17`、定义在 `lib/shells.c:17-25`。
- **当前状态**：本轮日志中 `libcommon*.la` 与 `nologin` 均链接成功，
  仅 login.o 编译失败；修复后预期进入 `make install` + `test_package`。

## 清理记录

2026-09-06 清理了误提交的 archives/u/util-linux-login/2.42.2/.ci-trigger（0 字节空文件），该文件不在 CI JC5 白名单内，会阻塞 junk_check。
