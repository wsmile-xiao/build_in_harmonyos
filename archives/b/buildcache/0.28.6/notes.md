# buildcache 0.28.6 OHOS 适配笔记

## 概述

将 buildcache 0.28.6 移植到 OpenHarmony PC (aarch64 / HMDFS / musl)。
上游: https://gitlab.com/bits-n-bites/buildcache, tag v0.28.6
    -> commit 4fd765083ef6e64d4c92ae5171c10336643d3104 (2023-09-07)
源码 tarball: .../archive/v0.28.6/buildcache-v0.28.6.tar.gz
SHA-256: 62829917b16d437a821a92c67b3f15aba3eb3bd026078513ddcafd006520d14e

## 构建系统

- CMake >= 3.16 + C++11，产物为单个可执行 buildcache
- 依赖全 vendored (lz4 1.9.2 / xxHash 0.8.0 / zstd 1.4.5 / hiredis 1.0.1 /
  lua 5.3.4 / cJSON 1.7.13 / cpp-base64 / HTTPRequest)
- OpenSSL 可选: -DDISABLE_SSL=on 绕开 (E006)
- 注意: 项目顶层 CMakeLists.txt 位于 tarball 的 src/ 子目录

## 关键决策

1. 无 conan requirements() —— 全部依赖内嵌 (src/third_party)。
2. -DDISABLE_SSL=on —— 绕开 OHOS 下 OpenSSL 汇编 BAD_SIGNATURE (E006)，
   与上游 Linux CI 同开关。S3 HMAC / Redis TLS 功能损失可接受。
3. TMPDIR 指向可写目录 —— OHOS /tmp 只读 (E002)；get_temp_dir() 优先读 $TMPDIR。
4. 上游 8 个 ctest 单元测试在 conan build() 中直接运行 (层1, cmake.ctest())。
5. src/buildcache_version.h 已存在于 v0.28.6 tag tarball，无需预生成
   (scout 未知项已消除)。
6. 系统脚本不进 CI 主流程: run_file_lock_stresstest.sh 硬编码 /tmp 必挂;
   build_with_buildcache.sh 需真实编译器 + 软链。

## 遇到的问题与解决方案

### Round-1 (CI): JC junk-check 门禁失败 (环境性, 非配方)
- 现象: JC1/JC5/JC6 fail — 误扫到基线遗留文件
  (middleclass/4.1.1/conandata.yml.ghfast-bak,
   swift-corelibs-blocksruntime/6.3.3/.staging-verified)
- 根因: 分支无 commit, 无 pr.diff, junk_check 落入
  `git diff origin/main...HEAD` 增量模式, 对称差返回 3766 个基线文件
- 解决: 提供 pr.diff (仅含本次 10 个 buildcache 文件), 使 JC 进入生产
  buildbot 同款 prdiff 模式 (优先级 1)。pr.diff 是 CI 本地验证夹具,
  不属于交付物, 交付前由 Coordinator 清理。

### Round-2 (CI): configure 失败
- 现象: `CMake Error: The source directory ".../b" does not appear to
  contain CMakeLists.txt`
- 根因: buildcache 顶层 CMakeLists.txt 在 src/ 子目录; conan 的
  CMake.configure() 默认以 source_folder 为 CMake 源目录
- 解决: `cmake.configure(build_script_folder="src")` (conan 2.29 官方参数)

### Round-2 附带加固
- `cmake.build(cli_args=["-j1"])`: OHOS conan 默认生成器为 Unix Makefiles,
  make jobserver 依赖 mkfifo (HMDFS 不支持), 单线程构建规避 (规则 9)
- `cmake.ctest()`: 直跑 ctest, 便于日志留证 (L1c)

### Round-3 (CI): PASS
- 8/8 ctest 可执行全部通过 (含 HMDFS 上 file_lock_test fcntl 记录锁)
- 上游测试实际运行时统计:
  39 个 TEST_CASE 全部通过 (源级 40 个, 其中 1 个 dir_exists 测试为
  #ifdef _WIN32 窗口条件编译, OHOS 不注册)
  88 个 SUBCASE / 190 条 CHECK_EQ (源级静态计数, scout 口径)
  doctest 运行时断言全部通过 (含 file_utils_test 499550 次循环断言)
- test_package: buildcache --version / --help / -h 冒烟通过
- L1e 破坏性验证: mv bin/ 后 conan test 失败 → 真依赖被测包
- 打包产物在 OHOS 上原生运行 (无 ELF 签名问题)

## 测试

- 上游 ctest: 8 可执行 / 100% 通过 (40 TEST_CASE 源级, 39 运行时注册)
- 系统脚本: run_file_lock_stresstest.sh (/tmp 硬编码) 不纳入 CI;
  可选改造方案: 改 $TMPDIR 后可用于多进程锁压力验证
- test_package: buildcache --version / --help 冒烟

## 遗留事项

- pr.diff 为 CI 本地夹具 (worktree 根目录), 交付前移除
- conandata.yml 在 CI pre-download 阶段会被临时改写为 file:// (curl 缺失时
  不改写), 设备端子进程 PATH 无 curl, 由 conan 自带下载兜底

## round-4（Web Review REVISE 修复）

- **F1（P2/A）**：conanfile.py `url = ""` 占位符 → 填官方上游 `https://gitlab.com/bits-n-bites/buildcache`（code-style §5）。
- **F3（P3/B）**：软件级与版本级 manifest 头部「ARCHIVE-SPEC v2.0」→「v3.0」（基线实际规范）。
- **F4（P3/B）**：test_package/MANIFEST.yml 断言口径如实化：`assertion_count 1→2`（--version 与 -h 两个可执行断言点），`test_package_tests.command` 与 test.sh 实际流程一致。
- **F6（P3/A-可选）**：test_package 内 `/data/service/hnp/bin/bash` 路径保留现状——仓库 1012 个配方同款惯例（CONFIG_SHELL buildenv 注入 + os.environ.get 兜底），reviewer 认可。
- **F7（P3/B）**：删除空目录 `patches/`、`test_package/metadata/`。
- **F2（P2/B）**：worktree 根 `pr.diff` 为 CI 本地夹具，交付前移除（交付阶段执行）。
- **F5（P3/C）**：39 运行时/88 SUBCASE/190 CHECK_EQ 为源级推导口径（ctest 非 -V 模式），与源码一致，报告已注明非日志直证。
