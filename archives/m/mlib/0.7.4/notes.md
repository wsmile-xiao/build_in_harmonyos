# mlib 0.7.4 — 适配笔记（OHOS aarch64）

## 来源核验
- 官方仓库：https://github.com/P-p-H-d/mlib
- 正式标签：`V0.7.4`（git tag 指向 commit `f4e3d9cd4c13f7b639b67cd18ad3a2ffe078ac09`）
- 源码 tarball：`https://github.com/P-p-H-d/mlib/archive/refs/tags/V0.7.4.tar.gz`
- SHA-256：`dff01fe0635f6d4027abea736044976fff1b8ba9f8d930ca3f7e0a595a5d3875`（tarball 实测）
- 许可证：BSD-2-Clause（LICENSE，Copyright (c) 2017-2025 Patrick Pelissier）
- 平台任务：7314（`mlib/0.7.4`，依赖活动 activity_id=6）

## 结构
- 纯头文件库：34 个 `m-*.h` 位于 tarball 根目录，互相以裸名 include（m-array.h → m-core.h 等），需整组打包
- 无库构建系统：根 Makefile 仅驱动 tests/doc/example（无 install 规则、无 CMake/configure）
- C99 主体；check-*.cpp 为 C++ 对照测试（可选 STL 对比目标 check-stl，非主测试目标）
- 依赖：无任何第三方依赖（仅标准库 + pthread，pthread 仅测试/并发模块运行期使用）

## 分支基线说明
- 分支 `feat/mlib-0.7.4` 基于 fork `origin/main`（9b49d7903）而非 upstream/main：框架 W3 的 JC6 用 `git diff origin/main...HEAD` 判定 PR 原子性，fork main 落后 upstream main 时会把上游新合入的其他包算进 diff 造成多包假阳性（thread-pool 4.1.0 同场景实证）；fork main 是 upstream main 的祖先（`git merge-base --is-ancestor` 实证），PR 与官方 main 的三点 diff 仍只含本包，不影响 PR 内容。

## 上游测试（四维账本）
- 测试目录 `tests/`，m-tests 自写框架（非第三方框架，无 CTest 注册层）：
  - `test-*.c`：32 个程序，`static void testXxx()` 函数为用例注册单元，main 串行调用，断言失败即 abort
  - `except-*.c`：5 个程序（M_TRY/M_THROW 异常语义）
  - `fail-*.c`：3 个程序（预期编译失败，编译失败=通过）
  - `check-*.cpp`：11 个 C++ STL 对照程序（独立目标 `check-stl`，非 `check` 组成部分，需 sanitizer）
  - `tgen-*.c`：生成变体源码，不在 check 目标内
- **N_static（静态声明）= 211 + 5 + 3 = 219**：C 测试函数 211 个（`grep -cE '^static void test[a-zA-Z_0-9]*\('` 32 个 test-*.c 逐文件统计，含 test/test1/test2 短名形态）+ except 5 个程序 + fail 3 个程序
- **N_executed / 失败 / 跳过**：见下方运行矩阵（运行日志 `check.log` 与逐程序 `*.log`）

## 运行矩阵（设备实测，clang 15.0.4 OHOS）
| 轮次 | 配置 | 结果 |
| --- | --- | --- |
| 1 | `make check CC="clang -std=c99" XCFLAGS="-Wno-everything"`（32 test-*.c + 5 except-*.c + 3 fail-*.c） | **RC=0，`All tests passed`**：37 个运行程序全部退出码 0；fail-* 98 个编译预期失败子检查全部符合预期（71 OK + 27 WARNING，0 ERROR——WARNING 为编译按预期失败但报错非 M_LIB_ 前缀，make 判定通过；OK/WARNING 分文件：chain-oplist 25+1、incompatible 1+25、no-oplist 45+1） |
| 2 | `make check-stl`（C++ STL 对照，11 程序，需 ASan/LSan sanitizer） | 未执行：独立辅助目标，不属上游 `make check` 口径，如实记录为未执行项 |

- 运行证据：`~/tmp/uc2/mlib-0.7.4/dl/src074/mlib-0.7.4/tests/check.log`（含 37 个 `./xxx.exe` 运行行与 fail-* 逐项 OK），完成标志 `check.done` 内容 `RC=0`
- 执行口径：执行项 219/219（100%）；无失败、无跳过

说明：tests/Makefile 硬编码 `CC=cc`/`CXX=c++`，OHOS 设备无 `cc`/`c++`（init-build 环境检查亦提示），以 make 变量覆盖为 clang/clang++ 直传，未修改上游文件；`-Wno-everything` 仅压上游自带的 -Werror 级告警噪声，不改变语义。

## 语言预检
`ohc-run.py lang-preflight` 判定 cpp 匹配通过（c↔cpp 兼容族，milestone=lang_checked）。

## 路径 B 判断（结论：不走 B，纯路径 A）
- 本任务零补丁、零上游修改、构建流程零报错，未产生新错误签名与跨仓库复用知识；header-only C 库打包模式已在库内多例沉淀，无新增价值。按纯路径 A 交付。

## test_package（消费者验证）
- Conan L1：CMakeDeps + find_package（C99），消费者程序 `test_mlib.c`（1 个程序，9 项断言）：
  1. m-array 推入 100 元素、size/get 抽查、`special_sort` 升序全序校验；
  2. m-list 推入 50 元素、LIFO pop_back 顺序校验、empty_p；
  3. m-dict 50 个字符串键值对 set_at/get/size/覆盖校验；
  4. m-string 格式化构造、equal_str_p、size 校验。
- `test()` 经 bash 包装执行二进制（OHOS mksh 直接 exec 受限的既有规避模式），退出码 0 判定通过。
- 消费者 API 口径经设备试编译迭代确认（get 返回指针、sort 需显式 cmp、pop_back 为 (out,list) 双参）。

## 未执行项
- `make check-stl`（11 个 C++ STL 对照程序）：独立辅助目标，需 -fsanitize=address,undefined,leak 的 C++ 环境，不属于上游 `make check` 测试口径；未执行，不影响 check 全量通过的结论。

## 后续
- 状态：built（2026-09-12 finish 收尾）
- 无 commands.json（纯库，无命令行产物）
