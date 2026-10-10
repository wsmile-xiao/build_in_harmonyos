# sfk 2.0.0.3 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，`bin_PROGRAMS = sfk`）
- 编译日期: 2026-09-30
- 编译器: clang/clang++（ohos-aarch64 profile 注入）
- 状态: built（待真机 rule4 预检通过后由 HMBS 提交发布）

## 编译步骤
1. `get()` 下载官方 SourceForge 归档 `sfk-2.0.0.tar.gz`（sha256 已校验）。
2. `AutotoolsToolchain` 生成 toolchain，追加 `--disable-dependency-tracking`。
3. `Autotools.configure()` → `Autotools.make()` 构建单个 `sfk` 可执行文件
   （源码：`sfk.cpp`、`sfkext.cpp`、`sfkpack.cpp`）。
4. `Autotools.install()` 将 `bin/sfk` 安装进 package；best-effort chmod 0o755
   兜底 HMFS 丢失执行位（`HMBS_CAP_CHMOD=0`）。
5. test_package 在真机上运行 `test.sh`（功能冒烟）+ `ohos_abi_check.py`
   （鸿蒙 aarch64 ABI 检查），并输出 HMBS 硬门禁标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无测试套件 | `Makefile.am` 仅 `bin_PROGRAMS=sfk`，无 `TESTS`/`check_PROGRAMS`/`tests/` 目录；`mtk/` 是可选跟踪库 | 按 no_tests 处理：MANIFEST 写 `upstream_tests_exist:false` + 审计；test_package 补全真实命令功能冒烟 |
| 2 | 版本串不确定 | 目录名 2.0.0.3 而归档版本为 2.0.0 | 二进制横幅权威输出 `Release 2.0.0  Revision 3`（fixpack=3 → 2.0.0.3），以此为版本断言来源 |
| 3 | HMFS 可能丢失执行位 | `HMBS_CAP_CHMOD=0` 时安装的二进制可能不可执行 | `package()` 对 `bin/sfk` best-effort `os.chmod(0o755)` |
| 4 | OHOS `/tmp` 只读 | erofs，shell 的 `$(...)` 用硬编码 /tmp | test.sh 避免 `$(...)`，改用重定向+grep，并预置可写 TMPDIR |

## 依赖版本
- 无外部依赖（单二进制工具，仅用系统 libc/libm/libstdc++）。
- 构建工具：clang 15 + OHOS SDK（`/data/service/hnp` 注入），Conan 2.x。

## 验证结果

本地（x86-64 宿主）验证逻辑正确性 —— 用真机同源 sfk 源码在宿主编译后跑 test.sh：
```
[test] PASS: version banner reports Release 2.0.0
[test] PASS: version banner reports Revision 3
[test] PASS: sfk calc 2+3 == 5
[test] PASS: sfk mkdir created nested directory
[test] PASS: sfk md5 matches known digest
[test] PASS: sfk list exposes created file
[test] PASS: sfk time emits a timestamp
[test] sfk consumer assertions: passed=7 failed=0
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":7,"passedCount":7}
```
证伪检查：把被测二进制换成输出 garbage 的桩 → 6 项 FAIL、`passed:false`、exit 1，
证明 harness 能真实抓到失败而非"空跑全过"。

鸿蒙特有 ABI 检查对宿主 x86-64 二进制如实判 FAIL（e_machine=62 非 183、
interp 非 musl），对 OHOS 产物应全 PASS —— 已按 `ohos_abi_check.py` 逻辑验证脚本
能正确区分平台。

真机 conan create 结果以 HMBS 预检日志为准（环境与官方 CI 同源），PR 正文通过率
据此填写。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/s/sfk/2.0.0.3/conanfile.py | autotools 主配方 |
| archives/s/sfk/2.0.0.3/conandata.yml | 官方源 URL + sha256 |
| archives/s/sfk/2.0.0.3/test_package/ | 消费者测试（test.sh / ohos_abi_check.py / conanfile.py / MANIFEST.yml） |
| archives/s/sfk/2.0.0.3/manifest.yaml | 版本级 manifest |
| archives/s/sfk/manifest.yaml | 软件级 manifest |
| archives/s/sfk/commands.json | 命令行工具声明（R38） |

## 注意事项
- 上游 `make check` 不存在（无 TESTS），不能在 build() 里调用 `make check`。
- 测试断言数：test_package 7 项独立功能断言 + 2 项鸿蒙 ABI 检查 = 9（MANIFEST assertion_count）。
- 若后续真机日志出现源码包下载超时，再按镜像映射为 conandata URL 增加回退列表。

