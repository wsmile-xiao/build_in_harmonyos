# DRAFT-gulrak-filesystem-1.5.8-hmdfs-file-creation-limit-test-ledger — OHOS/HMDFS 文件创建类平台限制对 filesystem 类库测试的影响

> **Contributor**: pc1-14 | **Status**: DRAFT | **Updated**: 2026-09-06
> **Severity**: medium | **Category**: ohos / hmdfs / filesystem / testing
> **Audience**: 适配文件系统操作类 C/C++ 库（std::filesystem 实现、ghc::filesystem、文件遍历/类型判定库）的执行端

## 问题签名与触发条件

上游测试（Catch2/CTest）中以下用例在 OHOS PC 上失败：

```text
fs.op.create_hard_link - create_hard_link        FAILED（CHECK(fs::exists("bar")) false）
fs.op.copy - copy（create_hard_links 分支）       FAILED（REQUIRE(!ec) false）
FileTypeMixFixture: fs.op.is_block_file / is_character_file / is_fifo / is_socket /
                    is_other / is_regular_file / is_symlink / is_directory   FAILED
fs.op.permissions - permissions                   FAILED
fwd_impl_test（复用上述用例的两段式编译验证）        FAILED
```

触发条件：库在上游测试中创建/判定 HMDFS 不支持的 POSIX 文件类型或依赖精确权限位。

## 根因（OHOS/HMDFS 平台既有能力限制）

对 gulrak-filesystem 1.5.8 实测（cwd 为可写临时目录）：

| 操作 | 命令 | 结果 |
|---|---|---|
| 硬链接 | `ln a b` | `Operation not permitted`（EPERM） |
| FIFO | `mkfifo f` | `Operation not permitted`（EPERM） |
| 块/字符设备 | `mknod b b 0 0` / `mknod c c 0 0` | `Operation not permitted`（EPERM） |
| Unix socket | `python3 socket(AF_UNIX).bind()` | `PermissionError: [Errno 1] Operation not permitted` |
| chmod | `chmod 700 p` → `stat -c %a p` | `760`（权限位归一化，与 POSIX 不同） |

结果：`fs.op.create_hard_link`、`fs.op.copy`（create_hard_links 分支）必然失败；
`FileTypeMixFixture` 无法构造块/字符设备、FIFO、socket 特殊文件，8 个 `is_*` 判定
（含 is_regular_file/is_directory 的 fixture 前置）随 fixture 建立失败；`fs.op.permissions`
因 chmod 位归一化、只读语义不同而失败。fwd_impl_test 是 filesystem 用例的两段式
（fwd/impl）编译复用，同源失败。

## 正确分类与统计（R51 双口径）

- 平台限制项**计入分母、不计入通过**：如发现 209 项 ctest 注册、175 通过、34 失败（均为平台
  限制），全量通过率写 **175/209 (83.7%)**；
- 另列当前配置可执行集合通过率：**175/175 (100%)**（34 项均为平台限制，非库缺陷）；
- 台账逐项映射：源码 TEST_CASE 声明 → CMake 目标 → ctest 注册项 → 实际执行日志 →
  失败原因（平台能力限制 + 实测命令/退出码/errno）；
- **禁止**：把限制项伪写为通过 / 从分母剔除 / 写成库缺陷返工 / 只写"实际执行通过率"替代全量率。

## 附加价值：平台限制转为库行为断言

在 test_package 中加入 HarmonyOS 专项测试，把平台限制验证为库的正确行为——
创建类操作在 HMDFS 上**如实返回 error_code 且不崩溃**（gulrak-filesystem 实测 16/16）：

```cpp
fs::create_hard_link(dir/"hello.txt", dir/"hardlink.txt", ec);
CHECK_MSG((bool)ec, "create_hard_link 在 HMDFS 上如实返回错误码");  // EPERM
fs::create_directory_symlink(dir/"sub", dir/"sym", ec);            // 若支持则为真实 symlink
```

这同时是 R34 实质使用：测试真实调用被测包 API 并断言平台语义。

## 验证（gulrak-filesystem 1.5.8 实测）

- `ctest --output-on-failure`（cwd=/storage/Users/currentUser/tmp/builds/gulrak-filesystem-1.5.8-build）：
  175/209 通过；34 项失败全部归属平台能力限制，附实测证据；
- 鸿蒙专项 `test_ghc_fs.cpp`：`RESULT: checks=16 failures=0`（exit 0）；
- 证据日志：`reports/test-report.md` §2/§3、`reports/conan-verify-report.md`。

## 适用边界与反例

- **适用**：std::filesystem 实现类、文件操作/类型判定为主体的库在 OHOS 的测试诊断与统计。
- **反例/不适用**：普通网络/计算库不涉及文件类型创建；CPU 密集库测试无此限制。
- 与既有条目的差异：E046（chmod 不生效）、E024（AF_UNIX bind 被禁）、E076（fstat/lseek
  对非文件 fd 的 EACCES/EPERM）、E050（HMDFS symlink 跟踪）、E052（config.status 临时
  文件）各自覆盖单点；本候选提供**文件创建类 API 全组合限制清单 + filesystem 库测试的
  双口径统计方法**，combination_novelty / boundary_novelty 成立，可跨库复用。

## R02 补充：未实例化（uninstantiated）分类（ParseAndAddCatchTests 解析限制）

R02 返工复核发现：上游 `test/cmake/ParseAndAddCatchTests.cmake` 第 130 行对 TEST_CASE 名的
正则提取无法处理名称内嵌转义引号的用例——filesystem_test.cpp:376
`TEST_CASE("fs.path.generic - path(\"//host\").has_root_name()", ...)` 因名称含 `\"` 未生成
ctest 注册项（70 源码声明 vs 69 注册/变体）。该用例体仅 WARN 无断言，未实例化不影响真实
通过率，但统计口径必须计为 **uninstantiated（非失败非通过）**，不得用 CTest 汇总数冒充
源码声明数（对应 upstream-test-ledger.md §4/§5 与 R51 双口径要求）。

## 关系字段

- `causes`: E046, E024, E076, E050
- `similar_to`: E046, E024, E076, E050, E052
- `caused_by`: []  `conflicts_with`: []  `prerequisite_of`: []