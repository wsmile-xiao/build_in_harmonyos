# trickle 1.08 适配笔记

## 基本信息

- 上游：https://github.com/mariusae/trickle （主页 monkey.org/~marius/trickle）
- 版本：1.08（Debian 1.08+ds orig tarball，git snapshot 2024-05-06）
- 许可证：BSD-3-Clause
- 类型：C / autotools，应用 + LD_PRELOAD 模块
- 分支：`feat/trickle-1.08-codex`（worktree：`D:\harmonyos\worktrees\trickle`）
- issue：待补（本轮无明确 issue 编号）

## W0 依赖结论

- 依赖数量：2（libevent、libtirpc）
- 已满足依赖：libevent/2.1.13、libtirpc/1.3.7（仓库已有配方）
- 缺失依赖：无
- 是否需要拆分依赖适配：否
- 说明：trickled 使用 libevent 旧 API（event_init/event_set/event_dispatch
  /signal_set/evtimer_set），经 libevent2 兼容头 `<event.h>` 工作；
  trickled/tricklectl 的 XDR 编解码走 libtirpc（configure 强制
  PKG_CHECK_MODULES）。构建工具链需 automake/libtool/pkgconf。

## W1 源码与构建分析

- 产物：bin/trickle、bin/trickled、bin/tricklectl +
  lib/trickle/trickle-overload.so、lib/trickle/libtrickle.so
  （LD_PRELOAD 模块，`-module -avoid-version -nostdlib` 链接）。
- tarball 无 configure/Makefile.in，必须 autoreconf 自举。
- configure 探测：
  - `AC_TRY_RUN` 探测 libc 访问方式（dlsym((void*)-1) 或
    dlopen("libc...")），交叉编译无法执行 → 0011 号补丁给出 musl
    默认 `dlopen("libc.so")`（musl 对已加载 libc 特判）。
  - `AM_CONFIG_HEADER`（automake≥1.13 已移除）→ 0012 号补丁换
    AC_CONFIG_HEADERS/LT_INIT/AC_CONFIG_FILES。
  - Makefile.am 直接用 `@LTLIBOBJS@` → 0013 号补丁换 `$(LTLIBOBJS)`。
- 采用 Debian 1.08+ds-1.1 全部 10 个 series 补丁（含 getopt 符号冲突、
  -P overload 路径覆盖、64bit time_t、ax_pthread clang 适配等）。
- 上游无测试套件：无 tests/ 目录，make 无 check 用例，.travis.yml 仅
  configure+make。build() 无法运行上游测试（如实记录，非静默跳过）。

## W2/W3 配方与 test_package

- conanfile.py：application 类型；依赖 libevent/2.1.13、libtirpc/1.3.7；
  tool_requires automake/1.18、libtool/2.5.4、pkgconf/3.0.6；
  `--with-libevent=<conan 包目录>`；make -j1（E074）；configure 生成后
  umask 077→022（E175）。
- 不传 --enable-static/--disable-shared：preload 模块必须 shared。
- test_package：5 用例 13 断言（-V 版本、-h usage ×3、无参数 usage），
  只测参数解析入口；不启动 trickled、不 LD_PRELOAD 子进程、无网络。

## W4 本机验证（已完成项见 README 交接）

- 源码 SHA256：79163aea3a39f32c5a1619b2a532140ff7c7c18e8d4b2ed8dfbd247a9cf72f06
- Python 语法 / YAML 结构 / 补丁 apply（对解包源码）已在本机校验。
- 本机为 Windows，无 OHOS 交叉工具链与 Conan 环境，未做交叉编译实测。

## W5 真机 / shadow CI 记录

### r1（2026-10-01 20:55，job trickle-1.08-20261001）

- run：`codex-1.08-trickle-1.08-20261001-conan-20261001-205520-14701`，排队 0s，exit 1
- L0 = fail: registry_unreachable；L1/L2/L4/L5 = skip: blocked_by_L0
- 报错原文：`ERROR: Remote 'ohpcd' doesn't exist`（automake/libevent/libtirpc/libtool/pkgconf 全部探测失败）
- 根因：隔离 job 新建的 CONAN_HOME 未配置 ohpcd remote（job 创建脚本基础设施差异，
  非 R36 依赖未发布、非配方问题）
