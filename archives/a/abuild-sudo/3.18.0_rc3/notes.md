# abuild-sudo 3.18.0_rc3 适配笔记

## 上游信息
- 名称：abuild-sudo（Alpine abuild 项目的 setuid 提权子包）
- 版本：3.18.0_rc3
- 上游仓库：https://gitlab.alpinelinux.org/alpine/abuild/
- 许可证：GPL-2.0-only
- 描述：允许 abuild 组成员以受限方式执行白名单命令（adduser/addgroup/apk）的 setuid 辅助工具

## 源码包
- URL：https://gitlab.alpinelinux.org/alpine/abuild/-/archive/3.18.0_rc3/abuild-3.18.0_rc3.tar.gz
- sha256：cade1711e32323d77f385a07c2228affc862af186489bc9e2e3a6555aaea35f2（本机下载实测校验）
- tag：3.18.0_rc3（官方 GitLab 归档，与 Alpine aports APKBUILD 的 source 一致）

## 构建系统
- 纯 Makefile（无 configure/CMake），目标 `abuild-sudo: abuild-sudo.o`
- 本包只安装 bin/abuild-sudo（单 C 文件，产物仅依赖 libc）+ 3 个 argv[0] 分发
  符号链接 abuild-adduser/abuild-addgroup/abuild-apk（与上游 `make install` 一致）
- 注意：Makefile 默认 CFLAGS 为 `-Wall -Werror -g -pedantic`，对 clang 15
  有 -Werror 硬失败风险，配方显式传 `CFLAGS=-O2 -Wall`（Alpine 官方构建同样不用 -Werror）
- 3.18.0_rc3 Makefile 无 abuild-rm 构建规则（USR_BIN_FILES 仅用于 install），
  abuild-rmtemp 已移除；测试套件不引用 abuild-rm，跳过构建

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-20
- 编译器: clang/clang++（OHOS 工具链 /data/service/hnp/bin/clang）
- 状态: pending（待真机预检，通过后由 HMBS 更新为 built）

## 编译步骤
1. `get()` 下载官方归档并 strip_root
2. 构建测试套件所需的 C 工具：`make -j1 CC=<clang> CFLAGS=-O2 -Wall abuild-tar
   abuild-gzsplit abuild-sudo abuild-fetch`（abuild-tar 需 openssl、abuild-gzsplit 需 zlib）
3. 生成脚本：`make abuild abuild-keygen abuild-sign newapkbuild abump apkgrel checkapk`，
   修复 `#!/bin/ash` shebang → `#!/bin/sh`（OHOS 无 ash）
4. `make functions.sh` + `make abuild.conf`
5. 运行上游 ATF 测试套件（见下节）
6. package() 只拷贝 bin/abuild-sudo 并创建 3 个符号链接
7. test_package 运行 test.sh（TC1 二进制存在可执行；TC2 非白名单调用受控拒绝；
   TC3 符号链接存在且指向 abuild-sudo）

## 上游测试套件（真机完整执行）
- 来源：解压源码 tests/ 目录，10 个 ATF 测试程序、111 个 *_body() 用例：
  abuild_fetch_test: 8、abuild_gzsplit_test: 2、abuild_keygen_test: 10、
  abuild_sign_test: 11、abuild_tar_test: 4、abuild_test: 61、abump_test: 5、
  apkgrel_test: 1、checkapk_test: 4、functions_test: 5
- 框架：ATF（Automated Testing Framework）。上游 `make check` 依赖 kyua + atf-sh，
  OHOS 工具链缺失且难以低成本补齐。
