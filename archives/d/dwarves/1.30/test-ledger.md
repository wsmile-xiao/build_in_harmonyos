# dwarves 1.30 上游测试全量枚举台账

任务: dwarves-1.30-r01-pc1-26（R02 于 2026-09-11 补 /tmp 平台闭环；R03 于 2026-09-11 补测试入口适配与依赖适配）

## R03 失败分类与统计（原始入口 vs 适配入口分开）

### 原始入口（未修改，6 项分母）
| # | 入口 | cwd | exit | 结果 | 原因 | 日志 SHA-256（前16） |
|---|------|-----|------|------|------|----------------------|
| 1 | default_vmlinux_btf.sh | ~/oh-runner-tmp/dwarves-src/dwarves-1.30/tests | 0 | ✅ 通过 | 无 BTF 系统路径，pahole 不段错误有输出 | fecf86cb2e16acfae |
| 2 | btf_functions.sh | 同上 | 2 | skip（依赖缺失） | 无匹配 HongMeng Kernel 1.12.0 aarch64 的 vmlinux | e4b4f9e5ff9c9e3b |
| 3 | flexible_arrays.sh | 同上 | 2 | skip（依赖缺失） | 无 vmlinux | ffe49a3e8e4bbdfa |
| 4 | reproducible_build.sh | 同上 | 2 | skip（依赖缺失） | 无 vmlinux；真实 bpftool 就位后重跑仍 exit=2（同 sha256 前缀，见下） | ffe49a3e8e4bbdfa |
| 5 | prettify_perf.data.sh | 同上 | 2 | skip（依赖缺失） | 无同架构/兼容内核的 perf | 1afe7beaaebf3ea4 |
| 6 | pfunct-btf-decl-tags.sh | 同上 | 1 | 平台阻塞（原始入口） | /tmp erofs 只读，mktemp 模板硬编码 /tmp | 0c20e94bc935b929 |

### 适配入口（测试适配补充通过率，单列）
| 入口 | 适配 | exit | 结果 | 日志 SHA-256 |
|------|------|------|------|--------------|
| pfunct-btf-decl-tags-r03.sh | mktemp 模板 `${TMPDIR:-/tmp}/...`（保持 BTF/断言/退出语义） | 0 | ✅ 通过（`Check that pfunct can print btf_decl_tags read from BTF: Ok`） | d04c23cb8aecc445 |

### 统计结论
- 原始上游 6 项全量通过率：**1/6 (16.7%)**（default_vmlinux_btf 通过；4 skip + 1 平台阻塞计入分母不计通过）
- 实际执行集通过率：1/2 (50%)（default_vmlinux_btf 通过、pfunct 平台阻塞）
- 测试适配补充通过率：pfunct 适配入口 1/1（100%），作为适配补充单列，不改变原始 6 项分母
- 四项依赖适配结论：
  1. /tmp 适配：**成功**（适配入口 exit=0，证据见 R03 章节）
  2. vmlinux：**未获得**（设备/SDK/registry/厂商渠道/内核构建输出全部查询无匹配制品，架构 aarch64 且需 HongMeng Kernel 1.12.0 构建标识；pahole --running_kernel_vmlinux 失败；恢复条件=厂商提供匹配 vmlinux 调试包）
  3. bpftool：**部分成功**（真实 bpftool v7.7.0 已从官方源码构建并验证 --version=libbpf v1.6、arm64 ELF；但 reproducible_build.sh 仍需 vmlinux 才能运行，bpftool 就位后重跑 exit=2 原生缺件退出）
  4. perf：**未获得**（设备/SDK/registry 均无匹配制品；构建需完整内核源码树 tools/perf，设备无内核源码；恢复条件=厂商提供同架构 perf 或内核源码）

## R03 测试入口适配（pfunct-btf-decl-tags.sh，最小修改 + 适用边界）

### 修改
单行差异：`mktemp /tmp/pfunct-btf-decl-tags.sh.XXXXXX.o` → `mktemp "${TMPDIR:-/tmp}/pfunct-btf-decl-tags.sh.XXXXXX.o"`
，即硬编码 `/tmp` 前缀改为 `${TMPDIR:-/tmp}` 等价可配置方式。
BTF 生成（clang --target=bpf -g）、断言（pfunct -P -F btf 三函数 btf_decl_tag）、
退出语义（exit 0/1）与预期输出均保持不变；仅在临时目录位置可配置化。

### 原始入口首错（适配前独立记录）
```
$ bash ./pfunct-btf-decl-tags.sh                                   # cwd: ~/oh-runner-tmp/dwarves-src/dwarves-1.30/tests
mktemp: failed to create file via template '/tmp/pfunct-btf-decl-tags.sh.XXXXXX.o': Read-only file system
Check that pfunct can print btf_decl_tags read from BTF: clang-15: error: no input files
exit=1
```
日志: ~/oh-runner-tmp/r03-tests-pfunct-orig.log（SHA-256 见 R03 回报）

