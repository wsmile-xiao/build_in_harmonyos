# liboprf 0.9.4 适配笔记

## 上游信息

- 上游仓库：https://github.com/stef/liboprf（官方源，非 fork）
- 版本：v0.9.4（Minor release，2026-02-23；相对 v0.9.3 仅 python 3.14 兼容 + xk_noise 编译警告消除）
- 源码包：https://github.com/stef/liboprf/archive/refs/tags/v0.9.4.tar.gz（tag 自动归档；release 页仅附 .asc 签名，无预打包 tarball）
- sha256：`c89e3057cbd1fe34b79c67fe08e2752aa60ea72864eab69d95e27e34720d2de5`（实测下载 248914 字节计算）
- 许可证：LGPL-3.0-or-later（LICENSE + 各头文件 SPDX 一致）
- 功能：OPRF(ristretto255, SHA-512)（RFC 9497）+ 阈值 OPRF + 3hashTDH + DKG，纯 C，依赖 libsodium

## 编译环境

- 构建系统：手写 makefile（注意是小写 `src/makefile`，GNU make 默认识别，无需 `-f`）
- 编译日期：2026-09-18
- 编译器：clang（hnp 工具链，由 Conan conf 注入）
- 依赖：libsodium/1.0.22（制品仓已有 1.0.20/1.0.22 配方；minisign/0.12-r1 配方注明 1.0.22 已发布，含 OHOS aarch64 静态二进制）
- 构建工具依赖：pkgconf/3.0.5（tool_requires；fcft、cataract 等先例同版本）
- 状态：built（首轮仅工作树，真机预检通过前不标 published）

## 编译步骤

1. `get()` 拉取 tag 归档并 strip_root（顶层目录 `liboprf-0.9.4/`）。
2. `make -C src CC=<hnp clang> AR=<llvm-ar> CPPFLAGS="-I<libsodium>/include" LDFLAGS="-L<libsodium>/lib" all -j1`：
   先编 vendorized `noise_xk`（静态 + 共享），再链接 `liboprf.so`（soname，strip + debuglink
   由上游规则完成）、`liboprf_release.a`（符号本地化后归档）、生成 `liboprf.pc`。
   CFLAGS 故意不覆盖，保留上游加固选项（`-fstack-protector-strong`、`-D_FORTIFY_SOURCE=3`、
   `-Wl,-z,defs/relro/noexecstack/now`、UBSan trap 模式——trap 模式无需运行时库，预期可链）。
3. `make -C src/tests ... all -j1` 构建 11 个上游测试二进制（含 `testvecs2h.py` 生成 CFRG 向量头）。
4. 依次运行 11 个二进制（重阈值测试按上游包裹 `ulimit -s`），按逐条审计的退出码判定
  （tp/stp-dkg-corrupt 以 1..125 非零退出判检出通过，崩溃信号不计；
   toprf-update-corrupt 按上游要求以退出 0 判通过），输出 `HMBS_UPSTREAM_TEST_RESULT`；
   失败则抛异常中断构建。
5. `make -C src install PREFIX=/ DESTDIR=<package>` 安装 `lib/liboprf.so(.0)`、`lib/liboprf.a`、
   `lib/liboprf-noiseXK.so(.0/.a)`、`include/oprf/` 全套头文件、`lib/pkgconfig/liboprf.pc`；
   另复制顶层 `LICENSE` 到 `licenses/`。
6. test_package：`test_oprf.c` 以 `-loprf -loprf-noiseXK -lsodium` 链接共享库并运行，
   2 个真实 OPRF 往返检查各打印一行 `CHECK-OK:`，计数后输出 `HMBS_TEST_PACKAGE_RESULT`，
   再以 conanrun 环境复跑一次。

## 上游测试审计

- 测试位置：`src/tests/`（C 源码）+ `src/tests/makefile` 的 `tests` 目标；`src/tests/README.md`
  仅 180 字节说明；`fuzz-*` 子目录与 `update-poc.c`/`ft-mult.c`/`allocations.c` 不在 `tests`
  目标内，不计入。
- 共 11 次运行：dkg、tv1、tv2（CFRG 官方向量，TC=0/1 两种配置）、toprf、tp-dkg 3 2、
  tp-dkg-corrupt 3 2（反例）、stp-dkg 9 4、stp-dkg-corrupt 9 4（反例）、toprf-update 9 4、
  toprf-update-corrupt 9 4（反例）、mpmult。