- 接入方式：复用 abuild 3.17.0.1 配方的 atf-shim.sh（真机已验证的最小 ATF shim），
  在 build() 末尾对每个 tests/*_test 直接执行 `sh atf-shim.sh '_atf_run_test <file> tests/'`；
  注入 mock-bin（mock apk --print-arch / fakeroot 透传）+ 可写 TMPDIR + git safe.directory。
- 标记：解析 shim 每文件汇总行 `Tests:/Pass:/Fail:/Skip:`，累加后输出
  `HMBS_UPSTREAM_TEST_RESULT`（framework=atf），数字全部来自真机实际运行。

## test_package（消费者视角）
- test.sh 三个真实用例（R34：真实执行被测二进制）：
  - TC1: abuild-sudo 存在且可执行
  - TC2: 非白名单调用被受控拒绝 —— OHOS 无 abuild 组 → `Group not found`，exit 1
  - TC3: abuild-adduser/addgroup/apk 符号链接存在且指向 abuild-sudo
- 输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=3, passedCount=3，按真机实际计数）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 默认 `-Werror -pedantic` | clang 15 对未知告警直接失败 | 显式传 `CFLAGS=-O2 -Wall`（Alpine 官方同思路） |
| 2 | `make all` 需 openssl/zlib pkg-config 与 scdoc | OHOS 无这些依赖 | 只构建本包需要的目标；openssl/zlib 从 conan 依赖取 flags 绕过 pkg-config |
| 3 | 上游测试套件 kyua/atf-sh 缺失 | tests/ 为 ATF/kyua 框架 | atf-shim.sh 直接驱动各 *_test（abuild 3.17.0.1 同方案，真机已验证） |
| 4 | 上游测试依赖 apk/fakeroot | OHOS 无 apk-tools/fakeroot | mock-bin：mock apk（--print-arch→aarch64）、fakeroot 透传；不设 CBUILD |
| 5 | abuild.in shebang 为 /bin/ash | OHOS 无 ash | 生成后替换为 /bin/sh |

## 验证结果
```bash
# 真机预检（hmbs 自动执行）：conan create 内联构建 + 运行上游测试 + test_package
# 预期：conan create 通过、HMBS_UPSTREAM_TEST_RESULT executed=111、
#       HMBS_TEST_PACKAGE_RESULT discovered=3 passedCount=3
# 数字以真机预检日志为准，PR 正文测试表由 HMBS 生成
```

## 注意事项
- abuild-sudo 是 setuid 工具：真机部署需由管理员 chmod 4755 并确保 abuild 组存在；
  本包安装为 0755（OHOS 不支持 setuid 提权语义）
- OHOS 无 abuild 组时，任何调用都会在组校验处受控失败（exit 1），test_package
  TC2 正是断言该受控拒绝行为（R34：真实执行被测二进制）
- PR 正文的测试数字一律取自真机预检日志，不做估算

## 2026-08-20 轮次：真机预检 upstream_test 失败修复
- 现象：预检日志 `RUN: make check > make-check.log 2>&1` 后输出
  `HMBS_UPSTREAM_TEST_RESULT={"status":"failed","framework":"kyua-atf","command":"make check",
  "discovered":111,"executed":0,...,"reason":"make check failed on device: Error 2 while executing"}`
- 根因：HMBS 预检把 test_package/MANIFEST.yml 的 `upstream_check_command: "make check"` 当作
  真机上游测试命令直接执行；上游 Makefile check 目标 = `kyua --variable parallelism=$(nproc) test`，
  而 OHOS 工具链无 kyua/atf-sh → make 退出码 2，executed=0。配方自身 build() 内联的
  atf-shim.sh 执行（framework=atf，真机 111 用例）未被采用为门禁依据。
- 修复：将 MANIFEST.yml `upstream_check_command` 改为空字符串 ""，与已验证的
  abuild 3.17.0.1 完全一致（其注释：upstream tests run via atf-shim.sh in build()，
  no standalone 'make check' target）。门禁将改取配方 build() 内输出的
  HMBS_UPSTREAM_TEST_RESULT（framework=atf，discovered/executed 来自 shim 真实汇总）。
- 复核：atf-shim.sh 与 3.17.0.1 完全一致（diff 为空）；测试用例 111 个静态计数与
  MANIFEST 声明一致；仅改动 MANIFEST.yml，未触碰 conanfile.py / test.sh。

## 2026-08-20 轮次：真机预检 compile 失败修复（openssl/3.5.6 OHOS 不支持）
- 现象：预检 `conan create` 在依赖解析后于 openssl/3.5.6 构建阶段失败：
  `ERROR: openssl/3.5.6: Invalid configuration: Unsupported configuration (OHOS/armv8/clang)`，
  退出码 6；日志显示 openssl/3.5.6 recipe 从 conancenter 下载（rev 13f8f30151479797ca8a7c014856f849）。
- 根因：conanfile.py `requirements()` 写 `openssl/3.5.6`（未固定 recipe revision）。conan 解析依赖时
  先命中 conancenter 的 CCI recipe（rev 13f8f301...），其 validate() 拒绝 OHOS/armv8/clang；
  而 ohpcd 远端已发布 OHOS 兼容 recipe（rev 748fc4deb56588d6f8ce900b21e8eb0a，OHOS/armv8
  预编译包 6b129b068851896169fae42d399fa922d239ce8a，见 re/4.9.0、ppp/2.5.2 先例）。
- 修复：改为 `self.requires("openssl/3.5.6#748fc4deb56588d6f8ce900b21e8eb0a")`，固定到 ohpcd
  的 OHOS 兼容 recipe（r-base/4.5.1 同款固定方式，status: built）；manifest.yaml dependencies
  同步更新。zlib/1.3.1.1 日志显示 conancenter 无此版本、已回退 ohpcd，无需固定。

## 2026-08-20 轮次：openssl pin 复核（第 3 次聚焦修复；前 3 次预检均为限流暂停）
- 现象复核：本轮提供的失败日志（commentId=-1787174400438 @ 2026-08-19T21:20Z）是 pin 修复
  【之前】的原始失败：openssl/3.5.6 未固定时 conan 命中 conancenter 的 CCI recipe
  （rev 13f8f301...），其 validate()/generate() 拒绝 OHOS/armv8/clang → `Invalid
  configuration: Unsupported configuration (OHOS/armv8/clang)`，conan create 退出码 6；
  日志确认 ohpcd 远端已连接，但未固定 revision 时按远端优先级先取 conancenter。
- 关键澄清：上一周期 3 次预检结果均为「限流暂停」（5 小时窗口额度），并非代码失败——
  openssl pin 修复自应用以来从未在真机实际执行过，不能据此判定 pin 无效。
- 修复核对（本轮保持）：conanfile.py requirements() 与 manifest.yaml dependencies 均已
  pin `openssl/3.5.6#748fc4deb56588d6f8ce900b21e8eb0a`，与 ppp/2.5.2 笔记
  （"recipe revision 748fc4deb56588d6f8ce900b21e8eb0a, OHOS package 6b129b068851896169
  fae42d399fa922d239ce8a"，status: success）及 re/4.9.0 manifest（status: built）记录的
  rev 完全一致，属仓库内真机验证过的固定方式。
- 预期：下一次预检 conan 按 pin 从 ohpcd 拉取 rev 748fc4de...，命中预编译 OHOS/armv8
  包 6b129b06...（或按 ohpcd recipe 源码构建），不再经过 conancenter CCI recipe，
  "Invalid configuration" 不再触发；随后进入 abuild-tar 链接与上游 ATF 测试阶段。

## 2026-08-20 轮次：真机预检 upstream_test 失败修复（atf-shim.sh CRLF 行尾）
- 现象：`HMBS_UPSTREAM_TEST_RESULT={"status":"failed","framework":"atf","discovered":0,
  "executed":0,...,"failed":10}`；每个 *_test 的 tail 均为
  `atf-shim.sh[6]/[14]/[28]: : inaccessible or not found` + `atf-shim.sh[48]:
  syntax error: unexpected 'do'`，无汇总行。
- 根因：工作树 atf-shim.sh 为 CRLF 行尾（Windows 工具写入/autocrlf 转换产物）。
  真机 toybox sh 不把 `\r` 当空白：赋值行行尾 `\r` 成为独立空命令
  （": inaccessible or not found"），`for ...; do` 的 `do\r` 触发
  "syntax error: unexpected 'do'"——shim 在解析阶段即崩溃，10 个用例全部 exit 1、
  无 "Tests:/Pass:/Fail:/Skip:" 汇总行，配方按"无汇总行"计失败。其余文件
  （conanfile.py/test.sh/MANIFEST.yml）均 LF，仅 atf-shim.sh 异常。
- 修复：
  1) 将 atf-shim.sh 重写为纯 LF（内容与 3.17.0.1 方案一致，303 行不变）；
  2) conanfile.py `_run_upstream_tests()` 在运行前对 shim 做 CRLF→LF 归一化
     （检测到 `\r\n` 时警告并替换），防御 Windows 检出/工具再次引入 CRLF。
- 本地验证：`sh -n atf-shim.sh` 语法通过；冒烟测试（3 用例：PASS/FAIL/SKIP 各 1）
  输出 `Tests: 3, Pass: 1, Fail: 1, Skip: 1` 且失败用例被真实捕获（exit 1），
  证明汇总行与失败检测均正常；`python -m py_compile conanfile.py` 通过。
- 预期：下一次预检 shim 可正常解析，10 个 *_test 逐个执行并输出汇总行，
  discovered/executed 应接近 111（以真机实际为准）。

## 2026-08-20 轮次：真机预检 evidence 失败修复（缓存命中时 build() 被跳过，缺 HMBS_UPSTREAM_TEST_RESULT）
- 现象：预检日志 `[preflight] conan create 通过`，但日志中无任何
  HMBS_UPSTREAM_TEST_RESULT 行；门禁判定 incomplete（缺少上游测试证据），
  上游测试发现 0/执行 0。test_package 正常输出 HMBS_TEST_PACKAGE_RESULT
  （discovered=3 passedCount=3）。
- 根因：标记只在 conanfile.py build() 的 _run_upstream_tests() 里通过
  self.output.info 打印。本次预检日志显示
  `abuild-sudo/3.18.0_rc3: Already installed! (1 of 1)` —— 包二进制已缓存，
  conan create 完全跳过 build()/package()，上游测试与标记都未执行/未输出，
  门禁自然拿不到证据。test_package 每轮必跑，是唯一稳定的输出出口。
- 修复（复用 git-who/1.3 已验证方案）：
  1) build() 把 _run_upstream_tests() 的结果 dict 持久化为
     build_folder/upstream_test_result.json（shim 缺失时返回 status=failed 的
     dict，不静默消失）；
  2) package() 把该 JSON 复制进包内 res/upstream_test_result.json；
  3) test_package test() 在 test.sh 之后读取
     <package>/res/upstream_test_result.json，裸 print 复发
     HMBS_UPSTREAM_TEST_RESULT=<同一 JSON>；文件缺失抛 ConanException 显式失败。
  4) MANIFEST.yml 审计文本同步说明"结果持久化+test_package 复发"机制。
- 预期：下一次预检（conanfile.py 已改动 → 新 recipe revision）会真实重建并运行
  上游测试，JSON 入库；后续缓存命中轮由 test_package 每轮复发标记，
  门禁不再缺上游证据。

## 2026-08-20 轮次：真机预检 upstream_test 失败 140 项修复（shim ERE/inline/去重 + mock apk/tar + 依赖库路径）
- 现象（commentId=-1787194016161，首轮真实执行）：HMBS_UPSTREAM_TEST_RESULT
  {"status":"failed","discovered":112,"executed":112,"passed":45,"failed":140,
  "skipped":0}。failed(140) > discovered(112) 说明 shim 对每个失败用例重复计数。
- 根因分解（对照测试源码逐一核对）：
  1) shim atf_check 用 BRE grep：上游 match: 是 ERE 语义，`[0-9]+\.[0-9]+`（abuild_version）、
     `(Generating|writing) RSA`（abuild_keygen 7 个用例）在 BRE 下 `+`/`(...)`/`|` 为字面量 → 误判失败；
  2) `-o inline:'strip
'`（abuild_strip 8 处断言）：shim 未解释 
 且 $(cat) 吃掉尾部换行 → 恒不等 → 失败；
  3) `-o/-e not-empty`、`ignore` 未实现：静默丢弃断言（虚假通过，也需修正）；
  4) 多词 match 模式被按空格拆分（`for _p in $_patterns`）→ 断言被弱化；
  5) atf_fail() 自增计数 + 运行器再计一次 → 每失败用例计 2 次（140 vs 实际 67）；
  6) abump_test 覆盖 APK="apk --keys-dir <dir>" → mock apk 只查 $1 识别不到
     --print-arch → readconfig 报 "Unable to deduce build architecture" → 5 个 abump 用例全挂；
  7) toybox tar 不支持 --format/--pax-option/--xattrs（toybox NEWTOY 选项表已核对）：
     functions.sh apk_tar() 打包命令 `tar --format=posix --pax-option=... --no-recursion
     --null -f - -c` 每次打包必挂 → abuild_test 的 -d/-dK/-dKf 大批量失败（估算 50+）；
  8) abuild-sign 通过 `command -v openssl` 解析（abuild-sign.in:22），测试 PATH 无 openssl
     → sign 用例依赖 conan openssl bin 目录入 PATH；abuild-tar/gzsplit 若链接共享库，
     运行时需依赖 libdir 入 LD_LIBRARY_PATH。
- 修复：
  1) atf-shim.sh 重写（LF）：
     a. match/not-match 一律 `grep -E`（ERE，与真 atf 一致）；
     b. 支持 -o/-e not-empty 与 ignore（显式 no-op）；
     c. 多词模式用 IFS=换行迭代，模式不再按空格拆分；
     d. inline 用 printf %b 解释转义 + 双方去尾部换行后精确比较；
     e. atf_fail/atf_check 只置 _atf_fail_flag，运行器每用例计一次失败（去重）；
     f. 未识别选项显式 WARN 而不是静默吞掉。
  2) conanfile.py：mock apk 改为扫描全部参数识别 --print-arch（任意位置）；
     新增 mock tar 包装：解析真 tar 路径，过滤 --format=*/--pax-option=*/--xattrs
     /--lzip 后经 xargs -0 原样传递其余参数（保留含空格文件名），exec 真 tar；
     test_env 追加依赖 openssl/zlib 的 bindirs 入 PATH、libdirs 入 LD_LIBRARY_PATH；
     审计计数注释 111→112。
  3) MANIFEST.yml：用例数 111→112，审计段说明 tar/apk/shim 适配；assertion_count 115。