- 解法：从 reniced-1.23-20261001 job 复制 remotes.json（ohpcd remote）+ global.conf
  到 trickle job 的 conan-home 后重跑（r2）
- 附注：stderr 有 `build_and_test.sh:164: permission denied: git`（设备无 git，
  非本次失败主因，观察 r2 是否影响）

### r2（2026-10-01 21:01，job trickle-1.08-20261001）

- run：`codex-1.08-trickle-1.08-20261001-conan-20261001-210104-17907`，排队 0s，exit 1
- L0 门禁通过（L0i 依赖全部在 ohpcd registry），KC = fail
- 报错原文：`build_and_test.sh:980: permission denied: bash`
- 根因：KC 检查以 `bash ci/scripts/knowledge_check.sh` 执行，设备 bash 位于
  `/data/service/hnp/bin/bash`（自检模板坑清单已知项），不在 runner 默认 PATH
- 解法：job 的 run-conan-heavy.sh（job 私有脚本，非 repo 基础设施）source env.sh
  后注入 `export PATH=/data/service/hnp/bin:$PATH`，base64 重写传输，重跑（r3）

### r3（2026-10-01 21:03，job trickle-1.08-20261001）

- run：`codex-1.08-trickle-1.08-20261001-conan-20261001-210345-18995`，排队 0s，exit 1
- KC/L0/JC 全过；依赖 5 个包从 ohpcd 全部下载成功；源码下载解压成功
- 失败于 build()：`apply_conandata_patches` 第一个 Debian 补丁报
  `source/target file does not exist: --- b'trickle-1.07.orig/getopt.c'`
- 根因：Debian 补丁头使用 `trickle-1.07.orig/`、`trickle-1.08+ds.orig/` 等
  前缀（非标准 a/ b/ 形式），Conan 内置 patch 应用器无法按 -p1 剥离
  （git apply 可容忍，Conan 不行）
- 解法：批量重写 10 个 Debian 补丁的 `---/+++` 头为 `a/ b/` 标准形式
  （fix_patch_headers.py，hunk 体不动）；本机干净源码树 13 补丁链
  git apply 重新全过；重传设备后重跑（r4）

### r4（2026-10-01 21:07，job trickle-1.08-20261001）

- run：`codex-1.08-trickle-1.08-20261001-conan-20261001-210712-21247`，exit 1
- KC/JC 全过；0001 补丁通过；失败移到 0002：
  `source/target file does not exist: --- b'a/test.c'`
- 根因：0002 是"新建 test.c"补丁（`@@ -0,0 +1,20 @@`），Conan 的 patch
  应用器要求新文件源侧必须写 `--- /dev/null`，写 `--- a/test.c` 时它先检查
  源文件存在性而失败
- 解法：0002 补丁头改为 `--- /dev/null`；干净树 13 补丁链重验全过；重跑（r5）
- 附注：CI pre-download 阶段报 `No such file or directory: 'curl'`（设备无
  curl，非致命，自动回退 conan 自带下载器，源码下载成功）

### r5（2026-10-01 21:22，job trickle-1.08-20261001）

- run：`codex-1.08-trickle-1.08-20261001-conan-20261001-212258-28158`，exit 1
- 0002/0003/0004/0005 补丁全部通过；失败移到 0006：
  `source file is different - b'configure.in'`（expected csysconfdir 行，
  actual 是 HAVEMETHOD 行 —— hunk 行号偏移 15 行）
- 根因：Debian 补丁基于不同快照编写，hunk 行号与 1.08+ds orig tarball 有
  偏移；git apply 用上下文搜索可容忍，Conan 内置 patch 应用器按行号定位
  则拒绝（这是与 git apply 验证的关键差异，后续适配要以 Conan 语义验证）