- python 绑定（`python/`，pyoprf）与 zephyr 目录不属于 C 库测试，本次不接入。
- 未修改任何上游测试；未补测试（上游已有完整套件）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | release 下载页无 `liboprf-0.9.4.tar.gz`（仅 `.asc`） | 上游未上传预打包产物 | 改用官方 tag 自动归档 `archive/refs/tags/v0.9.4.tar.gz`（同仓库官方源，R39 合规），实测 sha256 入 conandata |
| 2 | `src/Makefile` 404 | 文件名为小写 `src/makefile` | 配方用 `make -C src`（GNU make 默认识别 `makefile`），无需补丁 |
| 3 | makefile 硬要求 `pkgconf` 二进制 | `PKGCONF_MISSING` 检查失败即 error | `tool_requires("pkgconf/3.0.5")`（仓库已有该版本配方，先例一致） |
| 4 | sodium 头文件/库路径 makefile 不感知 | makefile 只调 `pkgconf --exists/--atleast-version`，不用 `--cflags/--libs` | 配方显式传 `CPPFLAGS="-I..." LDFLAGS="-L..."`（makefile 仅读取不赋值，不破坏原有选项） |
| 5 | Windows 本机 `archives/l/libXext` 与 `archives/l/libxext` 大小写冲突导致 status 常脏 | 上游同时存在新旧大小写两个目录，Windows 不区分大小写 | 本地未动这两处；PR 只含 `archives/l/liboprf/`，Linux 真机/CI 不受影响 |

## 待真机验证的风险点

- `uname -s` 在真机返回值：若非 Linux，noise_xk 分支走不到 `-soname` 分支也能编（仅缺 soname flag），install 的 `.0` 拷贝规则不受影响。
- `strip`/`objcopy` 用 PATH 解析：若 strip 破坏 OHOS `.codesign` 致 `.so` 无法加载，预检失败后改传 `STRIP=true` 跳过剥离（上游行为保留为首选）。
- `testvecs2h.py` 直接执行依赖 shebang：若失败，改为 `python3 testvecs2h.py` 预生成（HMBS 已注入 python3）。
- 重阈值测试（stp-dkg/topf-update 9 4）在单 job 真机上的耗时：单测超时 1500 秒，失败会在日志中标明。
- `LD -r` 合并对象：用 PATH 的 `ld`；若交叉合并失败，改传 `LD` 为工具链对应版本。

## 依赖版本

- libsodium-1.0.20 vendored（conandata `sodium` 条目，官方 download.libsodium.org URL + 不变 sha256；无外部 conan requires；>= 1.0.19 走 HAVE_SODIUM_HKDF）
- pkgconf/3.0.5（tool_requires；待真机复核）

## 2026-09-18 第二轮：真机依赖构建失败改内聚（未提交）

- 现象：预检在 `libsodium/1.0.22: Calling build()` 失败：`src/configure[142]: /data/service/hnp/bin/bash: inaccessible or not found`（Error 127），另有 `/tmp` 只读与 `HMBS 平台诊断 [readonly_tmp]`。
- 根因：外部 `requires("libsodium/1.0.22")` 被 conancenter 影子配方劫持（日志 `Downloaded recipe revision ... from conancenter`），无匹配 OHOS 二进制，被迫真机从源码重编；而 profile 的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 在该 runner 上缺失，configure 重执行即死。换 1.0.20 同样被劫持（libequihash 1.0.10 / libmacaroons 0.3.0 notes 已实证），与 `/tmp` 只读无关的主因是缺可执行的 shell/编译器路径。
- 方案（libmacaroons 0.3.0 同构移植，单包不碰 libsodium 目录）：`requirements()` 置空；conandata 新增 `sodium` 官方 1.0.20 归档；`build()` 内以 `/bin/sh` + HMBS TMPDIR + PATH 优先探测到的 CC/AR 编到 `build_folder/sodium_prefix`（umask 022 放宽、config.guess/sub 识别 HarmonyOS/linux-ohos、native 不传 --build/--host、`make -j1`、纯 Python 手工 stage 规避 chmod=0 的 `make install` 失败，并生成 `libsodium.pc` 供 makefile 的 pkgconf 探测）；主 make 以 `CPPFLAGS/LDFLAGS` 指 stage 前缀；`package()` 同包交付 `libsodium.a` + sodium 头；`package_info.libs` 追加 `sodium`；test_package 仅链本包（`-loprf -loprf-noiseXK -lsodium`）；上游结果持久化到 `share/liboprf/hmbs_upstream_result.json` 供缓存命中轮重发。
- 证伪/边界：stage 后校验 `libsodium.a` 非空、头文件数；上游 11 测试退出码判定不变（含 3 反例非零即过）；`make install` 的 strip/codesign 风险仍按首轮待验证点观察。