## 真机修复记录（2026-09-30）
- 真机 compile 阶段失败：`./config.status: line 619: ./confiDHNfb/subs1.awk: Permission denied` +
  `config.status: error: could not setup config files machinery`（autotools configure 生成
  Makefile 时中止）。
- 根因（对照 knowledge/drafts/DRAFT-cpdb-libs-1.2.0-config-status-hmdfs-mktemp-wrapper-path-prepend）：
  autoconf AS_TMPDIR 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录并依赖 0700 语义；
  HMDFS 上 toybox mktemp 的 chmod(0700) 被映射为 drwx--S---（组位空），且 OHOS 构建进程
  uid 映射异常非目录属主、组位又空 → 在临时目录内建 subs1.awk 时 EACCES。
- 修复：conanfile.py generate() 在 conanbuild env 的 PATH 前置 build_folder/mktemp-wrapper/mktemp
  可执行脚本（模拟 `mktemp -d`，用 `(umask 077 && mkdir -p "$cand")` 产 drwxrws--x 可写目录；
  非 -d 调用转发真 mktemp 保退出码）。该 wrapper 与 cpdb-libs/1.2.0 已验证实现逐字节一致，
  仅存在于 build_folder，不提交（R6）。
- 注意：写 conanfile.py 内嵌 shell 时 `$`（PID）在补丁直写时会被折叠成 `# sfk 2.0.0.3 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，`bin_PROGRAMS = sfk`）
- 编译日期: 2026-09-30
- 编译器: clang/clang++（ohos-aarch64 profile 注入）
- 状态: built（待真机 rule4 预检通过后由 HMBS 提交发布）

## 编译步骤
1. `get()` 下载官方 SourceForge 归档 `sfk-2.0.0.tar.gz`（sha256 已校验）。
2. `AutotoolsToolchain` 生成 toolchain，追加 `--disable-dependency-tracking`。
3. `Autotools.configure()` → `Autotools.make()` 构建单个 `sfk` 可执行文件
   （源码：`sfk.cpp`、`sfkext.cpp`、`sfkpack.cpp`）。
4. `Autotools.install()` 将 `bin/sfk` 安装进 package；best-effort chmod 0o755
   兜底 HMFS 丢失执行位（`HMBS_CAP_CHMOD=0`）。
5. test_package 在真机上运行 `test.sh`（功能冒烟）+ `ohos_abi_check.py`
   （鸿蒙 aarch64 ABI 检查），并输出 HMBS 硬门禁标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无测试套件 | `Makefile.am` 仅 `bin_PROGRAMS=sfk`，无 `TESTS`/`check_PROGRAMS`/`tests/` 目录；`mtk/` 是可选跟踪库 | 按 no_tests 处理：MANIFEST 写 `upstream_tests_exist:false` + 审计；test_package 补全真实命令功能冒烟 |
| 2 | 版本串不确定 | 目录名 2.0.0.3 而归档版本为 2.0.0 | 二进制横幅权威输出 `Release 2.0.0  Revision 3`（fixpack=3 → 2.0.0.3），以此为版本断言来源 |
| 3 | HMFS 可能丢失执行位 | `HMBS_CAP_CHMOD=0` 时安装的二进制可能不可执行 | `package()` 对 `bin/sfk` best-effort `os.chmod(0o755)` |
| 4 | OHOS `/tmp` 只读 | erofs，shell 的 `$(...)` 用硬编码 /tmp | test.sh 避免 `$(...)`，改用重定向+grep，并预置可写 TMPDIR |

## 依赖版本
- 无外部依赖（单二进制工具，仅用系统 libc/libm/libstdc++）。
- 构建工具：clang 15 + OHOS SDK（`/data/service/hnp` 注入），Conan 2.x。

## 验证结果

本地（x86-64 宿主）验证逻辑正确性 —— 用真机同源 sfk 源码在宿主编译后跑 test.sh：
```
[test] PASS: version banner reports Release 2.0.0
[test] PASS: version banner reports Revision 3
[test] PASS: sfk calc 2+3 == 5
[test] PASS: sfk mkdir created nested directory
[test] PASS: sfk md5 matches known digest
[test] PASS: sfk list exposes created file
[test] PASS: sfk time emits a timestamp
[test] sfk consumer assertions: passed=7 failed=0
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":7,"passedCount":7}
```
证伪检查：把被测二进制换成输出 garbage 的桩 → 6 项 FAIL、`passed:false`、exit 1，
证明 harness 能真实抓到失败而非"空跑全过"。

鸿蒙特有 ABI 检查对宿主 x86-64 二进制如实判 FAIL（e_machine=62 非 183、
interp 非 musl），对 OHOS 产物应全 PASS —— 已按 `ohos_abi_check.py` 逻辑验证脚本
能正确区分平台。

真机 conan create 结果以 HMBS 预检日志为准（环境与官方 CI 同源），PR 正文通过率
据此填写。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/s/sfk/2.0.0.3/conanfile.py | autotools 主配方 |
| archives/s/sfk/2.0.0.3/conandata.yml | 官方源 URL + sha256 |
| archives/s/sfk/2.0.0.3/test_package/ | 消费者测试（test.sh / ohos_abi_check.py / conanfile.py / MANIFEST.yml） |
| archives/s/sfk/2.0.0.3/manifest.yaml | 版本级 manifest |
| archives/s/sfk/manifest.yaml | 软件级 manifest |
| archives/s/sfk/commands.json | 命令行工具声明（R38） |

，必须用 Python
  写入以保留 `$-$RANDOM`（单 `# sfk 2.0.0.3 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，`bin_PROGRAMS = sfk`）
