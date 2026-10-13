## PR 信息

- **三方库名称**：utest
- **上游版本**：0.0-git20260928-df92c758（官方提交 df92c7589f7f1d1bd22489cc029e8a61ef538588）
- **上游仓库地址**：https://github.com/sheredom/utest.h
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（高难度挑战候选）
- **使用知识库**：E272；E2026100405 草稿（知识补充至 [PR 2991](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/2991)）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 没有额外独立单元测试入口；不单独以内部用例作为报告分母；2178 个框架用例嵌入每个 CTest 场景，详见下述边界 |
| 集成测试 | 13 | 原 CMake 注册的完整原生 CTest 场景：基础/排序/固定种子、WPO、Address/Undefined/Thread sanitizer |
| 其他测试 | 0 | 当前非 MSVC 平台无额外注册场景；Memory sanitizer 不通过原上游能力探测，不伪造其注册 |
| **合计** | **13** | 与真实 inventory.json、JUnit 场景名逐项一致 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 没有额外独立单元测试入口；内部用例保持原样，不与场景分母重复计数 |
| 集成测试 | 15 | +2 | 完整 13 个上游场景，以及安装头的分配/释放和字符串消费者 2 例 |
| 鸿蒙特有测试 | 1 | 新增 | __OHOS__/aarch64 与 HarmonyOS 原生 CLOCK_MONOTONIC 计时器后端，实际调用 utest 计时接口 |
| **合计** | **16** | **+3** | 原生 W3 r008：上游13/13、消费者2/2、专项1/1 |

每个上游套件包含 2178 个内部用例：2168 PASS、10 个 Todo 是上游用于验证框架 skip 行为的故意控制。所有 13 个注册场景均 PASS，JUnit 无 failed/skipped 场景。不能写为零内部 skip，也不将重复/随机顺序/sanitizer 执行累计为 28314 个独立用例。

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

原 CMake、测试 TU、utest.h 和全部断言字节不改，但测试编译环境增加下列兼容后端：

1. 原 vendored subprocess.h 通过其现有 SUBPROCESS_SPAWN_VIA_FORK=1 路径执行真实 fork/chdir/exec；OHOS 缺少 addchdir_np，不能用空实现。
2. GNU make 4.4 在 HMDFS 上使用 pipe jobserver，不创建不支持的 FIFO。
3. OHOS 原生编译签名包装保留真实工具参数与上游严格告警；只忽略 SDK 为编译步骤注入的链接专用 --code-sign 参数告警。
4. 恒定设置 -D_GNU_SOURCE，保证严格 C 标准模式下 POSIX/GNU 声明可见；该编译环境设置不修改原测试 TU 或断言，不因运行时重试而动态增加。
5. 测试专用 ohos_test_tmpfile.h 将 tmpfile 调用绑定到任务私有 mkstemp/fdopen/unlink 流；维持原 write/seek/read/close 和输出比较断言。C/C++ 多标准的 null/cast 写法分别适配；生产安装头不注入此宏。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增消费者 2 例和独立鸿蒙计时器专项 1 例，不替代上游完整自测。源码 pin 修复不等于测试 PASS。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：13/13（100%）
- 新增测试用例通过率：3/3（100%）

- W3 run：utest-20261004-r008，HEAD 69f46703b0192a1f244a901ede58ef254edadb75，运行 tree 72a6ecdaa7e27adcbbb0af6a890d80c5567edb28。
- AtomCode 超时检视 F1：Conan 显式传 build_folder，包装器和编译/签名/运行子进程共享独占任务目录；r008 清空父 TMPDIR/TMPPREFIX 后直接运行修复脚本，消费者2/2、鸿蒙1/1。F2 ELF 类型编号误报不改：ET_EXEC=2、ET_DYN=3，4为core。F3 分母来自完整官方注册清单，未硬编码13或禁用 sanitizer。F4 明确消费者2用例/4断言，专项独立1用例。
- 一次 launch，精确字节传输/独立回读、完整 WAL/receipt 链、AFTER、owned_processes=0、release/postrelease PASS。
- 本轮 formal-utest-r002 的正式原生 Conan create、配方验证和本地 CI 模拟通过，输入哈希前后不变，独立回读匹配当前配方；未沿用前驱 PASS。完整 finish 仍为 PARTIAL_POST_W3（RC1）：step5b 为主线旧知识字段/索引检查，step7 为稀疏投影的旧框架范围比较，step8 为旧打包与空 marker 要求；自有 PR 原子性独立校验通过，不将整体记录为 PASS，不制造 tar 包或空标记。终态完整日志快照 SHA-256：18fad4569fc5390a254d4055df434d2e614e4195b2526f8f2c28efba193ae2ee。
- reports/r008-* 保存本轮真实清单、JUnit、哈希绑定和测试报告。按仓库 *.log 禁入规则，原始日志逐字节保存在 PR 外的任务证据目录，文件字节数与 SHA-256 对照见 reports/raw-log-evidence-index.json；本次仅修正文档证据布局，运行输入和测试分母不变，不重复 launch。原 r001-r006 失败与 r007 前驱成功独立保留，不与当前轮次拼接。r008 配置 SHA-256：88303ea005f491e4a91958fee1748de5bfeb675591e2e460a4cd9ea63d8db6b8。
- 当前平台 CI #69937 为旧 HEAD 的源码解包失败；修复更新后须等待新 HEAD 的真实 AI Review 和 CI，不宣称平台已通过或已提审。

---

## 补充说明

- 关联 Issue：#3720
- 队伍名称：2301_80739235（个人）
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/utest-0.0-git20260928-df92c758
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 官方不可变源码 tar.gz 43656 bytes，SHA-256 00e8918b42a8e10efaeb38ca7d6a9c32cea14b956e8d511a8379cd26288718b5；原滚动归档完整30文件逐字节等价，只改封装身份。
- E2026100405 是对 E272 / [PR 2991](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/2991) 的实质补充：测试临时流后端注入混合语言严格告警矩阵时的语言合同和结果分母边界。四域知识查重已执行，不重复申报基础 tmpfile 方案。原 PR 使用完整 pull URL，避免平台把裸编号误关联为同号的无关 Issue。
- 产品零外部依赖，公开工具链；HD1/HD2/HD3=false。HD4按混合标准、严格告警与sanitizer真实执行闭包申请候选，详见唯一Issue #3720；不把2178参数/标准展开或13次重复执行作为数量门槛，不宣称委员会获批。
- 发布仅在官方合并后通过平台 /release；本修复不上传制品仓、不合并 PR。
