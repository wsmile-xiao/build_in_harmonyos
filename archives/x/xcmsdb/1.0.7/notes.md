# xcmsdb 1.0.7 适配笔记（HarmonyOS PC / ohos-aarch64）

- 任务：xcmsdb 1.0.7（积分赛任务 12064，档位【易】）
- 适配路径：路径 A（直接适配），补丁为声明式 `conandata.patches` + `apply_conandata_patches`
- 构建主机：**B 机**（frp-bar.com:19214，HarmonyOS aarch64）
- worktree：`~/qzy/主理-10-xcmsdb-1.0.7`，分支 `feat/xcmsdb/1.0.7`（本地目录名 `feat/xcmsdb-1.0.7`），基线 `origin/main=48d9cee68`
- CONAN_HOME：`~/tmp/ch/home-z10-xcmsdb`（纯 ASCII）
- 证据区：`~/tmp/uc2/zhuli-10-xcmsdb/`（前任 46 条探针 + 本窗 `verify-*.log`、`finish-*.log`、`pristine/`、`CHECKPOINTS.md`）

## 一、症状

xcmsdb 是 X.Org 官方 app 包（`individual/app/xcmsdb-1.0.7.tar.gz`），GNU autotools 构建，
源码只有 2 个 C 文件（`xcmsdb.c`、`loadData.c`）+ 1 个手册页。上游 tarball 已内置生成的
`configure`，因此不需要 autoconf/automake，但在 HarmonyOS PC 上一键 `conan create` 依次暴露 3 类问题：

1. `configure: error: working directory cannot be determined`（伴随 20+ 行
   `getcwd: cannot access parent directories` 与 `pwd: error retrieving current directory`）；
2. `configure: error: Package requirements (x11) were not met` +
   `Package xorg-macros was not found in the pkg-config search path`；
3. CI 门禁 L0k：`CLI tool detected but commands.json missing (R38)`。

上游 config.guess（2024-07-27 版）不认 `uname -s=HarmonyOS`，config.sub（2024-01-01 版）不认
`ohos` OS 记号——只是本轮没走到那一步就先被 1、2 拦下（补丁 0002/0003 属于家族必做项，
不是可选项）。

## 二、根因

| # | 根因 | 证据 |
|---|---|---|
| 1 | HMDFS 上 conan 建好构建树后，父目录对 `getcwd()` 不可达；autoconf 的 `ac_pwd=\`pwd\` && test -n "$ac_pwd" && …` 判定链因 `pwd` 失败而整体失败 | `archives/x/xcmsdb/1.0.7/reports/conan-create.log` 行 157–176（第一条真实错误 `shell-init: error retrieving current directory`，结论行 `configure: error: working directory cannot be determined`） |
| 2 | 同上目录内 `config.status` 的 `umask 077 && mktemp -d ./confXXXXXX`：HMDFS 新建目录固定带 setgid，0700+setgid 目录连属主都写不进去（E011/E118 家族机制） | 与 `archives/a/adms/2.3.7/notes.md` 第 4/5 行同现象；本轮补丁同时处理两处 |
| 3 | `configure.ac` 用 `PKG_CHECK_MODULES(XCMSDB, x11)` 与 `XORG_DEFAULT_OPTIONS`（内部经 pkg-config 探测 `xorg-macros`），配方未生成 pkg-config 视图，PKG_CONFIG_PATH 里没有依赖的 `.pc` | `reports/conan-create.log` 行 196、202；`configure.ac` 中 `PKG_CHECK_MODULES(XCMSDB, x11)` |
| 4 | 上游无自动化测试：`Makefile.am` 与 `man/Makefile.am` 中 `grep -cE "TESTS\|check_"` = 0 / 0 | `~/tmp/uc2/zhuli-10-xcmsdb/pristine/base/Makefile.am`，读数记录在 `verify-2.log` 之后的一致性复核 |

## 三、最小复现

```sh
# 在 B 机、CONAN_HOME=~/tmp/ch/home-z10-xcmsdb、profile ci/conan/profiles/ohos-aarch64 下
conan create archives/x/xcmsdb/1.0.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# 去掉配方里的 os.environ["PWD"] 与补丁 0001 的 pwd 回退 ⇒ 复现症状 1
# 去掉 PkgConfigDeps / VirtualBuildEnv / tool_requires(util-macros) ⇒ 复现症状 3
```

## 四、已试失败方案（不要重复踩）

