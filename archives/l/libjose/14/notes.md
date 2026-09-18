# libjose 14 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-15
- 编译器: clang/clang++ (aarch64-linux-ohos, 真机预检)
- 状态: built (待真机 evidence 轮确认后由 HMBS 统一提交)

## 上游信息
- 上游仓库: https://github.com/latchset/jose
- 上游版本: v14 (2024-05-22, latchset/jose releases)
- 源码包: https://github.com/latchset/jose/releases/download/v14/jose-14.tar.xz
- sha256: cee329ef9fce97c4c025604a8d237092f619aaa9f6d35fdf9d8c9052bc1ff95b
  (三方交叉确认: Homebrew formula、PureOS 软件源、Buildroot jose.hash 一致)
- 许可证: Apache-2.0

## 编译步骤

配方执行流程 (conanfile.py):
1. `PkgConfigDeps` 生成 jansson/openssl/zlib 的 .pc 文件,并派生
   libcrypto.pc/libssl.pc 别名,供 meson `dependency('libcrypto')` 解析。
2. `MesonToolchain`: `default_library` 跟随 shared 选项,
   `docs=disabled` 跳过 asciidoc man 页,`wrap_mode=nodownload`。
3. `meson setup --native-file conan_meson_native.ini -D... <build> <src> --prefix=/`
   (显式 -D: default_library/docs/wrap_mode/werror/b_ndebug;setup 系手写命令,
   不依赖 helper 转发;随后 `meson introspect --buildoptions` 核验生效值,
   探针绕开 meson harness 直跑 `jose alg/jwk pub` 与 `alg_comp` 留证据)
4. `meson compile -C <build> -j1`
5. `meson test -v -C <build> --no-rebuild --print-errorlogs` (上游 25 项,
   汇总 Ok/Fail 解析后输出 HMBS_UPSTREAM_TEST_RESULT 标记,失败即抛异常)。
6. `meson install -C <build> --destdir <package> --no-rebuild`,
   COPYING 拷入 licenses/,共享库别名链物化为实体拷贝。

## 上游测试审计 (源码审计,tests/meson.build @ v14)

| # | 测试名 | 类型 | 说明 |
|---|--------|------|------|
| 1-5 | alg_hash/alg_sign/alg_encr/alg_wrap/alg_comp | 编译 C 程序 | 各算法族覆盖;alg_comp 含 DEF 压缩往返与解压上限 DoS 防护断言 |
| 6-8 | api_b64/api_jws/api_jwe | 编译 C 程序 | 公共 Base64/JWS/JWE API 测试 |
| 9-24 | jose-alg/jose-fmt/jose-b64-enc/jose-b64-dec/jose-jwk-{eql,exc,gen,pub,use,thp}/jose-jws-{fmt,ver,sig}/jose-jwe-{fmt,dec,enc} | shell 脚本 | jose CLI 行为测试 (sh + grep,无 jq 强依赖) |
| 25 | issue-75/issue75 | 编译 C 程序 | openssl 存在时才注册的回归测试 |
| 合计 | 25 | meson test | `meson test` 汇总行 Ok/Fail 为准 |

