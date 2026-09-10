# c-kermit 9.0.302 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 `makefile`，`make linux` 探测后递归 `linuxa` 构建 `wermit`）
- 编译日期: 2026-09-06
- 编译器: clang（由 Conan `tools.build:compiler_executables:c` 提供，经 `make CC=/CC2=` 命令行传入）
- 状态: built（待真机预检回填实测证据）

## 编译步骤

```bash
# cku302.tar.gz 为扁平包（无顶层目录），conan get 用 strip_root=False
make linux CC=<conan-cc> CC2=<conan-cc> SHELL=<bash> -j1
# 产物 ./wermit → 打包为 bin/kermit；COPYING.TXT → licenses/
```

说明：
- `linux` 目标先探测 `/usr/include` 头与系统库（ncurses/curses/resolv/crypt/lockdev 均按存在性开关），再递归 `linuxa`；
- `linuxa` 硬编码 `CC = gcc`，配方以 make 命令行变量覆盖（GNU make 自动透传给递归 `$(MAKE)`），无需 gcc symlink；
- 缺失的探测项在鸿蒙上自然为空（HAVE_* 为空），不影响核心串口/网络/脚本功能；
- R9：全程 `-j1`。

## 历史经验核验（W0b：archives/c/ckermit/302）

历史 `ckermit/302`（2026-05-28，设备原生工具链，`make linux` 成功）记录 4 处 musl 适配，
经本次源码审计逐项核验，可迁移 3 项（第 2 项当时为自动生成文件，无需移植）：

| # | 历史问题 | 本次核验 | 本配方方案 |
|---|----------|----------|------------|
| 1 | 无 gcc（鸿蒙用 clang） | `linuxa` 硬编码 `CC = gcc` 属实 | `make linux CC=<cc> CC2=<cc>` 命令行覆盖，不创 symlink（CI clean 环境可用） |
| 2 | `stdin->_cnt` 访问错误 | 属实：`cmdgetc` 的 `#undef CMD_CONINC` 使 `cmdconchk()` 走 stdio 窥探分支，musl 下 `FILE` 不透明 | `0002` 补丁：musl 下（`__linux__ && !__GLIBC__`）强制 `CMD_CONINC`，走 `conchk()` 设备检查（OS/2 与 MINIX 已用路径，R8 合规无平台宏） |
| 3 | `getusershell/endusershell` 未定义 | 属实：musl 无此函数族 | `0001` 补丁：musl 下（`__linux__ && !__GLIBC__`）定义 `NOGETUSERSHELL`（接历史方案，R8 合规无平台宏） |
| 4 | `vhangup` 未定义 | 属实：`ckupty.c` 在 `LINUX` 下定义 `CK_VHANGUP` 并调用 `vhangup()` | `0003` 补丁：仅 glibc 下定义 `CK_VHANGUP`，musl 改走 `HAVE_OPENPTY` 探测到的 pty 路径（R8 合规无平台宏） |

环境语义差异：历史成功依赖 `~/usr/local/bin/gcc` 手工 symlink（设备原生环境），
本配方改用 make 命令行变量，CI clean 环境逐字可执行。

## 上游测试审计（R51 三步法之清点）

- 源码包 `cku302.tar.gz`（3122219 字节，sha256 见 conandata.yml）：74 个顶层条目，
  `makefile` + 约 60 个 `.c/.h` + `COPYING.TXT`/`.txt`/`.ini` 文档，无 `tests/`、`test/` 目录；
- `makefile` 共 676 个目标：全部为平台构建目标（`linux`/`linuxa`/`xermit`/`wermit`/`mermit` 等），
  无 `check`/`test` 目标、无 `TESTS` 变量；注释明示不使用 autoconf/automake/configure；
- 结论：上游 9.0.302 确无自动化测试（`status:"no_tests"`），
  详见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 待真机预检回填 | — | — |
