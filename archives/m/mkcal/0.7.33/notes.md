# mkcal 0.7.33 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMakeLists.txt`，CMake ≥ 3.16）
- 编译日期: 2026-09-29
- 编译器: clang / clang++ 15.0.4（`aarch64-linux-ohos`）
- Conan profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, os.version=6.0, arch=armv8）
- 状态: built

## 编译步骤

```bash
# 1) 取源码（官方 GitHub archive）
curl -sL https://github.com/sailfishos/mkcal/archive/refs/tags/0.7.33.tar.gz -o mkcal-0.7.33.tar.gz
sha256sum mkcal-0.7.33.tar.gz   # d31cba7ad4a7fd6463058a1843b3195942619d89ec042c5695f6a6f29be10793

# 2) 依赖预热 + 配方构建（只构建本包，依赖全部取制品仓 binary）
conan install archives/m/mkcal/0.7.33 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=never
conan create archives/m/mkcal/0.7.33 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=mkcal/0.7.33
```

上游构型：`-DENABLE_QT6=ON`（OHOS-PC 目标构型为 Qt6/KF6；上游 CMake 默认 `ENABLE_QT6=OFF` 走 Qt5/KF5）、`-DBUILD_PLUGINS=OFF`（唯一插件 `defaultinvitationplugin` 依赖 QmfClient，制品仓无此包）、`-DBUILD_TESTS=ON`、`-DBUILD_DOCUMENTATION=OFF`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan install` 在 `generate()` 抛 `KeyError: 'CMAKE_PREFIX_PATH'` | 同一表达式里混用 f-string 与 `.format()`，`${{CMAKE_PREFIX_PATH}}` 在 format 阶段被当成占位符 | 改为纯 f-string 表达式（同 libkgapi 26.04.0 先例） |
| 2 | CTest 运行即 `SIGSYS`（exit=159），进程在 `SqliteStorage` 构造时被终止 | `src/semaphore_p.cpp` 用 SysV IPC 信号量（`ftok`/`semget`/`semctl`/`semtimedop`）实现跨进程 DB 互斥；OHOS 未实现这些 syscall，调用即发送不可捕获的 SIGSYS（知识库 E051）。实测：`semget()` 触发 SIGSYS，而 POSIX `sem_open()/sem_post()/sem_getvalue()` 全部正常 | 补丁 0002/0003：新增 `#ifdef __OHOS__` 分支，用 POSIX 命名信号量（`/mkcal-<md5(路径)>-<slot>`）实现同样的计数信号量契约（`sem_wait/sem_trywait/sem_timedwait/sem_post/sem_getvalue`）；非 OHOS 平台保持 SysV 原实现 |
| 3 | 测试二进制启动即报 `Error loading shared library ./libical.so` 等 | OHOS 上依赖库记录的是相对 soname；musl 加载器对含斜杠的 `DT_NEEDED` 从进程 CWD 解析，而非 `LD_LIBRARY_PATH` | conanfile `_prepare_ctest_runtime_links()`：把依赖库与 `libmkcal-qt6.so` 复制到 CTest 各 CWD 深度（`<build>/tests`、`<build>`、`<build>/bin`） |
| 4 | `tst_timezone`/`tst_allday` 等大量失败，时间戳显示 `[UTC+00:00:01]` | OHOS 既无 `/usr/share/zoneinfo` 也无 `/etc/localtime`；`/system/etc/zoneinfo` 是私有格式（`tzdata`+`timezone_list.cfg`），Qt 的 QTimeZone 无法读取 | conanfile `_zoneinfo_dir()`：优先 qtbase 的 `share/zoneinfo`，回退到 `tzdata/2026.3` 包内的 `site-packages/tzdata/zoneinfo`；测试环境设 `TZDIR` + `TZ=Europe/Helsinki`（上游测试数据基于芬兰时区） |
| 5 | `tst_perf::tst_save/init` 失败：`rawEvents().isEmpty()` 为假 | `ExtendedCalendar::close()` 在 `KCALENDARCORE_VERSION >= 5.245` 分支不清理内存数据（KF6 移除了 `Calendar::close()`） | 补丁 0001：新增 `#else` 分支，用 `rawIncidences()` + `QSignalBlocker` 静默丢弃内存中的 incidence，恢复 KF5 `MemoryCalendar::close()` 语义（不通知观察者，避免污染 storage 的待写队列） |
| 6 | `conan create` 的 `source()` 报 `BadZipFile: File is not a zip file` | `codeload.github.com/.../tar.gz/refs/tags/0.7.33` 的 URL 尾部无扩展名，conan 按 zip 解压 | 改用官方 `https://github.com/sailfishos/mkcal/archive/refs/tags/0.7.33.tar.gz`（sha256 一致，已实测核验） |
| 7 | 使用 `qtbase/6.11.1.2` 时 `kcalendarcore/6.26.0` binary 缺失 | 依赖图变更导致 kcalendarcore 的 package_id 变化，已发布 binary 不匹配 | 回退到 `qtbase/6.11.1`（与 kcalendarcore 已发布 binary 匹配），时区数据改由 `tzdata/2026.3` 提供 |
| 8 | W3 本地 CI 的 JC 门禁报 junk | 未提交时 `git diff origin/main...HEAD` 为空，JC 回退 full 模式扫到仓库既有历史 junk（`archives/c/cloog`、`kics`、`thc` 的 `.build-closed`/`.staging-verified`）；且 `conan-verify` 会在 `test_package/` 下生成 `build/` | 以 `JUNK_PR_DIFF`（CI 的 prdiff 模式，与 buildbot checkout-pr 同源）提供精确的白名单文件清单；清理 `test_package/build`、`conandata.yml.ghfast-bak`、`patches/.patch-backup-*` |
| 9 | W3 L5 门禁失败：`libmkcal-qt6.so` 缺少 `DT_SONAME`，且 `DT_NEEDED` 含绝对路径 `/storage/.../kcalendarcore/p/lib/libKF6CalendarCore.so` | OHOS 工具链未把上游 `SOVERSION` 属性传到链接器，产物没有 SONAME；同时制品仓 `kcalendarcore/6.26.0` 自身也无 SONAME，链接器遂把构建机绝对路径写进 `DT_NEEDED`（不可搬迁） | conanfile `package()` 新增 `_normalize_elf_sonames()`：安装后用 `patchelf` 为每个共享库补 `DT_SONAME`（取文件名），并把绝对 `DT_NEEDED` 条目改写为裸库名（kio-kwallet 6.28.0 / E018 先例）；在 ELF 签名之前执行 |
| 10 | `conan-verify` 的镜像注入残留 `conandata.yml`（出现 `gh-proxy.com` 前缀且 URL 变列表） | `conan-verify` 为规避 GitHub 不可达会临时注入镜像并在结束时"恢复"，实际恢复了注入后的内容 | 恢复为单一官方 URL（R39/PF7 要求官方源；镜像由工具运行时注入，不写入文件） |

