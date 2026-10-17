# imlib2 1.9.1 编译笔记

## 软件概述
imlib2 是 Enlightenment 项目的通用图像加载/渲染库，GNU Autotools 构建。
本版本为官方 git tag v1.9.1（git.enlightenment.org/old/legacy-imlib2，
commit 8dc921286c9e1844e3ec2f1ce2d6174891e32901）。官方 sourceforge release
归档从执行端不可达，故以官方 git tag 作为源码（bearssl 先例）。

## 依赖处理
- 必需：freetype（configure.ac `PKG_CHECK_MODULES(FREETYPE, freetype2)` 无 fallback）
- 启用 loader：PNG（libpng）、ZLIB（zlib）
- 禁用 loader（依赖未适配发布，与 1.12.6 历史构建一致）：
  gif/heif/jpeg/j2k/jxl/ps/svg/tiff/webp/bz2/lzma/id3

## 适配要点（OHOS）
1. **--without-x**：OHOS 无 X11，configure.ac 未禁用 X 会 AC_MSG_ERROR。
   且 Imlib2.h 用 `#ifndef X_DISPLAY_MISSING` 守卫 X11 头，config.h 不会被
   消费者包含，需在 package_info 向消费者注入 -DX_DISPLAY_MISSING。
2. **config.guess 不识别 OHOS**：uname -s=HarmonyOS 无匹配 → 显式传
   `--build=aarch64-linux --host=aarch64-linux`（abiword 先例）。
3. **freetype2.pc**：freetype 配方未设 pkg_config_name，PkgConfigDeps 生成
   freetype.pc；freetype 包内自带 freetype2.pc 但为 DESTDIR 原始文件
   （prefix=/ → //include 无效），补写指向包内实际路径的 freetype2.pc 桥接。
4. **E114/HMDFS**：configure 的 config.status 建 ./confXXXXXX 临时目录被拦，
   预建可写 TMPDIR 并把 ac_tmp 指向它（abiword 先例）。
5. **autogen**：git 源无 configure，aclocal→autoconf→autoheader→ltmain.sh→
   automake 直跑链生成（绕 autoreconf 的 autoconf.m4f 加载冲突）。
6. **上游测试默认禁用**：configure.ac `AM_CONDITIONAL(BUILD_TEST, false)` 硬编码，
   补丁 0001 改为 --enable-test 开关（默认 no），-o test=True 时可编译运行。

## 构建验证
- conan create（ohos-aarch64 profile，clang15/armv8/Release）通过；
  test_package 消费（find_package imlib2 + 公开 API 创建/填充/缩放/像素校验）通过。
- 上游测试 39 例源码声明（见 reports/test-report.md）：21 通过 / 10 失败 /
  8 未实例化（X11 互斥）。失败均为平台限制（HMDFS chmod、/tmp 只读 + loader
  硬编码 /tmp）或配方禁用格式（saver 缺失），非库缺陷。
- OHOS 专项测试 reports/test_ohos_loader：create→save png→reload 像素校验通过。

## 消费者可用性
test_package 为真实消费者：仅用公开头 Imlib2.h 与公开 API，编译链接并运行
（ARGB 像素值可观察断言），RC=0。

## W2/W3 基线隔离复验审计（其他库 cloog 基线噪声）
- 现象：本地 W3（finish step 5，build_and_test.sh）的 JC 门禁在 full 模式
  （分支尚无 commit、diff vs origin/main 为空 → `git ls-files` 全仓扫描）
  命中 archives/c/cloog/0.21.1/ 下两个**已在 main 提交**的运行时状态文件
  （.build-closed、.staging-verified，内容为空，由 cloog PR 906cc59ae7 引入，
  早于本任务、与本库无关）。
- 隔离复验（逐项）：
  1. 记录路径 + 隔离前 SHA-256：两文件均
     `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空文件）
  2. isolation_command：`git rm --cached archives/c/cloog/0.21.1/.build-closed
     archives/c/cloog/0.21.1/.staging-verified`（仅索引隔离，不动工作区文件）
  3. rerun_command：`bash ci/scripts/junk_check.sh <repo>`；rerun_exit_code=0，
     Junk Files: 0，JC_RESULT=pass → 证明当前库文件无垃圾、失败完全归因于
     其他库基线文件
  4. restore_command：`git reset`（恢复索引）；post_sha256 与 pre 一致
     （e3b0c44…），文件原样保留，未修改、未提交、未入知识库或 PR
- 结论：隔离复验通过，JC 失败属于提交前已存在的其他库基线噪声，非当前库
  失败；按 ./SKILL.md 规则继续当前库审计与交付。分支 commit 后 diff 非空，
  JC 进入 incremental 模式（仅扫描本 PR 文件），远端 CI（prdiff 模式）不受影响。

## W3 复验（r02）
- 分支已有 commit（diff vs origin/main 非空，15 文件）→ JC incremental 模式
  仅扫描本库文件：Junk Files: 0 / JC_RESULT=pass（cloog 基线不再命中，
  无需再次隔离）。
- `zsh ci/conan/build_and_test.sh archives/i/imlib2/1.9.1`（r02 直接运行）：
  L0=All quality gate checks passed；JC=pass；L1a/L1b=test_package 执行证据
  ok；L5=pass；Build Summary **Success: 1 / Failed: 0 / Pass rate: 100%**
  （log: reports/w3-local-ci-r02.log）。
- conan-verify：G0-G4 全 PASS（log: reports/conan-verify-report.md）。
- 注：L4 对 0004 补丁报 strcasecmp/fopen 上下文 warn（仅 warn 非阻塞，
  0004 为 XPM 命名色内置表，无危险调用）。
---

**编译结束**: 2026-09-17 12:40
**最终状态**: built