1. **复用 libfontenc/1.1.7 的 `0001-configure-umask.patch` 原文**：toybox `patch --fuzz=5`
   不支持（`patch: Unknown option 'fuzz=5'`），且该补丁只改 umask、不含 pwd 回退，
   对本包树应用后 configure 仍停在症状 1。⇒ 必须按本包 `configure` 重算 hunk。
2. **直接沿用别包补丁不重算偏移**：`0003-config.sub.patch`（libfontenc 版）在本包 rc=1，
   因为 xcmsdb 的 config.sub 是 2024-01-01 版，锚点从 `*-eabi* | *-gnueabi*)` 变成
   `linux-gnu*- | linux-android*- | …` 那一行。
3. **写死 `--build/--host` 三元组**（`archives/m/makedepend/1.0.10` 的做法）：本轮**不采用**。
   实测靠 config.guess/config.sub 补丁即可，`config.log` 里 `host='aarch64-unknown-linux-ohos'`
   是补丁真实生效的证据（写死三元组会掩盖 config.guess 失效，CI 干净环境更易假绿）。
4. **在中文路径 CONAN_HOME 下构建**（上一代理所在环境）：本轮全程使用纯 ASCII
   `~/tmp/ch/home-z10-xcmsdb`，未复现前任记录的 toybox sed 行数现象，因此该现象
   **未跨包复现、不作为本包结论、也不落 B 草稿**。

## 五、最终方案

- `patches/0001-configure-hmdfs-pwd-tmpdir.patch`（2 hunk，按本包偏移重算）
  - `ac_pwd=\`pwd\` && …` ⇒ `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd=$PWD` + `test -n "$ac_pwd" &&`
  - `config.status` 两处 `umask 077` ⇒ `umask 022`
- 配方 `build()` 里 `os.environ["PWD"] = self.build_folder`（与 adms/analog 同法，
  与补丁 0001 互为兜底：一个让 shell 内建走逻辑路径，一个让 configure 在 `pwd` 失败时回退）
- `patches/0002-config.guess.patch`：`*:HarmonyOS:*:*` 分支 ⇒ `aarch64-unknown-linux-ohos`
  （能力判定按 `$UNAME_MACHINE` 分派，新增行无 `__OHOS__` 类平台宏）
- `patches/0003-config.sub.patch`（3 hunk）：`ohos-linux)` 归一化 + OS 白名单加 `ohos*`
  + `kernel-$os` 校验表加 `linux-ohos*-`
- `build_requirements()`: `tool_requires("util-macros/1.20.1")`（提供 `xorg-macros.pc`）
- `generate()`: `AutotoolsToolchain` →（OHOS 下显式给 SHELL/CC/CXX/LD/AR/RANLIB/STRIP/NM）
  → `PkgConfigDeps`（libX11 配方已声明 `pkg_config_name=x11`，故生成可用的 `x11.pc`）
  → `VirtualBuildEnv`（把 generators 目录与 util-macros 的 pkgconfig 目录导出进 PKG_CONFIG_PATH）
- `package_type = "application"`，`package()` 里 `make install` + 清 `*.la`/`*.o`
- OHOS 专属 `install` shim（E182/E188 家族，`archives/a/adms/2.3.7` 同法）：HMFS 上带 `-c`
  的 install 直接失败（手册页 `install-man` 退出码 64），因此把生成的 Makefile 里的
  `INSTALL = …` 重定向到 cp/mkdir shim，`INSTALL_DATA`/`INSTALL_PROGRAM` 引用 `${INSTALL}` 自动跟随
- 软件级 `archives/x/xcmsdb/commands.json`（R38/L0k 门禁要求）
- 源 URL 主写 `https://xorg.freedesktop.org/archive/individual/app/…`，且 `url` 写成**列表**
  （躲开单值镜像改写把 xorg 域改到 404 镜像）；sha256 由真机 `curl -L` 下载后实测：
  `2de6f66e1a25b7f6cbfb8f86b0e8da3fab454fc53a71b55a7705caf1a9d5677c`（196217 字节）

## 六、测试五维账本

