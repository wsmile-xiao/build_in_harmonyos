- **三方库名称**：lr（"list files, recursively" —— 递归列出文件的命令行工具，作者将其定位为 ls(1)/find(1)/stat(1)/du(1) 常用能力的合集：一次遍历整棵树、按名称排序输出相对路径、C 风格过滤表达式、自定义输出格式、计算目录大小）
- **上游版本**：1.5.1（上游 tag `v1.5.1`，NEWS.md 记录发布于 2020-01-18）
- **上游仓库地址**：https://github.com/leahneukirchen/lr （源码取官方 tag 归档 `https://github.com/leahneukirchen/lr/archive/refs/tags/v1.5.1.tar.gz`，官方 HTTPS 源；sha256 `3c9337b9d924f2318083edc72fa9dfcf571a4af2a411abf57ad12baa5e27cc4a`）
- **适配路径**：路径 A（基础适配，零补丁）
- **使用知识库**：无正式条目命中（G0 预查询因上游为纯 Makefile、构建系统未被识别为 cmake/autotools 而跳过；零补丁、零依赖、零编译错误，未触发知识图谱引擎匹配）。可复用经验已沉淀于版本级 `archives/l/lr/1.5.1/manifest.yaml` 的 `knowledge_gained`（9 条），其中三条对其他包同样适用：`conandata.yml` 注释中放额外 URL 会被 CI 的镜像重写/预下载步骤污染成畸形地址；lr 的字符串字面量不支持反斜杠转义；断言的期望值不能取自被验命令自身的输出（详见版本级 `notes.md` 问题表 #5/#6/#7/#9/#10/#11）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 tarball 不含任何测试：`tar tzf` 共 14 个条目 = 12 个普通文件 + 2 个目录项（`lr-1.5.1/`、`lr-1.5.1/contrib/`），即 LICENSE、Makefile、NEWS.md、README.md、`_lr`、contrib/{lr.el,lr.vim,lrls,lrocate}、lr.1、lr.c、lr.png，无 `tests/` 目录 |
| 集成测试 | 0 | 无 `test`/`check` 目标：`grep '^[a-zA-Z_.-]*:' Makefile` 只有 `all:`、`clean:`、`install:`、`FRC:` |
| 其他测试 | 0 | 无 CMakeLists.txt / meson.build / configure.ac，ctest / meson test / pytest 无可枚举注册项；解压目录 `find . -iname '*test*'` 命中 0；上游 README 的 Installation 一节仅 `make all` / `make install` |
| **合计** | **0** | **上游确实不携带任何测试用例**（清点证据逐条登记于 `test_package/MANIFEST.yml` 的 `upstream_test_inventory_evidence`，不是"没环境跑不了"式推断） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游为单翻译单元（lr.c），无可拆分的单元测试 |
| 集成测试（消费者视角行为回归） | 43 | **+43（新增）** | `test_package/test_lr.sh`（A01–A43）：在一次性 fixture 目录树上真实执行**安装后的** lr 二进制，断言见下节；`conan test` 内 43/43 通过 |
| 鸿蒙特有或与平台语义相关的断言（含于上 43 条） | 4 组 / 7 条 | 新增 | A35 `%Y` 返回文件系统名且**排除纯数字回退**（上游 `fstype()` 查不到挂载表时打印设备号，故只判"非空"恒真；真机得 `hmdfs`，证明 musl `setmntent`/`/proc/mounts` 分支可用）；A19 模式说明符与 `mode =` 过滤自洽并配 `mode = 000` 负向对照（HMDFS 不强制 `chmod(2)`）；A16/A26/A30/A32 的期望值由 `wc -c`/`awk`/`find` 从文件系统独立反查，不写死 umask 与平台常量；A42 `$NO_COLOR` 在 `-GG` 强制着色下仍关闭颜色 |
| **合计** | **43** | **+43** | |

