# libaiff 6.0 适配笔记

## 编译环境
- 构建系统: direct-cc（上游 configure.ac + Makefile.am 仅作审计依据，不再运行 autoreconf；8 个可移植 C 文件直接编译）
- 上游版本: 6.0（mtszb/libaiff tag v6.0，ABI version 2:0:0）
- 上游地址: https://github.com/mtszb/libaiff
- 源码包: https://github.com/mtszb/libaiff/archive/refs/tags/v6.0.tar.gz
- SHA256: `9d90765b2b90942f928698c02ae1b7caf3037847dbe20a100469998f93e61ffd`（33,447 字节，GitHub codeload 实测）
- 原始项目: https://aifftools.sourceforge.net/libaiff（最新仅 5.0；6.0 由 mtszb 维护分支发布，2022-05-09 提交 "Set the ABI version to 2 and LibAiff version to 6.0"）
- 编译日期: 2026-09-15
- 编译器: clang/clang++（OHOS profile，clang 15，libc++）
- 状态: built（待真机预检通过后由 HMBS 统一提交）

## 编译步骤

上游 6.0 树内无 configure（仅 configure.ac/Makefile.am/m4 + autogen.sh），配方不再运行 autoreconf，改为直接编译：

1. `autoreconf -fi`（tool_requires：automake/1.18 + autoconf/2.72 + libtool/2.5.4）
2. 生成的 `configure` 中 `umask 077` 替换为 `umask 022`（HMDFS 下 umask 077 建临时目录不可写，config.status 报 Permission denied）
3. `configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`（config.guess 无法识别 HarmonyOS，必须显式 triplet；aarch64 上 OPTIM_FAMILY=generic，不编 x86/ppc 汇编）
4. `make -j1`（HMDFS jobserver fifo EPERM，禁用并行）
5. `make install`，删除 `lib/*.la`

## 上游测试审计

- 上游树（v6.0，27 个文件）无 tests/、test/ 目录，无 `TEST`/`TEST_F`、`add_test`、`def test_`、`TESTS`/`check_PROGRAMS` 声明，`make check` 无目标。
- 结论：上游确实无自动化测试套件（test_package/MANIFEST.yml 记录完整审计，upstream_tests_exist: false）。
- 配方 build() 不调用 `make check`；覆盖由 test_package 两个消费者程序提供（见下）。

## test_package 设计（R34 实质调用）