## 源码修改

补丁目录 `patches/`（3 个，均已在 `conandata.yml` 登记）：

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-src-extendedcalendar.cpp.patch` | `src/extendedcalendar.cpp` | `ExtendedCalendar::close()` 在 KCalendarCore 6.x 分支补齐内存清理（`rawIncidences()` + `QSignalBlocker` + `deleteIncidence()`），恢复 KF5 `MemoryCalendar::close()` 语义 |
| `0002-src-semaphore_p.cpp.patch` | `src/semaphore_p.cpp` | OHOS 分支改用 POSIX 命名信号量替代 SysV IPC 信号量（SysV 在 OHOS 上调用即 SIGSYS） |
| `0003-src-semaphore_p.h.patch` | `src/semaphore_p.h` | 声明 POSIX 信号量后端成员与初始化入口 |

> **平台宏说明（R8 例外）**：补丁 0002（5 处）/0003（2 处）含 `#ifdef __OHOS__`。这是**内核能力缺失**导致的编译期分支——OHOS 未实现 SysV IPC 信号量，`semget` 触发的 SIGSYS **不可捕获**（`sigaction` 无效、进程直接终止），因此无法用运行期探测替代编译期判定。补丁 0001 为 KCalendarCore 6.x API 兼容性补偿，不含平台宏。