### 适配入口运行（TMPDIR 指向真实可写目录）
```
$ TMPDIR=/storage/Users/currentUser/oh-runner-tmp/dwarves-r03-tmp bash ./pfunct-btf-decl-tags-r03.sh
Check that pfunct can print btf_decl_tags read from BTF: Ok
exit=0
```
日志: ~/oh-runner-tmp/r03-tests-pfunct-adapted.log（SHA-256 见 R03 回报）

### 候选临时目录验证（0700 语义）
- /data/local/tmp/dwarves-r03（任务建议候选）: mkdir Permission denied（系统挂载点，普通用户无写权限）
- home HMDFS ~/oh-runner-tmp/dwarves-r03-tmp: 可写，stat 显示 2771（HMDFS 不保留 POSIX 0700 位，
  但真实可写且适配入口运行通过；R02 已确认其他挂载点均不可用）
- /（tmpfs）、/dev/shm（tmpfs）: Permission denied（R02 记录）

### 适用边界
- 该适配仅影响上游测试入口的临时目录位置，不改 dwarves 库/测试语义；
  用于 OHOS /tmp 为 erofs 只读挂载的平台
- 原始上游入口在全量统计中仍按其天然结果计（exit=1 平台阻塞/依赖缺失），
  适配入口作为"测试适配补充通过率"单列，不把原始入口改写为通过
- 不提交 test 脚本到归档（上游源码保持原样，测试执行在 worktree 外源代码树进行）

## R02 /tmp 平台测试闭环（pfunct-btf-decl-tags.sh）逐方案证据

### 原始入口运行（未修改）
```
$ bash ./pfunct-btf-decl-tags.sh            # cwd: ~/oh-runner-tmp/dwarves-src/dwarves-1.30/tests
mktemp: failed to create file via template '/tmp/pfunct-btf-decl-tags.sh.XXXXXX.o': Read-only file system
Check that pfunct can print btf_decl_tags read from BTF: clang-15: error: no input files
exit=1
```
首错: 脚本第 6 行 `mktemp /tmp/pfunct-btf-decl-tags.sh.XXXXXX.o` 硬编码 /tmp，
OHOS /tmp 为 erofs 只读挂载（`mount: /dev/block/dm-0 on /tmp type erofs (ro,...)`）。

### 方案 1: TMPDIR/TMP/TEMP 指向可写 0700 目录（无效）
```
candidate: ~/oh-runner-tmp/upertmp-r02  → stat: drwxrws--x 2771（HMDFS 不保留 0700）
TMPDIR=TMP=TEMP=.../upertmp-r02 bash ./pfunct-btf-decl-tags.sh → exit=1
mktemp: ...'/tmp/pfunct-btf-decl-tags.sh.XXXXXX.o': Read-only file system
```
结论: mktemp 模板含 `/tmp/` 绝对路径前缀，GNU mktemp 对含斜杠模板不使用 $TMPDIR，
环境变量无效。候选目录已验证但无法生效。

### 方案 2: mount namespace 内 tmpfs /tmp（无工具/权限）
```
$ unshare -m sh -c 'mount -t tmpfs tmpfs /tmp && ...'
sh: unshare: inaccessible or not found
```
设备无 unshare 程序，且普通用户（uid 20020101）无 mount 权限。

### 方案 3: 真实可写 /tmp 候选挂载点（全部 Permission denied）
| 候选 | 类型 | 结果 |
|------|------|------|
| /data/local/tmp | hmfs rw | mkdir Permission denied |
| /（根） | tmpfs 16G | mkdir /.cand-r02 Permission denied |
| /dev/shm | tmpfs | mkdir Permission denied |
| /tmp 直接挂载 | erofs ro | mount: bad /etc/fstab（无权限） |

### 最小测试入口兼容修复（保持测试原意）
修复入口: `~/oh-runner-tmp/pfunct-btf-decl-tags-fixed.sh`（R02 记录备查）
差异: 仅第 6 行 mktemp 模板由硬编码 `/tmp/pfunct-btf-decl-tags.sh.XXXXXX.o`
改为 `$TMPDIR/pfunct-btf-decl-tags.sh.XXXXXX.o`；断言、clang bpf 编译、
pfunct -P -F btf 读取 btf_decl_tag 逻辑与预期输出完全未改。
原因: OHOS /tmp erofs 只读且候选挂载点均无写权限/0700 语义；
仅改临时目录位置，保持测试原意。
验证:
```
$ TMPDIR=~/oh-runner-tmp/upertmp-r02 bash ./pfunct-btf-decl-tags-fixed.sh
Check that pfunct can print btf_decl_tags read from BTF: Ok
exit=0
```
边界: 修复仅证明 btf_decl_tag 功能链路在 OHOS 可用（clang bpf 编译 +
pfunct 读取）；原始上游入口在硬编码 /tmp 的平台上仍报平台首错，
按上游评审口径该入口原始形态计"平台阻塞"，修复验证另计。