> **未覆盖项如实登记**：以下上游能力未纳入断言（仅人工抽查或未验证）—— `-X` OSC 8 超链接、`-S` stat 风格输出、`-H` 仅跟随命令行符号链接、`-x` 的跨文件系统边界、`-C [COLOR:]PATH` 自定义着色、`@file` 读参数文件、`-TA/-TC/-TM` 时间戳选择、以及 `%y %l %R %e %C*` 等格式说明符。本 PR 不宣称"全部功能已验证"。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：上游没有测试用例，因此不存在任何修改。本包**零补丁**（`patches/` 目录不存在，`conandata.yml` 为 `patches: {}`），上游 `lr.c` / `Makefile` / `lr.1` / `_lr` 一字未改，源码与配方中也不引入任何平台宏。所有平台差异都在配方层（`package()` 直接复制产物）与测试层（期望值运行时反查 + 负向对照）处置。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为 lr 的对外契约新增 **43 条**行为断言（脚本输出 `1..43` 计划 + 逐条 TAP 风格 `ok / not ok`，任一失败即 `conan test` 非零退出）。覆盖面分组如下：
>   1. 遍历与排序：默认递归与名称排序（A02–A04）、`-d` 不进入目录（A05）、`-1` 限层（A06）、`-A` 隐藏文件且不下降隐藏目录（A07–A08，正/反对照，对应 1.5.1 的唯一修复项）、`-U` 遍历即输出（A31）、`-W` 输出序列与默认排序一致（A39；流式时机不作断言）、`-B` 广度优先不丢条目（A40）、`-D` 深度优先并计算目录累计（A32）、`-s` 前缀剥离（A27）
>   2. 过滤表达式：`type == f/d/l`（A09、A10、A33）、`size > 1000`（A15）、`mode` 说明符↔过滤往返含负向对照（A19）、`depth = 1`（A41，与 `find -maxdepth 1` 独立对照）、`~~` glob（A12）、`=~` POSIX ERE（A13）、`===` 大小写不敏感（A14）、`name = "x" ? prune : print` 三元动作（A28）、`-e` 名称正则（A11）
>   3. 输出格式：`-0` NUL 分隔（A20 原始流零换行 + A21 还原后集合一致）、`-F` 类型标记（A22）、`-Q` shell 引用（A23）、`-P` `$'...'` 引用（A24）、`-l` 模式列 + ISO 8601 时间戳（A25）、`-h` 人类可读大小（A26）、`%s %d %i %n %m %Y %t` 说明符与文件系统真值一致（A16–A19、A32、A35）、排序串 `-os/-oS`（A29、A30）
>   4. 输入/输出通道与颜色：参数 `-` 从标准输入读文件名（A36）、`-GG` 强制着色（A43）与 `$NO_COLOR` 关闭着色（A42）
>   5. 符号链接：悬空链接在 `-L` 下仍列出且不失败（A34，对应上游对 ENOENT/ELOOP 的 lstat 回退分支）
>   6. 契约与交付物：退出码语义（A38：缺失路径 rc=1 并报错、未知选项 rc=2 且 Usage 走 stderr 且 stdout 为空）、PATH 上的 `lr` 确为被测包产物（A01）、包内 man 手册与 zsh 补全齐备（A37）
> - **补全原因**：上游是单文件 C 工具，作者未在仓库或 tarball 中提供任何测试框架（见上文清点），"编译通过"本身不构成任何功能证据；适配后必须有真实执行安装产物的回归套件，才能证明交叉编译出的 arm64 二进制在 HarmonyOS PC 上的行为与上游 README/man 手册一致。
> - **新增测试文件清单**：
>   1. `archives/l/lr/1.5.1/test_package/test_lr.sh` — 43 条断言的行为回归套件（POSIX sh，一次性 `lr-test.$$` fixture 目录 + `trap` 清理；期望值凡涉及大小/权限/文件系统类型均在断言当场由 `wc -c`/`find`/`awk` 独立反查并配负向对照；不依赖外部注入变量，缺 `LR_PACKAGE_FOLDER` 时由 PATH 反推包目录，因此 `sh test_lr.sh` 单独可复现满分）
>   2. `archives/l/lr/1.5.1/test_package/conanfile.py` — 测试配方（`VirtualRunEnv` 注入 PATH；先判定包内 `bin/lr` 存在，再把包目录传给套件以断言 man/补全交付物；复现命令 `LR_PACKAGE_FOLDER=<package folder> sh test_lr.sh`）
>   3. `archives/l/lr/1.5.1/test_package/MANIFEST.yml` — 上游 0 用例的清点证据、套件覆盖与**未覆盖**清单、`assertion_count: 43`（与脚本 `1..43`、A01–A43 标号严格一致）

