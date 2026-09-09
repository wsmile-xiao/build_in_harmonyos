# dee 1.2.7 适配笔记

## 编译环境
- 构建系统: autotools（LT_INIT，libdee-1.0 + dee-tool）
- 编译日期: 2026-09-05
- 编译器: clang 15 / clang++（/data/service/hnp/bin，OHOS SDK）
- profile: ci/conan/profiles/ohos-aarch64（os=OHOS 6.0, armv8, libc++, cppstd=17）
- 状态: 配方已备；本地 configure 通过验证 OHOS 适配；全量构建/测试由 CI 承担

## 编译步骤
```
cd archives/d/dee/1.2.7
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- configure options: `--disable-maintainer-flags --disable-icu --disable-extended-tests --disable-trace-log`（--disable-tests 已移除，上游 test-dee 启用）
- 依赖：glib/2.84.0.1.1（唯一硬依赖；D-Bus 经 GDBus，无需 dbus/dbus-glib）
- 产物：libdee-1.0.so（codesign）+ dee-tool（bin）+ include/dee-1.0/ 头 + libdee-1.0.pc

## 依赖与前置
- PKG_CHECK_MODULES(DEE, glib-2.0/gthread-2.0/gobject-2.0/gio-2.0/gio-unix-2.0 >= 2.32) — 全为 glib 族，ohpcd 上 glib/2.84.0.1.1 已发布。
- **gio-unix-2.0.pc**：glib conan 包未装此 .pc（configure 报 No package 'gio-unix-2.0' found）→ 配方 generate() 生成 shim（`Requires: gio-2.0`，gio-unix 是 glib 的一部分，属准确补充）+ 注入 PKG_CONFIG_PATH。

## 已知问题与设计决策

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess "cannot guess build type" | **OHOS 本机 uname -s=HarmonyOS**（非 Linux），2012 旧版 config.guess 的 `aarch64:Linux` 分支不匹配 | 0001 补丁：加 `aarch64:HarmonyOS:*:*)` 分支（保留 `aarch64:Linux` 分支供 CI worker 用）→ echo aarch64-unknown-linux-ohos；config.sub 加 linux-ohos* 到 maybe_os/os 合法性列表 |
| 2 | -Werror 默认开启（odd micro=1.2.7） | dee_micro%2==1 → maintainer_flags_default=yes | `--disable-maintainer-flags` |
| 3 | 可选分支（icu/gtx/gtk-doc/vala/introspection） | 非核心 C 库所需 | `--disable-icu --disable-extended-tests --disable-trace-log --disable-tests` |
| 4 | 本地 config.status 临时文件 "Permission denied" | **根因已定位**：本设备 hmdfs 缓存路径上 umask 077 建的目录（0700）拒绝 owner 写（隔离复现：`drwx--S---` 写不进、默认 `drwxrws--x` 可写） | **修复**：配方 build() 在 configure 前把 configure 脚本的 umask 077 改 022（config.status 模板随之生成可写目录）；本地构建已通过 |
| 5 | 共享库需 OHOS codesign | E077 | 配方 _sign_shared_libs（glib 同款） |

## 源码修改
- `patches/0001-config-ohos.patch`：config.guess（aarch64:HarmonyOS/Linux → linux-ohos）+ config.sub（linux-ohos* 识别），2012 旧版格式

## 上游测试

- **清点**：tests/ 下 21 个 test-*.c → test-dee / test-benchmark / test-icu（noinst_PROGRAMS），另有 model-helper-*/peer-helper/server-helper 辅助二进制；test-dee 聚合 16 个 test-*.c 的 g_test 用例，TAP `1..188` 确认 N=188（最小测试单元）。
- **状态（2026-09-07 实测）**：已**重新启用**（移除 `--disable-tests`），test-dee 在 OHOS **编译+链接成功**（conan create exit 0）。`make check` 的 tests 步骤依赖 `dbus-test-runner`（CI/本机均无）不会执行 test-dee → 配方 build() 内置**逐用例运行器**（source 生成环境 + 前置 build 树 src/.libs，`test-dee -p <path>` 单测模式跑全 188 个）。
  - **结果**：**182/188 通过（96.8%）**（口径 passed/(passed+failed+errors)，无 skipped/xfailed）。
  - **6 个失败**（均为 `g_test_trap_assert_stderr` 断言，exit 134）：/Model/Sequence/Column/NoSchemas、/Model/Proxy/Column/NoSchemas、/ModelTags/SequenceModel/NoTags、/ModelTags/SequenceModel/OneTag、/ModelTags/SharedModel/NoTags、/ModelTags/SharedModel/OneTag。
  - **精确根因**：`test_no_schema`（test-model-column.c:331）等用 `g_test_trap_fork(0, G_TEST_TRAP_SILENCE_STDOUT|G_TEST_TRAP_SILENCE_STDERR)` 起子进程触发 dee-FATAL-CRITICAL，再用 `g_test_trap_assert_stderr("*pattern*")` 断言；但本 glib 上 dee-FATAL-CRITICAL 消息落在子进程 STDOUT、子进程 STDERR 为空 → 模式匹配失败 → 该用例 Bail out。单进程跑（make check）时首个失败即整 run Bail out、其余用例被遮蔽（此前只跑 5/188）；逐用例 `-p` 隔离后仅这 6 个 trap 用例失败，其余 182 全部通过。
  - **为何不能安全修**：①改 `assert_stderr`→`assert_stdout`：dee CRITICAL 在 Linux 落 STDERR（原断言在 Linux 正确）、OHOS 落 STDOUT，改动会破坏 Linux 测试（R8：不得破坏其它平台，且 `#ifdef __OHOS__` 守卫被禁）；②根修（让 CRITICAL 在 OHOS 走 stderr）属 glib 日志处理器行为深挖，超适配范围。**数字：N=188、182/188≈96.8%，6 个失败均精确归因（见上）**
  - 其余用例无需活 dbus 会话（纯内存 DeeModel 单测）；client-server/model-interactions/peer-interactions 为默认构建外集成测试（不在 test-dee 内，需多进程 D-Bus 会话，OHOS 私有会话连不上，libqtdbustest 同根因）
- **extended-tests**：需 gtx 框架（ohpcd 无），`--disable-extended-tests`（R51 记录）。

## 验证结果（本地实测，CI profile）
```bash
conan create . --user=ohpcd --channel=stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# exit 0 —— 主包构建+打包+test_package 全链路本地通过
# configure 全通过（DEE=yes；config.guess OHOS/umask 工作区/-Werror/可选分支均正确）
# test_package R34: PASS: dee model created, schema set, 1 row appended (n_rows=1)
#   （DeeModel create/set_schema('s')/append_row(GVariant)/get_n_rows；无活 dbus 会话）
```

## 注意事项
- 旧版（2012）config.guess：**不传 --build/--host**（旧版传 --build 致 CI configure 失败，依赖 config.guess 内联 OHOS 识别）。
- R34 test_package：DeeModel 独立模型操作（create/set_schema/append_row/get_n_rows）无需活 dbus 会话。
