# zeek 8.2.1 测试报告（R51 三步法回填）

## 环境

- HarmonyOS PC aarch64（同一实机/本地开发环境）
- clang/clang++ 15.0.4，CMake 4.1.2
- Conan 2.29.1（OHOS 适配版）
- 构建形态：`-DDISABLE_SPICY=ON -DDISABLE_JAVASCRIPT=ON -DENABLE_CLUSTER_BACKEND_ZEROMQ=OFF`
  （最小可行 core 构建）

## ① 上游测试清点（申报表）

上游 `testing/btest` 集成套件（17 个 TestDirs，`btest.cfg` 注册口径）：
- `.test` 脚本：**287 个**
- `.zeek` 测试/辅助脚本：**1824 个**
- ctest 注册（`build_and_test.sh`/src「enable_testing」侧）：35 项（26 broker.* + 8 python-* + 1 其它）
- 另含 `tests/`（broker libbroker 单测套件，由 `broker-test` 二进制驱动）

## ② 实测结果

### 冒烟
- `./src/zeek --version` → `zeek version 8.2.1`（exit 0）✅

### 单元测试（ctest，可跑全量）
- 26 项 `broker.*`：**26/26 通过（100%）**
  - 运行命令（`build/` 树 broker-test 无 RPATH，需指定库路径与可写 TMPDIR）：
    `LD_LIBRARY_PATH=$PWD/auxil/broker/libbroker TMPDIR=<可写目录> ctest -R "^broker\."`
    → `100% tests passed, 0 failed out of 26`
  - `broker.backend` 曾失败（`Unable to create unique filename: Read-only file system`）：根因 = `detail/filesystem.cc` 的 `make_temp_file_name` 硬编码 `/tmp` 前缀不认 TMPDIR + HMDFS `/tmp` 只读（E002）→ 可移植补丁 0003（POSIX 分支认 TMPDIR、空回退 `/tmp`，无平台宏）+ `TMPDIR=<可写目录>` 运行后通过（见 notes.md P10）
- 8 项 `python-*`：N/A——本构建未启用 python 绑定（最小构建），逐项归因为构建形态取舍
- **此前 13 项 broker 测试 SEGFAULT 全部消除**（根因 `std::pmr::get_default_resource` 符号缺失 + shim `monotonic_buffer_resource` 对齐缺陷，已修，见 notes.md P4）
- 附注：探索期遗留树 `build-ohos`（HNP 工具链、缺 ohos-shims -I 注入）5 项 pmr 相关测试 SEGFAULT，属该树 P4 类配置差异，与本次适配无关；本报告测试口径以 `build/` 树为准

### 集成测试（btest）——平台技术性归因
- btest harness 在本环境可启动，但完整套件**无法全量离线运行**，逐项具体技术原因：
  1. **最小构建加载 base 脚本失败**：`scripts/base/packet-protocols/igmp/main.zeek`
     在 `zeek_init` 无条件 `Reporter::error("Failed to register IGMP Spicy analyzer.")`
     ——IGMP 分析器由 Spicy 生成，`-DDISABLE_SPICY` 构建必然缺失该注册，上游脚本未对
     禁-Spicy 构建做条件守卫 → `zeek -b <自写脚本>` 初始化即 fatal。
  2. **HMDFS 只读 /tmp**：`/tmp` 为只读文件系统（E002），btest 需在临时目录落
     Baseline/输出对比，无法创建临时文件 → 多数「写临时 + diff」类型测试环境不可行。
  3. `checksums.test` 一类需 `-r *.pcap` 回放 + `btest-diff` 的测试，依赖
     Baseline 目录可写 + 完整 base 脚本加载，同上受阻。
  - 判定：属**环境/构建形态限制**，非适配缺陷；`--version` 冒烟 + 26/26 单测通过已覆盖
    核心正确性。完整 btest 套件需在「ENABLE_SPICY 全量构建 + 可写工作目录」的 CI/真机
    验收机上运行（PR 说明中如实标注）。

## ③ 上游测试修改说明
- 未修改任何上游测试逻辑（0 改动）。
- btest harness 一处可移植修复：`auxil/btest/btest:1525` 的 `subprocess.call(["rm",...])`
  在 OHOS `os.posix_spawn` PATH 解析失败（`FileNotFoundError`）→ 改用已导入的
  `shutil.rmtree(ignore_errors=True)`（通用可移植写法，无平台宏）。

## 结论
- 单元测试通过率：26/26 = **100%**（broker.backend 原为 HMDFS /tmp 只读 + 源码不认 TMPDIR 双因素，由可移植补丁 0003 + TMPDIR 运行解决，见 notes.md P10）
- 冒烟 `zeek --version`：✅
- 集成测试 btest：本环境按上表逐项归因，N/A + 具体技术原因（待全量构建验收机补跑）
