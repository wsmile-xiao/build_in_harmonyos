# skiparray 0.2.0 适配记录

## W0/W0b/R47

- 任务语言为 C，源码主体为 C，语言预检通过。
- W0 依赖核验：生产库没有外部依赖；上游测试通过 pkg-config 依赖 `libtheft`，但 `theft/0.4.5@ohpcd/stable` 在本地和 ohpcd 均未找到。
- 官方 tarball SHA-256：`05ba00503e3c0974dae808ce1b92d759a1ad37bf39e43c057f25cef5442024d6`。

## 上游测试取证

- 直接运行 `make CC=/data/service/hnp/bin/clang test` 时，核心三个源文件可以编译，但测试编译阶段报 `Package libtheft was not found` / `theft.h` 缺失。
- 上游测试注册宏静态计数为 25，完整运行汇总无法开始；不能把核心库编译成功或消费者测试通过写成上游 25/25。
- 按 R36 不使用 `--build=missing`，不把 theft 源码、recipe 或 dummy 依赖捎带进 skiparray PR。

## Conan 包与消费者验证

- recipe 不声明未发布的 test-only 依赖；直接用 OHOS profile clang 编译 `skiparray.c`、`skiparray_fold.c`、`skiparray_hof.c` 为 `libskiparray.a`。
- test_package 真实链接 `skiparray::skiparray`，执行插入、计数、member/get、first/last、forget、pop 和 free 共 13 项检查。

## 路径 B 判断

- 本任务走路径 A+B：A 交付核心库和真实消费者；B 固化“未发布的 test-only Conan 依赖必须阻塞完整上游测试，不能用偷带依赖/假测试绕过”的可复用证据。
- 该 B 草稿包含错误签名、根因、W0 二次验证、可复现核心构建、适用边界和禁止策略；若后续发布 theft，应按精确版本重新启用完整上游测试并更新结果。

## 发现与知识

- ✅ `theft/0.4.5` 是上游测试专用依赖且尚未发布；核心库可以独立构建，但上游完整测试必须单独标记为阻塞，不能把消费者测试结果替代上游测试结果。
- ✅ 该经验已关联草稿：`knowledge/drafts/DRAFT-unpublished-test-dependency-blocks-upstream-tests.kv`。

## 对话记录

### 对话 #1（2026-09-03）

- 先确认 `theft/0.4.5` 未发布，再分离生产库构建与测试依赖；没有因为测试依赖缺失而宣称全部上游测试通过。
- 记录为部分适配候选，不按语言不匹配处理，也不伪造路径 B 的成功测试数字。

## 对话记录（续）

### 对话 #2（2026-09-05，theft 发布后解除阻塞）

- 复核 `conan download theft/0.4.5 -r ohpcd --only-recipe`：已发布，revision `46372da4dacaca771da48de53bf6661d`（2026-09-02）。
- 配方新增 `upstream_tests` 选项（默认 False）：生产默认构建零外部依赖、依赖图不含 theft；`-o "skiparray/*:upstream_tests=True"` 时按 R36 以已发布的 `theft/0.4.5` 作为 test-only 依赖，`can_run` 时编译上游 9 个测试源文件并运行 Greatest 套件；pkg-config `libtheft` 以 Conan 包 include/lib 目录显式替换，链接加 `-lm`。
- 设备端验证（CONAN_HOME=~/tmp/ch/home-auto-skiparray-upstream，profile ci/conan/profiles/ohos-aarch64）：
  - `conan create . -o "skiparray/*:upstream_tests=True" --build=skiparray/* --build=theft/*`：上游 Greatest 套件 **Total: 67 tests, 67 passed, 0 failed, 0 skipped**（110.7s，4,682,969 assertions；basic 24、builder 8、fold 25、hof 2、integration 2、prop 6）；依赖 theft 自身套件 384/384 通过（其 OHOS RLIMIT_CPU 跳过补丁由该包自带）；消费者 test_package 1/1 通过。日志：设备 ~/tmp/uc2/skiparray-7926/create.log。
  - 默认选项 `conan create --build=skiparray/*`：包构建 + 消费者 1/1 通过，确认生产依赖图不含 theft。
- 静态/运行口径：上游静态注册 25 处 `RUN_TEST(p)`；参数化循环后运行时 67 个用例。适配后合计 = 上游静态 25 + 消费者 1 = 26，全部通过。
- 路径 B 草稿按 fallback 路径闭合：依赖发布 → test-only 接入 → 完整上游套件重跑，证据同步更新。

## 结束

最终状态: built（上游完整测试已补齐：运行时 67/67 通过）
---

**编译结束**: 2026-09-05 00:34
**最终状态**: built
