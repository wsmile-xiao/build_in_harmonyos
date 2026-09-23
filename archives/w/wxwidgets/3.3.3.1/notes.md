# wxWidgets 3.3.3.1 适配笔记

## 版本与范围

- Conan 版本：`wxwidgets/3.3.3.1`
- 上游版本：wxWidgets 3.3.3（适配修订后缀 `.1`，未改变上游源码版本）
- 官方源码：GitHub Release asset `471278068`
- 源码 SHA-256：`81b09d6dd9f1ed9301f8c55a968a488d0491f264dc2bab19a7e407ac67009482`
- 构建系统：CMake
- 交付范围：静态 wxBase 非 GUI 组件；不宣称 wxCore 图形窗口栈已适配

## 启动前检查

- 目标分支：`feat/wxwidgets-3.3.3.1`
- 主仓基线：`2595c9dc958d9ffa1d7d3a90b3d933a82e88d01a`
- 制品仓查重：已有 `wxwidgets/3.2.10`、`wxwidgets/3.3.3`，未发现 `wxwidgets/3.3.3.1`
- Conan 前置依赖：无，W0 通过；仓库预检脚本在当前 main 第 189 行存在未闭合引号，按脚本失败的手动接管规则核对配方 `requires=[]`
- 语言预检：C++ 主体（2582 个源文件中 cpp 1938、c 516），与任务语言 `cpp` 匹配
- 官方资产核验：GitHub API 返回的资产 ID、大小和 SHA-256 与本地下载文件一致

## 历史经验核验

3.3.3 的成功结论来自 HarmonyOS PC 真机原生构建，不能用 macOS 结果替代。
本修订继承其已验证的 CMake 配置、20 个可重放补丁、完整 Catch2 清单和严格的
expected-skip 计数逻辑，但不继承旧版本的 W3、W4 或 CI 通过状态；3.3.3.1 必须重新
完成一次干净的真机 `conan create`。

必须继续遵守的历史结论：

- 强制静态构建并关闭 GUI：`BUILD_SHARED_LIBS=OFF`、`wxBUILD_SHARED=OFF`、`wxUSE_GUI=OFF`。
- 构建完整 console-only 上游测试目标，禁止只跑消费者冒烟测试。
- Catch2 `--list-tests` 对 429 个条目返回 255 是条目数编码，不是测试失败。
- 目标能力不足只能通过已登记的 `WX_EXPECTED_SKIP` 事件计数，未知、重复或损坏 marker 必须失败关闭。
- 补丁使用 POSIX/运行时能力语义，不在补丁中新增 `__OHOS__` 条件宏。
- 真机测试可执行文件与消费者测试程序必须先签名再运行。

## 上游测试申报（R51）

- 上游测试目录：`tests/`
- CTest 注册：1 个 `test_base` 驱动
- Catch2 精确条目：429 个；大小写折叠后 423 个唯一名，6 组合法大小写折叠冲突
- 有序清单 SHA-256：`2214c00249801b8f0b2b1b7b72c6fdf6c00217d32da3a3b777c2d8afabe73ebe`
- 消费者测试：1 个 CMake 测试程序，覆盖初始化、字符串、分词、URI、缓冲区和版本 API，共 6 项断言
- 3.3.3.1 实测结果：待新的 HarmonyOS PC W3 运行后回填，禁止复用 3.3.3 的结果

## 当前验证状态

- 官方源码完整性：PASS
- 补丁静态继承与版本字段更新：已完成
- 补丁三引擎重放：PASS；patch-ng、GNU patch（fuzz 0）、git apply 均为 20/20
- 三份结果树：均为 9776 个文件，聚合 SHA-256 均为 `9ca450197ca9219a59fd265decbce4bda0028be593d60cc7e8fc1851f26c5668`
- W2 静态结构检查：PASS；Conan 本地 inspect 识别 `wxwidgets/3.3.3.1`、`package_type=library`、`requires=[]`
- macOS 补充验证：源码下载、补丁应用和完整编译均通过；测试清单审计按预期停止于 467 个 macOS 条目与 429 个 OHOS 条目不一致，不能替代真机 W3，也不应放宽 OHOS 清单契约
- 真机入口探测：历史 worker `10.62.148.108:2222` 连接超时，未创建或复用任何远端运行目录
- 当前主仓 preflight 的 PF9 会把 R38 要求更新的软件级 `commands.json` 判为“缺版本目录”，而不更新该文件又会触发 PF8 缺版本；这是框架门禁矛盾，本任务未使用绕过参数，提交前需由可用流程确认例外或修复框架
- HarmonyOS PC W3：待执行
- 独立 W4 审计：待执行
- PR/CI：待执行