## 枚举方法（可复制）
1. 上游 tarball 根目录: `find . -iname '*test*' -o -iname '*selftest*'`（不含 .git/）
2. CMakeLists.txt 无 enable_testing/add_test/CTest 注册（纯命令行测试套件）
3. tests/ 目录: 6 个独立可执行 shell 测试脚本（官方 run-selftests.sh 即运行 tests/tests 驱动）
4. 驱动: tests/tests 遍历 *.sh，exit 0=通过、2=skip、其他=失败
5. regtest（仓库根 python 回归工具）依赖开发机 /media/tb 路径，非 CI 独立用例，不计入
6. ostra/ 为运行时工具非测试；.github/ 为 CI 编排脚本非独立用例

## 逐项台账（6 个独立上游用例，全量分母=6）

| # | 入口 | 分类 | 实际运行 | 退出码 | 结果 | 原因/首个错误 |
|---|------|------|---------|--------|------|--------------|
| 1 | tests/btf_functions.sh | 独立上游用例(依赖 vmlinux) | 是 | 2 | skip | 无 vmlinux：`pahole --running_kernel_vmlinux` 返回空（本机无内核调试包），首错 `Please specify a vmlinux file to operate on` |
| 2 | tests/default_vmlinux_btf.sh | 独立上游用例(无外部依赖) | 是 | 0 | ✅ 通过 | `Default BTF on a system without BTF: Ok`（PAHOLE_VMLINUX_BTF_FILENAME=foobar 无 BTF 系统路径，pahole 不段错误、有输出） |
| 3 | tests/flexible_arrays.sh | 独立上游用例(依赖 vmlinux) | 是 | 2 | skip | 无 vmlinux：首错 `<vmlinux> file not available, please specify another` |
| 4 | tests/pfunct-btf-decl-tags.sh | 独立上游用例(依赖 clang+/tmp) | 是 | 1 | 硬阻塞(平台) | 首错 `mktemp: failed to create file via template '/tmp/...': Read-only file system`——/tmp 为 erofs 只读挂载；TMPDIR 候选目录恢复后模板含 /tmp 斜杠仍指向 /tmp；候选挂载点验证见下。clang bpf 目标可用（已实测产出 bpfcheck.o） |
| 5 | tests/prettify_perf.data.sh | 独立上游用例(依赖 perf) | 是 | 2 | skip | 无 perf：`skip: No 'perf' binary available` |
| 6 | tests/reproducible_build.sh | 独立上游用例(依赖 vmlinux+bpftool) | 是 | 2 | skip | 无 vmlinux：`<vmlinux> file not available`；另缺 bpftool |

## /tmp 只读恢复流程（pfunct 用例，按 SKILL 临时目录规则）
- 首错: `mktemp /tmp/pfunct-btf-decl-tags.sh.XXXXXX.o` → Read-only file system（/tmp = erofs ro 挂载）
- 候选1: ~/oh-runner-tmp/upertmp（HMDFS）: `chmod 700` 后 stat = `2771 drwxrws--x`，不保留 POSIX 0700 语义 → 不合格
- 候选2: /（tmpfs）: mkdir Permission denied → 不可写
- 候选3: /dev/shm（tmpfs）: mkdir Permission denied → 不可写
- 候选4: /data、/data/service、/data/local/tmp（hmfs）: Permission denied → 不可写
- 重跑命令（TMPDIR/TMP/TEMP 指向候选1）: `TMPDIR=.../upertmp bash ./pfunct-btf-decl-tags.sh` → 仍失败于同一首错（模板含 /tmp 绝对路径）
- 结论: 所有候选挂载点均无法满足真实可写/0700 语义 → 记录为平台阻塞（/tmp erofs ro），该项计入上游总分母 6 但不计通过
- 恢复条件: 设备提供可写 /tmp（或重新挂载 rw），或测试模板改为使用 $TMPDIR

## 双口径统计
- source_declared_total = 6（tests/*.sh 全量枚举）
- configured_executable_total = 6（全部为 shell 脚本，无编译期互斥分支；本机 /bin/bash 缺失但以 /data/service/hnp/bin/bash 显式执行）
- executed_passed_total = 1（default_vmlinux_btf.sh）
- 失败 = 1（pfunct-btf-decl-tags.sh：/tmp 平台硬阻塞，非 dwarves 代码缺陷——clang bpf 编译与 pfunct 读取均可用）
- skip（依赖缺失）= 4（btf_functions/flexible_arrays/reproducible_build 缺 vmlinux；prettify_perf 缺 perf）
- 全量通过率 = 1/6 (16.7%)；实际执行集通过率 = 1/2 (50%)（6 项中 4 项为上游设计内 skip 路径 exit 2）
- 依赖复查：vmlinux/perf/bpftool 为本机系统能力，无 registry 制品可查；/sys/kernel/btf/vmlinux 不存在

## 映射链
tests/*.sh 源码声明 → 无预处理/构建条件（shell 直接执行）→ 无 CMake 目标 → tests/tests 驱动按 *.sh 枚举 → 实际执行日志见 ~/oh-runner-tmp/testlogs/*.log