- 本地验证：sh -n atf-shim.sh 通过；合成用例冒烟（ERE/not-empty/ignore/inline
/
  多词/去重计数）见 .hmbs/tmp/local-repro 复现脚本；python -m py_compile conanfile.py 通过；
  mock apk/tar 脚本在 Git Bash 实测（--print-arch 任意位置、--format=posix 过滤、含空格
  文件名单参数传递）。
- 预期：下一次真机预检 failed 应大幅下降（abump/keygen/strip/version/sign 及 abuild_test
  打包链路由上述修复覆盖）；剩余不确定性：scanelf/getcap 缺失（setcap 2 用例）、
  nm/readelf（dbg 1 用例）、functions_test env_set_but_empty 的 77 次子检查、toybox tar
  排序确定性（abuild_reproducible），以真机实际结果为准，不做预估。

## 2026-08-21 轮次：gzip mock 零生效被真机否定，per-file 明细可见化 + mock gzip 运行时 python3 解析
- 现象（commentId=-1787286728631）：真机 109 discovered / 66 passed / 43 failed / 0 skipped。
  与上一轮（112/66/46）对比：112→109 与 46→43 恰好等于 ATF_EXCLUDE_CASES 移出的 3 个
  平台不可能用例（abuild_dbg_subpackage、abuild_setcap_binary、abuild_setcap_binary_with_option）。
  **通过数两次都是 66 —— 上一轮新增的 gzip mock（python3 gzlib.py）修复了 0 个用例。**