| 2 | CI #40845 `gcc: command not found`（`make linux` 在 `linuxa` 递归时被硬编码 `"CC = gcc"` 覆盖，配方 `CC=` 透传失效；真机因 PATH 有 gcc 而通过，CI 干净环境无 gcc） | `linuxa` 写死 `"CC = gcc" "CC2 = gcc"`（全文件 72 处），子 make 显式赋值覆盖父级命令行；`make[2]` 日志仍执行 `gcc ... -c ckcmai.c` 即直接证据 | 配方在 `build()` 创建 `build_folder/hmbs-shim/gcc`（symlink 到 Conan 编译器，失败时回退为 wrapper 脚本）并前置到 `PATH`，不碰上游目标，探测逻辑（KFLAGS/LIBS）保持不变 |

## 源码修改

3 个补丁（`patches/`，均为实质平台分支，非空壳 stub）：

1. **0001-ckcdeb.h-ohos-nogetusershell.patch**：musl 无 `getusershell()`，musl 下（`__linux__ && !__GLIBC__`，R8 合规）定义 `NOGETUSERSHELL`；
2. **0002-ckucmd.c-ohos-stdio-musl.patch**：musl 下 `FILE` 不透明，musl 下（`__linux__ && !__GLIBC__`，R8 合规）强制 `CMD_CONINC`，`cmdconchk()` 走 `conchk()`；
3. **0003-ckupty.c-ohos-no-vhangup.patch**：musl 无 `vhangup()`，仅 glibc 下定义 `CK_VHANGUP`（R8 合规）。

## 依赖版本

无外部依赖（纯 C，系统库按探测结果自动开关：ncurses/curses/resolv/crypt/lockdev）。

## 验证结果

待真机预检回填（`conan create` + `test_kermit.sh` 3 项检查 + 双 HMBS 标记）。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/kermit | C-Kermit 9.0.302 可执行文件（上游 `wermit` 改名） |
| licenses/COPYING.TXT | BSD-3-Clause 许可证文本 |

## 注意事项

- `test_kermit.sh` 用 `command -v kermit` 定位二进制（VirtualRunEnv 提供 PATH），stdin 取 `/dev/null` 或管道，避免交互挂起；
- 上游 `make linux` 的探测 `grep` 在缺失路径时返回空 HAVE_*，属正常回退；
- 本机（Windows）未运行 conan；一切验证以真机预检与官方 CI 为准。

## 下载可靠性调查（2026-09-06，第二轮策略）

- 真机连续两轮在 `source()` 报同一指纹：`Provided 0d5f2cd1…dac0711 / Computed a7c3881f…5861de271b`，且 source 目录哈希变化（`c-ker6950…`→`c-kerbecb…`）而 computed hash 不变，说明是确定性下载内容不一致，非偶发截断；上轮 source 阶段 TMPDIR 加固已同步到真机（报错行号 37→49）但 computed hash 未变，证明与临时目录无关。
- 三方字节验证配方哈希无误：① 本机直连官方 URL 得 3122219 字节、sha256 与配方完全一致（与文档记载 2.9MB 相符）；② Wayback 两份独立存档（2025-01、2026-08）`id_` 原始字节同为 3122219 字节且 sha256 一致；③ 同一 URL 换 4 种 UA 结果相同。故不改 sha256。
- 镜像验证结论：Wayback 字节虽一致，但仓库历史（rc/1.7.4、monero 笔记）证明 web.archive.org 从真机网络不可达，列为首选只会增加超时而不解决问题；ftp.kermitproject.org 无法验证字节同一性；columbia 备选路径 403。按守则“找不到可信且可用的镜像时保留原 URL”处理，不引入新 URL，不改校验值。
- 配方内无法 vendoring（JC 门禁拦截源码 tarball）。综合判定为真机下载链路对该站点的确定性故障（代理/拦截页可能性大），需后端排查网络出口，而非配方缺陷。

## 下载可靠性加固（2026-09-06，第三轮策略周期新路线）