## 依赖版本

- `qtbase/6.11.1`（Qt6 Core/Gui/Widgets/Test/DBus；`FEATURE_testlib=ON` 提供 Qt6::Test）
- `kcalendarcore/6.26.0`（KF6 CalendarCore）
- `sqlite3/3.53.4`（静态库；上游用 `pkg_check_modules(SQLITE3 ... REQUIRED)`，制品仓包不含 `.pc`，配方在 generators 目录内合成 `sqlite3.pc` 并设置 `PKG_CONFIG_PATH`）
- `tzdata/2026.3`（上游 kcalendarcore 的传递依赖；同时作为测试时区数据源）
- `ecm/6.26.0`（tool_requires）、`pkg-config/0.29.2`（tool_requires）
- `libical/4.0.1`（传递依赖）

## 验证结果

```bash
conan create archives/m/mkcal/0.7.33 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    -r=ohpcd --build=mkcal/0.7.33     # exit 0
```

- 上游测试（3 个 CTest 条目，全部为门禁）全部通过：`tst_storage` 93/93、`tst_perf` 5/5、`tst_load` 18/18（合计 **116/116**，0 失败 0 跳过）
- `test_package` 消费者验证通过：`PASS: mkcal SQLite storage round-trip <uid>`
- OHOS ELF 签名：`Signed 2 OHOS package ELF file(s)`
- `conan-verify`：**G0/G1/G2/G3/G4 全部 PASS**（其 L2/L4/L5 检查由 W3 执行，见下）
- W3 本地 CI 模拟：`setup.sh` + `build_and_test.sh` 通过；`JC_RESULT=pass`、`L0_RESULT=pass`、`L4_RESULT=pass`、**`L5_RESULT=pass`**（`L5a` SONAME / `L5b` 相对 `DT_NEEDED` 均通过）
- `.ci-result.json`：`exit_code=0`（由 `finish` 写入，`log_sha256` 与 `reports/w3-local-ci.log` 实测哈希一致）

## 交付物

| 文件 | 说明 |
|------|------|
| `libmkcal-qt6.so` | SQlite 存储后端共享库（已设 `DT_SONAME`、`DT_NEEDED` 无绝对路径） |
| `mkcaltool` | 上游命令行工具 |
| `include/mkcal-qt6/*.h` | 公共头文件 |
| `lib/pkgconfig/libmkcal-qt6.pc` | pkg-config 元数据 |

## 注意事项

1. **构型绑定 Qt6/KF6**：本配方固定 `-DENABLE_QT6=ON`，因为 ohpcd 只发布 KF6/Qt6（`kcalendarcore` 仅 6.18.0/6.26.0，无 5.x；`ecm` 无 5.116）。
2. **POSIX 信号量语义差异**：SysV 的 `SEM_UNDO`（进程异常退出自动释放）在 POSIX 命名信号量中不存在，极端异常退出后可能残留计数；正常 close 路径不受影响（代码未主动 `sem_unlink`，以便多进程共享同一信号量）。
3. **ELF 后处理**：`package()` 阶段用 `patchelf` 补 `DT_SONAME` 并改写绝对 `DT_NEEDED`，随后才做 OHOS 签名（顺序不可颠倒）。
4. **测试环境**：上游测试硬依赖欧洲/赫尔辛基本地时区与完整 tzdata，OHOS 系统不提供，故在 `build()` 的测试环境中显式设置 `TZ`/`TZDIR`；`/tmp` 只读，`MKCAL_STORAGEDB` 指向构建目录并在每个套件前清理（与上游 `tests/tests.xml` 的 `rm -f` 语义一致）。
5. **测试构建树**：`test_package` 的构建目录输出到 `<repo>/.ohc/mkcal-test-build`（仓库已 gitignore），确保归档目录零生成物。
---

**编译结束**: 2026-09-29 08:50
**最终状态**: built