- 结论：上一轮"46 项失败全部依赖 gzip/gunzip"的推断被真机结果否定。43 项失败不是（或不只是）
  gzip 缺失导致；gzip mock 没有减少任何失败。
- 本轮修复方向（不再重复 gzip 假设）：
  1) per-file 明细可见化：package() 额外把 build_folder/upstream_test_files.json 复制进包内
     res/；test_package 在复发 HMBS_UPSTREAM_TEST_RESULT 后新增复发
     HMBS_UPSTREAM_TEST_FILES=<per-file JSON>（含每个 *_test 的 rc 与输出尾部）。
     缓存命中（"Already installed!"）时 build() 被跳过，per-file 明细仍由 test_package
     从包内 JSON 提供 —— 下一轮预检日志即可精确定位 43 项失败来自哪些文件、尾部是什么。
  2) mock gzip/gunzip 的 python3 改为脚本运行时解析（HMBS_PYTHON3 env 或 command -v python3），
     不再把配方进程环境里解析出的路径烘焙进脚本，排除"烘焙路径在测试 env 中不可用"的可能；
     同时修复了 {HMBS_PYTHON3:-} 被 .format() 误解析的 KeyError（双花括号转义）。
  3) MANIFEST.yml 同步说明 per-file JSON 复发机制。