| 维度 | 读数 | 口径与证据 |
|---|---|---|
| 静态（上游声明） | **0** | `grep -cE "TESTS\|check_"` 在 `Makefile.am`、`man/Makefile.am` 均为 0；automake 只生成空 `check` 目标 ⇒ 上游无可执行测试，不存在"上游 N 项"基线 |
| 可执行 | **5** | `test_package/test.sh` 5 条自造断言，`conan create` 内 `======== Testing the package: Executing test ========` 真实执行 |
| 通过 | **5** | `reports/conan-create.log` 行 135–153：`PASS 1`…`PASS 5`，末行 `declared=5 passed=5 skipped=0 failed=0` |
| 跳过 | **0** | 本轮 readelf 存在故第 5 条实测通过；无 DISPLAY 环境下前 4 条均可执行 |
| 失败 | **0** | 同上 |

`test_package` 断言内容（无头可复现，全部是真断言，不为凑数）：
1. conanrun 环境下 `command -v xcmsdb` 可解析；
2. `xcmsdb -version` 退出码 0 且横幅含 `1.0.7` → 实测 `xcmsdb 1.0.7`；
3. 未知参数 30s 内返回（实测 rc=1 + `unrecognized option`）；
4. **`unset DISPLAY` 后走真 X 客户端主路径 `xcmsdb -query`，必须在 30s 内自行终止**
   → 实测 `rc=1 elapsed=0s`、`Can't open display ''`：**干净报错，不挂死**（超时即 FAIL，不把超时当通过）；
5. `readelf -d` 的 NEEDED 闭包含 `libX11.so.6 libxcb.so.1 libXdmcp.so.6 libXau.so.6`。

## 七、适用边界（不许越界声明）

- 已验证：能在 HarmonyOS PC 上 `conan create` 通过、产物 ELF 与依赖闭包正确、
  参数解析/版本/错误路径行为正确、无 DISPLAY 时干净退出不挂死。
- **未验证**：xcmsdb 的真实功能路径——把 ICC/RGB 颜色表写入 X server 属性并再查询回来。
  xcmsdb 是真 X 客户端（不是只读文本的工具），需要可用 X 会话才能做端到端功能验证；
  本轮**没有**跑过任何写入 X server 的往返，因此本包**只可声明"构建与可执行文件验证通过"**，
  不可声明"功能已验证"。
- 若后续要在真机 X 会话补功能验证，最小动作：起 X 会话后
  `xcmsdb datafiles/sample1.dcc` 写入，再 `xcmsdb -query` 回读比对。

## 八、本地 W3 模拟（build_and_test.sh）另有两个与 conan create 不同源的坑

W3 模拟不是 `conan create` 的重复：它自带"PR 差异扫描 + 源码预下载"两段逻辑，本包各踩中一次。

1. **JC 杂项门禁的 full 模式误扫全仓**：配方尚未提交时 `git diff origin/main...HEAD` 为空，
   `ci/scripts/junk_check.sh` 退回 `ls-files` 全仓扫描，命中基线上**他人**归档的运行时状态文件
   （`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`）
   ⇒ 报 `Junk Files: 2 / junk_check failed`，与本包无关。
   处置：**先把 `archives/x/xcmsdb/**` 精确提交，再重跑 finish**，JC 即转为 diff 模式并放行（实测 ✅）。
   基线脏文件属框架/仓库卫生问题，未自行改动。
2. **预下载把 x.org 镜像表里的 404 页当成 tarball**（阻塞真因，也是**本包提 CI 的已知风险**）：
   `ci/conan/build_and_test.sh` 的预下载会把 `xorg.freedesktop.org/(archive|releases)/…` 改写成
   三个镜像依次试（脚本行 1133 与 1236），而它的验收条件只有 `size > 100`
   ——**既不校验 HTTP 状态码，也不校验 sha256**（行 1272 附近）。B 机实测：

   | URL | http_code | 下载字节 | 内容 |
   |---|---|---|---|
   | `https://xorg.freedesktop.org/archive/individual/app/xcmsdb-1.0.7.tar.gz` | 200 | 196217 | 真 tarball，sha256 `2de6f66e…` 匹配 |
   | `https://mirror.csclub.uwaterloo.ca/x.org/individual/app/…` | 404 | 162 | `<html> 404 Not Found` |
   | `https://www.mirrorservice.org/sites/ftp.x.org/pub/individual/app/…` | 404 | 1796 | HTML 404 页 |
   | `https://mirrors.ircam.fr/pub/x.org/individual/app/…` | 404 | 236 | HTML 404 页 |
   | `https://www.x.org/archive/individual/app/…` | 000 | 0 | TLS/连接失败（鸿蒙机不可达） |

   三张 404 页都 >100 字节 ⇒ 被 `[ok] … (0KB) via mirror 1` 收下并写进
   `.build-cache/predl_cache/2e26e247_xcmsdb-1.0.7.tar.gz`，随后 conandata 的 URL 被替换成该
   `file://`，conan 报 `sha256 hash failed for '2e26e247_xcmsdb-1.0.7.tar.gz'`。
   本轮处置：把**已实测 sha256 匹配的真 tarball**（`~/tmp/uc2/zhuli-10-xcmsdb/dl/`，
   conan 自己会再校验一次哈希，放错文件必然仍然失败）放到该缓存路径，W3 模拟通过
   （`✅ 本地 CI 模拟通过`，日志 `reports/w3-local-ci.log`）。
   **未改 `ci/` 任何脚本**；conandata 仍写官方 URL 列表（`url` 必须是列表：
   单值会被脚本改写，列表不参与改写但**仍会进入预下载**，所以两条路径都要留）。
   ⇒ 遗留风险（交主理/CIW 裁决，不自行改动）：CI runner 上若同样命中 404 页投毒，
   conan 会 fallback 到列表第二条 `www.x.org/releases`；若该域在 CI 侧也不可达，
   本包首轮 CI 可能在源码下载环节红一次，届时按 `/rebuild` 或镜像表修正处理。

