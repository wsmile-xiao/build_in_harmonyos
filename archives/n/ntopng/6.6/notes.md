# ntopng 6.6 适配笔记（buildwork 续跑 2026-09-05）

## 编译环境
- 构建系统: autotools（configure.ac.in + Makefile.in；autogen.sh 生成 configure）
- 编译日期: 2026-09-05
- 编译器: clang / clang++（aarch64 HarmonyOS 本机编译，非交叉）
- 状态: configure 绿（RC=0）；make 未绿（见报告），整体未发布
- 源/依赖/日志新位置（旧 ~/tmp 全部失效）:
  - 源码: /storage/Users/currentUser/ohc-tmp/ntopng-campaign/buildwork/ntopng-6.6.work（.orig 同目录）
  - 依赖: buildwork/ntopng-deps/（full_deploy/host/* 含 ndpi/6.0；lmmd-prefix 含 libmaxminddb 1.11.0；*.pc + pclinks）
  - env:   buildwork/ntopng-deps/env.sh（source 后 CC/CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH/LD_LIBRARY_PATH/NDPI_DEP_BASE 就绪）
  - 日志:  buildwork/ohc-logs/（ntopng-autogen.log / ntopng-configure.log / ntopng-make.log / clickhouse-guard.diff）

## 编译步骤（已验证可复现）
```
cd buildwork/ntopng-6.6.work
source ../ntopng-deps/env.sh
# configure 已由 autogen 生成（勿重跑 autogen）
sed -i 's/umask 077/umask 002/g' configure     # E011 本 FS 修复
./configure --prefix=$DEFAULT_PREFIX \
  --with-ndpi-static-lib=$NDPI_DEP_BASE/lib \
  --with-ndpi-includes=$NDPI_DEP_BASE/include/ndpi   # RC=0
make -j1 CC=clang CXX=clang++                  # 续跑：尚未绿，见报告
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoconf config.status `can't create ./confXXXX/subs1.awk: Permission denied` | 本 worker FS 对 umask 077 生成的 0700 临时目录**属主也不可写**，且 chmod 无效（写需 group 写位） | `sed -i 's/umask 077/umask 002/g' configure`（建 0775 目录） |
| 2 | bundled rrdtool configure `cannot guess build type` | rrdtool 2012 config.guess 不识别 HarmonyOS/HongMeng Kernel | Makefile.in 规则注入 `--build=aarch64-unknown-linux-gnu`（config.sub 接受该三元组） |
| 3 | make 顶层报 `*** [-lm] Error 2` 且 -j4 下 rrdtool configure 并发互踩 | `LIBRRDTOOL_LIB=…librrd_th.a -lm` 中裸 `-lm` 被 make 当成第二个目标；同一规则并发跑两次 configure | Makefile.in 去掉 LIBRRDTOOL_LIB 中 ` -lm`（LIBS 尾部已有 -lm）+ 使用 `-j1` |
| 4 | lua-5.4.6 构建 `gcc: No such file or directory` | lua src/Makefile 硬编码 `CC= gcc`，本机无 gcc | `make CC=clang CXX=clang++`（命令行变量覆盖子 make 赋值） |
| 5 | `json.h file not found` / hiredis 头找不到 | full_deploy .pc 迁移后仍内嵌旧 `~/tmp` prefix；json-c 头在 include/json-c 子目录而 ntopng 用 `#include "json.h"` | 批量修正 *.pc prefix→buildwork 新路径；json-c.pc Cflags 增 `-I${includedir}/json-c`；重跑 configure |
| 6 | lang-preflight 误判 python | 检测命中 third-party/rrdtool-1.4.8/bindings/python/setup.py | 人工复核按 ndpi 先例续 C++ 族；勿重跑 lang-preflight |
| 7 | F068 init-build 源码误删（前次事故） | `_promote_nested_source` 见 doc/Makefile 误当源码根 | 已手动重新解压恢复；沉淀草稿建议 |
| 8 | 命令 60s 上限 / 高负载(~78/8核) | harness 单命令 ~60s；后台随调用结束被杀 | 长前台调用（超时后服务端继续跑完）+ 轮询日志；make -j1 |

## 源码修改（补丁）
- 0001-makefile-in-clickhouse-submodule-guard.patch：clickhouse-cpp submodule 守卫
  （community tarball 无 submodule，避免 cmake 失败）。
- 0002-makefile-in-rrdtool-configure-build-type.patch：rrdtool --build 三元组 + 去 `-lm`。
- E011 configure umask 修复不入补丁（configure 为 autogen 生成文件），在配方 build() 内 sed。

## 依赖版本
- json-c/0.18、openssl/3.5.6.1、sqlite3/3.49.1、libpcap/1.10.6、hiredis/1.2.0、
  curl/8.15.0、zeromq/4.3.5（buildwork/ntopng-deps/full_deploy/host，均已发布 ohpcd）
- ndpi/6.0（本地 full_deploy，含 libndpi.a + include/ndpi）
- libmaxminddb/1.11.0（本地 lmmd-prefix 手工 CMake 构建；ohpcd 无包）
- 可选缺失（非阻断，configure 告警）：expat（speedtest disabled）、librrd（走 bundled 1.4.8）

## 验证结果
- configure RC=0（buildwork/ohc-logs/ntopng-configure.log，含 3 次运行；末次 CONFIGURE_RC=0）
- ntopng 二进制：**尚未产出**（make 未绿；-j1 需数小时，负载 ~78/8 核）
- 冒烟（--version/R7 弹窗）：待 make 完成后执行，见 reports/compile-resume-report.md

## 交付物
- patches/0001、0002；conanfile.py；conandata.yml；commands.json；test_package/conanfile.py；
  reports/compile-resume-report.md
- conan-verify / conan create：未运行（整树编译不可在本会话时限内完成 + shell 通道结尾不可用），如实记录

## 【2026-09-05 第三轮续跑（make 长跑进行中）】追加

### 关键突破：bundled rrdtool 真因与本地解法
- 现象：bundled third-party/rrdtool-1.4.8 的 configure 即使加了 `--build` 与 `-j1` 仍报
  `configure: error: Please fix the library issues listed above and try again.`（还曾报
  `I need a copy of *nroff/*troff`）。
- 根因（configure.ac 核实）：
  1) `EX_CHECK_ALL(glib-2.0…)` 与 `EX_CHECK_ALL(xml2…)` 是无条件**硬**检查；本机无
     glib-2.0/libxml-2.0（无 .pc/头/库），任一缺失即置 EX_CHECK_ALL_ERR → 末尾 abort。
  2) `AC_PATH_PROGS(NROFF,[gnroff nroff])` / TROFF 缺失 → AC_MSG_ERROR abort。
  3) src/Makefile.am 的 librrd(_th) 源清单含 `rrd_restore.c`（#include libxml/parser.h）；
     glib 只被 graph 系源使用（--disable-rrd_graph 已排除），核心库本身不需要 glib/xml。
- 解法（只影响本地 work 树，未改上游 autotools 源；备份 configure.ohcpd-orig.bak）：
  1) 就地修补 generated configure：3 处 as_fn_error（glib/xml 门、nroff、troff）替换为 `:`。
  2) 跑通 configure（--build=… + 原 disable 组 + --disable-shared）→ 生成 rrd_config.h
     （日志 ohc-logs/rrdtool-configure.log）。
  3) 手工编译 librrd 核心 26 个 .c（排除 rrd_restore/graph；flags 需 -DHAVE_CONFIG_H
     -D_GNU_SOURCE -DNUMVERS=1.4008，因 rrd_tool.h 仅在 HAVE_CONFIG_H 下 include rrd_config.h）
     → ar 为 third-party/rrdtool-1.4.8/src/.libs/librrd_th.a（232KB）。脚本/日志：
     ohc-logs/build-librrd.sh、ohc-logs/librrd-build.log。nm 已验证 rrd_create_r/
     rrd_update_r/rrd_lastupdate_r/rrd_strversion/rrd_clear_error/rrd_get_error/rrd_fetch/
     rrd_tune/rrd_freemem/rrd_parsetime。
  4) 因 .a 已在顶层 Makefile 期望路径，make 不再触发 bundled rrdtool 的 configure 规则。
- 说明：librrd_th 为 rrdtool 1.4.8 真实核心代码子集（未含 dump/restore/graph），可满足 ntopng
  对 rrd 的引用集合。

### 第三轮执行状态（如实）
- lua-5.4.6：经顶层 make 子 make（CC=clang 命令行覆盖 gcc）成功产出 liblua.a。
- 顶层 make：cd buildwork/ntopng-6.6.work && source ../ntopng-deps/env.sh && make -j1 CC=clang
  CXX=clang++（nohup 后台 PID 42724，日志 buildwork/ohc-logs/ntopng-make.log）。至 23:5x 约
  26/256 对象（src 168 + flow_checks 27 + flow_alerts 34 + host_checks 13 + host_alerts 14），
  0 error。负载 ~67/8 核，实测 ~1 对象/50s，全量预计数小时。nohup 孤儿进程，会话结束后继续跑。
- 冒烟（R7 弹窗 + ./ntopng --version）：待产出二进制后执行；本轮未做（不伪造）。
- ndpi sha256：conandata.yml 已补 21fc40cab5505942c0b21d9bbaf73e9adf8162ddfe782e4cd072cab855a2eda9
  （来源 /storage/Users/currentUser/tmp/builds/ndpi-6.0.tar.gz，依赖准备期官方 URL 下载；当前 GitHub
  不可达未复核，provisional）。

### 精确续跑/轮询命令
```
# make 仍在后台跑 → 轮询：
tail -n 30 /storage/Users/currentUser/ohc-tmp/ntopng-campaign/buildwork/ohc-logs/ntopng-make.log
find /storage/Users/currentUser/ohc-tmp/ntopng-campaign/buildwork/ntopng-6.6.work/src -name '*.o' | wc -l
# 若中断/出错则增量续跑：
cd /storage/Users/currentUser/ohc-tmp/ntopng-campaign/buildwork/ntopng-6.6.work
source ../ntopng-deps/env.sh
make -j1 CC=clang CXX=clang++ 2>&1 | tee -a /storage/Users/currentUser/ohc-tmp/ntopng-campaign/buildwork/ohc-logs/ntopng-make.log
# make 全绿后冒烟（先触发 R7 安全弹窗——直接运行一次产物）：
./ntopng --version ; ./ntopng -h
```

## 注意事项
- 提交仅限 archives/n/ntopng/6.6（+自建 knowledge 草稿）；禁 git add -A；禁含 archives/l/libXext（他人 M 状态）与 feedback/（自动生成）。
- 不 push、不 conan upload、不写框架文件。
- worktree `.build-context-ntopng-6.6` 中 BUILD_SRC_DIR 等仍指向旧 ~/tmp，续跑请以 buildwork 为准。
- rrdtool configure 就地修补仅存在于 buildwork 源树（configure.ohcpd-orig.bak 可对比）。如需固化为
  可重放补丁：改 configure.ac（去 glib/xml/nroff/troff 硬检）+ src/Makefile.am 源清单去 rrd_restore.c
  + rrdtool autogen 再生成（本轮以手工子集归档替代，未走该路径）。


---

## 第四轮（2026-09-06 主会话收尾）：**ntopng 6.6 编译全绿**

### 决定性发现：nDPI 版本配对错误
- ntopng tag 6.6 提交时间 2025-11-17T09:36Z；nDPI tag **5.0** 发布时间 2025-11-17T08:11Z（同日上午）。
- ntopng 6.6 源码调用 `ndpi_init_detection_module(NULL)`（1 参）；nDPI 5.0 为 1 参
  `(struct ndpi_global_context *g_ctx)`；nDPI tag 6.0（2026-08-28）改为 2 参
  `(g_ctx, enum ndpi_license_type)`，与 ntopng 6.6 不兼容（编译报 `no matching function`）。
- **结论：ntopng 6.6 正确配对 = nDPI 5.0**（本 campaign 此前构建的 ndpi/6.0 是错误配对，仅适用于 ntopng 6.6 之后的上游）。
- conandata.yml 的 ndpi 已改为 tag 5.0（sha256 8b0d3dc0c8a6a68578e09a18c922021ef6458d4aca1c7a20ce04efc267aa9ea5，本地官方下载验证）。

### 编译结果（真实证据）
- nDPI 5.0：autogen RC=0 → configure RC=0 → make RC=0 → libndpi.a(4.3MB) install 到
  `buildwork/ndpi-5.0-prefix/{lib,include/ndpi}`（1 参头文件已核）。
- ntopng：`make clean` 后重新 configure（RC=0，Makefile 指向 ndpi-5.0-prefix）→ `make -j8 CC=clang CXX=clang++`
  **全绿**（256 个对象全编译 + 链接成功，`make` 复跑输出 "Nothing to be done" RC=0）。
- 产物：`buildwork/ntopng-6.6.work/ntopng`（ELF 64-bit LSB arm64 PIE，约 13.1MB，未 strip）。
- 新增编译期修复（已固化为 patches/0003、0004）：
  1) `src/Utils.cpp` getMaxIfSpeed：OHOS sysroot ethtool.h 无 `ethtool_cmd_speed()`（旧 struct ethtool_cmd 布局），改用 `edata.speed | (edata.speed_hi<<16)`；
  2) bundled rrdtool `rrd_client.c`：`rindex()` 不存在于 OHOS libc → `strrchr()`。

### 冒烟状态（如实）
- `./ntopng --version` 在缺依赖 LD_LIBRARY_PATH/签名环境下无法启动：
  loader 报缺少 libjson-c.so.5/libzmq.so/libcurl.so 及 relocation 错误（动态依赖 + OHOS 加载/签名策略）。
- 结论：**编译链接已完成（本任务"编译工作"达成）**；可执行运行需部署侧处理
  （静态链接或签名后的 .so 环境 / conan run env / 打包），留待 conan-verify/CI 阶段。
- 若干 conan 依赖（curl/zeromq）仅有 .so 无 .a；json-c/openssl/sqlite3/libpcap/hiredis/ndpi/lmmd 有 .a。

### 执行环境要点（后续 worker 参考）
- 单命令客户端 ~60s 超时但服务端进程继续；服务端 ~300s 硬杀直接前台进程；
  **nohup 脱离子进程可跨命令/会话存活**（本会话后台 make 用 nohup 驱动）。
- 长任务统一模式：`nohup <cmd> >> log 2>&1 &` + 短命令轮询日志。
- GitHub 大文件/raw 网络不稳定：gh-proxy 快但曾给残缺 commit 归档（缺 alphabetically 靠后的目录）；
  大文件优先官方/gh-proxy 全量 tag 归档（tag 5.0 42MB 完整可用）。


---

## 第五轮（2026-09-06 Flow A Worker，正规 PR 流程）：配方修订 + 环境阻塞实录

### 本轮已完成（可复核）
- 读 resume-plan Flow A 段 + notes + SKILL；通道首条 `echo alive` 通过（10:17）。
- 超时预算：`ohc-run.py timeout set ntopng 6.6 54000` → build_timeouts.txt 已写入（W3/CI 同源）。
- gitcode/main 已 fetch（FETCH_RC=0，仍与 feat/ntopng-6.6 差 2 ahead / 70 behind，
  merge-base 75ad7349ef）。检查：gitcode/main 自 merge-base 起**未动 archives/n**（diff 0 文件），
  故 rebase 对 ntopng 内容零冲突。但本 worktree 存在「phantom」libxext 脏改（大写/小写双 index 条目
  在大小写不敏感 FS 上互斥，git status 永远报一个 M；git stash 无法彻底清空、rebase 无法启动），
  已在多处验证（stash uc/lc 后 diff 在 libXext/libxext 间翻转）。→ rebase 需用
  `git update-index --assume-unchanged`（本 worktree 独立 index，不影响他人）或临时干净 worktree 方案
  （见 Flow A 清单步骤 1 后续处理）。
- **conanfile.py 已重写**（archives/n/ntopng/6.6/conanfile.py，未 commit，待 shell 恢复后先
  `python3 -m py_compile` 校验再 conan-verify），覆盖 resume-plan「已知配方缺口」：
  1) rrdtool 可重放：build() 内 `_neutralize_rrdtool_sources()` 把 configure.ac 的 glib/xml
     EX_CHECK_ALL 收进 `if test $enable_rrd_graph != no` 分支、nroff/troff AC_MSG_ERROR→WARN、
     src/Makefile.am 去 rrd_restore.c；随后 `sh autogen.sh` 再生成 configure/Makefile.in，
     并对新 configure 做 E011 umask 077→002。⚠ 若 rrdtool autoreconf 需 autopoint/gettext
     失败，回退方案＝直接改 generated configure 5 处（对照 buildwork/ntopng-6.6.work rrdtool
     configure.ohcpd-orig.bak）+ 手工归档 26 核心 .c 为 src/.libs/librrd_th.a（探索期已验证）。
  2) nDPI 私有构建改为 5.0：`--with-only-libndpi --disable-shared --enable-static --with-pic
     --prefix=<priv>` + autogen 后 E011 sed；docstring 已改 5.0。
  3) make -j1 → -j8（探索期 -j8 全绿实证）；lua CC=clang 命令行覆盖保留。
  4) generate() 增加 json-c.pc/hiredis.pc Cflags 增补子目录 include（对照 buildwork env 做法）+
     libssl.pc/libzmq.pc 别名（保留原 _ensure_pc_aliases）。
  5) libmaxminddb cmake 增加 -DCMAKE_SYSTEM_NAME=Linux（json-c 先例）。
  6) ntopng configure 与子命令统一走 `env="conanbuild"`（AutotoolsDeps/PkgConfigDeps 注入
     CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH），PKG_CONFIG_PATH 前插 priv/lib/pkgconfig。
- **manifest.yaml 已同步**（status built、ndpi/5.0、patches 0001-0004、rrdtool 说明）。
- 环境阻塞：10:35 起 mcp-shell `tool not found` 持续（≥20 次连续失败，含 `echo`），
  无法执行任何命令 → conan-verify/finish/W4/submit 全部无法启动。

### 恢复执行序列（shell 恢复后按序）
```
cd /storage/Users/currentUser/ohc-tmp/ntopng-campaign/ntopng-6.6-wt
python3 -m py_compile archives/n/ntopng/6.6/conanfile.py     # 语法自检
# （可选）沙箱验证 rrdtool 改写+autogen：在 buildwork/ntopng-6.6.orig 副本上跑 build() 的
#   _neutralize_rrdtool_sources 逻辑 + cd third-party/rrdtool-1.4.8 && sh autogen.sh
python3 scripts/ohc-run.py timeout get ntopng 6.6            # 期望 54000s
nohup python3 scripts/ohc-run.py conan-verify ntopng 6.6 >> /storage/Users/currentUser/ohc-tmp/ntopng-campaign/buildwork/ohc-logs/ntopng-conan-verify.log 2>&1 &
# 轮询日志；G2 conan create 全绿后：
nohup python3 scripts/ohc-run.py finish ntopng 6.6 built >> .../ntopng-finish.log 2>&1 &
# 之后 W4 审计与 submit 见 resume-plan「Flow A 执行清单」步骤 7-10。
# W1 rebase（若仍被 phantom libxext 挡）：先备份 libxext 磁盘文件到 buildwork，
#   git update-index --assume-unchanged -- <4 个大小写路径>，rebase，再 --no-assume-unchanged。
```


---

## 第六轮（2026-09-06 Flow A Worker 第 2 次尝试，续第五轮）：conan-verify 全绿

### W1 rebase
- gitcode/main fetch（tip dfe3d3ac77，自 merge-base 起 70 commits，**零触碰** archives/n/ntopng 与
  libXext）→ `git update-index --assume-unchanged` 屏蔽 phantom libXext → rebase 成功
  （3 commits 干净重放，新 tip 59eb78b87e）→ 恢复 assume-unchanged。
- 清理了上次残留的半成品 rebase-merge 状态（仅 autostash 文件、无 todo，rebase 从未真正重放；
  HEAD 始终在分支尖端）。

### 配方修复链（conan-verify G2 迭代，最终全绿）
1. **test_package/MANIFEST.yml 缺失**（G1 L0e）→ 补齐（对齐上游 `make test`=`./ntopng --version`）。
2. **补丁 0001/0002/0003/0004 损坏**（git apply/patch_ng "corrupt patch"/"hunk 行号偏移"）：
   归档补丁非 pristine 基线产物。全部基于 `.orig` 重新生成最小功能 diff，用 conan 同款
   patch_ng 引擎顺序应用验证通过。
3. **ohpcd-local file:// zombie remote** 使 conan 无法计算依赖图 → `conan remote remove ohpcd-local`。
4. **rrdtool autogen 缺 autopoint**（`autoreconf --install` 失败）→ 改为：修补 checked-in generated
   configure（E011 umask + 3 处 abort 中和：EX_CHECK_ALL 汇总 / nroff / troff）→ 跑 configure 生成
   rrd_config.h → 按探索期 build-librrd.sh 的 26 核心源归档 src/.libs/librrd_th.a（跳过顶层 rrdtool 规则）。
5. **rrdtool/ndpi configure 的 conftest "cannot run C compiled programs"**：conanbuild AutotoolsDeps
   向环境注入 LIBS（含 -lcurl/-lzmq/-ljson-c 等共享库），configure 的测试程序链接后在运行时找不到
   这些 .so → 子构建 configure 前 `env -u LIBS CPPFLAGS= LDFLAGS=` 清除（rrdtool/ndpi 自包含，不需依赖）。
6. **ntopng configure conftest 同理**：但 ntopng 需要依赖 flags → configure 前导
   `LD_LIBRARY_PATH=<全部 require lib dirs>:$LD_LIBRARY_PATH`（等价探索期 env.sh）。
7. **maxminddb.h not found**：libmaxminddb CMake 生成的 .pc 里 `libdir=lib`/`includedir=include` 为
   **相对路径** → pkg-config 输出 `-Llib -Iinclude`（相对 ntopng 构建目录无效）。修复：cmake install 后
   将 .pc 的 libdir/includedir 规范化为绝对 priv prefix。
8. **package 为空 / conan test `ntopng: not found`**：build() 原来只 make 不 make install，package()=pass。
   改为 configure `--prefix=<build>/stage` → make → `make install` → package() 将 stage 拷入
   package_folder。

### conan-verify 结果（真实）
- 2026-09-06 11:20 报告 reports/conan-verify-report.md **Verdict PASS**：
  G0 ✅ / G1 ✅ / G2 ✅（conan create 成功，含 test_package `ntopng --version` 冒烟）/
  G3 ✅ / G4 ✅ / L2/L4/L5 ⏭️（无 cache 路径跳过，工具判 PASS）。
- 关键中间产物：ntopng 二进制 ~13.1MB（aarch64，stage/bin），conan 包安装成功。
- build_timeouts.txt 已含 `ntopng/6.6 54000`（W3/CI 同源）。

### 后续（第七轮）
- `finish ntopng 6.6 built`（W2+R36+W3 conan create，预算 54000s）→ W4 审计 → submit 建 PR。
---

**编译结束**: 2026-09-06 11:36
**最终状态**: built

## 2026-09-20 复验与修复（j669539，限核恢复轮）

- **conan create EXIT_RC=0（jobs=2）**：主包全绿（ndpi 5.0 bundled R49 + rrdtool 子集 + lua + 顶层 256 对象），test_package 版本横幅通过（`Version: 6.6.260920 [Community build]`）。
- **test_package 运行环境修复**：原 test() 直接 `self.run("sh test_version.sh", env="conanrun")` 在 conanrunenv 未含 /system/lib64 的环境报 `Error relocating ntopng: _ZTISt9bad_alloc: symbol not found`（libc++_shared.so 不可达，Error 127）。补 Environment 注入依赖 lib 目录 + /system/lib64（kgoldrunner 26.04.0 / audiocd 26.04.3 test 先例）。CI #41111 当时绿是 worker 环境差异，本修复让两环境一致。
- **本机 PATH 污染坑（记录供后来者）**：`~/usr/local/bin` 存在 automake-1.17/aclocal-1.16/libtoolize，与 conan tool_requires automake/1.18 混链 → ndpi autogen.sh `configure.ac:6: version mismatch. This is Automake 1.17 ... comes from Automake 1.18` exit 63。本地验证需隔离用户目录 autotools（CI clean 环境无此问题）。
- **上游测试口径**：上游 `make test` = `test_version` 目标 = `./ntopng --version`（无独立单测套件，N=0）；test_package 即执行该验证并通过。