- 编译日期: 2026-09-30
- 编译器: clang/clang++（ohos-aarch64 profile 注入）
- 状态: built（待真机 rule4 预检通过后由 HMBS 提交发布）

## 编译步骤
1. `get()` 下载官方 SourceForge 归档 `sfk-2.0.0.tar.gz`（sha256 已校验）。
2. `AutotoolsToolchain` 生成 toolchain，追加 `--disable-dependency-tracking`。
3. `Autotools.configure()` → `Autotools.make()` 构建单个 `sfk` 可执行文件
   （源码：`sfk.cpp`、`sfkext.cpp`、`sfkpack.cpp`）。
4. `Autotools.install()` 将 `bin/sfk` 安装进 package；best-effort chmod 0o755
   兜底 HMFS 丢失执行位（`HMBS_CAP_CHMOD=0`）。
5. test_package 在真机上运行 `test.sh`（功能冒烟）+ `ohos_abi_check.py`
   （鸿蒙 aarch64 ABI 检查），并输出 HMBS 硬门禁标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无测试套件 | `Makefile.am` 仅 `bin_PROGRAMS=sfk`，无 `TESTS`/`check_PROGRAMS`/`tests/` 目录；`mtk/` 是可选跟踪库 | 按 no_tests 处理：MANIFEST 写 `upstream_tests_exist:false` + 审计；test_package 补全真实命令功能冒烟 |
| 2 | 版本串不确定 | 目录名 2.0.0.3 而归档版本为 2.0.0 | 二进制横幅权威输出 `Release 2.0.0  Revision 3`（fixpack=3 → 2.0.0.3），以此为版本断言来源 |
| 3 | HMFS 可能丢失执行位 | `HMBS_CAP_CHMOD=0` 时安装的二进制可能不可执行 | `package()` 对 `bin/sfk` best-effort `os.chmod(0o755)` |
| 4 | OHOS `/tmp` 只读 | erofs，shell 的 `$(...)` 用硬编码 /tmp | test.sh 避免 `$(...)`，改用重定向+grep，并预置可写 TMPDIR |

## 依赖版本
- 无外部依赖（单二进制工具，仅用系统 libc/libm/libstdc++）。
- 构建工具：clang 15 + OHOS SDK（`/data/service/hnp` 注入），Conan 2.x。

## 验证结果

本地（x86-64 宿主）验证逻辑正确性 —— 用真机同源 sfk 源码在宿主编译后跑 test.sh：
```
[test] PASS: version banner reports Release 2.0.0
[test] PASS: version banner reports Revision 3
[test] PASS: sfk calc 2+3 == 5
[test] PASS: sfk mkdir created nested directory
[test] PASS: sfk md5 matches known digest
[test] PASS: sfk list exposes created file
[test] PASS: sfk time emits a timestamp
[test] sfk consumer assertions: passed=7 failed=0
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":7,"passedCount":7}
```
证伪检查：把被测二进制换成输出 garbage 的桩 → 6 项 FAIL、`passed:false`、exit 1，
证明 harness 能真实抓到失败而非"空跑全过"。

鸿蒙特有 ABI 检查对宿主 x86-64 二进制如实判 FAIL（e_machine=62 非 183、
interp 非 musl），对 OHOS 产物应全 PASS —— 已按 `ohos_abi_check.py` 逻辑验证脚本
能正确区分平台。

