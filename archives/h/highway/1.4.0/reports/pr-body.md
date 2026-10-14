## PR 信息

- **三方库名称**：highway
- **上游版本**：1.4.0
- **上游仓库地址**：https://github.com/google/highway
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E332；restclient-cpp PRE_TEST 草稿；CMake SONAME/签名知识；本 PR 配对草稿 knowledge/drafts/E15139-draft-A715.kv + .md

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 861 | 保留 core/contrib/SIMD/动态 dispatch；上游维护的 standalone runner 经 CTest JSON 完整发现 861 项，不沿用旧版分母；按真实注册/框架用例计数，不把 CHECK 断言计为上游用例 |
| 集成测试 | 0 | 已注册上游项统一计入上一行，不重复计数 |
| 其他测试 | 0 | 无另外声明的默认套件 |
| **合计** | **861** | 完整清单与同次实跑日志见 test-report.md |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 861 | 不变 | 全部上游用例实跑，失败/跳过均 0 |
| 集成测试 | 0 | 不变 | 安装消费者的功能断言与鸿蒙文件行为属于下行同一个组，不重复计数 |
| 鸿蒙特有测试 | 1 | +1 | 安装 core/contrib；对齐 SIMD 加法、动态 VQSort 边界排序及鸿蒙私有文件结果往返，1 个组共 11 处 CHECK |
| **合计** | **862** | **+1** | 上游 861 + 新增安装消费者/鸿蒙功能组 1 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

仅调整 CMake/Conan 构建和局部执行环境；保留上游断言、预期结果和受测套件。使用上游维护的 HWY_TEST_STANDALONE，完整发现并执行所有可达原生测试，不裁剪 SIMD/contrib。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有完整套件；额外 test_package 补充安装后 API/平台行为，不替代上游测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：861/861（100%）
- 新增测试用例通过率：1/1（100%）

HarmonyOS PC aarch64，clang 15.0.4，CMake 4.1.2，Conan 2.29.1；原生共享库 Release。
独立事务 highway-official-w3-20261013-r2，唯一 launch=1，12/12 PASS 回执且 runner 已退出。L0/L1/L4/L5 通过；L2 因包无安装 bin/ 不适用。
原始日志 SHA-256：aa43a5d925bd36a192403d95ef79487c3c750a8cd3c00228361d8cceb246fece。
官方 finish 的 W3 子步骤自动生成的结果已精确回读；未手写 .ci-result.json。
原始源码 URL/SHA 固定；任务本地源覆盖仍验证同一 SHA，不依赖未声明裸环境变量。
平台 AI Review、比赛 worker CI 待 PR 提交及双向关联完成后执行，不声称已通过；其他构建配置和架构不在通过声明中。

---

## 补充说明

- 关联 Issue：#3961
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/highway-1.4.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：不重复 standalone 开关或 PRE_TEST 本身；新增独立 POST_BUILD 与发现机制的能力边界和执行顺序，本次实际 hwy_list_targets 构建后执行验证该场景。 PRE_TEST 只延迟 gtest_discover_tests，不会延迟独立的 POST_BUILD 程序。新增在构建期提供当前构建树运行库，再签名、发现并完整执行测试的阶段决策，适用于混合构建期工具执行与动态测试发现的原生 CMake 工程。
- 发布边界：仅在合并后运行 /release 发布至 ohpcd；PR 校验不上传。


### 2026-10-13 当前 CI 修复

Conan creates CMake generator directories before recipe generate(); a source BUILD file can collide with the default build directory on a case-insensitive target filesystem. Select a non-colliding cmake_layout build_folder rather than deleting the upstream build-system input.

当前真机事务 `highway-ci-repair-w3-20261013-r1`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `6b0e18bce41f8e097e48b74514edb6326bc290e4a225cc76e53d15032d7dc24a`。上游 861 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