## 2026-09-18 第三轮：clang-15 不认 -fstack-clash-protection（未提交）

- 现象：内聚后 libsodium 构建已过，主包死于 `src/noise_xk`：`clang-15: error: argument unused during compilation: '-fstack-clash-protection' [-Werror,-Wunused-command-line-argument]`（`makefile:85 Error 1` → `makefile:133 Error 2`）。
- 根因：上游三处 makefile（`src/makefile`、`src/noise_xk/makefile`、`src/tests/makefile`，v0.9.4 实测）在非 Darwin 全架构无条件追加 GCC 专属 `-fstack-clash-protection`；`noise_xk/makefile` 带全局 `-Werror`，clang-15 的未使用参数警告直接变致命错误。因追加用 `+=`，命令行传 `ARCH`/`CFLAGS` 覆盖不掉（`?=` 基址会丢而 `+=` 照加；tests/makefile 连 armv7-a 豁免都没有），故改用 build() 内代码 strip。
- 方案：新增 `_patch_stack_clash()`，build() 首步对三处 makefile 仅删除 `-fstack-clash-protection` token（幂等，其余加固原样保留；in-code 方式沿用 libmacaroons config.guess 先例，不建 patches/ 目录）。
- 证伪/边界：仅去加固 flag，不碰测试口径与 11 用例判定；若后续再报同类 `-Werror` 未使用参数，按同法逐 token 处理。

## 验证结果

- 本机：未运行 conan（按守则仅真机验证）。源码包下载 + sha256 已实测；配方语法待真机 `conan create` 实测。
- 真机预检：待 HMBS 后台执行，`HMBS_UPSTREAM_TEST_RESULT` 与 `HMBS_TEST_PACKAGE_RESULT`
  两行标记以预检日志为准，届时回填 PR 正文通过率。

## 2026-09-18 第四轮：src/tests 链接缺 -L 致 tv1 找不到 -lsodium（未提交）

- 现象：主包 `src all` 已过，`src/tests all` 首个目标 tv1 即死：
  `cc -I.../sodium_prefix/include ... -o tv1 ... -lsodium` →
  `ld.lld: error: unable to find library -lsodium`（`makefile:31 Error 1`）。
  主包链接行带 `-L.../sodium_prefix/lib`，测试链接行没有。
- 根因：`src/makefile` 链接用 `$(LDFLAGS) $(LIBS)`，配方 `LDFLAGS="-L<stage>/lib"`
  能到达；但 `src/tests/makefile`（v0.9.4 实测）7 条规则（tv1/tv2/toprf/mpmult/
  toprf-update/-corrupt/update-poc/ft-mult）只展开
  `$(CC) $(CPPFLAGS) $(CFLAGS) ... -lsodium`，根本不引用 `$(LDFLAGS)`，
  仅 dkg/tp-dkg/stp-dkg 系列引用了。只有 tv1 先死，后续目标同样会死。
  与 `/tmp` 只读诊断无关（配方早已用 HMBS TMPDIR）。
- 方案：新增 `_patch_tests_ldflags()`（与 `_patch_stack_clash` 同先例，
  in-code 幂等，不建 patches/ 目录，不碰测试源码与 11 运行口径）：
  把 ` -lsodium` 全替换为 ` $(LDFLAGS) -lsodium` 再把重复的
  `$(LDFLAGS) $(LDFLAGS)` 折叠为单个，已带 LDFLAGS 的规则保持不变；
  build() 首步与 stack-clash 补丁并列调用；另导出
  `LIBRARY_PATH=<stage>/lib` 作编译器搜索路径兜底（有 LDFLAGS 时无害）。

## 2026-09-18 第五轮：src/tests 链接已过但 SSH 在测试运行前断开（未提交）

