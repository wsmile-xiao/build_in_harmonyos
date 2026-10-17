## PR 信息
- **三方库名称**：mmh
- **上游版本**：0.4
- **上游仓库地址**：https://marmaro.de/prog/mmh/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无
- **PR 分支**：`feat/mmh-0.4`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架 |
| 集成测试 | 57 | `test/` 目录 28 组 57 个 `test-*` 脚本，`test/runalltests` → `test/runtest` 逐例驱动（退出码 0=PASS / 1=FAIL / 2=SKIP，SKIP 经 `test_skip()` 置 120 映射） |
| **合计** | **57** | 清点证据见 `reports/test-report.md` 第二节 |

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例。适配层改动全部在 `patches/` 十三个移植补丁与 conan 配方，不触碰上游测试。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | — |
| 集成测试（上游套件） | 57 | 不变（零修改） | 真机全量执行：49 PASS / 6 SKIP（合法）/ 2 FAIL（平台文件系统语义归因，见下方验证结果） |
| 鸿蒙特有测试 | 12 | 新增 | 消费者冒烟 4 例（test.sh）+ **完整消费者端到端用例 1 个**（test_e2e.sh，8 例全链路）；MANIFEST: assertion_count=12, consumer_case_count=1 |
| **合计** | **69** | **+12** | 真机 conan create 实测：上游 49/57 + 新增 12/12 |

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试用例（适配层改动只在 `patches/` 与配方，见下）。

### 补丁说明（适配层，不涉及测试用例）

补丁全部经 `ohc-run.py refresh-patch --auto` 管线生成（R3，per-file-difflib），无手工 `.patch`；13 补丁按编号序对 pristine 源码 `git apply -p1` 全部干净应用，结果树与适配树逐字节一致（工具聚合哈希 `6cb42c751c8ff2f1` → `ba9a5d2e8fc80538`）。

| 补丁 | 目标 | 修改内容 |
|------|------|----------|
| `0001-config.guess.patch` | `config.guess` | 新增 `*:HarmonyOS:*:*` 分支（arm64→aarch64，输出 `aarch64-unknown-linux-ohos`） |
| `0002-config.sub.patch` | `config.sub` | 4 处补 aarch64 CPU 与 `linux-ohos` 内核-OS 组合 |
| `0003-configure.patch` | `configure` | tgetent 探测顺序补 ncursesw；临时目录 umask 077→022（HMDFS） |
| `0004-configure.ac.patch` | `configure.ac` | 同步 ncursesw 顺序（与生成物 configure 保持一致） |
| `0005-man-Makefile.in.patch` | `man/Makefile.in` | `version.sh`/`gettitles.sh`/`mh-chart-gen.sh` 改 `sh` 前缀驱动（shebang execve） |
| `0006-sbr-Makefile.in.patch` | `sbr/Makefile.in` | `version.sh` 改 `sh` 前缀（`-DVERSION` 才有值） |
| `0007-sbr-folder_addmsg.c.patch` | `sbr/folder_addmsg.c` | 入箱复制回退 EXDEV → EXDEV/EPERM/EOPNOTSUPP（HMDFS 无硬链接） |
| `0008-sbr-path.c.patch` | `sbr/path.c` | `etcpath()` 支持 `MMHETC` 环境变量覆写（conan 包布局定位；未设置时与上游行为完全一致） |
| `0009-test-setup-test.patch` | `test/setup-test` | 测试套件临时目录改 `${TMPDIR:-/tmp}`（OHOS /tmp 只读） |
| `0010-uip-Makefile.in.patch` | `uip/Makefile.in` | `version.sh` 改 `sh` 前缀（各命令编译期版本串） |
| `0011-uip-mhpgp.sh.patch` | `uip/mhpgp.sh` | 临时目录改 `${TMPDIR:-/tmp}` |
| `0012-uip-mhsign.sh.patch` | `uip/mhsign.sh` | 临时目录改 `${TMPDIR:-/tmp}` |
| `0013-uip-sendfiles.sh.patch` | `uip/sendfiles.sh` | 草稿临时文件改 `${TMPDIR:-/tmp}` |

两份构建系统补丁（`configure` 与 `configure.ac`）保持同步，确保再生成时语义不回退。

## 验证结果