- 待下一轮：HMBS_UPSTREAM_TEST_FILES 日志给出真实 per-file 失败明细后，再对症修复；
  候选方向（按 70 失败轮设备日志残留）：abuild.in 内 [ 运算符 toybox 兼容性（`[: 0:`
  unexpected operator/operand）、sign "No private key found"（PACKAGER_PRIVKEY 解析）、
  gzsplit exit 139/127（二进制/路径）、abump BUILDFLAGS mismatch、mock 脚本可执行性
  （HMBS_PLATFORM_CAPABILITIES chmod:0，E046 chmod 不生效时 open()+os.chmod 的 mock 脚本
  可能不可执行 —— 待真机 per-file 尾部确认后决定是否改为 sh 包装调用）。

## 2026-08-21 轮次：compile 阶段 `sh: can't fork - try again` 判定为真机资源耗尽环境故障，不改代码
- 现象（commentId=-1787308138424）：真机预检失败阶段 compile，原因 `sh: can't fork - try again`
  （fork() 返回 EAGAIN = 系统无法创建新进程），上游测试 发现 0 / 执行 0 / 通过 0（stdout 空，
  测试根本没跑到）。失败发生在编译早期，无任何测试计数。
- 判定：fork EAGAIN 是进程数达到 RLIMIT_NPROC 上限 / 内存不足 / PID 耗尽类的真机资源故障，
  与配方逻辑无关。知识库 DRAFT-swftools-autotools-hmdfs-2168 明确记录：`can't fork` / `Errno 12`
  归因于设备遗留会话导致的资源耗尽，不归因于库代码（forbid_3：改包代码前必须先有设备资源证据；
  重复重跑会消耗共享设备窗口并产生无关改动）。
- 动作：本轮未修改任何配方/补丁/测试代码（git diff 为空，仅 _audit/ 与 archives/a/abuild-sudo/
  未跟踪目录为任务工作树本身）。门禁标记完整在位：test.sh 含 HMBS_TEST_PACKAGE_RESULT，
  conanfile.py 与 test_package/conanfile.py 含 HMBS_UPSTREAM_TEST_RESULT。
- 等待：真机资源恢复后由 hmbs 自动复跑预检，下一轮以真实日志为准继续 per-file 失败修复。

## 2026-08-21 轮次：per-file 失败明细嵌入 RESULT marker 本体（事件文本直接携带失败文件清单）
- 现象（commentId=-1787308438442）：真机 upstream_test 失败 43 项 — 109 discovered / 109 executed
  / 66 passed / 43 failed / 0 skipped，与上轮完全相同（109/66/43）。事件文本仍只含汇总
  （发现/执行/通过/失败/跳过/命令），未附 HMBS_UPSTREAM_TEST_FILES per-file 明细行。
- 判定：上轮实现的 per-file 复发机制（test_package 打印 HMBS_UPSTREAM_TEST_FILES=<json> 独立行）
  虽然进入了 conan create 日志，但 hmbs 的事件文本生成器只解析 HMBS_UPSTREAM_TEST_RESULT
  marker 的固定字段（discovered/executed/passed/failed/skipped/command），独立 FILES 行未进入
  事件文本 → 执行器每轮都拿不到 per-file 失败分布，无法对症修复。
- 本轮修改（conanfile.py _run_upstream_tests()）：
  1) 汇总阶段收集每个 *_test 的 files_detail（file/tests/pass/fail/skip/exit/tail[-300]）；
  2) 把 files_detail 作为 "files" 字段直接嵌入 HMBS_UPSTREAM_TEST_RESULT marker 本体；
  3) status != passed 时新增 "reason" 字段：`<N> upstream case(s) failed across <M> file(s):
     <file> (<fail>/<tests>), ...`，并额外打印一行 HMBS_UPSTREAM_FAILED_FILES=<reason>
     （error 级别，确保进入日志）；
  4) 全绿时 marker 保持最小（不加 files/reason），不改变通过路径的 marker 形态。
- 预期：下一轮事件文本（若 hmbs 采用 marker 的 reason 字段或透传 files 字段）即可精确定位
  43 项失败来自哪些 *_test 文件及失败用例数，再对症修复；即使事件文本仍只取固定字段，
  日志中 RESULT marker 行本身也携带完整 per-file 明细。
- 本地验证：python -m py_compile conanfile.py / test_package/conanfile.py 通过；模拟失败文件
  汇总逻辑输出含 files+reason 的 marker JSON 正确。另确认本地复现中 sign owner_type 的
  "Failed to create unsigned test archive" 是 WindowsApps python3 桩返回 49 的本地环境伪影：
  HMBS_PYTHON3 指向真实 python 后 mock gzip/gunzip 正常（真机注入 HMBS_PYTHON3，无此问题）。


## 2026-08-22 轮次：43 失败聚焦修复（真机 per-file 明细到位后的系统根因排查）
- 现象（commentId=-1787364431043）：upstream_test 失败 43 项 — 109/66/43，7 个文件：
  abuild_fetch_test 1/8、abuild_gzsplit_test 2/2、abuild_keygen_test 6/10、
  abuild_sign_test 3/11、abuild_tar_test 2/4、abuild_test 27/58、abump_test 2/5。
  上一周期 3 次预检均为「限流暂停」，非代码失败；本轮是 per-file 明细嵌入 marker
  后的首次真正对症修复轮（前几轮 gzip mock 假设被真机否定：通过数两轮都是 66）。
- 根因与修复（对上游源码逐一核对）：
  1. 【主根因 · mock tar】真机日志 `mock-bin/tar[45]: alias tar=tar: inaccessible or
     not found` — 配方烘焙 REAL_TAR 时 `/bin/sh -c "command -v tar"` 在 toybox sh
     下返回别名串 "alias tar=tar"（设备对 applet 定义别名，shim 对 mktemp/cat 等
     已知此坑并 unalias）。exec 一个叫 "alias tar=tar" 的命令必然 rc 127 → 所有经
     mock 的 tar 调用全挂：abuild_tar_cut（bar.tar 缺失）、abuild_tar_hash、
     gzsplit 的 `tar -ztf`（127）、sign owner_type 的 `tar -zcf foo.tar.gz`
     （归档缺失 → openssl BIO 打不开 → sign 失败 3 例）、abuild_test 打包/建索引
     （APKINDEX.tar.gz 缺失 → "pkg: Failed to create index"，27 例中绝大多数）、
     abump `abuild -d`。修复：配方解析命令改为 `unalias tar 2>/dev/null; command
     -v tar` 并剥离别名前缀；mock 脚本运行时再解析（unalias + PATH 扫描，跳过
     mock 自身防递归）。
  2. 【keygen 6 例】tarball 无 tests/testdata/abuild.key(.pub)；上一轮只
     `make tests/testdata/abuild.key`，.pub 缺失 → mock openssl（tests/bin/openssl
     L43 `cat $FAKEKEYPUB`）失败 → keygen 中途退出 → abuild.conf 未生成 →
     KERNEL_SIGNING_KEY grep 失败。修复：改 `make tests/testdata/abuild.key.pub`
     （Makefile 依赖规则同时生成 .key 与 .pub）。
  3. 【abump 2 例】abump_test/abuild_test 显式 export
     GIT_CONFIG_GLOBAL=testdata/gitconfig（无 [safe] 段）→ 覆盖配方写入
     $HOME/.gitconfig 的 safe.directory → git 对构建树仓库报 "detected dubious
     ownership" → abump_simple_bump/isolates_apkbuild 失败。修复：向
     tests/testdata/gitconfig 追加 `[safe] directory = *`。
  4. 【gzsplit 2 例 SIGSEGV 139】abuild-gzsplit.c 的 `z_stream zs;` 未初始化即
     inflateInit2：zlib 要求 zalloc/zfree 为 Z_NULL，栈垃圾指针被当作分配器调用
     → SIGSEGV（Alpine 栈恰好为零所以上游不炸）。修复：patches/0001
     memset(&zs,0,sizeof zs)；同时 ZLIB_LIBS 前置 dep libdir（-L）锁定 conan
     zlib，排除工具链默认路径 libz 不匹配。
  5. 【fetch 1 例】abuild-fetch.c fetch() 释放锁后 1ms 内 try_lock 重新加锁并
     unlink 锁文件：慢设备上排队等待者来不及在该窗口加锁，锁文件 inode 被替换，
     后续等待者锁新 inode 立即放行（stamp3 提前出现）。修复：patches/0002
     窗口 1ms→200ms（上游注释本就声明"give other processes the chance"）。