- 解法：fix_hunk_lines.py 以 pristine 源 + 虚拟逐补丁应用重算所有 hunk 的
  @@ 行号（0003: -86→-82 等；0006: -216→-231；0008/0009/0012 同步修正），
  git apply 全链复验通过后重传重跑（r6）

### r6（2026-10-01 21:29，job trickle-1.08-20261001）

- run：`codex-1.08-trickle-1.08-20261001-conan-20261001-212934-33976`，exit 1
- 0001/0002 过；失败移到 0003（usage 区 hunk 行号错误匹配）
- 根因：r5 后对全部补丁做的行号"修正"引入新错误——搜索算法在相似文本区
  （usage print 字符串）命中错误位置；Debian 原始行号多数本来就对
- 解法（本机闭环，不再消耗真机轮次）：发现本机 conan 2.29.1 的补丁应用器
  即 patch_ng（strip=1, fuzz=False），写 conan_patch_check.py 在本机完整
  复现 Conan apply 语义；autofix_hunks.py 自动迭代：失败时在当前文件状态
  中定位 hunk 上下文唯一位置并重写 @@ 行号，直至全链通过
- 结果：13 补丁 patch_ng 本地全过（0003/0008/0009/0012 行号精确修正），
  重传设备

### r7（2026-10-01 21:40，job trickle-1.08-20261001）

- run：`codex-1.08-trickle-1.08-20261001-conan-20261001-214048-42218`，exit 1
- **13 个补丁全部通过**（本地 patch_ng 验证 + 真机确认）
- 新失败点：autoreconf 阶段 `Can't exec ".../conan-home/p/autom*/p/bin/aclocal":
  Permission denied (exit 13)`
- 根因：conan automake/libtool 包脚本在 HMDFS 上无有效执行位（mode 显示
  -rwxr-x--- 但属主 uid 不匹配，other 无权限；E087）。进一步实验：
  - 复制到 /data/storage/el2/base/haps/entry/files/ 并 chmod 755 后依然
    exec 拒绝（该分区对未签名脚本同样限制，E054/SELinux 域）
  - `~/usr/local/bin/aclocal`（设备系统级）同样无执行位
- 可行解法（设备端完整验证 BOOTSTRAP-OK）：**显式解释器序列**——
  - libtoolize 不可用（重定位推算脱离 wrapper 后失效）→ 直接复制
    ltmain.sh + 5 个 libtool m4 宏到源码 m4/
  - `/data/service/hnp/bin/perl -I <automake share> <.aclocal-real> ...`
    跑 aclocal（真身 shebang 即 hnp perl）
  - autoconf/autoheader 用 hnp PATH 中可执行的系统工具
  - perl 跑 .automake-real --foreign --add-missing --copy
  - m4 需可写 TMPDIR（runner 环境已提供；交互 shell 需手工 export）
- 配方落地：build() 的 autoreconf 包 try/except，失败时走
  _bootstrap_autotools() 回退（正常 Linux worker 不受影响）

### r8–r15（2026-10-01 22:0x–23:0x，job trickle-1.08-20261001）

- 逐轮修复配方回退自举路径（每轮一个 Python/环境层面 bug）：
  - r8/r9：`output.warn`→`output.warning`；build() 阶段
    `self.dependencies` 不含 tool requires（KeyError）
  - r10–r13：PATH 定位工具包失败（os.environ 无 conanbuild PATH；PATH 中
    `~/usr/local/bin` 同名工具干扰）→ 改从 CONAN_HOME glob 包目录并以
    `.aclocal-real` 作为 conan automake 包特征
  - r11 附注：一次 scp 传输静默失败（复合命令中 scp+ssh 并发），后续每轮
    scp 后 grep 验证内容
  - r14：aclocal cwd 不对（'configure.ac' is required）→ 自举命令
    全部加 cwd=self.source_folder
  - r15：**自举全链成功**（aclocal/autoconf/autoheader/automake 生成
    configure/Makefile.in/config.h.in），umask 修复生效；新失败：
    生成的 configure 脚本在 HMDFS 无执行位（exec 126）