## 验证结果

- 编译状态：**通过**。`conan-verify`（profile `ohos-aarch64-device`）G1/G2/G3/G4 全 PASS，`conan create` 干净构建 EXIT=0；`finish` step [5/10] 的 W3 本地 CI 阻塞门禁通过（`.ci-result.json` 由工具写入，`exit_code=0`，含 `integrity_hash` 与 `log_sha256`）；与平台同源的 `ci/conan/build_and_test.sh` 结果行：

  ```text
  G0_RESULT=pass        KC_RESULT=pass        JC_RESULT=pass
  L0_RESULT=pass: all checks passed
  L1_RESULT=pass: test_package executed
  [ok] L1e: Negative test confirmed — test genuinely depends on lr
  L2_RESULT=skip: lr version/help failed
  L4_RESULT=pass: patches clean        L5_RESULT=pass: bin/ has content
  ```

- 上游测试用例通过率：**不适用（上游 0 例用例）**，未以任何自建用例冒充上游结果。
- 新增测试用例通过率：**43/43（100%）**，三处独立执行均为满分：① `conan create` 的 test_package（`1..43` → `pass=43 fail=0 total=43`）；② W3 本地 CI 阻塞门禁内的同一条 `conan create`；③ 设备侧对交叉编译产物 + 已安装布局直跑脚本（toybox `sh` 与 harmonybrew `bash`，各含设置/不设置 `LR_PACKAGE_FOLDER` 两种跑法，共 4 次，均 rc=0）。
- 破坏性自检（本地复刻 CI L1e 口径）：把 `lr` 换成"无输出、exit 0"的 stub 时 `pass=8 fail=35 total=43` 且 rc=1；从 PATH 移除 `lr` 时 `pass=7 fail=36 total=43` 且 rc=1。A01 另以"输出条目数 = `find` 独立统计 + 1"作为全套件的非空前置，避免等式型断言在产物被破坏时空洞通过。

## 补充说明

### 适配要点

1. **零补丁、零依赖**：上游是单翻译单元 ANSI C + 纯 POSIX Makefile（目标仅 `all/clean/install/FRC`），`requires`/`tool_requires` 为空（W0 依赖检查：无第三方库，仅链接系统 libc；构建期只需 make + clang，由 CI worker 与 profile 提供）。源码不经修改即可用 OHOS SDK clang 15（aarch64-linux-ohos）编译为 PIE ELF64；配方 `build()` 额外断言 `e_machine == 0xB7`，保证 armv8 profile 下产出的确是 arm64 二进制。
2. **为什么不需要 fts 移植**：lr 自带 `opendir/readdir` 遍历（NEWS 1.2 记录不再使用 tsearch），**不依赖 `fts(3)`**，因此避开了 musl 对 `fts.h` 支持不完整这一常见障碍 —— 这是它能零改动落在 OHOS 上的关键。
3. **Linux 专有分支在 OHOS 上实测可用**：`#ifdef __linux__` 引出的 `sys/xattr.h`（`listxattr`/`llistxattr`）与 `mntent`（`setmntent(_PATH_MOUNTED)` → 回退 `/proc/mounts`）均编译通过且真实工作：`-l`/`%x` 输出 `@` 标记（HMDFS 确实报告 user.* xattr），`%Y` 返回 `hmdfs`。因此未做任何屏蔽或 stub（避免 R40 关注的空壳适配）。
4. **`package()` 直接复制产物，不跑上游 `make install`**：上游 install 目标依赖 `install(1)` 且写入硬编码 `PREFIX` 默认值。实测本设备 **`install(1)` 不存在**（toybox 无该工具，`make install` 在 Makefile:19 以 127 退出），CI worker 亦不保证存在；向共享系统前缀写入同样违反 R49。配方改为直接 `copy()` 三件产物：`bin/lr`、`share/man/man1/lr.1`、`share/zsh/site-functions/_lr`。设备端 staging 验证也按同样的等价方式完成（`PREFIX=/usr` + 隔离 DESTDIR + 执行验证），过程记录在 `notes.md`。
5. **L2 冒烟为何必然 skip**：lr 1.5.1 没有 `--version`/`--help` 长选项（getopt 串 `01ABC:DFGHLQPST:UWXde:f:lho:st:x`（含字符 `l`，即 A25 断言的 `-l` 长格式，不接参数）；`-h` 是"人类可读大小"开关而非帮助），未知选项以 rc=2 打印 Usage 到 stderr。为不把"能编译"当成"能运行"，`build()` 内实际执行一次产出的 ELF（`./lr -1 -f '%f\n'` 并在 Python 侧断言其列出 `lr.c`，失败即 `ConanException`），退出码语义另由 A38 锁定。
6. **CLI 声明（R38）**：软件级 `archives/l/lr/commands.json`（`type=tool`，`versions["1.5.1"].ref="lr/1.5.1"`，`binary=false` 待合入后发布）。
7. **测试真实性（R34）**：A01 先确认 PATH 上解析到的 `lr` 就是被测包 `bin/` 内的那个文件，避免宿主同名命令串扰；删除或 stub 掉包内 `bin/lr` 时套件大面积失败（本地 CI 的 `L1e` 破坏性反向验证已 pass）。