- 现象：`src all` 与 `src/tests all` 链接行均已出现（含 tv1/tv2/dkg/toprf/tp-dkg/mpmult），随后 `Connection to 47.242.172.160 closed by remote host`，`compile` 阶段判 failed。开头的 `preflight.sh[306] /tmp Read-only` 发生在 conan 启动前且构建仍能推进，为 harness 侧警告，非致命；`RequestsDependencyWarning` 同理。
- 根因：`_run_upstream_tests` 用缓冲式 `subprocess.run()`，重阈值用例（stp-dkg/toprf-update 9 4）长达数分钟无输出，SSH 会话空闲被远端关闭。非编译器缺失（本次已 `selected working cc` 成功），非测试口径问题。
- 方案：测试执行改流式 `Popen` 逐行回显（`[upstream] start` + 每行 `[upstream <用例>]`），`wait(timeout=1500)` 语义不变，3 反例非零即过不变；vendored sodium 的 configure/make 补 `env="conanbuild"`（VirtualBuildEnv PATH 不丢失）；test_package 新增 PATH 优先 `_resolve_cc`（与主配方同策略，防 profile 绝对路径缺失 Error 127）。均不碰测试源码与 11 用例口径。

## 2026-09-18 第六轮：上游测试 8/11，反例契约逐条纠正（未提交）

- 现象：预检跑完 11 个用例（executed=11），passed=8、failed=3。构建与链接已全过，
  无超时、无 spawn 失败；失败为退出码与配方预期不一致。
- 根因（逐条重审 `src/tests/makefile` v0.9.4 实测 + `src/toprf-update.c` 源码）：
  配方把 3 个 `*-corrupt` 一律按“非零退出=通过”处理，但上游契约并非如此——
  `tp-dkg-corrupt` 与 `stp-dkg-corrupt` 行尾有 `|| exit 0`（任一退出都不让 make 变红），
  而 `toprf-update-corrupt` 行是 `(ulimit -s 1966000; ./toprf-update-corrupt 9 4)`，
  无 `|| exit 0`，即上游要求它退出 0；`src/toprf-update.c` 的 `corrupt_ci0_good_ci`
  注释亦写明该破坏“does not influence the outcome of the protocol ... end result
  is correct”。故 `toprf-update-corrupt` 退出 0 是上游定义的正确结果，
  配方旧预期（非零）必然判错，至少贡献 1 个失败。
  另旧判定 `rc != 0` 会把崩溃（信号负值/128+ 退出，如 16MB×(n+1) VLA 栈溢出）误计为
  “检出通过”，掩盖真崩溃。
- 方案（不碰上游源码与测试口径，只改配方判定以匹配上游契约）：
  1) `toprf-update-corrupt` 改为 expect exit 0（与上游 `tests` 目标一致）；
  2) tp/stp-dkg-corrupt 保持非零预期，但收紧为仅接受 1..125 普通错误退出，
  崩溃信号/128+ 退出一律判失败，避免把段错误误认为检出成功；
  3) marker 与持久化 JSON 新增 `cases` 数组（name/expect/rc/ok），下轮摘要即可直接定位，
  不再依赖被截断的中间日志；
  4) `test_package/MANIFEST.yml` 同步修正三条反例描述与 `upstream_test_command`
  （补上与配方一致的 `ulimit -s` 包裹与期望说明）。
- 证伪/边界：改动前后上游二进制与运行命令不变，仅判定对齐上游 makefile；
  若下轮 `toprf-update-corrupt` 实际非零退出，说明本机行为与上游 Linux 不一致，
  届时再按真机日志深挖，而非放宽口径；tp/stp 反例若仍报 0 退出（未检出），
  同样视为真失败继续查，不静默放过。

## 2026-09-18 第七轮：6 个阈值测试栈溢出 SIGSEGV 改堆分配（未提交）

- 现象：预检 11 跑 11，通过 5、失败 6；失败全为阈值测试
 （tp-dkg/stp-dkg/toprf-update 各 plain+corrupt），`rc=-11`（SIGSEGV）；
  5 个小测试（dkg/tv1/tv2/toprf/mpmult）全过。开头的
  `preflight.sh[306] /tmp Read-only` 在 conan 启动前且构建能推进，
  为 harness 侧警告；上游测试源码无 `/tmp` 硬编码（内存 network_buf
  模拟网络），故不改临时文件根目录，只保留既有 HMBS TMPDIR 导出。