## 九、对话记录

### 对话 #1

- 症状：`configure: error: working directory cannot be determined`，日志里 20+ 行 `getcwd` 告警
- 根因：HMDFS 上 conan 建树后父目录对 `getcwd()` 不可达，autoconf 的严格 `pwd` 判定链断裂
- 证据：`archives/x/xcmsdb/1.0.7/reports/conan-create.log` 行 157–176
- 修正动作：补丁 0001 让 configure 在 `pwd` 失败时回退 `$PWD`，配方同时预置
  `os.environ["PWD"] = self.build_folder`（照 `archives/a/adms/2.3.7` 先例，不自己发明）

### 对话 #2

- 症状：`Package requirements (x11) were not met` + `Package xorg-macros was not found`
- 根因：配方没给 pkg-config 视图——`PKG_CHECK_MODULES(XCMSDB, x11)` 需要 `x11.pc`，
  `XORG_DEFAULT_OPTIONS` 需要 `xorg-macros.pc`
- 证据：`reports/conan-create.log` 行 196/202；`conan cache path libx11/1.8.13` 的配方
  第 209 行确有 `cpp_info.set_property("pkg_config_name", "x11")`
- 修正动作：`tool_requires("util-macros/1.20.1")` + `PkgConfigDeps` + `VirtualBuildEnv`，
  改完 `preflight_check.sh` 三依赖全 `[OK] 已发布`

### 对话 #3

- 症状：复用 libfontenc 补丁时 `patch: Unknown option 'fuzz=5'`，`0003-config.sub.patch` rc=1
- 根因：设备 `patch` 是 toybox 实现，无 `--fuzz=N`；且别包 config.sub 是老版本，锚点行不同
- 证据：`~/tmp/uc2/zhuli-10-xcmsdb/logs/regen-0003-config.sub.log`、`p54-patch.sh` 输出
- 修正动作：改用「pristine 树 + 精确文本编辑 + `diff -ruN` 重算 hunk」的补丁生成法
  （脚本 `p54/p55/p56/p61` 与 `gen_sub.py`、`gen_configure.py` 留在证据区），
  三包补丁全部零偏移命中，`grep -c "__OHOS__" patches/*.patch` = 0

### 对话 #4

- 症状：`finish` 停在 Step5，`L0k: CLI tool detected but commands.json missing (R38)`
- 根因：包产出可执行文件，R38 要求软件级 `commands.json`
- 证据：`~/tmp/uc2/zhuli-10-xcmsdb/finish-1.log`、`reports/w3-local-ci.log`
- 修正动作：按 `templates/commands.json.template` 与 `archives/s/strace/commands.json`
  补 `archives/x/xcmsdb/commands.json`（`binary: true`）

### 对话 #5

- 症状：xcmsdb 是真 X 客户端，无头环境跑不了写 X server 的主路径
- 根因：功能面依赖 X server；但参数解析、版本、错误路径、依赖闭包与"无 DISPLAY 是否挂死"
  都可在无头下真验证