### 已知限制

| 项 | 技术原因 |
|----|----------|
| CI L2 冒烟 skip | 上游 CLI 无 `--version`/`--help`（设计如此，非适配缺陷）；已由 build() 内真实执行 + ELF 架构断言 + A38 退出码断言替代覆盖 |
| `-l` 的属主/组与 `%x` 标记随宿主而异 | OHOS 使用 HarmonyOS 账号体系的 uid/gid；HMDFS 不强制 `chmod(2)` 的只读语义（E046）。断言因此不写死这些值 |
| `fstype` 过滤 / `%Y` | 上游要求按平台实现 `scan_filesystems`；OHOS 走 `__linux__` 分支，实测返回 `hmdfs`。注意上游在查不到挂载表时会回退打印数字设备号，断言已排除该回退路径 |
| 第一节末段列出的未断言能力 | `-X`/`-S`/`-H`/`-x`/`-C`/`@file`/`-T*`/部分 `%` 说明符未纳入断言，仅人工抽查或未验证 |
| zsh 补全 `_lr` | 仅对 zsh 生效，按上游原样安装，不在本包内改写 |

### 验证证据

| 证据 | 位置 |
|------|------|
| 上游 0 用例的清点证据、43 条断言声明与未覆盖清单 | `1.5.1/test_package/MANIFEST.yml`（CI 输入文件，已入仓） |
| 43 条断言逐项说明、TAP 与门禁结果行、真机观察 | `1.5.1/reports/test-report.md` |
| 适配笔记（11 项问题与解决方案、上游测试申报表、staging 等价验证、风格例外说明） | `1.5.1/notes.md` |
| 配方与套件本体（评审可直接复核） | `1.5.1/conanfile.py`、`1.5.1/conandata.yml`、`1.5.1/test_package/{conanfile.py,test_lr.sh}` |
| W4 独立审计结论 | `1.5.1/reports/audit-result.json` |

> 说明：`conan create` 的完整构建日志、`conan-verify` 工具报告与 W3 门禁日志均为 `*.log`，按 `.gitcode/review-memory.md` 第 19 条不入 PR，改为把其中的关键结果行原样引用到 `reports/test-report.md` 第四节与本节，确保结论在提交物内可核。`reports/test-report.md` 本身按归档规范（`knowledge/ARCHIVE-SPEC.md` §2.2 与交付清单）保留；若评审按第 19 条字面要求一并移除，其全部结论已由本节承载，删除不影响可核验性。

### 其他

- 平台贡献任务 **#8564**，分支 **`feat/lr-1.5.1`**（与平台提供名称逐字一致），活动：开源鸿蒙PC专项积分赛 → 标题前缀 `【积分赛】`。
- 源码获取备注：设备侧对 `github.com` 的 TLS 通道被干扰（`SSL: UNEXPECTED_EOF_WHILE_READING`），改由同机可达的 `codeload.github.com` 取同一 tag 归档并放入本地 `TMPDIR/builds` 缓存后完成 init-build；**归档内 `conandata.yml` 仍声明官方 `github.com` URL（R39/PF7，不使用 gitcode/镜像搬运源）**，两条独立通道的下载哈希完全一致（`3c9337b9…27cc4a`）。
- 本 PR 只包含 `archives/l/lr/` 单一软件目录（W2 原子性），未触碰框架文件与他人归档目录。