- 根因：三处测试 main 在栈上定义
  `uint8_t network_buf[n+1][NETWORK_BUF_SIZE]`（单槽 16MB）：
  tp-dkg 3 2 需 64MB，stp-dkg/toprf-update 9 4 需 160MB。
  上游靠 `(ulimit -s 66000 / 1966000; ./...)` 抬 RLIMIT_STACK，
  但真机硬限制拒绝约 1.9GB 请求，栈保持小尺寸，首次触及即段错误。
- 方案：新增 `_patch_tests_heap()`（与 `_patch_stack_clash` 同先例，
  in-code 幂等，不建 patches/ 目录）：三文件补 `#include <stdlib.h>`
  （缺失时），把该声明改为等大堆分配
  `uint8_t (*network_buf)[NETWORK_BUF_SIZE] = malloc(((size_t)n+1)*NETWORK_BUF_SIZE)`
  并判空返回 1；`_send/_recv` 逻辑、fuzz_loop 的 `[][NETWORK_BUF_SIZE]`
  形参兼容性、协议断言与 11 运行口径均不变；`ulimit` 包裹保留。
- 证伪/边界：若下轮仍 SIGSEGV，则按新日志定位是否另有大栈数组；
  堆泄漏仅存在于错误提前返回路径（进程即退，OS 回收），正常路径
  同样由 OS 回收，不影响判定。

## 2026-09-18 第八轮：上游 11/11 通过但 test_package 误链共享库（未提交）

- 现象：预检上游 11 跑 11 全过；test_package 死于
  `Error loading shared library liboprf.so.0` +
  `oprf_KeyGen/Blind/Evaluate/Unblind/Finalize: symbol not found`，
  `rc=127 ok=0/2`。开头 `preflight.sh[306] /tmp Read-only` 在 conan
  启动前且构建能推进，为 harness 侧警告；`HMBS 平台诊断` 另给
  `[stale_runtime_library]`（测试进程加载了系统旧动态库）。
- 根因：上游 `make install` 不分 shared 选项，同时安装 `.a` 与
  `.so(.0)`；配方 `package()` 未按 `shared` 过滤（默认 False 仍留
  `.so`），`test_package` 以 `-loprf` 链接时优先选中 `.so`；
  OHOS loader 忽略 `LD_LIBRARY_PATH`，运行时回落到系统旧
  `liboprf.so.0`（符号缺失），与测试源码/`/tmp` 无关。
- 方案（不碰上游源码与测试口径）：1) 主包 `package()` 按选项过滤
  （False 删 `*.so*`，True 删 `*.a`）；2) `test_package/build()`
  有 `.a` 齐全时按绝对路径直链三静态库，消除运行时依赖，
  缺失才回落 `-l`；3) `_run_env()` 透传 HMBS `TMPDIR/TMP/TEMP`，
  保留 `LD_LIBRARY_PATH` 并仅在包内存在 `.so` 时追加对应
  `LD_PRELOAD`（静态包无 PRELOAD）。
- 证伪/边界：默认 shared=False 走全静态链，不再依赖 loader；
  shared=True 才走 `-l` + `LD_PRELOAD`；上游 11 用例判定不变。

## 2026-09-18 第九轮：静态链已过但代码树二进制 EPERM（未提交）

- 现象：静态直链生效（RUN 行已直链三 `.a`），上游仍 11/11；
  test_package 死于 `test() line 195 subprocess.run PermissionError:
  [Errno 1] Operation not permitted: '.../liboprf-0.9.4/test_package/test_oprf'`。
  开头 `/tmp Read-only` 仍为 harness 侧警告；`[readonly_tmp]` 诊断沿用。
- 根因：构建输出落在同步代码树下，该路径在 `chmod=0`/受限挂载下不保证
  可执行；上一轮动态链恰好能 exec 不能复用为“目录可执行”的证据。
  与测试口径无关（2 个 CHECK-OK 未变），与 `/tmp` 硬编码无关
  （测试无临时文件）。
- 方案（保留静态链，只改执行路径）：1) `build()` 后 best-effort
  `chmod 0755`；2) 新增 `_stage_exe()` 以纯 Python copyfile 把二进制
  搬到 HMBS `TMPDIR/test_oprf_run`（可写且可执行）再 best-effort chmod；
  3) `test()` 优先执行 staged 路径，`_run_test_exe()` 在直接 exec 报
  EPERM 时自动回落到 staged 路径；marker `command` 与 conanrun 二次
  运行同步改为实际执行路径。
