# fastconstmap 0.9.0 适配记录

上游 v0.9.0 是 setuptools 构建的 Python C11 扩展，源码包 SHA-256 为 `d1564b621f3fba4ebee07acd47caa2c1b4d535fdc63aa23bc5c3b5db87fc0dcf`。Conan 依赖只有已发布的 `python/3.12.9`。配方从该依赖动态发现 Python 头文件、libpython、site-packages 和编译器；直接编译上游声明的两个 C 源文件，避免未声明的 setuptools 构建工具依赖。

## 测试统计

统计单位是 pytest 测试函数，使用 AST/pytest 发现清单复核：上游共 56 项（`tests/test_constmap.py` 44 项、`tests/test_shared_memory.py` 12 项）。适配后未修改上游测试；test_package 另有 2 项独立消费者断言。最终执行必须满足：上游 `TOTAL=56 PASS=56 FAIL=0 SKIP=0 NOT_RUN=0`，消费者 `TOTAL=2 PASS=2 FAIL=0 SKIP=0 NOT_RUN=0`。

## OHOS 验证

扩展模块在 package 最终复制后由 profile/环境提供的 `binary-sign-tool` 签名并恢复可执行权限；test_package 使用 Conan `python/3.12.9` 解释器。pytest 作为测试工具由官方 PyPI HTTPS 下载固定版本及依赖，逐个校验 wheel SHA-256 后安装到一次性 test-only 目录，不修改全局 Python。pytest 临时目录由测试代码从可写候选中动态创建并写探针，随后以显式 `--basetemp` 传入；这样可绕过 HMDFS 挂载所有权元数据与活动 UID 不一致导致的 pytest 共享根目录拒绝，测试结束后清理临时目录。

设备验证命令：

```sh
conan create archives/f/fastconstmap/0.9.0 \\
  --build='fastconstmap/*' \\
  -pr:h=ci/conan/profiles/ohos-aarch64 \\
  -pr:b=ci/conan/profiles/ohos-aarch64 \\
  -s:h os.version=6.0 -s:b os.version=6.0 \\
  -s:h compiler.cppstd=17 -s:b compiler.cppstd=17 \\
  -s:h compiler.libcxx=libc++ -s:b compiler.libcxx=libc++
```

原始日志：`$HOME/tmp/fastconstmap-0.9.0-conan-create.log`（最终提交对应的设备实跑，退出码 0；输出含 `56 passed`、`CONSUMER_TESTS TOTAL=2 PASS=2 FAIL=0 SKIP=0 NOT_RUN=0` 和 `UPSTREAM_TESTS TOTAL=56 PASS=56 FAIL=0 SKIP=0 NOT_RUN=0`；运行耗时随设备负载变化）。pytest 版本固定为 8.3.5，依赖 wheel 在 test-only 目录中安装并校验，缺少 curl/下载源时明确失败而不伪报通过。

官方 CI 运行 #39300 暴露了 CI 镜像没有 pytest 且 Conan Python 的 `_ssl` 不可用；固定 wheel 下载方案修复了测试工具闭环，但 #39332 又显示 HMDFS 挂载的目录所有权元数据与活动 UID 不一致，旧的严格 UID 检查无法选出临时目录。现改为对动态创建目录执行写探针并传入显式 `--basetemp`，避免 pytest 的共享根目录所有权检查。随后 #39353 在测试前的 G0e 阶段发现 CI checkout 根目录有未被最终 SHA 跟踪的 `test_file.txt`，因此在测试开始前被白名单门禁拦截；本地 `git ls-tree -r HEAD` 已核实该文件不存在，属于 CI 工作区污染而非配方变更。已再次 `/rebuild`，需以新构建确认。

## 路径 B

本次沉淀的是可跨 Python C 扩展复用的 Conan Python ABI、动态工具发现、OHOS ELF 签名/权限和测试运行环境组合方案，不是孤立源码补丁。知识草稿：`knowledge/drafts/E543-draft-DF80.kv`。