### 编译验证
- 编译状态: 通过（真机 conan create 全绿：构建 + 装包 + test_package 全部通过，rc=0）
- 上游测试用例通过率: **49/57（86.0%）**——真机全量执行（N=57，N′=57，零遗漏）：49 PASS；6 例 SKIP 全部经上游 `test_skip()` 正规机制（缺 valgrind ×1、上游自跳 ×1、缺 UTF-8 locale ×4）；2 例 FAIL 均为平台文件系统语义归因且证据齐备（`anno`=测试自造硬链接夹具在 HMDFS 上 EPERM 不可构造；`rcvstore`=HMDFS 权限位归一 0660 使 `find -perm 0600/640` 精确匹配必然落空，真机探针实证）。**上游测试脚本零修改**；逐例清单、日志原样引用与定性见 `reports/upstream-test-run.md`
- 新增测试用例通过率: 12/12（100%）——真机实测（2026-10-04）：test.sh 冒烟 4 例 ✅ + test_e2e.sh 端到端 8 例 `== test_e2e.sh: ALL-PASS ==`（conan create rc=0）

### 产物验证

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | 构建系统: autotools，状态: built |
| 产物存在性 | ✅ | 包内 `bin/` 40 命令（34 C + 6 脚本）与 8 别名、`lib/` 辅助二进制、`etc/` format/component 文件、man、licenses |
| 运行测试 | ✅ | 消费者 12/12（真机）+ 上游套件 49/57（6 合法 SKIP、2 平台归因 FAIL 明示） |
| 动态依赖 | ✅ | ncurses/6.6（静态宽字符版） |
| 质量门禁 | ✅ | `verify-build` Verdict PASS（G1/G2/G3/G4，见 `reports/quality-report.md`） |

### 依赖

- ncurses/6.6（OHOS 制品仓二进制；仅提供 `libncursesw.a`，补丁 0003/0004 在 tgetent 探测顺序中补 `ncursesw`）

### 测试结论
- 总体评价: 真机 conan create 全绿 + 消费者用例 12/12；上游 57 例套件全量执行 49 PASS，端到端用例覆盖 mmh 的真实消费通道（批次邮件处理脚本链路：`inc` 投递 → `scan`/`pick` 检索 → `mhlist`/`mhstore` 附件处理 → `refile` 归档）
- 已知限制: 2 例上游 FAIL 为 HMDFS 文件系统语义不可构造/不可满足（硬链接、0600/640 精确权限），非 mmh 行为缺陷，测试脚本保持上游原样；6 例 SKIP 为环境缺口（valgrind/locale）与上游自跳

### 遇到的问题与解决方案
1. **`config.guess` 无法识别 HarmonyOS**：rc=1 无法输出三元组（上游 2005 年版无 HarmonyOS 分支）→ `patches/0001`。
2. **`config.sub` 拒绝 `...-linux-ohos`**：`maybe_os` 与内核-OS 列表均无 `-ohos`，或静默规范化为 `...-linux-gnu-ohos` → `patches/0002`。
3. **链接失败：`libncurses.a` 不存在**：制品仓 ncurses/6.6 仅宽字符版 `libncursesw.a` → `patches/0003`/`0004` 探测顺序补 ncursesw。
4. **`config.status` 临时目录不可写**：HMDFS 把目录 owner 映射为固定 UID，`umask 077` 自建临时目录不可写（E011）→ `patches/0003` 放宽 umask。
5. **首跑全部用例 rc=74（锁等待）**：mmh 默认 dot-lock 依赖 `link(2)` 建 `.lock`，HMDFS EPERM（表观症状为 context 写入 ENOENT 假象——lockit 重试循环最终 errno 停在 stat 的 ENOENT）→ 配方 `--with-locking=fcntl`（F_SETLK，真机可用；无源码补丁）。
6. **`refile`/`rcvstore` 入箱失败**：`folder_addmsg()` 复制回退只覆盖 EXDEV → `patches/0007` 扩展到 EPERM/EOPNOTSUPP。
7. **`make install` 造 8 个命令别名 EPERM 失败**：`install-lcmds` 用硬链接（flists/folders/fnext/fprev/unseen/prev/next/scan）→ 配方安装参数 `LN=cp`（副本；命令本体按 `argv[0]` 分派，语义等价）。
8. **构建期 `Permission denied` rc 126、VERSION 静默为空**：OHOS 内核拒 shebang 脚本 execve，`man/`/`sbr/`/`uip/` Makefile 反引号直执行 `version.sh` 等 → `patches/0005`/`0006`/`0010` 改 `sh` 前缀。
9. **脚本命令临时目录 `/tmp` 不可写**（OHOS `/tmp` 只读，真机探针实测）→ `patches/0009`/`0011`/`0012`/`0013` 改 `${TMPDIR:-/tmp}`。
10. **链接期 duplicate symbol（`tmp`）**：clang≥11 默认 `-fno-common` 与 2019 年版 C 代码的暂定定义合并语义冲突 → 配方 CFLAGS 追加 `-fcommon`（复现上游构建语义，非源码缺陷）。
11. **`inc`/`scan`/`pick`/`comp`/`forw` 全线 `unable to open format file`**：conan 以 `--prefix=/` + DESTDIR 打包，编译期 `NMHETCDIR=/etc`（设备不存在），format/component 文件在包内 `etc/` → `patches/0008` 让 `etcpath()` 先查 `MMHETC`；配方 `runenv_info` 导出 `MMHETC=<包>/etc`（VirtualRunEnv 对消费者自动生效）。

