## PR 信息

- **三方库名称**：xkeyboard-config
- **上游版本**：2.48
- **上游仓库地址**：https://xorg.freedesktop.org/archive/individual/data/xkeyboard-config/xkeyboard-config-2.48.tar.xz
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E2176（本 PR 知识草稿）；windows-meson-extensionless-tool-resolution（相关平台条目）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游 pytest 参数化用例统一按其他测试入口统计 |
| 集成测试 | 0 | 上游没有独立集成测试入口 |
| 其他测试 | 5083 | pytest 5082 项，加 tests/verify-group-names.sh 1 项 |
| **合计** | **5083** | 清单：reports/upstream-test-inventory.txt；原始日志见任务 evidence |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 数据包无独立编译单元测试 |
| 集成测试 | 0 | 不变 | 未新增独立集成测试入口 |
| 鸿蒙特有测试 | 28 | +28 | Conan consumer 读取真实 package_folder，覆盖规则、XML、别名和 pkg-config 语义 |
| **合计** | **28** | +28 | consumer-local-r2.log 与 W3 r5 均为 28/28 PASS |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游源代码和 tests 目录保持原样；仅新增 Conan 配方、安装闭包检查和独立消费者断言。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

补全范围是包级安装和消费语义：验证生成规则文件非空、各 XKB 数据域安装计数、XML 解析、兼容别名目标和可重定位 pkg-config；新增文件为 archives/x/xkeyboard-config/2.48/test_package/test_xkeyboard_config.py。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：5083/5083（100%）
- 新增测试用例通过率：28/28（100%）

补充证据：

- Conan create r11 PASS，recipe revision `004c6f41020119e49b7d79bcc7b3d89e`，package revision `5b586f7ba1ffdbb38a33020de5cf5b08`。
- 真机 W3 `xkeyboard-config-2.48-w3-20260907-r5` 在 `10.62.150.125:8022` 完成 fresh transfer/readback、唯一 launch 和 release/postrelease；payload SHA-256 为 `496d357f4bebdad1403325523d8a75c705cb8077213eb1faa9bbca70d9a14409`。
- W3 结果冻结为 PASS，launch_count=1，远端 runner 和任务根已清零；旧 Windows local-CI 模拟因 setup.sh 缺少 fcntl 在前置阶段失败，未伪造 `.ci-result.json`。
- 当前候选在 PRE_CREATE 阶段绑定 HEAD `d142b346567145aae7ee0e072eb90582e899f2a6`；加入本 PR 合同文件后将按新 tree 建立 successor W3。

---

## 补充说明

- 关联 Issue：#2777
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/xkeyboard-config-2.48
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：知识查重结果为 NO_EQUIVALENT_REUSABLE_KNOWLEDGE，E2176 是本 PR 的新增通用知识。该包声明无运行时 Conan 依赖；Meson 在 Windows 到 POSIX 交叉场景显式使用 --prefix=/。HD1-HD4 当前均 matched=false，分类为路径 A+B 和 【知识库扩展】。平台 AI Review、平台 CI 和提审必须绑定后续唯一当前 HEAD，不能使用旧 W3 证据跨 tree 拼接。