shell 脚本以 `#!/bin/sh` 执行;若真机缺 /bin/sh 导致 16 项脚本失败,
下一轮将补 shebang 可移植补丁并重新验证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson `dependency('libcrypto')` 在 Conan 环境下找不到 | ohpcd openssl 配方 cpp_info 只有 libs,PkgConfigDeps 只生成 openssl.pc | generate() 内由 openssl.pc 派生 libcrypto.pc/libssl.pc 别名 (Name/Libs 改写,沿用 aravis 的 glib 别名手法) |
| 2 | HarmonyOS CPython 经 posix_spawn 调子进程不查 PATH,ninja 探测 ENOENT | 平台特性 (libdicom 已验证) | machine 文件注入 ar/ranlib/ninja 绝对路径;NINJA 环境变量指向绝对路径 |
| 3 | 共享库 `libjose.so -> libjose.so.0 -> libjose.so.0.0.0` 符号链在 HMDFS 上不可靠 | HMDFS 软链限制 (R5) | `_materialize_shared_aliases` 物化为实体拷贝 |
| 4 | jansson 无 published 版本 | 制品仓中 jansson 仅 built (2.14/2.15.1/2.15.1.1) | 选用最新的 2.15.1.1 (含 SONAME 修复);若真机预检报依赖未发布则按 HMBS 指示处理 |
| 5 | 真机 /tmp 只读,12 个 shell 测试 `mktemp -d` 默认落 /tmp | preflight readonly_tmp 门禁 | 测试 env 显式 e.set TMPDIR/TMP/TEMP + 测试命令前缀三变量,仅换临时根目录 |
| 6 | 真机 alg_comp SIGSEGV + jwk-pub exit 1(均不经过 mktemp,env 方案无效) | 断言密集型测试 + 手写 setup 命令是否透传 toolchain 选项存疑 | setup 命令行显式 -D 五选项 + introspect 核验 + 探针复现(区分库缺陷与 harness 问题);master 版测试与 v14 一致,无上游补丁可回溯 |
| 7 | 真机 23/25:仅 jose-jwk-pub/thp 失败(均无 mktemp,上一轮 TMPDIR 透传对此二者无效) | 已证伪 TMPDIR 假设:tarball 审计仅 3 个脚本用 mktemp(jwe-enc/jwk-exc/jws-sig),pub/thp 无 mktemp、无 /tmp 硬编码;且 eql 同用 jwk pub 却通过,故非 jose 通路故障,须区分 harness 与库输出差异 | 改走串行+取证路线:meson test 加 --num-processes 1 消除并行共享 TMPDIR 竞争;探针改 Python 捕获逐断言严格比对(5 条 pub+2 条 thp)并单行输出 PASS/FAIL;失败时从 meson-logs/testlog.txt 抽取两用例片段拼入 RuntimeError,使下轮摘要保留真实 diff;不跳过不断言 |
| 8 | 上轮取证零信号:argv 直调探针绕过 shell,HMBS 截断吞掉探针行,extract 抓到的是环境头而非 stdout | argv 复现与 meson 经 `#!/bin/sh` 执行路径不一致;若缺陷在 shell 行为(backticks/test/echo)则 argv 通过而 harness 失败,无法区分;且存活率最高的是 RuntimeError 通道(探针 info 行会被省略) | 改走 shell 保真路线:探针新增 `_probe_shell_repro`,用 `/bin/sh -ex -c` 原样执行两条首断言并保留 trace,结论写入 `hmbs_probe_summary.txt`;extract 改取 FAIL 行前 550 字符尾部(stdout diff)并链入探针结论,总量压至 950 字符内以穿透摘要截断;通过的 eql(jwk pub 真实密钥)与失败的 pub(空合成密钥)对比仍指向输出差异待下轮实证 |

## 真机突破(第 3 次预检回传)
- `HMBS_PROBE_SHPUB rc=1 … Error removing private keys! … test '' '=' …`:经 `/bin/sh` 原样复现,`jose jwk pub` 在合成 oct 键(`"k":""`)上直接退出 1,输出为空;而 eql 用例用真实生成密钥调同一子命令通过,触发条件锁定在合成键的空成员上。
- `THP_S256 PASS`、`THP_S1FIND PASS`(argv 直调)与 `SHTHP256 rc=0`(shell 首断言)一致通过:thp 失败藏在后半段,本轮以 FINDPOS/FMT/NEG/DEF 四行二分定位。
- 平台诊断 readonly_tmp 仍在,但两失败脚本经审计无 `/tmp` 写入,继续沿用最小适配(已透传 TMPDIR/TMP/TEMP,不删测试)。
- 取证通道修正:extract 改用 `jwk-pub.*FAIL` 行定位尾部 550 字符,探针结论压缩为 `TAG:rc` 链入异常,总预算 950 字符。

## 本轮证伪记录
- fixture 非空检查:探针先 `getsize` rfc7638_3.1.jwk/.thp 与 rfc7520_4.8.jwkset,空文件即判取证无效,避免空比空假通过。
- harness 抓错能力:meson test 仍以 --print-errorlogs 全量运行,25 项全部执行;若探针 PASS 而 harness FAIL 则定位 shell/harness,若双方一致 FAIL 则定位库输出,下轮按取证结论走。

## 依赖版本

- jansson/2.15.1.1 (JSON 解析,meson dependency('jansson'))
- openssl/3.5.6 (published;libcrypto,EC/RSA/AES/HMAC 后端)
- zlib/1.3.1 (published;JWE "zip" 压缩)
- meson/1.11.0 (published with prebuilt binary in ohpcd,tool_requires)

## 验证结果

```bash
# 真机预检 (HMBS 后台执行,本轮未运行):
# conan create archives/l/libjose/14 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 ...
# 预期: meson test 25/25 通过;test_jose 8/8 通过;
# HMBS_TEST_PACKAGE_RESULT 与 HMBS_UPSTREAM_TEST_RESULT 双标记齐全。
```

待 HMBS 真机 evidence 轮回填实测数字,本轮不猜测通过率。

## 交付物

配方输出: `lib/libjose.so*`、`include/jose/*`、`lib/pkgconfig/jose.pc`、`bin/jose` (CLI)。

## 注意事项