- 证据：`reports/conan-create.log` 行 135–153（`PASS 1`…`PASS 5`，
  `PASS 4: -query without DISPLAY terminated rc=1 elapsed=0s`、`declared=5 passed=5 skipped=0 failed=0`）
- 修正动作：`test_package` 用 5 条真断言并把"挂死"设为失败条件；
  在 §七 明确写出"未验证真实写入功能"，不拿编译通过冒充功能验证

### 对话 #6

- 症状：`finish` Step 5 本地 CI 模拟报 `Junk Files: 2 / L0_RESULT=fail: junk_check failed`，
  但列出的三个文件全在 `archives/c/cloog/0.21.1/` 与 `archives/k/kics/2.1.20/`
- 根因：配方未提交 ⇒ `git diff origin/main...HEAD` 为空 ⇒ `junk_check.sh` 退回
  `git ls-files` 全仓扫描（`检查模式: full (85512 个文件)`），命中基线上他人归档的
  运行时状态文件；与本包无关（本包的 `.build-closed`/`.conan-verified`/`.handoff.json`
  均在 `.gitignore` 内）
- 证据：`archives/x/xcmsdb/1.0.7/reports/w3-local-ci.log` 行 75–106、
  `git check-ignore -v` 对四个状态标记的命中行号
- 修正动作：先 `git add -- <精确路径>` + commit（13 个文件），再重跑 `finish`，
  JC 转入 diff 模式后 `[ok]`；未删除任何他人归档文件

### 对话 #7

- 症状：`sha256 hash failed for '2e26e247_xcmsdb-1.0.7.tar.gz'`，随后
  `Error downloading file https://www.x.org/releases/…: CERTIFICATE_VERIFY_FAILED`
- 根因：`ci/conan/build_and_test.sh` 预下载把 `xorg.freedesktop.org/(archive|releases)` 映射到
  三个镜像（脚本行 1133 / 1236），验收只看 `size > 100`（不校验 http 状态码与 sha256），
  而三个镜像对本包全返回 404 HTML（162 / 1796 / 236 字节）⇒ 404 页被当 tarball 缓存
- 证据：`~/tmp/uc2/zhuli-10-xcmsdb/urlprobe/` 五路 URL 实测表（见 §八 表格）、
  `reports/w3-local-ci.log` 行 99–106 与 `conan-create.log` 行 199–210
- 修正动作：把**实测 sha256 匹配的真 tarball**放入 `.build-cache/predl_cache/` 对应缓存名，
  W3 模拟通过；不改 `ci/` 框架脚本、不把 URL 改成 404 镜像；
  遗留 CI 首轮风险与两条候选缓解写进 `NEED-DECISION.md` 交主理裁决

### 对话 #8

- 症状：`finish` 主门禁已绿但 `FINISH_RC=1`，失败步骤 `step5b, step8`
- 根因：step8 `gen_summary` 抛 `'str' object has no attribute 'append'`（框架缺陷，
  非配方问题）；step5b/W5 报的是基线上他人条目 `E219/E253/E305.kv` 字段为空 +
  本包 `manifest.yaml knowledge_gained` 5 条未被图谱引用；Step 10 的三项
  （`reports/test-report.md`、`packaging/` 发布包与调试包、`.staging-verified`）
  是 submit 就绪预检项，同基线上近期合入的 `archives/2/2048.c/1.0.3`、
  `archives/l/libfontenc/1.1.7` 都没有这些产物，属非阻塞
- 证据：`~/tmp/uc2/zhuli-10-xcmsdb/finish-4.log` 行 60–100 与 106–140
- 修正动作：**不在本窗处理**（改 `scripts/` 需另开框架 PR，`packaging/` 会往 PR 里塞二进制，
  与 JC2 冲突）；已在交接与 `NEED-DECISION.md` 列清单交主理/CIW

## finish 收尾块（CIW-1 补记 2026-09-25，应提审门禁 presubmit 判据）

**最终状态**：success——`conan create` 通过（机器可读汇总 `declared=5 passed=5 skipped=0 failed=0`，reports/conan-create.log 行 135–153）；`conan-verify` G0–G4 通过；W3 本地 CI 模拟（B 机 03:05 轮）通过；W4 独立审计 `pass`（P0=0/P1=0/P2=4，见 reports/audit-result.json）。上游无测试套件（0 用例），消费者 test_package 5 用例实跑全过。上文「修正动作：不在本窗处理」所列 scripts/ 与 packaging/ 两项为框架级遗留，不阻塞本包交付态。
