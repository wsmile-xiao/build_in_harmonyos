# Guile 2.2.7.2 修复记录

## 来源与目标

- 上游源码仍为 GNU Guile 2.2.7；Conan 版本后缀 .2 是仓库 R37 规定的第二次适配修复。
- 以 `archives/g/guile/2.2.7.1` 为构建基线，保留其依赖和上游测试流程。上一版的真机结果只证明上一版，不作为本版验证结果。
- 本版修复消费者测试的假阳性：上一版 `test_package.test()` 捕获所有运行异常并继续成功，导致 `test_probe` 崩溃或命令失败时 `conan create` 仍可能通过。新版本让运行失败正常向 Conan 传播，并实际执行 `guile`、`guild`、`guile-config` 及 C API 探针。
- 修复继承自上一版的 `0006-test-suite-ohos-guile-test.patch`：`sandbox.test` 最后一处 hunk 的两行上下文缩进少一格，无法应用于 GNU 2.2.7 官方源码；已更正上下文并包含文件末尾空行。
- 独立提交前审计指出配方虽然声明 `shared=False`，却始终使用 `--enable-shared --disable-static`。本版明确拒绝未实现的静态库配置；真机已验证的范围仍是默认 `shared=True`。

## 验证状态

2026-09-26 鸿蒙 PC 真机首次 `conan create`、仓库 `conan-verify` 与 `finish ... built` 中的 W3 本地 CI 均成功。正式分支仍须完成提交范围审计：

- 2026-09-23 Mac 静态检查：主配方与消费者配方可由 Python AST 解析；`commands.json` 是有效 JSON；模拟 `./test_probe` 失败时，`test()` 抛错且之前六条消费者命令均已执行。这些检查不等同于 OHOS 构建或运行。
- 从 GNU 官方下载 `guile-2.2.7.tar.xz`，SHA-256 与 `conandata.yml` 相符；全新解包后按顺序用 macOS `patch -p1 --forward --batch` 应用六个补丁，全部退出码为 0。
- 六个补丁保留了上游上下文中的缩进和空行；`git diff --cached --check` 对复制的补丁报告空白警告。需以补丁可应用性和真机编译为准，不为消除警告擅改补丁上下文。
- 仓库当前 `ci/scripts/preflight_check.sh` 由 Bash 解析时报告未闭合引号；本机也未安装 OHOS 版 Conan。真机依赖检查应逐项用 `conan download <引用> -r=ohpcd --only-recipe` 执行，不把此脚本失败解释为依赖缺失。

1. 已确认 `gc/8.2.12`、`gmp/6.3.0`、`libffi/3.4.4`、`libunistring/1.0`、`libtool/2.5.4` 均能从 ohpcd 制品仓下载 recipe。
2. 首次真机 `conan create` 成功，执行了上游 Automake 与分成四段的 Scheme 测试。Automake 稳定面 standalone 36/36、VM 20/20、LALR 19/19，合计 75/75 通过。`conan-verify` G2 的 174 个 `.test` 文件分为 48/48/62/16 四段，依次得到 2,711/31,214/7,111/756 次 pass，合计 41,792 pass、0 fail、10 expected failures、594 unresolved、1 untested、65 unsupported、0 errors。这些合计与 `.1` 版笔记中记录的既有测试基线相同；unresolved、untested 和 unsupported 仍须如实保留，不能计作通过。
3. 消费者测试已真实执行 `guile`、`guild`、`guile-config` 命令和 C API `./test_probe`，全部退出码为 0，探针打印 `(+ 1 2) = 3` 与 `PASS`。先前 Mac 静态反向检查证明探针失败时 `test()` 会抛错；仓库 CI 反向门禁仍待运行。
4. 打包时 `exec_prefix=/` 替换未匹配，Conan 给出非致命 warning；GC 运行时给出 `PT_GNU_RELRO` warning。后续核对打包的 `.pc` 文件及安全扫描结果，再判断是否需要修复。
5. 仓库 `conan-verify` 已在鸿蒙 PC 真机通过 G0-G4 与 L2/L4/L5，生成 `reports/conan-verify-report.md`。流程自动写出的 `status: partial` 是进度草稿。版本 manifest 与 `reports/test-report.md` 已据真机日志补齐，并同步到 PC 正式分支。未 upload 前不能标记 `published`。

## W3 本地 CI 与收尾状态

