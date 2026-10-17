# sysrepo 3.7.11 适配笔记

## 编译环境
- 构建系统: cmake（upstream CMakeLists，conan CMakeToolchain + CMakeDeps）
- 编译日期: 2026-09-25
- 编译器: clang 15（OHOS SDK /data/service/hnp/bin，sysroot ohos-sdk_26.0.0.18）
- 平台: HarmonyOS PC aarch64（构建机 B），conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built（verify 全绿，未 upload）

## 编译步骤

1. W0 依赖核验：`conan download --only-recipe` 实测 `libyang/3.13.6`、`cmocka/2.0.2` 已发布（libyang 3.11/3.12.x、cmocka 1.1.x 未发布，不可用）。
2. `conan create archives/s/sysrepo/3.7.11 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable`：
   `apply_conandata_patches` 依次应用 0001/0002/0003 三个补丁；CMake 关键变量 `REPO_PATH=etc/sysrepo`、`YANG_MODULE_PATH=sysrepo-yang`、`ENABLE_TESTS=ON`、`CMAKE_POLICY_VERSION_MINIMUM=3.5`、`CMAKE_SYSTEM_NAME=Linux`（E092 映射）；libyang/cmocka 经 in-tree Find 模块消费（结果变量全部预置种子，另种 `CMOCKA_FOUND=1`）。
3. `build()` 末尾将源码 `modules/*.yang` 填入烤定的 `sysrepo-yang` 目录，并对构建树全部 ELF 自签（OHOS 要求）。
4. `package()` 安装后对包目录就地二次签名；保留 `share/yang/modules/sysrepo`（运行时必需）。
5. test_package 以 VirtualRunEnv + 私有 `SYSREPO_SHM_DIR`/`SYSREPO_REPOSITORY_PATH` 通过裸 `self.run(env=None)` 执行 ctest。
6. `conan-verify` G0–G4/L2/L4/L5 **全绿**（rc=0、`**Verdict**: PASS`，`reports/conan-verify-report.md`）。`finish` **分项如实**（⛔ 不写「finish 全绿」，实测两套读数必须并列）：
   - 通过项：W2 结构（仅含配方变更、无框架文件）、R36 依赖、**W3 本地 CI 模拟通过**，`.ci-result.json` = `exit_code=0` / `step=W3_local_ci`；`EXIT_REASON=finish_success`、`EXIT_CODE=0`。该文件由 `finish` 产出、**随每次 finish 重写** ⇒ 哈希**不写进仓内**，以文件实物为准，复算式：`integrity_hash = sha256(f"{timestamp}:sysrepo:3.7.11:0")[:16]`、`log_sha256 = sha256sum reports/w3-local-ci.log`。
   - **未通过项：整体 `FINISH_RC=2`、`STEP_FAILED=Step6`**，失败步骤逐条：
     ① `step5b` 知识图谱完整性检查报字段空，实测逐项为：**E219 `root_cause` 空、E253 `root_cause` 空、E305 `root_cause` + `rec_approach` 双空（合计 4 条）**（**全仓存量字段缺失，非本包条目**；本包 `manifest.yaml` 侧 `knowledge_count=7 unreferenced=0` 已 ✅）；
     ② `Step6 finalize` 警告致 RC=2；
     ③ `Step8 gen_summary` 报 `str object has no attribute 'append'`（**框架缺陷**，按 AGENTS §8 不在本包 PR 修）。
   - 结论口径：**门禁（W2/W3/R36）与 verify 全过、finish 因上述三条存量/框架问题整体 RC=2**；三者均非本包缺陷，⛔ 不得据此宣称「finish 全绿」，也 ⛔ 不在本包改动框架件。
7. 上游测试实跑：build 树内 ctest 顺序执行 23 项（详见 reports/test-report.md）。