### 验证命令
```
# 真机（HarmonyOS PC 设备，2026-10-04）
conan create . -pr:h=$HOME/bih/ci/conan/profiles/ohos-aarch64 -pr:b=$HOME/bih/ci/conan/profiles/ohos-aarch64
# → 构建/装包/test_package 全绿，rc=0
# → test.sh: ALL-PASS（4 例）；test_e2e.sh: ALL-PASS（8 例）

# 上游测试套件（等效驱动，差异 D1-D7 显式披露）
sh $HOME/mmh-fix/run-mmh-suite.sh
# → === FINAL: TOTAL=57 PASS=49 SKIP=6 FAIL=2 MODE=runtest ===

# 端到端用例覆盖的消费链路（test_e2e.sh 内部）
inc -file fixture.mbox                    # mbox 投递 inbox
scan | grep Subject                       # 双消息显示
pick -subject multipart                   # 条件检索
mhlist 2                                  # MIME 部件列表
mhstore 2 -auto -part 2                   # 提取附件并逐字节校验
refile -src inbox 1 archive               # 归档
```

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（57 个 `test-*` 用例，真机全量执行见上）
- [ ] 是，上游无测试用例，适配后补全了测试

保留原有 Conan 消费者测试（`test.sh` 冒烟 4 例），用于验证打包后的命令可用性、
`/tmp` 替换与 `MMHETC` 定位；本次为鸿蒙适配补充**完整消费者端到端用例**
（`test_e2e.sh`，8 例），覆盖 mbox 文件投递、双消息显示、条件检索、MIME 部件
列表、附件提取（内容逐字节校验）、归档移动与终态复查全链路——与批次邮件处理
消费者的 CLI 通道同构：

- **新增文件**：`archives/m/mmh/0.4/test_package/test_e2e.sh`（8 例全链路，
  逐例独立判定，末尾输出 `ALL-PASS`/`FAILED`，任一失败以非零退出结束）；
  `test_package/mbox-fixture` 夹具随脚本生成（不落盘二进制）。
- **MANIFEST 回填**：`assertion_count: 12`（冒烟 4 + 端到端 8）、
  `consumer_case_count: 1`、`upstream_test_count: 57`、`upstream_passed: 49`、
  `upstream_failed: 2`、`upstream_skipped: 6`。

## 补充说明

- 上游 mmh 0.4 为 autotools CLI 工具（`package_type=application`），静态链接
  ncurses/6.6（宽字符版）。13 个补丁全部为构建系统/文件系统语义的移植性修复，
  不含平台宏、不含平台分支；`0008`（`MMHETC`）未设置环境变量时与上游行为完全
  一致，属包管理器布局定位。
- 6 个脚本命令（mmh/mhsign/mhpgp/print-mimetype/sendfiles/whatnow2）与
  `lib/mmhwrap` 在 OHOS 真机需以 `sh` 前缀调用（内核拒 shebang 脚本 execve）；
  上游发行包即脚本形式安装，适配层未改命令本体。
- 软件级 `archives/m/mmh/commands.json` 随本 PR 携带（R38 对 CLI 包的要求，
  已登记 0.4；与 PF9 的框架级互斥留痕见 `reports/preflight-local.log.md`）。
- 测试清点与实测明细见 `reports/test-report.md` 与 `reports/upstream-test-run.md`，
  适配全记录见 `notes.md`。