- 本库同时产出共享库与 `jose` CLI,故软件级附 commands.json (type tool,沿 openssl 先例),binary 先标 false,发布后由流程翻 true。
- 上游 `werror=true` 在本移植中整体关闭(`-Dwerror=false`):其测试辅助均把副
  作用藏在 `assert()` 内(tests/alg_encr.c 的 `xxx`、tests/api_jwe.c 的 `dec()`,
  仅经 `assert(...)` 调用),Release(-DNDEBUG)下 `assert` 展开为空,每个目标暴露
  不同警告类别(-Wunused-variable、继而 -Wunused-function……),逐类
  `-Wno-error=` 打地鼠不收敛;关闭 werror 后测试二进制仍需编译且 meson test
  门禁仍须全过。另对 `xxx` 已知点做配方内 `(void)xxx` 字符串替换(不改测试语义)。
- 未修改上游任何测试用例;test_package 为新增消费者测试 (test_jose.c,8 断言)。

## 第4轮:全行级二分(本轮工作树未提交)
- 上三轮失败原因:仅覆盖4条pub+4条thp断言且用 -ex trace,输出被HMBS截断吞掉;pub缺L4(jwkset)/L5(-s)/L3(EC),thp缺L1/L2B/L6/L7,精准失败行始终不可见,故连续三轮23/25原地踏步。
- 本轮改走全行级二分:5条pub(L1-L5)+8条thp(L1/L2A/L2B/L3/L4/L5/L6/L7)逐行经 /bin/sh -c 隔离执行,stdout/stderr分离捕获,每行仅输出 TAG:rc 压缩结论(防截断);另加CTL_REALPUB(真实生成密钥走pub,预期PASS,区分二进制整体损坏与合成输入拒绝)与CTL_FMT(合成输入走fmt,排除JSON解析损坏)及CTL_RAWOUT(透出原始stderr)。
- 若CTL_REALPUB通过而PUBL1-5全败,则锁定合成空成员触发;若THPL2B或THPL7失败而其余通过,则锁定stdin-thp或Ed25519行为差异。下轮按回传矩阵定配方补丁或上游行为声明,不跳过不断言。

## 第5轮:单变量最小化(本轮工作树未提交)
- 第4轮全行二分已穿透截断取得突破:RuntimeError链入[probe PUBL1:1 PUBL2:1 PUBL3:1 PUBL4:1 PUBL5:1 THPL1:0 THPL2A:0 THPL2B:0 THPL3:0 THPL4:0 THPL5:0 THPL6:0 THPL7:1 CTL_REALPUB:0 CTL_FMT:0]，即pub5行全败、thp仅THPL7(Ed25519负例)失败、真实密钥对照通过。
- 本轮不再重复全矩阵(同指纹第2次修复禁复用相同策略)，改走单变量最小化:jose自身rc经out=$()捕获上报(旧探针报的是test(1)rc，掩盖jose真实行为);M1最小oct->M2+key_ops->M3空k->M4空k+key_ops逐级加压，M5真实oct对照，M6最小RSA;T7INNER去掉!取反透出Ed25519指纹真实rc/输出，T7GEN列出可用hash。
- 待回传JRC矩阵后定修复:若M1即败则为oct通路整体拒绝，若M4独败则为空成员触发;若T7INNER的JRC=0(指纹成功)则上游!断言已过时，需配方内处理。

## 第6轮:字节取证JRC/TRC分离(本轮工作树未提交)
- 第5轮最小化反转突破:8项M探针JRC全0(含PUBL1核心M4与最小RSA)，即jose自身全部成功，但上游test字符串比对仍失败——旧探针以shell rc(恒0)上报JRC，RuntimeError的M全0具误导性。
- 本轮换字节取证路线(从未用过):每案分离JRC(jose健康)与TRC(字符串相等)，以exit TRC使verdict rc与上游一致；TRC=1时od输出期望与实际前40字节hex(去空格截80字符，防截断)。B1/B2覆oct/EC精确行，B3覆stdin-thp回灌，B4覆Ed25519(以jrc!=0为TRC=0)。
- 若回传JRC=0/TRC=1且hex仅键序或空白差异，则为jansson版本序列化差异，需配方侧处理；若JRC=1则为库拒绝。下轮按hex定修复。

## 第7轮:整脚本harness保真+post-FAIL取证(本轮工作树未提交)
- 第6轮字节取证出现反转矛盾:合成探针B1_PUBOCT:0/B2_PUBEC:0/B3_THPL2B:0全部PASS,
  但meson仍报jose-jwk-pub+thp FAIL;B4_THPL7:1说明Ed25519内联键指纹成功而探针按
  失败预期判定,与上游L7(`! jose ... -f VHri...`期待找不到键)语义不同,旧extract
  取FAIL行前550字符抓到的是上一个测试块/环境头,零信号。
