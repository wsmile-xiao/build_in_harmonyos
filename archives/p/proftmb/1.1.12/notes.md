# proftmb 1.1.12 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.67 + automake，Ubuntu orig tarball）
- 编译日期: 2026-09-30
- 编译器: clang/clang++（OHOS aarch64 profile `ci/conan/profiles/ohos-aarch64`，libc++/cppstd=17）
- 状态: built

## 编译步骤

1. `conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64`
   （CONAN_HOME/TMPDIR/CONFIG_SHELL 按 CI 同款环境注入）
2. `build()` 内联修复（无独立 patch 文件）：
   - C++ 兼容：`char* =""` → `const char*`、`delete line` → `delete[] line`、
     `#define _HMMEVal` → `_HMMEval`、补 `uint` typedef、ostringstream 流输出补 `.str()`、
     动态异常规范 `throw(...)` → `noexcept(false)`
   - configure 注入 HMDFS sort/cat/rm shell 函数（toybox 对 `-` 参数与 safe-bin rm shim 的兼容）
   - build() 显式向 CPPFLAGS/LDFLAGS 拼接 opt/gsl 依赖的 -I/-L（AutotoolsToolchain 不下发）
3. `autotools.configure()` → 修 src/Makefile（剥 dnl 行 + HELP2MAN=/bin/true）与顶层 Makefile
   （`sed --in-place` 改临时文件方案）→ `autotools.make(args=["-j1", "HELP2MAN=/bin/true"])`
4. `package()`：install → 摊平 gsl 实体 .so + patchelf RUNPATH → binary-sign-tool 自签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 报 missing separator | Makefile.am 的 `dnl` 注释行泄漏进生成的 src/Makefile | configure 后剥除 `dnl ` 行 |
| 2 | man 页步骤失败 | src/Makefile 直接调用 `help2man`（非 `$(HELP2MAN)`），OHOS 无该工具 | PATH 前置 no-op wrapper 解析 `--output=` 生成最小 man 页（ref: E289） |
| 3 | 顶层 Makefile install 失败 | toybox sed 不支持 `--in-place` | 改写为 `sed -e … > tmp && mv`（ref: E010） |
| 4 | configure 探测不到 opt/gsl | AutotoolsToolchain 不下发依赖 -I/-L | build() 显式拼 CPPFLAGS/LDFLAGS |
| 5 | 运行期 Error loading shared library libgsl.so.28 | OHOS musl 加载器不跟随符号链接解析 DT_NEEDED | package() 摊平 libgsl.so.28/libgslcblas.so.0 实体副本 + RUNPATH=$ORIGIN/../lib（ref: E050） |
| 6 | exec 报 Operation not permitted | HMDFS 拒绝执行未签名 ELF | binary-sign-tool 自签名（ref: E077） |
| 7 | binary-sign-tool 报 .codesign section already exists | 工具链链接期插入空 .codesign 段 | 先 `objcopy --remove-section=.codesign` 再签（ref: E077） |
| 8 | 签名后 shell 报 can't execute: Permission denied | 签名产物丢失可执行位 | chmod 恢复 u/g/o x 位（ref: E077） |
| 9 | 端到端运行报 ReadMap: Reached EOF without an ENDRECORD | 上游 options 文件 -d 硬编码 //share/proftmb，且不带 @options 时 -s/-t 默认空串，ReadStatic 把数据目录当 arch 文件打开 | 消费者以 `@options -d <datadir>` 次序调用（命令行 -d 覆盖 options） |
| 10 | worktree（HMDFS el2）构建报 cat: -: Permission denied → config.status 报 could not setup config files machinery | conanbuild.sh 把 CONFIG_SHELL 指向 hnp bash，该 bash 在 HMDFS 上读 stdin 失败 | build() 在 conanbuild.sh 尾部追加 export CONFIG_SHELL/SHELL=/system/bin/sh（ref: E386，主仓 /storage 挂载点不触发、worktree 复现） |
| 11 | （预防性）config.status umask 077 在 setgid HMDFS 建 2700 目录被拒 | configure 内建 umask 077 + mkdtemp | configure 临时副本 umask 077 → 022（ref: E011，1272+ 配方同款） |
| 12 | CI worker make install 报 install-sh: can't execute: Permission denied（Error 126） | 2012 年上游 tarball 的 install-sh/missing 无执行位（实测 644）；本地 PATH 前置 pip coreutils 时 MKDIR_P 探测为 mkdir -p 不触发，CI worker PATH 无 coreutils 时 AC_PROG_MKDIR_P 回退 install-sh -c -d，make execve 644 脚本被拒 | build() 对已知 autotools helper（configure/config.guess/config.sub/install-sh/missing/depcomp/compile/ltmain.sh/ar-lib/test-driver）恢复执行位（ref: E490，CI #65812 实证） |

## 源码修改

无独立 patch 文件；全部修复内联在 conanfile.py（见上表与 knowledge_gained）。

## 依赖版本

- opt/3.19（AC_CHECK_LIB(opt)）
- gsl/2.8（libgsl.so.28 / libgslcblas.so.0 运行期依赖）

## 验证结果