真机 conan create 结果以 HMBS 预检日志为准（环境与官方 CI 同源），PR 正文通过率
据此填写。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/s/sfk/2.0.0.3/conanfile.py | autotools 主配方 |
| archives/s/sfk/2.0.0.3/conandata.yml | 官方源 URL + sha256 |
| archives/s/sfk/2.0.0.3/test_package/ | 消费者测试（test.sh / ohos_abi_check.py / conanfile.py / MANIFEST.yml） |
| archives/s/sfk/2.0.0.3/manifest.yaml | 版本级 manifest |
| archives/s/sfk/manifest.yaml | 软件级 manifest |
| archives/s/sfk/commands.json | 命令行工具声明（R38） |

 是 shell 选项标志，非唯一，会导致临时目录名碰撞）。



## 真机修复记录 round2（2026-09-30）：config.status 复现，根因=wrapper 不可执行
- 预检 compile 阶段再次失败：`./config.status: line 619: ./confGMlfAa/subs1.awk: Permission denied` +
  `config.status: error: could not setup config files machinery`（autotools.configure 中止，conanfile.py build() line 117）。
- 关键取证：临时目录名 `confGMlfAa`（纯字母数字、无 `-`）是**真 toybox mktemp** 的 XXXXXX 替换产物；
  而 _create_mktemp_wrapper 的模拟名形如 `conf<pid>-<RANDOM>`（必带 `-`）。说明本机 PATH 命中时 wrapper 未被执行，
  回退到了真 mktemp → 建出 drwx--S--- 不可写临时目录。
- 根因：本 worker 注入 `HMBS_CAP_CHMOD=0`。wrapper 用 `open(...,'w')`（umask 派生 0644）+ `os.chmod(0o755)` 设执行位，
  chmod 被禁时 os.chmod 抛 OSError 被吞掉 → wrapper 保持 0644 不可执行 → shell PATH 查找跳过它 → 用真 mktemp。
  与 cpdb-libs/accel-config 同款 wrapper 之所以能用，是因为那些 worker chmod 可用；本 worker（chmod=0）不行。
- 修复：改为**创建时即带执行位**——`os.open(wrapper, O_CREAT|O_WRONLY|O_TRUNC, 0o755)` + `os.fdopen` 写内容。
  内核按 mode 参数设权限（只被 umask 掩盖，而 umask 从不清 owner-exec），不调用 chmod 也得到 0o755。
  本地实证：os.open(mode=0o755) 建出的文件 mode=755、owner_exec=True、能按 shebang 执行。
- mkdir 模拟（`(umask 077 && mkdir -p)`）在 HMDFS 产 drwxrws--x 组位可写，即使构建 uid 非属主也能写 subs1.awk。
- wrapper 仍只存在于 build_folder（R6 不落系统目录/不提交）。


## 真机修复记录 round3（2026-09-30 聚焦轮）：放弃 wrapper，改用 configure 源码级 umask 修钉 + CONFIG_SHELL 钉压
- 预检 compile 阶段第 3 次失败（含 wrapper 后仍失败）：日志大量 `getcwd: cannot access parent directories` /
  `job-working-directory` 风暴，随后 `./config.status: line 619: ./confOIBafA/subs1.awk: Permission denied` +
  `config.status: error: could not setup config files machinery`。autotools.configure() 中止（conanfile.py build() line 123）。
- 取证（本机解包官方 sfk 归档，sha256 与 conandata 一致）：
  1. shipped `configure` 仅含 2 处 `umask 077`（AS_TMPDIR：`tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` 与
     兜底 `(umask 077 && mkdir "$tmp")`），这两行经 unquoted heredoc 写进生成的 config.status → config.status
     line ~619 的临时目录创建 = 这两处 text 的运行时展开。
  2. `ci/conan/profiles/ohos-aarch64` `[buildenv]` 注入 `CONFIG_SHELL=/data/service/hnp/bin/bash` +
     `SHELL=/data/service/hnp/bin/bash` → DRAFT-6487 的 getcwd 风暴（hnp bash 对 HMFS getcwd 返回 ENOTSUP/EINVAL）。
- 根因（两个互相独立的失败因子，wrapper 只堵了其中软的那条）：
  a) config.status 用 `(umask 077 ...)` 建 0700 临时目录，在 setgid HMFS 上落为 drwx--S---，构建 uid（非属主映射）
     写不进 → subs1.awk Permission denied。这是直接致命错误。
  b) CONFIG_SHELL 指向 hnp bash → 全链路 getcwd 风暴，污染路径解析与探测，属环境噪音/潜在不稳定。
