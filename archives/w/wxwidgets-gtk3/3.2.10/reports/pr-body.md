## PR 信息

- **三方库名称**：wxwidgets-gtk3
- **上游版本**：3.2.10
- **上游仓库地址**：https://github.com/wxWidgets/wxWidgets/releases/download/v3.2.10/wxWidgets-3.2.10.tar.bz2
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 858 | 分母采用评审复核的 wxWidgets 3.2.10 `tests/` 测试面总量（鸣弦artha rule4 实测口径，含非 GUI 与 GUI 套件及条件/构建测试入口，不能等同于一次 Catch 进程的注册数）；其中非 GUI Catch 套件 `tests/test`（Catch v1.12.2，87 个测试源文件）为无显示环境可运行子集 |
| 集成测试 | 0 | 上游无独立集成测试分类 |
| 其他测试 | 0 | benchmarks/fuzz 不在运行范围 |
| **合计** | **858** | 实际运行 295，未运行 563（拆分与技术原因见"补充说明"） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 858 | 不变 | 上游测试面原样保留（未修改任何上游测试源码）；真机实际执行非 GUI 子集 295：267 通过 / 28 失败（逐条归因见下），563 项因需 GUI 显示连接/构建边界未执行、不计入通过数 |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 4 | 新增 | test_package 消费者测试：链接 wx GUI 全静态库集 + gtk/3.24.43 依赖链，4 项无显示 API 断言（wxGetLibraryVersionInfo/wxColour/wxSize/wxString） |
| **合计** | **862** | +4 | 实际执行口径：上游 295 + 新增 4；未执行的 563 项不计入通过数 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

真机以 autoconf 路径原样构建运行上游测试（3.2.10 的 CMake 不支持构建 tests）。构建环境的 3 处修复（config.sub 增加 ohos 三元组、mktemp shim 规避 HMDFS ACL、移除上游 configure 无条件追加的 `-lX11`）均为验证工作区环境级调整，不触碰上游源码与测试源码，逐条说明见 `notes.md` r8。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

---

## 验证结果

- 编译状态：通过（最近一次 CI #43172 全绿：conan create + test_package + L0/L1 门禁）
- 上游测试用例通过率：实际执行子集 267/295（90.5%，真机实测 2026-09-04；断言级 1,229,496/1,229,604 = 99.99%）；按上游测试面总量口径为 267/858（31.1%），563 项未运行的具体技术原因见补充说明与 `reports/upstream-tests-report.md`
- 新增测试用例通过率：4/4（100%，test_package 消费者测试）

### 28 项上游失败逐类归因（完整逐条明细：`reports/upstream-tests-report.md`，原始日志 `reports/upstream-test-output.log` 857 行随 PR 提交可复核）

| 根因类别 | 用例数 | 可否自做依赖解决 |
|---------|-------|----------------|
| 测试夹具未就位（运行脚本时序缺陷，脚本已修正 S7c） | 5 | ✅ 已修待重跑（预期转通过，272/295=92.2%） |
| `/tmp` 只读（测试硬编码 `/tmp/foo` 前缀、tempnam 经 HMDFS X_OK 回退 /tmp） | 2 | ❌ 平台硬限制 |
| 应用沙箱拒绝枚举 `/`、读 `/proc`·`/sys`（设备实测 `ls /` → Permission denied） | 4 | ❌ 平台硬限制 |
| HMDFS 语义（AF_UNIX socket 不支持、inotify 事件类型差异） | 2 | ❌ 平台硬限制 |
| musl 无 glibc locale/charset/数值解析行为（Intl/Translations/UILocale/NumFormatter/MBConv/String，含 `ToString(1234L)`=`1234` 无千分位等实证） | 15 | ❌ 平台硬限制（与制品仓 wxWidgets/3.3.3 真机观察一致） |

无失败指向 wx 库适配缺陷。验证设备 sshd 当前离线，恢复后将以修正脚本重跑并更新数字。

---

## 补充说明

- **测试统计口径**：上游分母按评审 rule4 实测口径取 `tests/` 测试面总量 858（声明 N=858，实测 858，不再少报）；真机 Catch 日志中的 `test cases: 295` 是实际运行的非 GUI 子集，不是上游完整分母。858 = 已运行 295 + 未运行 563，未运行项不计入通过数；`test_package/MANIFEST.yml` 以 `upstream_case_count/upstream_executed_count/upstream_passed_count/upstream_failed_count/upstream_not_run_count` 五字段同步该拆分。
- **GUI 套件（tests/test_gui）**：链接成功（上游 autoconf configure 对 GTK 无条件追加 `-lX11`，系 unix 下 GTK=X11 的错误假设；broadway-only 无 X11，验证环境移除后链接通过，与 CMake 路径 `GDK_WINDOWING_X11` 探测结论一致）。运行需显示连接——SSH 沙箱（SELinux `u:r:adhoc_bin:s0`）无显示服务访问，broadway-only gtk 无 broadwayd 运行路径：`Error: Unable to initialize GTK+, is DISPLAY set properly?`（RC=255，`reports/upstream-test-gui-run.log`）
- 已知限制：上游 GUI 测试无法在无显示的 SSH 沙箱运行（技术原因如上）；CI worker 曾因损坏 msgfmt 导致 locale 构建失败，已显式 `wxBUILD_LOCALES=OFF` 加固（notes.md r9）
- 构建产物：13 个 wx 静态库 + 5 个内置 3rdparty 库 + wx-config/wxrc；`package_info` 声明 `__WXGTK__` 等端口宏，供 CMakeDeps 消费
- 迭代历史 r1-r11 见 `notes.md`