- `finish guile 2.2.7.2 built` 的 W3 `setup.sh` 与 `build_and_test.sh` 已在鸿蒙 PC 真机通过；后者强制重建 `guile/*` 并再次运行上游测试与消费者探针，完整日志保留于本机 `reports/w3-local-ci.log`，不加入源码 PR。
- 本机 Fork 浅克隆使 `junk_check` 默认退回全仓扫描，碰到与 Guile 无关的既有 `cloog`、`kics` 运行标记。用 `git diff --binary upstream/main HEAD` 生成准确 PR 差异并设置 `JUNK_PR_DIFF` 后，JC1–JC6 全部通过（16 个 Guile 文件）；W3 随后通过。未删除或提交其他软件的标记。
- `finish` 整体退出码为 1：W3 之后的全仓知识检查指出既有 E219/E253/E305 条目字段缺失，摘要生成器读取既有 `qpdf/12.3.2/manifest.yaml` 时发生类型错误；提交预检另提示缺少 `packaging/` 与 `.staging-verified`。这些并非 Guile 的 Conan 构建或 W3 失败。源码 PR 不包含运行标记或二进制打包产物，正式发布的上传由合并后的 CI 处理。

`archives/l/libXext` 在大小写不敏感工作树显示的两处修改来自与 `libxext` 路径碰撞；它们与本任务无关，不得暂存或提交。

## W4 Pre-PR 审计

2026-09-26 由独立子任务按 `templates/audit-prompt.md` 完成审计，输入以 `upstream/main` 为基准（16 个变更文件）。结论 **pass**：P0=0、P1=0、P2=1、P3=7。欺骗类五项（R34/R9/R8/R19/R40）、结构/合规（W2 原子性、R37 版本号、R32 平台判断、conandata 无 `file://`、补丁无 `__OHOS__` 注入）与 R51 测试三步法（四处测试数字一致且可加和还原）均通过。审计结果存于 `reports/audit-result.json`。

- P2（已处置）：打包的 `.go` Scheme 字节码取自上游 tarball `prebuilt/` 而非本机编译（`guild compile` 在真机触发 SIGTRAP，配方 docstring 已声明、`make -k` 容错）。本笔记与 `reports/test-report.md` 已补记该产源披露；SIGTRAP 根因待后续版本跟进。
- P3×7 为建议项（configure 补丁口径、conandata 描述句式、test_package 文件头、CC 环境变量优先级、runner 布局回退、MANIFEST 元占位写法、FAIL→UNSUPPORTED 重分类风险），不阻塞；其中重分类风险已在 test-report"已知限制"中如实声明。配方代码不再改动，保持与 W3 验证时一致。
- 提交时 preflight 说明：本地以官方 `main`（a2798f3a1）为基准复跑 PF1–PF9，仅 PF9 对软件级 `archives/g/guile/README.md`、`commands.json`、`manifest.yaml` 报"缺版本目录层"。这三处为仓库既有软件级元数据（guile 首个合入 PR 20b7fc911 与 checkit-tiff 等先例均含此层文件；PF8 又要求 CLI 包具备软件级 commands.json），属 PF9 通配规则与上游惯例的口径冲突，按工具提供的 `OHC_PREFLIGHT=0` 逃生通道跳过并在本 PR 说明；其余 PF 项全部通过。

## 打包与 staging 标记

- `packaging/guile-2.2.7.2-ohos-aarch64.tar.gz` 由本机 Conan 缓存包（`guile/2.2.7.2@ohpcd/stable`，W3 重建产物）打包生成，仅本地留存，不入源码 PR。
- `.staging-verified` 依据 W3 消费者检查证据落盘（`guile`、`guild`、`guile-config` 及 C API 探针均真实执行、退出码 0，见 `reports/w3-local-ci.log`）；OpenDesk Agent shell 受 HMDFS/链接器命名空间限制无法直接 exec 缓存内二进制复跑，该限制不影响已在用户终端环境完成的 W3 验证结论。

## 最终状态

编译结束：`guile/2.2.7.2` 已在鸿蒙 PC 上构建为 `built`，Conan 验证、W3 本地 CI 与 W4 Pre-PR 审计均通过，packaging 与 staging 标记已按上节说明落盘。`finish` 的整体退出码为 1 的历史原因与限制见前文；尚未发布制品，正式发布上传由合并后的 CI 处理。
