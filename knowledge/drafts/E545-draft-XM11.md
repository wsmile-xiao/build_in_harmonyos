# CMake 条件测试恢复前，先审计发布包与标签的源码范围

现象：开启测试、构建成功、CTest 100% 通过，但同版官方 Git 标签还有整套开发测试。

根因：上游使用 `if(EXISTS .../test-dev/)` 决定是否注册开发套件；发布归档省略目录时，这个分支安静地跳过。测试开关只控制现有源码树，不证明完整上游清单。

处理：检查不可变标签的测试入口与真实清单；获取可验证的完整官方归档，按固定提交逐一验证 Git blob 身份；保留上游 CMake 测试入口，并同时验证 CTest 程序数、程序内部逻辑用例数及每项结果。消费者断言单独统计。配方对缺失开发测试入口应明确报错。

本次证据：libxmp 4.7.3 发布归档仅一个 CTest；完整提交 `1e0812137e4f9e15cc026c0c75af82d71d3cb5ad` 的 `test-dev/all_tests.txt` 有 1013 项，完整 CMake 注册两个程序。官方归档 SHA-256 为 `f2ee83c3ec146d5024bcba2a094ba9cf48eebbf9518bca02cf2e7cb139889a43`，3277 个 blob 全部匹配。r4 的额外 Make 入口因缺少 `ar` 失败，整次事务仍是 FAIL；后续完整 CMake 验证必须使用新事务，不能追改旧结果。

复用边界：适用于测试子目录存在性控制注册、发布打包又省略该目录的项目。不适用于仅凭目录名推断测试、必要生成文件缺失的 Git 快照，或把外部应用测试误当当前库测试。完整源码仍须独立构建成功，全部有效测试须执行；不能修改期望结果、排除失败项或用消费者测试替代。

查重增量：`EXISTS` 静默缩减注册的通用现象已有 geographiclib 数据门控和 uvg266 测试框架子模块条目，不重复申报。这里新增的是“同一项目自身测试源码仅被发布打包省略”的决策边界：注入数据、test_requires 或补子模块都无法恢复。仅当同版固定官方标签源码本身能独立构建且每个官方 Git blob 完整一致时，才选择该完整源码输入，保持正式入口并拒绝缺失清单。它不是替换所有发布包的通用建议。libfsntfs 关注捆绑源码/生成文件；E2185 关注未注册工具自检，均不能替代这里的已注册开发套件恢复。

最终验证：正式 finish W3 r1 的原始日志 SHA-256 `85ae574b3461e95b2b4d176d6a2d7e94633e7af90c3d0164b87aa36096fa9c64`。1013命名开发项逐一匹配清单，发布程序内部3个run_test（test.it/test.itz/test.xm）原MD5通过，总计1016/1016；2个CTest程序和1个消费者程序是另外的口径。131消费者断言不计成131测试程序。初始1014混用了“1个发布程序”与“1013用例”，已按源代码/日志纠正；不改原始回执或日志。总finish RC1及旧G1格式误判报告仍保留，不冒充整个流程或worker CI通过。


## 2026-10-13 CI 反例与修复增量

An immutable official tag URL can end in a commit SHA while delivering tar.gz bytes. Conan uses the downloaded filename to choose archive handling, so declare the real filename/container without changing the URL or SHA256.

Do not re-claim generic complete-tag coverage. The new boundary is that a local archive override ending in tar.gz can mask a filename-based unpack failure on the extensionless official CI URL; independently check both source() argument routing and the pinned container identity before claiming reproducibility.

验证：新事务 `libxmp-ci-repair-w3-20261013-r1` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `fea19818afc60855ef0511a942a013ecef1af9e89026f36b76f891d7654644b0`。上游声明 1016 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。
