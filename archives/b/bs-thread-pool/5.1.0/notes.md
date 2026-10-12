# bs-thread-pool 5.1.0 适配笔记

## 编译环境
- 构建系统: header-only（单头文件，无 CMake/autotools/meson）
- 上游: https://github.com/bshoshany/thread-pool ，tag v5.1.0（2026-01-03）
- 源码包: https://github.com/bshoshany/thread-pool/archive/refs/tags/v5.1.0.tar.gz
- sha256: 54378fb9cbeaee72996d3f8761469c43bb7dd2d4b07faec6d29a68277bd91a51（本地下载实测）
- 编译器: 真机 PATH/环境中的可用 C++ 编译器经 --version 探针选中（C++17；不再硬编码 /data/service/hnp/bin/clang++，该路径在真机 /bin/sh 下报 inaccessible）
- 状态: built（待真机 rule4 预检后由 HMBS 提交）

## 上游结构
- `include/BS_thread_pool.hpp`：唯一需要的头文件（v5.1.0，2026-01-03）
- `modules/BS.thread_pool.cppm`：C++20 模块封装（本次只用头文件路径，不启用模块）
- `tests/BS_thread_pool_test.cpp`：4221 行自定义测试程序，无 ctest/gtest 注册
- `scripts/compile_cpp.py`：上游编译脚本，在 OHOS 上 `platform.system()` 返回 `HarmonyOS` 导致自动探测报 `No compiler found!`（见 knowledge/drafts/DRAFT-bs-thread-pool-5.1.0-ohos-python-platform-system.md），配方内不使用该脚本，改用显式编译器路径直接编译

## 上游测试盘点
- 测试入口: `tests/BS_thread_pool_test.cpp`，59 个 `check_*` 函数，145 处 `check(` 调用点
- 运行方式: `clang++ -std=c++17 -I include tests/BS_thread_pool_test.cpp -o bs_thread_pool_test -pthread` 后 `NO_COLOR=1 ./bs_thread_pool_test tests stdout`
- `tests stdout` 的含义: 有参数时仅开启指定 flag（tests=true, stdout=true），关闭 benchmarks/deadlock/plot/log，避免长时间基准和日志文件
- 原生扩展默认关闭: 不定义 `BS_THREAD_POOL_NATIVE_EXTENSIONS`，上游自动跳过 affinity/priority 检查并打印 NOTE，避开 musl 缺 `pthread_*affinity_np` 问题
- 计数口径: 运行时 `SUCCESS: Passed all N checks!` 单一确定性来源；静态 `check(` 计数会低估（循环展开），不做字符串数数或减法推导
- 历史证据: 2026-09-05 OHOS PC aarch64 上显式 `-c clang++` 跑 C++17 header 全量 208/208 checks 通过

## 配方要点
- `package()` 只拷贝 `include/BS_thread_pool.hpp` + `LICENSE*`，`package_id()` 清空为单一 ID
- `build()` 内编译并运行上游标准套件，解析 SUCCESS/FAILURE 行后输出 `HMBS_UPSTREAM_TEST_RESULT`（framework=custom），失败即抛异常阻断；编译器经存在性+`--version` 探针逐个验证（真机 208/208 通过）
- `test_package` 用 `generate()` 内探针到的可用编译器覆盖 `CMAKE_CXX_COMPILER`（profile 默认 `/data/service/hnp/bin/clang++` 在真机报 inaccessible，CMake configure 失败），不改测试口径
- `package_info()` 置空 bindirs/libdirs，`system_libs=["pthread"]` 仅在 `os in ("Linux", "OHOS")` 时声明，`cmake_file_name`/`cmake_target_name` 为 `bs-thread-pool`/`bs-thread-pool::bs-thread-pool`
- 无补丁: 头文件为纯 C++17 标准库实现（thread/mutex/future/functional），无需 OHOS 适配补丁