- 证伪/边界：只换执行位置，不改链接与断言；若 TMPDIR 同样 noexec，
  日志会显示 staged 路径同样 EPERM，届时再按新证据处理。

## 2026-09-18 第十轮：TMPDIR 同样 EPERM，改直出缓存可执行目录（未提交）

- 现象：上一轮 TMPDIR 策略双路径均 EPERM（直接执行
  `.../runtime/.../tmp/test_oprf_run` 报 EPERM，_stage 又落到同一文件
  再次 EPERM）；上游仍 11/11，静态直链 RUN 行正常。
- 根因：Python copyfile 新建文件按 644 落盘，`chmod=0` 下无法补 +x，
  故 TMPDIR 拷贝必然不可执行；代码树输出同样受限。反观上游
  `dkg/tv1/...` 在 `conan-home/p/b/.../build-release` 下全部可执行，
  证明 Conan 缓存挂载允许 exec。问题在落盘位置，不在二进制本身。
- 方案（与 TMPDIR 拷贝不同的策略，保留静态链）：新增 `_exe_dir()` 优先
  `base_build_folder`（ Conan 缓存，与上游可执行目录同挂载），`build()`
  直接 `cc -o <cache>/test_oprf` 让编译器一次性赋予执行位，不再做
  Python 拷贝；`test()` 按 `_exe_candidates()` 就近查找已存在二进制，
  `_run_test_exe()` 仅在 EPERM/缺失时换候选路径重试。
- 证伪/边界：只换输出目录，不改链接与 2 个 CHECK-OK 口径；若缓存目录
  同样 EPERM，日志将显示 `test_package output/exec` 实际路径，可再定位。

## 2026-09-18 第十一轮：双路径 EPERM 改 OHOS ELF 自签名（未提交，第二策略周期）

- 现象：第十轮（缓存直出）同样双路径 EPERM：直接执行与 `_exe_candidates`
  重试均 `PermissionError: [Errno 1] Operation not permitted`（回溯指向
  `_run_test_exe` 重试行，说明两个已存在候选文件都不可执行）；上游测试
  本轮 `discovered=0`（主包缓存命中、build 跳过，无新上游证据）。
- 上一周期为何无效（三轮同一根因假设：Unix 执行位/落盘位置）：
  第八轮静态直链、第九轮 TMPDIR 拷贝、第十轮缓存直出都假设 EPERM 是
  mode 或 noexec 挂载问题。但 HMBS 明确 `chmod=0`（chmod 是 no-op），且
  EPERM 发生在**所有**候选路径（含与上游可执行目录同挂载的缓存候选），
  位置假设无法解释；缺 +x 应报 EACCES（Errno 13）而非 EPERM（Errno 1）。
- 新根因（知识库已验证经验，非位置假设）：
  `knowledge/DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing.md`
 （VERIFIED）实证：HongMeng 内核拒绝执行无有效 `.codesign` 段的 ELF，
  首轮即 `PermissionError`，且“`chmod 755` 不是充分条件”；notes 首轮亦
  记录过 strip 破坏 `.codesign` 的怀疑。签名是文件内容属性，与落盘在哪
  无关——恰好解释双路径同时 EPERM。
- 方案（与之前三轮不同的实现路线，只动 test_package/build）：
  链接后立即按 cronutils 同款流程自签名（`user.ohos:sign_tool` →
  `OHOS_SIGN_TOOL` → PATH → `/data/service/hnp/bin/binary-sign-tool`；
  先 `llvm-objcopy --remove-section .codesign` 再
  `binary-sign-tool sign -selfSign 1` 到临时文件后 `os.replace`，
  best-effort chmod；签名工具缺失时仅 warning，不伪造通过）。
  另新增 `_log_codesign()` 以 `llvm-readelf -S` 在日志中留存
  `.codesign present=true/false` 证据，供下轮证伪。
  静态直链、缓存输出目录、2 个 CHECK-OK 口径、上游 11 用例判定均不变。
- 证伪/边界：若下轮 `codesign present=true` 但仍 EPERM，则签名假设被证伪，
  转查沙箱路径策略（如把执行委托给主包 build 期已验证可执行目录）；
  若工具缺失（warning）且仍 EPERM，则报告环境缺签名工具；
  `os != OHOS` 且无签名工具时跳过签名，不影响 Linux 行为。