> ⚠ **`reports/` 不入库**：本文与上文引用的 `reports/*`（`conan-verify-report.md`、`test-report.md`、`w3-local-ci.log`、`conan-create.log`、`audit-result.json` 等）全在 `.gitignore` 覆盖内，**不随 PR 出仓**（PR files 里 `archives/s/sysrepo/**` 只有配方与文档 13 件，无任何 `reports/` 文件）。读者按「B 机 worktree 绝对路径 + 行数 + sha256」取用，PR 内可解析的证据以本 notes 的摘录与 `.ci-result.json` 的 `integrity_hash`/`log_sha256` 为准。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接 `sysrepocfg`/`sysrepoctl` 报 `undefined reference due to --no-allow-shlib-undefined: pthread_mutex_consistent / pthread_mutexattr_setrobust` | OHOS musl 的 libc.so 与 libpthread.a 均不导出 robust mutex 函数（llvm-nm 实证）；libsysrepo.so 带未解析符号 | 知识库 E192 处方：条件编译降级为普通进程共享 mutex。patches/0001 + conanfile 注入 `SR_NO_ROBUST_MUTEX`（R32 settings 判断形态，补丁内无平台宏以过 PF5）。owner-death 恢复运行期不可达为已知退化 |
| 2 | `package()` 阶段 `file INSTALL cannot make directory "/etc/sysrepo": Read-only file system` | 上游 REPO_PATH Release 默认 `/etc/sysrepo`，且 CMake cache 把相对值绝对化到 CMAKE_BINARY_DIR | conanfile 设 `REPO_PATH=etc/sysrepo`（安装骨架落包前缀），编译内默认路径随 build 树，运行时经 `SYSREPO_REPOSITORY_PATH` 覆盖 |
| 3 | test_package 运行报 `Error loading shared library libsysrepo.so.7`（无 errno 串） | OHOS 动态加载器拒绝未签名 .so：未签名可执行文件可运行，dlopen/mmap 被拒；且 build 树内的签名不随 `cmake.install` 存活 | 双管齐下：`build()` 末尾对构建树 ELF 自签（ctest 用），`package()` 末尾对包目录就地自签（交付物与 test_package 用）。签名工具 `binary-sign-tool`，先 `llvm-objcopy --remove-section .codesign` 再重签（与 libyang/3.13.6 同款硬化） |
| 4 | test_package 构建 OK 但 ctest 无法解析 libsysrepo | ①构建树二进制无 RPATH，且 `cmake.test()` 的 conanbuild 包装会丢弃已应用环境；②cmocka/libyang 经 conan Config 模式找不到 | test_package 改 libyang/3.13.6 模式：`VirtualRunEnv` + `Environment` 变量在 `self.run(env=None)` 前应用，裸跑 ctest 继承 `LD_LIBRARY_PATH` |
| 5 | `sr_connect` 返回 SR_ERR_SYS：`/dev/shm` 操作失败 | OHOS 的 `/dev/shm` 是只写虚拟目录（可建文件，opendir/mkdir EACCES），sysrepo 连接时要枚举 SHM 目录 | test_package/ctest 均设 `SYSREPO_SHM_DIR` 指向可列的私有目录 |
| 6 | `sr_connect` 返回 SR_ERR_NOT_FOUND：`Retrieving UID ... passwd entry failed (No such UID)` | OHOS 应用 UID（如 20001006）在 /etc/passwd 无条目，getpwuid/getpwnam 失败且上游视为致命 | patches/0002：`SR_NO_PASSWD_ENTRIES` 下 uid→user 合成稳定名 `uid<N>`，user→uid 解析同型名字回数值（双向一致）；具名用户查询仍按上游报错 |
| 7 | 上游 20 个 cmocka 套件被静默关闭（无 tests/ 产物） | `find_package(CMocka 1.0.1)` 走 conan Config 模式（PREFER_CONFIG）只设 `cmocka_FOUND`；上游门禁检查全大写 `CMOCKA_FOUND`，模块模式 FPHSA 兼容层才会设 | conanfile 显式种 `CMOCKA_FOUND=1`（cmocka 实际可用），tests 正常构建出 23 个 ctest 条目 |
| 8 | fresh repo 内部模块安装失败（`Loading module failed, not found`） | `SR_YANG_PATH` 默认 `<repo>/yang`，测试逐套件建全新 repo，内无模块文件 | conanfile 设 `YANG_MODULE_PATH=sysrepo-yang`（烤定为 build 树内路径），`build()` 从源码 `modules/` 填充；所有 repo 共享该模块源 |
| 9 | tests_clear_shm fixture 失败：`find: '/dev/shm/': Permission denied` | 上游硬编码扫描 `/dev/shm`（CMake 变量 SHM_DIR），OHOS 不可列 | patches/0003：fixture 改为 `sh -c` 包装、按 `${SYSREPO_SHM_DIR:-/dev/shm}` 扫描 |
| 10 | preflight_check.sh 报 `pcre2` 依赖未发布（误报） | conanfile 注释里的 `requires("pcre2/...", ...)` 示例被依赖扫描正则当真实依赖，按 `pcre2/...` 探测必然失败 | 未改配方（不影响 W3/CI 链路）；pcre2 实际已发布（libyang 传递依赖，create 日志实证） |
| 11 | 16/23 上游测试失败：`mkfifo() failed (Operation not permitted)` → 订阅 setup 失败 | **OHOS 平台缺口**：mkfifo 在 HMDFS 主目录 EPERM、/dev/shm EACCES（逐路径探测实证）；sysrepo 订阅事件管道 evpipe 依赖命名 FIFO | **不绕、不硬啃**：evpipe 重设计属框架级改动（红线）。results 如实归档：依赖订阅的 15 个套件 + test_modules（模块生命周期断言）失败，其余 7 项通过（详见 test-report.md） |

