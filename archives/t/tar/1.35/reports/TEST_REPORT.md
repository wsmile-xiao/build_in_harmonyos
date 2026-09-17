# tar 1.35 上游测试双口径台账（R01）

任务：tar-1.35-r01-pc3-13-20260911T082155Z
执行环境：aarch64（OHOS 交叉工具链 clang 15.0.4，主机 aarch64 + musl loader 可本机运行测试）
测试框架：GNU autotest（tests/testsuite，由 testsuite.at + 各 .at 生成）

## 统计口径（双口径）

| 口径 | 数值 | 说明 |
|---|---|---|
| source_declared_total（源码声明总数） | 244 | `./testsuite -l` 注册的全部独立测试组（224 个 .at 文件 + testsuite.at 内联生成，AT_SETUP 宏展开后） |
| configured_executable_total（当前配置可执行总数） | 244 | 当前 OHOS 配置下全部注册并实际执行，无未实例化项 |
| executed_passed_total | 120 | 实际通过 |
| failed | 93 | 实际失败（详见 failed-list） |
| skipped | 31 | 运行时跳过（见 skipped-list） |
| **全量通过率** | **120/244 = 49.2%** | 通过数/源码声明总数（未运行/跳过/失败均计入分母） |
| 实际执行通过率 | 120/213 = 56.3% | 通过数/实际执行数（排除 31 个运行时 skip） |

## 失败分类（93 项）

| 类别 | 数量 | 根因 |
|---|---|---|
| UIDRANGE | 82 | `tar: value 20001006 out of uid_t range 0..2097151`：当前执行用户 uid 20001006 超出 ustar/v7 头字段 21-bit octal 容量（create.c `UID_TO_CHARS` 失败）。这是执行环境 uid 空间特性，非 tar 适配缺陷——默认/gnu/posix 格式均正常（base-256/xheader 存储大 uid，已验证 tar cf 默认格式 exit 0），仅测试强制 `-H v7`/`TEST_TAR_FORMAT=v7|ustar` 时触发 |
| XATTR | 9 | `tar: dir: Warning: Cannot fgetxattr: Invalid argument` / `getfattr: getxattr failed: Invalid argument`：HMFS 文件系统 xattr 语义（dir 上 fgetxattr 返回 EINVAL），平台文件系统特性 |
| TIME | 1 | `touch: bad date ...9999999999`：测试工具 touch（toybox 0.8.12）不支持纳秒时间戳，测试环境工具限制 |
| OTHER | 1 | 058 xform03：`--xform` 硬链接目标变换，v7 格式下归档创建同样受 uid 范围影响（stdout 为空，期望 t/dir/c/b） |

失败恢复条件：在 uid ≤ 2097151 的普通 POSIX 用户下运行 testsuite（v7/ustar 字段可容纳），或在支持完整 POSIX xattr 语义的文件系统（ext4/tmpfs）上运行 xattr 类测试。

## 逐批运行结果（命令、日志）

- 批次 1-80：`./testsuite 1..80` → 29 ok / 46 fail / 5 skip → logs/08-batch-1-80.log
- 批次 81-170：`./testsuite 81..170` → 55 ok / 24 fail / 11 skip → logs/09-batch-81-170.log
- 批次 171-200：`./testsuite 171..200` → 17 ok / 10 fail / 3 skip → logs/10-batch-171-200.log
- 批次 201-244：`./testsuite 201..244` → 19 ok / 13 fail / 12 skip → logs/11-batch-201-244.log
- 注册清单：`./testsuite -l` → logs/07-testsuite-list.txt
- 每批均在 `cwd=/storage/Users/currentUser/tmp/builds/tar-1.35.work/tests`、`exit_code=0/1`（有失败时 testsuite exit 1）
- 完整 SHA-256：logs/sha256sums.txt

## 逐项映射说明

源码声明（tests/*.at 内 AT_SETUP）→ m4 展开生成 testsuite → 注册为独立测试组（`testsuite -l` 244 项）→ 按编号分批实际执行（`./testsuite N`）→ 结果写入 testsuite.log 与 testsuite.dir/<N>/testsuite.log。所有 244 项均为独立上游用例（GNU tar 官方 autotest），无框架宏误计；skipped 项为 testsuite 内部 `AT_SKIP_IF`/exit 77 判定（缺工具、只读目录、超大文件等），均计入分母不计通过。

## 结论

上游测试全量通过率 120/244（49.2%）。失败中 82 项为执行环境 uid 超 ustar/v7 字段容量的平台特性（默认格式全部正常），9 项为 HMFS xattr 语义，1 项为 touch 工具限制，1 项为 v7 格式下 xform 联动。已在当前 task_id 内如实枚举、全量执行并分类，未伪造、未跳过未运行项。