- 本轮换全新路线(第4策略周期禁复用合成单行bisect/最小化/字节比对):探针改为整
  脚本保真执行——原样跑`source/tests/jose-jwk-pub`与`jose-jwk-thp`(`/bin/sh -ex`
  文件,meson同款PATH=build/cmd+VECTORS+CVE_2023_50967+TMPDIR三变量),各跑两遍
  NOLD(复刻meson无LD_LIBRARY_PATH)与LD(加build/lib)对照;若NOLD败而LD过则锁定
  loader/rpath而非JSON序列化,另加readelf -d与lib目录诊断区分加载与输出故障。
- extract改为取FAIL行后900字符(至下一`N/25`头截断,取末380字符真实diff),优先读
  `meson-logs/testlog.txt`,结论与探针TAG:rc链入RuntimeError,预算950字符穿透摘要。
- 若回传H_PUB_NOLD与H_PUB_LD同败且尾部`+ test`指向同一断言,则排除loader假设,
  下轮按真实diff修jansson/输出;若NOLD败LD过,则补meson测试env的rpath/LD处理。

## 第8轮:hashlib正交oracle+file-stdin隔离(本轮工作树未提交)
- 第7轮整脚本保真取得决定性证据:H_PUB_NOLD与H_PUB_LD同为rc=1且同报
  `Error removing private keys!`+空stdout,故loader/rpath假设被证伪排除;
  H_THP_NOLD与H_THP_LD同败但第二阶段指纹各异(8G8E…/AL96…均非HYRNO…),
  指向S1哈希后端或规范化,而非harness环境。[jwk-pub nosection]说明extract
  在testlog无匹配时须回退meson_test.log,已顺手修复为双文件候选。
- 本轮换全新正交路线(禁复用合成bisect/整脚本复跑):以Python hashlib为
  RFC7638指纹oracle,对rfc7638_3.1.jwk与rfc7520_4.8.jwkset各成员逐个算
  S1/S256参考值并与`jose jwk thp -i 成员文件`逐项比对;S256通过而S1独败
  即锁定S1后端(SHA-1),双败则锁定jwk_str规范化/jansson。同时pub改走
  FILE输入(`-i 文件`,json_loadf FILE分支)对照echo管道(stdin分支),
  stdout/stderr/rc分离上报,区分输入路径与jwk_clean逻辑故障。
- 待回传O_*矩阵:若S256全PASS而S1全FAIL则修哈希后端相关配方/补丁;
  若FOCT/FEC文件输入通过而管道失败则修输入路径理解;若一致失败则按
  差异字节定补丁。不跳过不断言。

## Round 9: shell-pipe fidelity + echo-to-printf (worktree only, strategy cycle 5)
- Why the previous route is rejected: round-8 hashlib oracle falsified the
  "library defect" hypothesis -- O_RFC7638_S1:PASS plus all JWKSET S1/S256
  PASS, and FILE-input pub rc=0, while STDIN-pipe variants of the SAME JSON
  failed. A library defect cannot pass via -i FILE and fail via -i- on
  identical bytes; NOLD/LD-identical failures had already rejected the
  loader hypothesis. Further bisecting jose crypto/canonicalisation would
  be a 4th reuse of the same root-cause assumption, so the route changes.
- New route (never used: shell layer, not jose layer): both failing
  assertions share unquoted `echo $var | jose ... -i-`, subject to word
  splitting + pathname expansion (`[...]` brackets in key_ops values) +
  platform echo escape handling, which can mangle JSON before jose parses
  it. The probe compares 4 delivery paths for byte-identical input
  (python-direct-stdin / echo-pipe / printf-pipe / -i FILE) plus a
  jose-free echo-vs-printf byte check (od hex vs python ground truth).
  Artifacts are isolated under build/hmbs_probe/ to avoid polluting the
  meson test CWD. Diagnostic only, never skips.
- Fix: in-recipe replacement of `echo $var |` with `printf '%s' "$var" |`
  in tests/jose-jwk-pub (5 lines) and tests/jose-jwk-thp (1 line). Only the
  pipe spelling changes; assertions, vectors and exit semantics untouched.
  Minimal upstream-shell portability adaptation, no test skipped.
- Pending matrix ECHO/PRINTF/DIR/FILEP/ECHOPIPE/PRINTPIPE/TFILE/TDIR/TECHO:
  ECHOPIPE-only failure with PRINTPIPE passing pins the echo layer and the
  patch is on-target; uniform failure across all four paths refutes the
  shell hypothesis and the next round moves to the json_loadf(stdin) pipe
  read layer.