## 源码修改

- `patches/0001-ohos-robust-mutex-fallback.patch`：`src/common.h` 增加 `SR_NO_ROBUST_MUTEX` 下 `pthread_mutexattr_setrobust`/`pthread_mutex_consistent` 的 static inline 回退（无平台宏）。
- `patches/0002-ohos-synthetic-passwd-fallback.patch`：`src/common.c`（sr_get_pwd）与 `src/plugins/common_json.c`（srpjson_get_pwd）在 `SR_NO_PASSWD_ENTRIES` 下做 `uid<->uid<N>` 双向合成映射。
- `patches/0003-ohos-tests-clear-shm-envdir.patch`：`tests/CMakeLists.txt` 的 SHM 清理 fixture 改为按 `SYSREPO_SHM_DIR`（缺省回落 /dev/shm）扫描。
- `test_package/conanfile.py`：VirtualRunEnv + OHOS ELF 自签 + 私有 SHM/repo 目录注入 + 裸 `self.run(env=None)` 跑 ctest。
- `test_package/test_sysrepo.c`：增加 `sr_log_stderr(SR_LL_DBG)`（失败时 ctest 日志可见内部错误链）。
- `conanfile.py`：依赖与 CMake 变量注入（REPO_PATH/YANG_MODULE_PATH/CMOCKA_FOUND/SR_NO_ROBUST_MUTEX/SR_NO_PASSWD_ENTRIES）、构建树与包目录签名、模块目录填充。

## 依赖版本

- libyang/3.13.6（transitive_headers + transitive_libs；其传递依赖 pcre2 由 conan 解析）
- cmocka/2.0.2（test_requires；上游 find_package 非 REQUIRED，缺 CMocka 会静默关闭全部测试，已钉住）

## 验证结果

```bash
# conan-verify：G0–G4 + L2/L4/L5 全 PASS（reports/conan-verify-report.md）
# W3 本地 CI 模拟：setup.sh + build_and_test.sh 通过（reports/w3-local-ci.log）
# test_package：PASS（sr_connect OK / sr_session_start OK / core connect-session-read path usable）
# 上游 ctest（顺序，-j1，SYSREPO_SHM_DIR 私有目录）：
#   注册 23 项（20 cmocka 套件 + headers + 2 个清理 fixture；format/perf 未注册见 test-report）
#   实跑 23，通过 7，失败 16（15 项直接因 OHOS 禁 mkfifo；test_modules 为模块生命周期断言失败）
#   逐项输出见 ~/tmp/uc2/z40/ctest-r3.log（构建目录 tests/CTestTestfile.cmake）
```

## 注意事项

- **robust mutex 退化**：降级后进程共享锁无 owner-death 恢复；持锁进程异常退出时其他进程将阻塞至超时（有 timeout 的路径报 SR_ERR_TIMEOUT）。这是 E192 既有处方，本包不自行发明恢复机制。
- **订阅不可用（平台缺口）**：OHOS 沙箱禁止 mkfifo，sysrepo 订阅事件管道（evpipe）无法创建；交付物覆盖数据面（连接/会话/数据存储读写路径），订阅面（notification/operational push/RPC 相关测试）在当前平台不可用。替换 evpipe 属上游框架重构，超出适配补丁边界。
- **passwd 合成名**：`SR_NO_PASSWD_ENTRIES` 下文件 owner 显示为 `uid<N>` 形式；NACM/属主校验按同名一致性运作。
- **shm 目录**：OHOS 上运行 sysrepo 必须设 `SYSREPO_SHM_DIR`（可列目录）。
- **shared yang 目录**：`sysrepo-yang` 在 build 树内被测试用作模块源（测试会安装/删除模块文件），每次全新构建时由 build() 重新填充。

编译结束
---

**编译结束**: 2026-09-28 14:00
**最终状态**: built

**本轮（2026-09-28）改动面（两个提交，均文档面、非构建输入 ⇒ `rrev` 不变、W3 证据不作废）**：① `finish` 重跑侧提交＝`manifest.yaml` **7 行**（`knowledge_gained` 七行各补同行 `ref:`，`unreferenced` 7→0）＋ `notes.md` **1 行**（`**编译结束**` 时间戳随 `finish` 刷新）；② W4 整改提交＝`manifest.yaml` **7 行**（七条 `ref:` 由行号改**章节锚**，避免后续改 notes 再漂行号）＋ `notes.md` **3 行**（第 6 条 `finish` 分项重写、`step5b` 字段映射三段式、本声明段）。`.ci-result.json` 的 `integrity_hash`/`log_sha256` 随每次 `finish` 重写 ⇒ 仓内不写字面值、以文件实物为准（复算式见上）。