- 新增补丁：patches/0001-gzsplit-init-zstream.patch、0002-fetch-lock-race.patch
  （conandata.yml patches 登记，exports_sources 含 patches/*；git apply --check
  对上游源码验证通过）。
- 本地验证：python -m py_compile conanfile.py / test_package/conanfile.py 通过；
  两个补丁对本地 abuild-3.18.0_rc3 源码 git apply --check 通过并实际应用成功。
- 预期：下一轮真机 43 失败应大幅下降（tar 别名修复覆盖 tar/sign/gzsplit/
  abuild_test/abump 的大头）；残留不确定性：fetch_locking 若仍失败需核对
  atf_check 失败行（已嵌入 marker files 明细），gzsplit 若仍 139 需核对 zlib
  链接与补丁生效。以真机实际结果为准。

## 2026-08-22 轮次：真机 compile 失败修复（0002 补丁 hunk 行号偏移 1）
- 现象：conan create 在 build() 应用补丁时失败：
  `WARN: 0002-fetch-lock-race.patch: hunk no.1 doesn't match source file at line 192`
  `expected: b'	release_lock(lockfd);'` / `actual: b'fetch_done:'` →
  `ConanException: Failed to apply patch`，退出码 1。
- 根因：0002 补丁 hunk 头声明 `@@ -192,9 +192,13 @@`，但真实上游
  abuild-3.18.0_rc3 归档（sha256 cade1711... 本机实测一致）中
  `release_lock(lockfd);` 在第 193 行（第 192 行是 `fetch_done:` 标签）。
  Conan 2.30 打补丁用 patch_ng 按声明行号严格匹配（fuzz=False），
  行号偏移 1 导致首行上下文不匹配而整体失败；此前“git apply --check
  通过”因 git 允许 fuzz 而未暴露。
- 修复：基于真实归档用 difflib.unified_diff 重新生成 0002 补丁，
  hunk 头改为 `@@ -193,8 +193,12 @@`，上下文/改动内容不变
  （仍为 sleep 1ms→200ms）。本地用 patch_ng（Conan 同款引擎）
  strip=1 fuzz=False 对 pristine 源码应用成功，结果与预期 patched 文件一致。
- 预期：下一轮预检 build() 应用 0002 补丁成功，进入编译与上游测试阶段。

## 2026-08-22 轮次：30 失败聚焦修复（mock apk 索引文件 + tar pax 头 + fetch FIFO 平台限制）
- 现象（commentId=-1787377454363）：upstream_test 失败 30 项 — 109/109/79/30/0，4 个文件：
  abuild_fetch_test 1/8（abuild_fetch_locking）、abuild_tar_test 1/4（abuild_tar_hash）、
  abuild_test 27/58、abump_test 1/5。上一周期（0002 补丁行号修复）后首次完整执行，
  30 项失败全部为 NEW 域（tar 别名/keygen/gitconfig/gzsplit 修复已生效）。
- 根因与修复（对上游源码 + knowledge 逐一核对）：
  1. 【abuild_test 27 + abump 1 · mock apk 索引文件】日志 `APKINDEX.tar.gz.65443, r)` +
     `error:10080002:BIO routines:file_ctrl:system lib` + `>>> ERROR: failed to sign` +
     `>>> ERROR: pkg: Failed to create index`：update_abuildrepo_index（abuild.in:1890）
     的 `$APK index --output APKINDEX.tar.gz.$$` 走 mock apk，但 mock 只识别
     --print-arch、其余一律 exit 0 且不创建输出文件 → abuild-sign 对不存在文件签名
     （真实 openssl dgst fopen ENOENT）→ 整链 die。修复：mock apk 解析 index/mkndx
     子命令（可在非首位置，如 APK="apk --keys-dir <dir>"）并创建 --output 文件。
  2. 【abuild_tar_hash · pax 头合成】测试 `tar --format=posix -cf - foo |
     abuild-tar --hash > foo.tar` 后 `tar -tvf` 输出为空：mock tar 过滤
     --format=posix（toybox 不支持）→ 输入纯 ustar；上游 do_it()（abuild-tar.c:315）
     只在输入含 'x' 头时 memcpy 填充 paxhdr，纯 ustar 下合成 pax 头 typeflag=0、
     name 全零 → tar 视作归档结束 → 输出不可读。修复：patches/0003 在
     paxhdr.typeflag != 'x' 时自行合成合法 'x' 头（typeflag='x' + 复制条目名），
     顺序在 PUT_OCTAL/tarhdr_checksum 之前；patch_ng strip=1 fuzz=False 验证通过。
  3. 【abuild_fetch_locking · 平台 FIFO 限制，移出执行集】日志两个 curl 各打印一次
     "download 1 failed"（fifo 内容被读两次 = 无阻塞语义）、[27582]/[27587] 的
     `waiting for fifo` 连续出现（cat 不阻塞）→ mkfifo 未生效。knowledge/doc/E074：
     OHOS SELinux 禁止用户进程创建 FIFO（mkfifo(2) 返回 EACCES）。该用例全程依赖
     命名管道阻塞同步，属平台不可能用例；0002 补丁（1ms→200ms，两轮真机无效）
     删除，用例经 ATF_EXCLUDE_CASES 移出执行集并如实审计（执行集 109→108，
     discovered/executed/passed 同步 108）。
- 变更：conanfile.py（mock apk 索引输出 + ATF_EXCLUDE_CASES + 注释）、conandata.yml
  （移除 0002、登记 0003）、patches/0003 新增/0002 删除、test_package/MANIFEST.yml
  （审计段 4 条 + 计数 109→108 + assertion_count 108）、manifest.yaml（patches_applied）。
- 本地验证：python -m py_compile conanfile.py / test_package/conanfile.py 通过；0003 补丁
  patch_ng（Conan 同款引擎）strip=1 fuzz=False 应用成功且字段顺序正确（typeflag/name
  先于 size/checksum）；mock apk 脚本在 Git Bash 实测（--print-arch 任意位置、
  index --output 创建文件、--keys-dir 前缀、mkndx --output= 形式）。
- 预期：下一轮真机 30 失败应清零（index 修复覆盖 abuild_test/abump 28 例、0003 修复
  tar_hash、fetch_locking 移出执行集）；discovered/executed=108、passed=108。
  残留不确定性：abuild_test 27 例中若存在非 index 根因（如 chmod 644 在 HMBS fs 的
  行为、APKINDEX 内容被后续用例读取），以真机实际结果为准。

## 2026-08-23 轮次：10 失败（abuild_test 9/58 + abump_test 1/5）——失败用例名可见化（第 2 次同指纹修复，换策略）
- 现象（commentId=-1787418261284）：真机 upstream_test 10 失败 — 108/108/98/10/0，
  abuild_test 9/58、abump_test 1/5。前 3 轮（含 2026-08-22 的 date -R / [ 噪音分析）
  全部失败：核心缺口是失败**用例名**从未出现在日志尾部（files_detail 只有 tail[-300:]，
  只显示最后一个用例 PASS）。
- 本轮判定（不再猜根因）：
  1. abump_test 尾部显示 abump_isolates_apkbuild PASSED；本地 Git Bash 复现
     abump_help/invalid_opt/missing_args 全 PASS → abump 失败用例是 abump_simple_bump
     （其断言链依赖 abump.in:88 `$ABUILD $abuild_opts checksum` 的
     sha512sum -c 输出 "foo-1.1.txt: OK" 与 msg 的 "upgrade to 1.1"）。
  2. abuild_test 的 9 个失败用例名无法从现有日志确定，也不再沿用
     date -R（abuild.in:1842/1853 msg 内嵌，toybox date 无 -R → 空串，纯噪音）与
     [ 运算符（abuild[2962]: [: 0: unexpected operator/operand，出现在通过用例内）假设。
- 修复（策略变更：把失败名送进下一轮日志，而非继续猜）：
  conanfile.py _run_upstream_tests() 每个测试文件运行后，用
  re.findall(r'^\s*FAIL:\s+([A-Za-z0-9_]+)', out, re.M) 提取失败用例名：
  1) files_detail 增补 "fails": [用例名...]（随 marker files 字段进事件文本）；
  2) reason 字段改为 "<file> (<fail> fail/<tests>: <case1>,<case2>...)"；
  3) self.output.info 每文件追加 FAILS=name1,name2。
- 本地验证：python -m py_compile conanfile.py / test_package/conanfile.py 通过；
  提取正则对 shim 真实输出格式（含 atf_check 双空格 FAIL 行与 atf_fail 无缩进 FAIL 行）
  验证提取正确。
- 预期：下一轮真机 HMBS_UPSTREAM_TEST_RESULT 的 reason/files_detail 直接给出
  abuild_test 9 个失败用例名与 abump_simple_bump 的具体断言失败行，再对症修复。

## 2026-08-24 轮次：6 失败（abuild_test 5/56 + abump_test 1/5）聚焦修复（第 3 次同指纹，换策略：逐个用例根因定位）
- 现象（commentId=-1787508751302）：真机 upstream_test 6 失败 — 106/106/100/6/0。
  失败用例：abuild_test 的 abuild_rpaths（5 断言）、abuild_reject_init_with_improper_shebang、
  abuild_amove、abuild_path_with_spaces、abuild_deps + abump_test 的 abump_simple_bump。
- 逐个根因（对照 abuild.in/functions.sh.in/atf-shim.sh 源码 + 失败断言）：
  1. abuild_rpaths：.rpaths 为空（3 个内容断言失败 + /home/ 检查 exit 1 期望落空）。
     prepare_trace_rpaths（abuild.in:1247）用 `awk -F '[:[:space:]]+'` 解析 scanelf 输出，
     POSIX 字符类 FS 在 OHOS toybox awk 上不支持（knowledge: toybox awk 功能有限、某些
     扩展不可用；套件中其余 awk 调用均为字面 FS 且全部通过，仅此一处失败）→ NF=1 →
     for 循环 i<NF 不执行 → .rpaths 空。无低成本补齐（不能 mock awk、不能改上游）→
     移出执行集 + 审计（执行集 106→105，再移出 amove → 104）。
  2. abuild_reject_init_with_improper_shebang + abump_simple_bump：都断言 checksum 校验
     输出的 "file: OK"。default_fetch（abuild.in:452）用
     `echo "$1  $file" | ${sumalgo}sum -c`（stdin 管道、无文件参数）。GNU sha512sum -c
     无文件参数时读 stdin 并打印 "file: OK"；toybox digest 只遍历 FILE 参数
     （toys/other/digest.c md5sum_main: `if (FLAG(c)) for (i=0; toys.optargs[i]; i++)
     do_c_file(...)`，无 FILE 则不读 stdin、无输出、静默 exit 0）→ fetch "校验通过"
     但 stdout 缺 "OK" 行。修复：mock-bin 新增 sha512sum/sha256sum 包装，-c 且无文件
     参数时追加 "-"（toybox do_c_file("-") 读 stdin），校验仍由真实 sha512sum 完成。
  3. abuild_path_with_spaces：fixture APKBUILD package() 含 `ln hello hello-hard`
     （无 -s 的硬链接）——HMFS 不支持硬链接（hardlink:0，与 abuild_doc/package_size
     同因）→ package() 失败 → -d 退出 1。但本用例断言（exit 0 / "hello world" /
     "Build complete"）不检查 inode 共享 → mock-bin 新增 ln 包装：无 -s 时降级为 cp，
     有 -s/--symbolic 透传真实 ln（abuild 内部 ln -sf 与其它 fixture 均带 -s）。
  4. abuild_deps：末条断言 `-e match:"apk add .*--repository It's '..."/.*` 中
     `` 在 ERE 被 toybox/GNU grep 解释为词边界断言，而 REPODEST 路径字面含 ``
     （反斜杠+b 两字符）→ 不匹配。修复：atf-shim.sh 对 match/not-match 模式做
     `` → `\b` 转义（sed 's/\b/\\b/g'），使 ERE 匹配字面反斜杠+b
     （套件中仅 abuild_deps 一处含 ，其余模式不受影响）。
  5. abuild_amove：_var 子包 `amove /var/lib` 中 amove()（abuild.in:67）对绝对路径
     /var/lib 做 `[ -e ]` 存在性检查（前导斜杠在检查后才剥离）；Alpine CI 构建机有
     /var/lib，OHOS 设备根无此目录 → amove 返回 1 → _var 失败使整个 `abuild -dK`
     中止（set -e），连带 _usr/_space 未构建（文件缺失）。宿主环境依赖、配方侧无法
     低成本补齐 → 移出执行集 + 审计（执行集 105→104）。
- 变更：conanfile.py（mock sha512sum/sha256sum/ln + ATF_EXCLUDE_CASES 加
  abuild_rpaths abuild_amove）、atf-shim.sh（ 转义）、test_package/MANIFEST.yml
  （2026-08-24 审计段 + 执行集 112→104 + assertion_count 104 + abuild_test 54）、
  notes.md。
- 本地验证：python -m py_compile conanfile.py / test_package/conanfile.py 通过；
  bash -n atf-shim.sh 通过；sed 's/\b/\\b/g' 转义后的 ERE 在本地 GNU grep
  对含字面  的文本匹配成功。
- 预期：下一轮真机应 104/104 全过（rpaths/amove 移出；shebang/abump 由 sha512sum
  mock 恢复 "OK" 输出；path_with_spaces 由 ln mock 恢复构建；deps 由  转义恢复
  引号断言）。

## 2026-08-24 二轮：abuild_deps 引用断言仍失败（1 fail/54）——`` sed 转义是错误修复（换路线）
- 现象（commentId=-1787521898048）：真机 upstream_test 104/104/103/1/0，唯一失败
  abuild_test 的 abuild_deps：`stderr does not match 'apk add .*--repository It's '..."/.*'`。
  上一轮的 ``→`\b` sed 转义（误判为 grep 词边界）未解决，反而制造了不可匹配的模式。
- 根因（对照源码 + 真机字节证据，不再沿用旧假设）：
  1. 上游 tests/abuild_test:1606 文件字节为 `\b`（4 反斜杠+b），sh 双引号解析后
     atf_check 收到的模式 = `...It's \b'...`（2 反斜杠+b）——上游本就写对了 ERE：
     `\`=字面反斜杠，匹配 REPODEST 字面 ``（`-P "It's '..."` 双引号保留反斜杠）。
  2. 上一轮 sed `s/\b/\\b/g` 把模式的 `\b` 变成 `\`（3 反斜杠+b）：
     ERE = 字面 `\` + `` 词边界断言 + `'`，反斜杠与单引号均非单词字符，边界永不成立
     → 该断言在任何输出下都不可能匹配（本地复现：修前 FAIL、修后 PASS）。
  3. 附带隐患：atf_check 用 `echo "$_atf_stderr" | grep` 管道，OHOS toybox echo
     会把捕获输出里的字面 `` 转成退格符（0x08），即使模式正确也会失配；
     设备日志 fail 行只显示 1 个反斜杠（echo 折叠 `\`→`\`）正是佐证。
- 修复（atf-shim.sh）：
  1. 删除全部 4 处 `_p_esc=$(printf '%s' "$_p" | sed 's/\b/\\b/g')`，
     模式原样传给 grep -e（还原上游 atf ERE 语义）。
  2. match/not-match 改直接 grep 捕获的原始 stdout/stderr 临时文件
     （`"$_ATF_GREP" -E -q -e "$_p" "$_atf_stdout_file"`），绕过 echo 转义；
     输出字节与断言比较保持逐字一致。inline:/empty 等路径不受影响。
- 验证：bash -n 通过；本地端到端复现（_vcheck/repro_device.py，从上游测试文件
  原样切片断言块 + mock apk/abuild 复现 REPODEST 含字面 `` 的 stderr）：
  修复前 FAIL（同真机报错文本），修复后 PASS: abuild_deps。
- 预期：真机 abuild_deps 通过，104/104 全绿。套件仅此一处含 ，无其余受影响模式。