```bash
# conan create（构建 + 打包 + test_package）
conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# EXIT=0；日志 /data/storage/el2/base/cache/proftmb-create-tc5.log

# test_package（HarmonyOS 消费者用例，test.sh 驱动）
# HC-1 proftmb --version 端到端 exec        PASS
# HC-2 @options 完整预测 example.Q          PASS（Successfully finished Prediction）
# HC-3 输出 vs 上游参考样例逐字节 cmp        PASS（tabular + .dat 均一致）
# total=3 passed=3 failed=0

# 上游测试：无（Makefile.am 无 check 目标 / TESTS / check_PROGRAMS）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/proftmb | ~510KB | 自签名 ELF 可执行（aarch64，动态链接） |
| lib/libgsl.so.28 | - | gsl 实体副本（DT_NEEDED 摊平） |
| lib/libgslcblas.so.0 | - | gslcblas 实体副本 |
| share/proftmb/* | - | 模型数据（Swiss8.arch/params、StateRedux4 等） |
| share/doc/proftmb/examples/* | - | 上游样例输入/输出 |

## 注意事项

- 二进制已自签名；再 strip 或 patchelf 会破坏 .codesign 哈希导致 Permission denied（E504/E077 同族），改动的顺序必须是 patchelf → 签名。
- 消费者调用必须 `@options` 在前、`-d <datadir>` 在后（命令行覆盖 options 文件内硬编码路径）。
- test_package/test.sh 为 3 个具名 HarmonyOS 消费者用例（HC-1/HC-2/HC-3），rule12 口径按端到端用例计数。
---

## 对话记录

### 对话 #1 [2026-09-29]

- 问题: 接手上游 `archives/p/proftmb/1.1.12` 骨架，产出可复现的 conan 配方并跑通 OHOS 真机构建
- 操作: 写 conanfile.py（autotools 直配），预处理 Makefile 的 dnl 泄漏行、help2man no-op wrapper（E289）、toybox sed --in-place 改临时文件（E010）、build() 显式拼 CPPFLAGS/LDFLAGS
- 结果: conan create 构建与打包通过

### 对话 #2 [2026-09-30]

- 问题: test_package 运行期报 Error loading shared library libgsl.so.28
- 操作: 隔离实验确认 OHOS musl 加载器不跟随符号链接解析 DT_NEEDED；package() 摊平 libgsl.so.28/libgslcblas.so.0 实体副本并 patchelf 设 RUNPATH=$ORIGIN/../lib
- 结果: 库闭包解析正常（知识 E050）

### 对话 #3 [2026-09-30]

- 问题: exec 报 Operation not permitted，posix_spawn/subprocess 均被 HMDFS 拦截；binary-sign-tool 又报 .codesign section already exists；签名后 shell 仍报 can't execute
- 操作: 三层定位——工具链链接期已插入空 .codesign 段 → objcopy --remove-section=.codesign 后再 sign -selfSign 1；签名产物丢失可执行位 → chmod 恢复
- 结果: 签名 ELF 直接可执行（知识 E077，适配实测补充 objcopy 剥离与 chmod 两步）

### 对话 #4 [2026-09-30]

- 问题: 端到端跑预测报 ReadMap: Reached EOF without an ENDRECORD
- 操作: 读源码定位 ReadStatic 读序列——上游 options 文件 -d 硬编码 //share/proftmb，不带 @options 时 -s/-t 默认空串把数据目录当 arch 文件打开
- 结果: 以 `@options -d <datadir>` 次序调用后完整预测跑通，输出与上游参考样例逐字节一致

### 对话 #5 [2026-09-30]

- 问题: 迁移到 HMDFS worktree 后构建报 cat: -: Permission denied → config.status 失败（could not setup config files machinery）
- 操作: 定位 conanbuild.sh 注入的 CONFIG_SHELL=hnp bash 在 HMDFS 上读 stdin 失败；build() 在 conanbuild.sh 尾部追加 export CONFIG_SHELL/SHELL=/system/bin/sh，并预防性归一化 configure 的 umask 077
- 结果: worktree 构建通过（知识 E386/E011）

### 对话 #6 [2026-09-30]

- 问题: 按 rule12 复核鸿蒙特有测试口径——conanfile.py 内联断言不构成具名端到端消费者用例
- 操作: 新增 test_package/test.sh 驱动 HC-1（--version 端到端 exec）/HC-2（@options 全模型完整预测）/HC-3（输出与上游参考逐字节 cmp）；conanfile.py 对齐 2048.c 先例（无 layout()、bash 驱动 test.sh）；同步 MANIFEST.yml
- 结果: conan create EXIT=0，鸿蒙消费者用例 3/3 PASS

### 对话 #7 [2026-09-30]

- 问题: CI #65812（PR #14059）编译全绿但 package() 的 make install 报 install-sh: can't execute: Permission denied（Error 126）
- 操作: 对比本地/CI 差异定位根因——上游 2012 tarball 的 install-sh/missing 本就 644，本地 PATH 有 pip coreutils 时 MKDIR_P=mkdir -p 不触发，CI worker PATH（/data/app/bin:/system/bin:...）无 coreutils 时 AC_PROG_MKDIR_P 回退 install-sh -c -d；按 E490 在 build() 恢复 autotools helper 执行位
- 结果: conan create 本地复验通过，等 CI 复跑

**编译结束**: 2026-09-30 22:02
**最终状态**: built
---

**编译结束**: 2026-09-30 23:17
**最终状态**: built