- r16 方案：configure 改 `sh configure` 显式调用 + `CONFIG_SHELL=/bin/sh`
  （config.status 同样经 sh 运行）；Makefile 的 libtool 经 `$(SHELL)`
  调用不受影响

### r17（23:24）：E007 config.guess 不识别 HarmonyOS → --build=aarch64-unknown-linux-ohos
### r18（23:35）：conftest exit 127 —— conan libevent/libtirpc 包只有 .so，
  conanbuild 环境无 LD_LIBRARY_PATH，musl ld.so 找不到 → 配方 build() 显式
  注入依赖包 lib 目录到 LD_LIBRARY_PATH（生效，全部函数探测通过）
### r19（23:4x）：新失败 "event.h or libevent.a not found"——上游 configure
  硬编码要求 libevent.a 存在，conan libevent 包只有 .so → 0014 号补丁将
  --with-libevent 检查放宽为 .a 或 .so（本地 patch_ng 全链 14 补丁通过）

### r23（2026-10-02 00:33–00:45）✅ 全部通过

- run：`codex-1.08-trickle-1.08-20261001-conan-20261002-003359-49766`，
  runner exit code = **0**
- 门禁结果：
  - G0_RESULT=pass / KC_RESULT=pass / JC_RESULT=pass
  - L0_RESULT=pass: all checks passed
  - **L1_RESULT=pass: test_package executed**（含 L1e 破坏性反向验证：
    "Negative test confirmed — test genuinely depends on trickle"）
  - L4_RESULT=pass: patches clean（14 个补丁）
  - L5_RESULT=pass: bin/ has content
  - L2_RESULT=skip（非阻塞）：CI 内置 smoke 用 `--version/--help` 长选项
    测试，trickle 上游 CLI 只有 `-V`/`-h` 短选项且按上游设计 exit 1，
    属 CLI 约定差异；test_package 已用 13/13 断言验证真实入口行为
- 消费者测试：**case_count=5, assertion_count=13, passed=13, failed=0**
  （trickle -V "version 1.08"、trickle -h/-无参 usage、trickled -h usage、
  tricklectl -h 空实现行为——上游 usage() 仅 exit(1) 无输出，r22 的
  唯一失败断言即因此误写，已按上游真实行为修正）
- r20–r22 的编译期修复（见上）已全部生效

## W5 最终结论

trickle/1.08 在 OHOS aarch64 真机完成 conan create + test_package 闭环，
L0/L1/L1e/L4/L5 全 pass、L2 非阻塞 skip。产物：bin/trickle、bin/trickled、
bin/tricklectl + lib/trickle/trickle-overload.so、libtrickle.so
（LD_PRELOAD 模块；限速工作行为属运行时功能，后续在设备上单独冒烟）。

## 真机 / shadow CI 待办命令

```sh
# 1) 隔离 job（设备已有仓库作 repo-source）
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex --job trickle-1.08 \
  --package archives/t/trickle/1.08 \
  --repo-source <existing-repo>

# 2) runner
sh "$HOME/ohos-users/codex/trickle-1.08/run-conan-heavy.sh"

# 3) 真机运行时验证（shadow CI 中补充）
trickle -V
trickle -s -u 10 -d 10 dd if=/dev/zero of=/dev/null bs=1k count=200   # 限速冒烟
```

重点观察：
- musl 下 `dlopen("libc.so")` 是否返回有效句柄（0011 补丁假设），
  失败则 trickle-overload 报 "[trickle] Failed to open libc"，需要改为
  dlopen(NULL)（RTLD_DEFAULT）方案。
- OHOS musl namespace（E088）对 LD_PRELOAD 的实际行为。
- libevent2 兼容头在 OHOS clang 下的编译告警。

## 下一步

1. 真机空闲窗口执行 shadow CI（上面命令）；
2. 按 L0-L5 结果修 patch/配方；
3. 补 issue 编号，提 PR（单库单分支单 PR）。