## 消费者测试
- `test_package/test_bs_thread_pool.cpp`: 6 项真实 API 检查（thread_count/submit_task/detach_task/detach_loop/submit_blocks/submit_sequence），打印 `PASS: X/Y checks passed.` 单一汇总行
- `test_package/conanfile.py` 解析该行输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=6/passedCount=实际通过数），ctest 失败即阻断

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `compile_cpp.py` 在 OHOS 报 `No compiler found!`，且初版配方误用 `tools.build:compiler_executables:cpp` 触发 `ConanException: does not exist in configuration list` | `platform.system()` 返回 `HarmonyOS`，不在脚本支持之列；Conan 2 该 conf 为 dict（`tools.build:compiler_executables`），`:cpp` 后缀键不存在 | 配方内不用该脚本，新增 `_detect_cxx_compiler()` 读 dict conf（cpp/cxx/c++）→ HMBS_CXX/CXX/CONAN_CXX → which(clang++/c++/g++)，`_detect_shell()` 兼容 CONFIG_SHELL/SHELL |
| 2 | Windows 检出主线遇到 `gama` 补丁文件名含回车及 `libXext/libxext` 大小写冲突 | 上游存在 Windows 非法文件名与大小写仅差目录 | 本机用 sparse-checkout（ci/docs/knowledge/templates/.gitcode/scripts/archives/b/bs-thread-pool）保持工作树干净，不碰冲突路径 |
| 3 | 上游无标准测试框架，无法用 ctest/gtest 口径 | 自定义 harness | `upstream_test_count_method: auto`，总数 208 以运行时 SUCCESS 行为准，真机复验 |
| 4 | 真机 test_package 编译失败：`BS_thread_pool.hpp:695 loop_task::operator()` 报 `no matching function for call`（2026-10-10 预检，上游 208/208 已通过） | 消费者测试把 `detach_loop` 当 `detach_blocks` 用：传了 `(a,b)` 双参 block 风格 lambda，而 v5.1.0 的 `loop_task` 以 `(*loop_ptr)(i)` 单索引调用（`block_task` 才以 `(start,end)` 调用，见头文件 `struct block_task`/`struct loop_task`）。上一周期三次编译器探针修复只解决了 build()/generate() 的编译器路径问题，本轮 test_package 已进入编译阶段说明探针有效，失败域已变为测试代码 API 误用 | `test_bs_thread_pool.cpp` 第 4 项改用单参 ` [&](std::size_t i){ sum.fetch_add(vals[i]); }`，与 `detach_loop` 单索引语义对齐；`submit_blocks` 双参与 `submit_sequence` 单参保持不变（经头文件核对正确）。工作树保持未提交，待 HMBS 真机复检 |
| 5 | 真机 evidence 轮 incomplete：上游 208/208 通过但 `HMBS_TEST_PACKAGE_RESULT discovered=6 passedCount=0` + `consumer test summary line not found`，ctest 仅用 0.05s（2026-10-10T05:04Z 预检） | `test()` 用 `ctest --output-on-failure`：该标志在全通过时抑制单测 stdout，输出里根本没有 `PASS: X/Y checks passed.`，正则必然落空造成假失败；且 except 分支无 emitted 守卫导致同一标记重复输出两次。日志证据：`Total Test time (real) = 0.05 sec` 紧接两次相同 RESULT 行。上一周期三次 RegionError 为模型调用环境故障、与代码无关，本轮首次进入 evidence 失败域，改走 harness 路线而非编译器探针 | `test_package/conanfile.py` 改跑 `ctest -V`（始终回显单测 stdout，仍只解析 PASS 单一确定性行，不做字符串数数/减法），`command` 字段同步为 `ctest -V`，test_package/MANIFEST.yml 同步；引入 `emitted` 守卫保证标记只输出一次。工作树保持未提交，待 HMBS 真机复检 |

## 验证结果
- 本轮为工作树准备轮，未做真机预检；`conan create` 与测试输出待 HMBS 后台真机验证后回填
- 本地仅做配方语法与 tarball 结构审计，未在本机运行 conan（按任务守则，W3 改为真机执行）

## 交付物
- `archives/b/bs-thread-pool/5.1.0/` 下 conanfile.py/conandata.yml/manifest.yaml/notes.md/test_package/
- PR 草稿见 `.hmbs/pr-body.md`（测试数待真机 evidence 轮填写）
