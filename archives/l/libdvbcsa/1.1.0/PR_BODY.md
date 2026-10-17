## PR 信息

- **三方库名称**：libdvbcsa
- **上游版本**：1.1.0
- **上游仓库地址**：https://download.videolan.org/pub/videolan/libdvbcsa/1.1.0/
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）
- **使用知识库**：已有 Autotools/config.sub 平台识别知识；本 PR 的 E778-draft-2501

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 4 | `test/Makefile.am` 注册 testbsops、testdec、testenc、testbitslice |
| 集成测试 | 0 | 未另设集成测试入口 |
| 其他测试 | 0 | 未另设其他测试入口 |
| **合计** | **4** | 真机 `make check -j1` 全量运行 4/4 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 4 | 不变 | 上游四个原始测试均保留并通过 |
| 集成测试 | 0 | 不变 | 无另设上游入口 |
| 鸿蒙特有测试 | 1 | +1 | test_package 链接已安装库并调用加解扰 API |
| **合计** | **5** | **+1** | 上游 4/4、消费者 1/1，分开报告 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 `archives/l/libdvbcsa/1.1.0/test_package/test_libdvbcsa.c`，验证已安装 Conan 包的 API，不计入上游四项测试。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：4/4（100%）
- 新增测试用例通过率：1/1（100%）
- 本轮真机：10.62.201.39:2222，W3 不可变事务 `libdvbcsa-w3-20261010T095900Z` 验证通过，12/12 收据、干净 Conan RC0、上游4/4及消费者1/1；原始日志 SHA-256 `b3372b7bd5f0bccb6250718b28ed02df25bb271ff721cee2474a9c98d205f8d2`。
- CI #80106 首错是 config.status 临时目录的创建权限，不是源码下载。配方只在一次性构建副本精确修复 primary/fallback，使用任务 TMPDIR 和排他 mkdir，知识草稿补充 mktemp 固定0700与外层umask的区别；保留全部测试。

## 补充说明

- 关联 Issue：#3760
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper/build_in_harmonyos:feat/libdvbcsa-1.1.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：旧 `config.sub` 缺少 linux-ohos 识别，最小补丁修复；一次 GNU patch fuzz dry-run 成功但 Conan patch-ng 因上下文空格不一致失败，修正为字节精确补丁后通过真机全量测试。知识草稿说明两个补丁引擎的验证边界。路径 B 四项高难标准均未命中：不依赖私有 OS 接口或工具链，无闭源/特殊调度架构，也无庞大依赖/全量测试成本。CI 和平台 AI 检视以提交后的当前 HEAD 为准。


### 2026-10-13 当前 CI 修复

A release configure shebang and inherited CONFIG_SHELL can select different interpreters. A mksh-only print choice then damages generated Libtool when config.status is run by Bash. Explicitly invoke the declared Bash configure interpreter and keep that interpreter bound in CONFIG_SHELL/SHELL.

当前真机事务 `libdvbcsa-ci-repair-w3-20261013-r2`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `6ad4f9d309cf6b6ef588e78753d71760bfe3dbff1e0034e0ae12bbfa838dea64`。上游 4 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
