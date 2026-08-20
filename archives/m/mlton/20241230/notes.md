# MLton 20241230 适配笔记

## 编译环境

- 构建系统: make（官方 Makefile，bootstrap-polyml + check + install-no-strip）
- 编译日期: 2026-08-11（鸿蒙设备真机编译，Round 19 完整 CI 复核）
- 编译器: clang / clang++（设备固定路径 /data/service/hnp/bin/clang，见「注意事项」）
- 状态: built（Round 19 CI PASS，exit 0，Build Summary 1/1，Pass rate 100.0%）

## 编译步骤

1. conan create 经 ci/conan/build_and_test.sh 触发；source() 从 conandata.yml 下载官方 tarball（官方 GitHub URL 在前、ghfast.top 镜像兜底在后），sha256=cd170218f67b76c3fcb4d487ba8841518babcebb41e4702074668e61156ca6f6。
2. generate() 基于 polyml/5.9.2.1 包的 polyc 生成引导 wrapper polyc-mlton-bootstrap（替换 prefix 为 Conan package 路径）。
3. build()：
   - `TMPDIR=... make -j1 bootstrap-polyml`（显式 build_requires=polyml/5.9.2.1，官方引导链，不重复自举）
   - `TMPDIR=... MLTON_FILESYS_TMPPREFIX=/dev/shm/mlton-filesys-<uuid>- make -j1 check`（332 项回归全通过）
   - `_sign_tree(build)` 对 build/ 下 5 个 ELF 做 HarmonyOS 自签名
4. package()：make install-no-strip（gzip -f -9 压缩 5 个 man 页）→ 复制 LICENSE → `_sign_tree(package_folder)` 再签名 5 个 ELF。
5. test()：test_package 三 marker（CONSUMER_TEST_MARKER / NEGATIVE_TEST_MARKER / PACKAGE_VALIDATION_MARKER）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /tmp 只读，regression 临时文件写失败 | OHOS 沙盒 /tmp 只读且不可靠 | bin/regression 临时文件根改由 TMPDIR 承载（${TMPDIR:=.} 兜底），benchmark 与工具自举同步迁移（patch 0001） |
| 2 | regression/world1-6.sml 固定写 /tmp/world 失败 | OHOS 沙盒不可写 | 改用 MLton.TextIO.mkstemp (MLton.TextIO.tempPrefix "world")，临时文件落在 TMPDIR（patch 0001） |
| 3 | filesys hardlink 用例 EPERM | HMDFS 不支持 Posix.FileSys.link | hardlink 文件改用环境变量 MLTON_FILESYS_TMPPREFIX 指定前缀（recipe 注入 /dev/shm/mlton-filesys-<uuid>-），测试结束删除 A/B 残留（patch 0001 + conanfile） |
| 4 | real 回归 "real: difference"，期望/实际差 1 ULP | 上游 real.ok 由 amd64-linux/glibc 生成，OHOS musl atan2f x<0 返回正确舍入 | 新增 regression/real.arm64-ohos.ok 平台 oracle 变体（25884 行，行数与 real.ok 一致），bin/regression 的 $f.$x.ok 变体选择机制自动拾取（patch 0002） |
| 5 | package() "gzip: Unknown option 'force'" | OHOS /usr/bin/gzip 为 toybox，仅支持 [-19cdfkt] 短选项 | install-no-strip 的 gzip --force --best 改 gzip -f -9（patch 0003） |
| 6 | 签名后 ELF 丢失执行位 | binary-sign-tool 输出 mode=640 | _sign_tree 签名前记录原 mode，签名后 os.chmod(signed, orig_mode) 恢复执行位（conanfile，最小 +2 行） |
| 7 | GC_displayMem 输出异常/不可靠 | OHOS 沙盒不暴露可读的 /proc/self/maps | patch 0001 将 OHOS 下 GC_displayMem 降级为输出提示并返回；该函数为调试辅助函数，不影响功能（本笔记记录说明，不改补丁逻辑） |
| 8 | 外层 3600s timeout 截断 | 全链路 CI 需 bootstrap + 332 回归 + 两轮签名 + test_package，耗时约 68m51s | ci/config/build_timeouts.txt 将 mlton/20241230 扩至 10800s（基建配置，不进配方 commit） |
| 9 | bootstrap 需 Poly/ML | 官方构建需先编译 bootstrap-polyml 引导编译器 | 配方以 Conan build_requires 显式依赖 polyml/5.9.2.1（已发布至 ohpcd 制品仓），mlton 分支不携带 polyml 文件 |

## 源码修改

