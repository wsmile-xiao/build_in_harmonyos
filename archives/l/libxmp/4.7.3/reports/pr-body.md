## PR 信息

- **三方库名称**：libxmp
- **上游版本**：4.7.3
- **上游仓库地址**：https://github.com/libxmp/libxmp
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E545-draft-XM11；参考libfsntfs、E2185、geographiclib数据门控、uvg266子模块条目

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1013 | 官方tag test-dev/all_tests.txt逐项命名；完整CMake开发程序 |
| 集成测试 | 3 | test/test.c三个run_test：test.it、test.itz、test.xm，实际渲染PCM MD5及播放时长校验 |
| 其他测试 | 0 | 未构建另一个可选lite库，未删除完整libxmp已注册测试 |
| **合计** | **1016** | 两个CTest程序，按内部逻辑项统计，避免混合程序数和用例数 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 1013 | 不变 | 全量命名项与原日志精确一致 |
| 集成测试 | 3 | 不变 | 三个官方样本原MD5均通过，无断言/素材修改 |
| 鸿蒙特有测试 | 1 | +1 | test_xmp.c真实库API解码、OHOS身份、TMPDIR文件生命周期；131断言不是131程序 |
| **合计** | **1017** | **+1** | 上游1016 + 独立消费者1 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

使用完整官方固定tag归档及上游CMake入口；仅配方设置原生OHOS SONAME/签名安全RPATH和执行环境，缺清单明确报错。不改上游源码、测试断言或期望输出。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增test_package测试用真实MOD解码生成141120非零PCM字节，并在鸿蒙TMPDIR实际写入、读回校验及清理；不替代1016上游用例。上游测试素材随官方tag下载，未额外引入私有测试集。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1016/1016（100%）
- 新增测试用例通过率：1/1（100%）

正式libxmp-finish-20261011-r1 W3 Conan create/安装消费者PASS，12阶段release/postrelease完整。原W3 SHA256 85ae574b3461e95b2b4d176d6a2d7e94633e7af90c3d0164b87aa36096fa9c64；官方ci-result integrity 86510283ef090228。1013开发测试6.96秒，发布程序3个原MD5通过。原始日志未改写，1016/1016派生摘要绑定原日志和源清单。总finish RC1/step3,step5b,step8保留：旧G1将合法exports_sources误判并要求无必要补丁；原报告FAIL不改，实际Conan验证成功。其他后置知识/提交约束由本候选草稿和Pre-PR合同单独验证。不宣称整个finish、比赛worker CI或发布成功。

---

## 补充说明

查重新增边界：EXISTS静默缩减已是现有知识，不重复申报。这里验证自身测试源码被发布包省略、而非数据或子模块缺失时，使用独立可构建且3277blob身份闭合的同版固定官方tag恢复正式套件；同时纠正发布程序与内部渲染用例混算。不是对所有库替换release归档的建议。

- 关联 Issue：#3920
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libxmp-4.7.3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：CMake以EXISTS条件注册开发测试时，测试开关打开与CTest成功不能证明完整上游覆盖；发布包可安静省略整个测试目录。固定官方标签、验证归档与Git blob闭包，并逐一对齐程序内部清单、渲染用例和日志分母；缺目录fail-closed，消费者断言单独统计。不修改上游测试或用绿色子集替代全量。 task#15050；HD1–HD4均否定。官方归档SHA256 f2ee83c3ec146d5024bcba2a094ba9cf48eebbf9518bca02cf2e7cb139889a43，完整3277blob已验证。LGPL-2.1-or-later，保留上游版权及测试素材来源；不独立宣称测试素材所有权。没有运行依赖、不关闭depackers/ProWizard。合并后/release。


### 2026-10-13 当前 CI 修复

An immutable official tag URL can end in a commit SHA while delivering tar.gz bytes. Conan uses the downloaded filename to choose archive handling, so declare the real filename/container without changing the URL or SHA256.

当前真机事务 `libxmp-ci-repair-w3-20261013-r1`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `fea19818afc60855ef0511a942a013ecef1af9e89026f36b76f891d7654644b0`。上游 1016 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