- 上一周期“镜像验证后保留原 URL、零改动上报链路故障”连续三轮未通过（computed hash 恒为
  a7c3881f…），按防重复要求必须换路线：本轮不再等待环境恢复，而是按守则“源码包下载
  超时是例外”把 `conandata.yml` 的单 URL 改为有序列表（Conan 2.x `get()` 逐个尝试直到
  哈希通过），官方 URL 保留最后回退，sha256 保持不变。
- 新证据（本机 HEAD 实测，非猜测）：
  - `https://www.kermitproject.org/ftp/kermit/archives/cku302.tar.gz` → 200，3122219 字节；
  - `http://www.kermitproject.org/ftp/kermit/archives/cku302.tar.gz` → 200，3122219 字节
    （同站同文件，仅协议不同，可绕过 TLS 层拦截）；
  - `http://www.minix3.org/distfiles-backup/kermit-9.0.302/cku302.tar.gz` → 200，3122219 字节
    （Minix 官方 distfiles 备份，独立主机，与配方字节数完全一致）。
- 列表顺序：Minix → 同站 HTTP → 官方 HTTPS；任一镜像字节不一致时 conan 按 sha256 拒收并
  试下一个，只会增加成功概率，不会降低校验强度。

## 补丁 hunk 计数修复（2026-09-06，真机 build 阶段新失败域）

- 真机在 `source()` 成功后（镜像回退生效）倒在 `build()` 第 52 行
  `apply_conandata_patches`：`0001` 报 `invalid hunk no.1 at 14` +
  `patch stream is incomplete`，属补丁文件结构错误而非上游源码问题。
- 根因：手写补丁的 hunk 头计数与正文行数不符——自研校验脚本逐 hunk 重数确认
  `0001` 首 hunk 头称 new=11 实为 10、次 hunk 头称 old=5/new=6 实为 4/5；
  `0002` 头称 old=6/new=14 实为 7/15；`0003` 计数正确。行尾均为 LF、无 BOM，
  排除换行符因素。
- 修复：仅修正三个 hunk 头为实际计数（`0001`: `-6413,6 +6413,10` /
  `-6435,4 +6439,5`；`0002`: `-7340,7 +7340,15`），上下文与补丁语义未动。
- 验证（本机，非估算）：Minix 镜像下载 3122219 字节、sha256 与配方完全一致
  （HASH-MATCH），解包后 `git apply --check` 三补丁全部通过（`0001` 次 hunk
  偏移 2 行属正常 fuzz 范围），全量试打成功且预处理 `#if/#endif` 深度平衡
  （前后均为 0），补丁标记均落入目标文件。

## 补丁落点修正（2026-09-06，真机 strict patcher 上下文失配）

- 上轮只修了 hunk 计数，真机改报 `source file is different - ckcdeb.h` 并指出
  `actual: '#endif /* SINIX */'`：conan 自带 patcher 为无 fuzz 严格匹配，
  按 hunk 声明行号定位，而上轮验证用的 `git apply` 自带 fuzz/搜索，
  掩盖了第二 hunk 起始行号错误。
- 根因：对照真实源码（Minix 包已验哈希一致）发现 `ckcdeb.h` 的嵌套是
  IRIX > PTX > AIXRS > SINIX > UNIXWARE > COHERENT，第二 hunk 上下文
  `PTX/IRIX/NOGETUSERSHELL/UNIX` 真实位于 6437-6440，而补丁误写 6435
  （该处实为 `#endif /* SINIX */`），故真机严格匹配失败。
- 修复：第二 hunk 头改为 `@@ -6437,4 +6441,5 @@`（语义与上下文未动）；
  新增严格校验脚本（按声明行号逐行精确匹配、零 fuzz，模拟 conan 行为），
  三补丁全部 STRICT-OK（0001 两 hunk 累计 +5 行，0002 +8 行，0003 +2 行），
  且试打后 `#endif /* musl */` 精确落在 `IRIX` 与 `NOGETUSERSHELL` 之间。
- 教训：补丁验证必须用严格匹配而非 `git apply`（fuzz 会掩盖落点错误）。