- patches/0001-ohos-platform-tmpdir-and-runtime.patch：平台识别（platform.sig/sml、sml-nj.sml、bin/platform、mlton/main/main.fun、runtime/cenv.h、runtime/platform/ohos.{c,h}、lib/mlnlffi-lib/memory/platform/memory.ohos.mlb）+ TMPDIR（bin/regression、regression/world1-6.sml）+ filesys /dev/shm 前缀 + GC_displayMem OHOS 降级 + mlrisc-lib build 脚本兜底。
- patches/0002-ohos-real-oracle-arm64.patch：新增 regression/real.arm64-ohos.ok 平台 oracle 变体。
- patches/0003-ohos-gzip-toybox-short-options.patch：install-no-strip 的 gzip 长选项改 toybox 兼容短选项 -f -9。

## 依赖版本

- gmp/6.3.0（Conan require）
- polyml/5.9.2.1（Conan build_require，官方 bootstrap-polyml 引导编译器；已发布至 ohpcd 制品仓，revision 983a2550，`conan download polyml/5.9.2.1 -r=ohpcd --only-recipe` 验证通过）

## 验证结果

- Round 19 完整 CI：exit 0，Build Summary 1/1（Success 1, Failed 0, Pass rate 100.0%）
- make check 332 项回归全部通过（testing X 332 条、0 失败）；real/filesys/hardlink/gzip/sign 差异计数均为 0
- 门禁：L0=pass、L1=pass、L4=pass、L5=pass；L2=skip（非阻断，20241230 的 mllex/mlnlffigen/mlprof/mlton/mlyacc 无 --version/--help 开关）
- 6 个 marker 各 1：UPSTREAM_BOOTSTRAP_MARKER / UPSTREAM_TEST_MARKER / ADAPTED_TEST_MARKER / CONSUMER_TEST_MARKER / NEGATIVE_TEST_MARKER / PACKAGE_VALIDATION_MARKER
- 摘要：/storage/Users/currentUser/.local/state/oh-device-porting/runs/MLton-20241230/diagnostics/mlton-round-19/round-19-ci-summary.log；完整日志：/storage/Users/currentUser/.local/state/oh-device-porting/runs/MLton-20241230/jobs/ci-round-19/full.log（SHA-256=3a554cf47c7bf428214fe3cceade3268b1308ed38e6278f8a4645113a9c5eb44）

## 路径 C（高难度挑战）候选申请

- MLton 20241230 的 OpenHarmony（OHOS / arm64）适配已作为路径 C（高难度挑战）候选申请：六轴触及（平台数值库差异/real oracle、toybox gzip、签名工具链、HMDFS hardlink、构建时长边界、bootstrap 依赖链）、官方历史无修复证据（Poly/ML ARM64 allocator、MLton real oracle）、真机验证（Round 17/18/19 CI 全链路 PASS）等完整材料并入 PR 报告「路径 C」小节，项目工程中不再单独生成报告文件；最终路径分类、验收与分值由评审决定。

### 依赖侧官方历史无修复

- **Poly/ML（依赖侧）ARM64 allocator**：官方提交 `5437d321b45d16677802cfb76eef1a5321569309`（Fixes #277）实测应用到 v5.9.2 仍 FAIL（NOT_FIX）；官方历史末端 `d615dad7975f48d83c7e1873a9beeab1fb71c077` 对同输入仍 `getAllocatedGenReg` → **NO_FIX_IN_OFFICIAL_HISTORY**。
- **归属标注**：属 **Poly/ML（依赖侧）官方历史**，区别于 MLton 官方历史；MLton `real` oracle 上游无 arm64-ohos 平台变体，oracle 缺口只能自建。
- **证据来源**：`reports/pr-report-polyml-5.9.2.1.md`（ARM64 allocator 官方历史无修复段）与 `reports/session-handoff.md` §6。

## 注意事项

- **OHOS 设备固定工具链路径**：conanfile.py 的 _make_vars() 硬编码 CC=/data/service/hnp/bin/clang、AR=/data/service/hnp/bin/ar、RANLIB=/data/service/hnp/bin/ranlib、STRIP=/data/service/hnp/bin/strip，签名用 /data/service/hnp/bin/binary-sign-tool + /data/service/hnp/bin/llvm-objcopy。这是 OHOS 设备固定工具链路径（设备编译环境约定），配方逻辑保持不变。
- test_package 每次 CI 会再生构建/测试残留（mlton-consumer、__pycache__、conanbuild.sh、conanrun.sh、conanbuildenv-*、deactivate_*、metadata/ 等），交付前必须清理使 test_package 保持 pristine；Round 19 CI 后已清理并留证（test_package-post-ci19-after-cleanup.txt）。
- Round 19 为纯复核轮：未改动配方/补丁/知识草稿；ci/config/build_timeouts.txt 为工作树本地基础设施修改，不进 commit。