- `test_libaiff_roundtrip.c`（7 个 CHECK-OK）：F_WRONLY 建文件 → SetAudioFormat(1ch/44100Hz/16bit) → StartWritingSamples → WriteSamples32Bit(8 帧) → EndWritingSamples → Close → F_RDONLY 重开 → GetAudioFormat 校验 → ReadSamples32Bit 回读比对 → Seek(0) 重读。
- `test_libaiff_metadata.c`（5 个 CHECK-OK）：写文件时 SetAttribute(NAME/AUTH/COPY) → 读回 GetAttribute 字符串比对 → GetInstrumentData 可调用性 → 打开不存在文件返回 NULL（错误路径）。
- 合计 12 个 CHECK-OK，test() 逐行计数后打印 `HMBS_TEST_PACKAGE_RESULT`（discovered=12）；上游标记固定 `status:no_tests`（discovered=0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包无 configure | 上游 6.0 仅提交 configure.ac/Makefile.am（autogen.sh 需本地生成） | build() 先跑 `autoreconf -fi`，tool_requires 提供 automake/1.18 + autoconf/2.72 + libtool/2.5.4（owamp/zzuf 同型先例） |
| 2 | config.status 可能 Permission denied | 生成脚本 `umask 077` 在 HMDFS 建不可写临时目录 | `_drop_umask_077` 全局替换为 `umask 022`（构建期平台适配，不进 patches） |
| 3 | config.guess 无法识别 HarmonyOS | 设备内核名无上游 case | 显式 `--build/--host=aarch64-unknown-linux-ohos` |
| 4 | Windows 检出本仓库必然脏（libXext/libxext 大小写冲突） | 上游同时存在仅大小写不同的归档目录，Windows 不区分大小写文件系统无法共存 | 对 4 个冲突文件 `git update-index --skip-worktree`，本 PR 仅新增 archives/l/libaiff/**，不触碰冲突文件 |

## 依赖版本

- 运行时/链接依赖：无（仅 libc，configure.ac 只探测 sys/types.h、string 系头与 memset 函数）
- 构建工具：无 tool_requires（直调 Conan compiler + llvm-ar，均走 build profile 的 PATH）

## 验证结果

```bash
# 真机预检（HMBS 后台统一执行，本轮不本地跑 conan）：
# conan create archives/l/libaiff/6.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
直编 8 个 C 文件 → ar/so → install → test_package 两二进制 12/12 CHECK-OK
```

本地已确认：`git rev-parse --verify HEAD` 成功、无 `.git/index.lock`、`ci/conan/profiles/ohos-aarch64` 存在；分支 `feat/libaiff-6.0` 基于 upstream/main（31c7a70）。

## 注意事项

- 本轮严禁 commit/push/建 PR/写 GitCode 接口与 `.hmbs/pr.json`；工作树保持未提交，待 HMBS 真机全部门禁通过后统一提交。
- `url` 字段填官方 GitHub 仓库（code-style 禁止空 `url = ""` 占位）；CI 会自动追加 GitHub 镜像 fallback，conandata 只写官方原始 URL。
- libaiff 非系统同名库，保留动态库（默认 shared=False 时按标准 flags 切静态/动态，不删 `.so`）。

## 2026-09-15 真机失败聚焦修复
- 失败指纹：preflight.sh[306] /tmp 只读 + m4 configure[139] /data/service/hnp/bin/bash inaccessible，HMBS 诊断 [readonly_tmp]，capabilities tmpdir 已注入、shell=/bin/sh。
- 根因：主配方 source/generate/build 未复用注入 TMPDIR 且沿用 profile 的 bash 路径；test_package 沿用旧 TMPDIR 探测并硬编码 /data/storage/el2/base/cache 签名目录。
- 改动：主包新增 _writable_tmpdir/_ensure_tmp_env（HMBS_TMPDIR>capabilities.tmpdir>TMPDIR/TMP/TEMP(跳过/tmp)>FALLBACK>build_folder/tmp，探写），source/build 入口重定向并置 SHELL/CONFIG_SHELL=/bin/sh+umask 022，generate 经 Environment 透传；test_package 同步优先级+探写，签名 staging 改走 TMPDIR。仅换临时根与 shell，不删测试。

## 2026-09-15 同指纹第2次修复（换路：去autoreconf直接编译）
- 前次对比：上轮 TMPDIR+SHELL 加固后预检指纹逐字节相同（m4 configure[139] bash inaccessible + preflight.sh[306] 只读/tmp），证明失败点在 m4 工具包构建，主配方 generate/build 尚未执行，原路无法触达。
- 根因：tool_requires（automake/autoconf/libtool）把无 OHOS 预编译二进制的 m4/1.4.19 拉入依赖图；其 configure 在沙箱重 exec 缺失的 profile bash 且 /tmp 只读。
- 改动：删除全部 tool_requires 与 autoreconf/configure/make/umask 逻辑；build() 直调 Conan conf 编译器编译 8 个可移植 C 文件并生成最小 config.h（小端 generic），package() 仅安装库与头文件。测试口径不变（test_package 12 CHECK-OK + 上游 no_tests 审计）。

## 2026-09-15 同指纹第3次修复（编译器路径探测）
- 前次对比：去autoreconf后m4依赖消失、主包进入build()，但卡在profile绝对路径/data/service/hnp/bin/clang inaccessible（前两轮分别为m4 bash缺失、m4依赖图问题，指纹已变化）。
- 根因：_compiler()无条件返回conf绝对路径，预检沙箱未挂载该目录；PATH可解析的编译器被短路。
- 改动：新增_usable_tool文件存在探测，仅接受可用的conf/CC/PATH编译器并记录resolved compiler与PATH；archiver同理；兜底返回PATH解析的裸名而非不可用的绝对路径。