- 先前的 mktemp wrapper（round1/round2）依赖 PATH 查找 + 可执行脚本 + 相对路径 mkdir，在 chmod=0 的 worker 上
  wrapper 不可执行/被遮蔽，且不修 CONFIG_SHELL，故反复失败。聚焦轮改策略：
  1. **configure 源码级修钉**：把 shipped configure 中 2 处 `umask 077` → `umask 002`（由 `_patch_configure_mktemp()`
     在 build() 首行、autotools.configure() 之前对该文件做精确 replace；count!=2 时 warn 并跳过，不做猜测式改写）。
     这样生成出来的 config.status 的 AS_TMPDIR 也会用 umask 002 → HMFS 上临时目录为 drwxrws--x（属主/组均可写），
     绕开 mktemp chmod 与 uid 非属主映射。DRAFT-inn umask022-hmdfs 实证表：umask 002 → drwxrws--x → 可写。
  2. **CONFIG_SHELL/SHELL 钉压到 toybox /bin/sh**：generate() 里 `env.define("CONFIG_SHELL","/bin/sh")` +
     `env.define("SHELL","/bin/sh")` 覆盖 profile buildenv 注入的 hnp bash，消除 getcwd 风暴（DRAFT-6487 同款）。
  3. 移除 `_create_mktemp_wrapper()` 及其 PATH-prepend（不再依赖可执行脚本/PATH 查找）。
- cfg 校验：patch 只动 2 处 `umask 077`→`umask 002`，其余行 diff 为空；count==2 才替换，防上游 configure 文本漂移。
- 待真机复跑确认：config.status 生成 Makefile 不再 Permission denied；配置/编译/test_package 全链路通过后由 HMBS 提交。

## 真机修复记录 round4（2026-09-30 聚焦轮）：musl/OHOS 编译错误（glibc 内部类型与 LFS 入口）
- 预检 compile 阶段（config.status/mktemp 问题已修复后）进入 make，sfk.cpp 编译报
  "21 warnings and 14 errors generated"，Makefile: sfk.o Error 1 → conan build 失败。
- 根因（本机用 musl-gcc + Linux UAPI 头复现，与 OHOS 同源 musl libc）：
  a) sfk 源码依赖 glibc 内部类型/成员，musl 不提供：
     - `__dev_t`（glibc sys/types.h 内部名）→ musl 只有 `dev_t`；
     - `fpos_t.__pos` 与 `__off_t`（glibc FILE 位置内部成员）→ musl 的 fpos_t
       是 union（__opaque/__lldata），无 __pos；
     - 调用点：mygetpos64/mysetpos64/mygetpos/mysetpos/myfseek/Coi::seek。
  b) sfkpack.cpp 使用 glibc LFS `*64` 入口（fopen64/fseeko64/ftello64/stat64/
     statvfs64/fgetpos64/fsetpos64）。musl 只在定义 `_LARGEFILE64_SOURCE` 时
     提供这些 `*64` 别名（且 fseeko/ftello 需 POSIX/GNU 特性宏——musl 默认
     _XOPEN_SOURCE 700 已开启），本构建未定义 → 声明缺失。
- 修复（新增 patches/0001-musl-posix-compat.patch + 配方 CXXFLAGS）：
  1. 把 `__dev_t` → `dev_t`（sfkbase.hpp 字段 ostdev/oClStDev、sfk.cpp sizeof 两处）。
  2. 把上述 6 个位置函数改为可移植的 `ftell`/`fseek`（去掉 fpos_t.__pos/__off_t）。
     宏无关、全平台等价（aarch64 OHOS long=64 位）；glibc 行为不变仍在 CI 验证。
  3. 配方 generate() 对 AutotoolsToolchain.extra_cxxflags 追加
     `-D_GNU_SOURCE -D_LARGEFILE64_SOURCE`，使 musl 暴露 `*64` 别名。
- 本地验证：patch_ng(strip=0，即 Conan apply_conandata_patches 的默认路径) 应用
  该 patch 到 CRLF 源文件产物与我实测树逐字节一致；修补后 sfk/sfkext/sfkpack
  在 musl-gcc（0 error）与 g++/clang++（glibc，0 error）下全部通过；链接后真机冒烟
  `calc 2+3`==5、copy 文本+200KB 二进制字节一致（cmp OK），证明 ftell/fseek 语义正确。
- 注：patch 以纯 LF 编写（diff -ruN 生成后去 CRLF），patch_ng 对 CRLF 目标自动处理；
  Conan 用 patch_ng 应用，故 GUN patch 的 "different line endings" 不构成问题。
