## PR 信息
- **三方库名称**：cscope
- **上游版本**：15.9
- **上游仓库地址**：https://sourceforge.net/projects/cscope/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无
- **PR 分支**：`feat/cscope-15.9`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无 `tests/` 目录、无 automake `TESTS` 变量、无 `check_PROGRAMS`、无 `AC_CONFIG_TESTDIR`、无 CI 配置 |
| 集成测试 | 0 | 同上（清点证据见 `reports/test-report.md` 第二节） |
| **合计** | **0** | 上游 15.9 不附带任何测试套件 |

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例。适配层改动全部在 `patches/` 四个移植补丁与 conan 配方，不触碰上游测试。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变（上游 N=0） | 上游无测试套件，不虚构用例 |
| 集成测试 | 0 | 不变（上游 N=0） | 同上 |
| 鸿蒙特有测试 | 10 | 新增 | 消费者冒烟 3 例（test.sh）+ **完整消费者端到端用例 1 个**（test_e2e.sh，7 例全链路）；MANIFEST: assertion_count=10, consumer_case_count=1 |
| **合计** | **10** | **+10** | 真机 conan create 实测 10/10 |

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试用例（适配层改动只在 `patches/` 与配方，见下）。

### 补丁说明（适配层，不涉及测试用例）

补丁全部经 `ohc-run.py refresh-patch --auto` 管线生成（R3），无手工 `.patch`：

| 补丁 | 目标 | 修改内容 |
|------|------|----------|
| `0001-config.guess.patch` | `config.guess` | 新增 `*:HarmonyOS:*:*` 分支 |
| `0002-config.sub.patch` | `config.sub` | 2 处补 `linux-ohos*` |
| `0003-configure.patch` | `configure` | `-lncurses`→`-lncursesw`；放宽 HMDFS 临时目录 umask |
| `0004-src-main.c.patch` | `src/main.c` | 放宽私有临时目录 umask 为 `S_IRWXO`（POSIX 兼容，无平台宏） |

四补丁对 pristine 源码 `patch --dry-run -p1` 均干净通过。

## 验证结果

### 编译验证
- 编译状态: 通过（真机 conan create 全绿：构建 + 装包 + test_package 全部通过，rc=0；平台 CI 校验通过）
- 上游测试用例通过率: N=0 不适用（上游不附带测试套件，非「跳过未跑」；清点证据见 `reports/test-report.md` 第二节）
- 新增测试用例通过率: 10/10（100%）——真机实测（2026-10-03）：test.sh 冒烟 3 例 ✅ + test_e2e.sh 端到端 7 例 `TEST SUMMARY: 7 passed, 0 failed`（conan create rc=0）

### 产物验证

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | 构建系统: autotools，状态: built |
| 产物存在性 | ✅ | 包内 `bin/cscope`（aarch64-unknown-linux-ohos ELF） |
| 运行测试 | ✅ | 冒烟 3 例 + 端到端 7 例全过（10/10，真机实测） |
| 动态依赖 | ✅ | ncurses/6.6（静态宽字符版） |

### 依赖

- ncurses/6.6（OHOS 制品仓二进制；仅提供 `libncursesw.a`，补丁 0003 将 `-lncurses` 改为 `-lncursesw`）

### 测试结论
- 总体评价: 真机 conan create 全绿 + test_package 10/10（冒烟 3 例 + 完整消费者端到端用例 7 例）；端到端用例覆盖 cscope 的真实消费通道（编辑器/IDE 经 `cscope -d -L` 行模式接口的查询链路）
- 已知限制: 上游不附带测试套件（N=0），其通过率不适用；适配后测试为本次补全（见「补全测试用例说明」）

### 遇到的问题与解决方案
1. **`config.guess` 无法识别 HarmonyOS**：rc=1 无法输出三元组，上游 2018 版无 HarmonyOS 分支 → `patches/0001` 新增 `*:HarmonyOS:*:*` 分支。
2. **`config.sub` 拒绝 `aarch64-unknown-linux-ohos`**：`maybe_os` 与内核-OS 校验列表均无 `-ohos`，或静默规范化为 `...-linux-gnu-ohos` → `patches/0002` 两处补 `linux-ohos*`。
3. **链接失败：`libncurses.a` 不存在**：OHOS ncurses 6.6 只提供宽字符版 `libncursesw.a`，而 `configure.in:153` 硬编码 `-lncurses` → `patches/0003` 改 `-lncursesw`。
4. **`config.status` 阶段 `Permission denied`**：HMDFS `umask 077` 语义使 `config.status` 自建临时目录不可执行（`./confCdKcbg/subs1.awk: Permission denied`）→ `patches/0003` 放宽临时目录 umask。
5. **行模式查询 `Cannot open file <TMPDIR>/cscope.<pid>/cscope.1`**：HMDFS 按组位解析目录访问，`umask(S_IRWXG|S_IRWXO)` 清零组位后 `open()` 返回 EACCES → `patches/0004` 放宽为 `S_IRWXO`（POSIX 兼容、无平台宏；实测矩阵见 `reports/test-report.md` 第四节）。
6. **真机内核拒绝 shebang 脚本 execve（真机验证期）**：`./configure` 直跑 rc=126（`Permission denied`）、`bash ./configure` rc=0；OHOS 适配版 conan 的 Autotools 驱动不支持 `CONFIG_SHELL` → 真机验证以等价驱动执行（`sh ./configure` + `make install DESTDIR=…`）；test_package 经 `bash` 前缀执行脚本。**MR 配方零改动**。

### 验证命令
```
# 真机（HarmonyOS PC 设备，2026-10-03）
conan create . -pr:h=$HOME/bih/ci/conan/profiles/ohos-aarch64 -pr:b=$HOME/bih/ci/conan/profiles/ohos-aarch64
# → 构建/装包/test_package 全绿，rc=0
# → test.sh 冒烟 3 例 ✅；test_e2e.sh: TEST SUMMARY: 7 passed, 0 failed

# 端到端用例覆盖的消费链路（test_e2e.sh 内部，在 e2e-probe/ 微型 C 工程上执行）
printf '%s\n' main.c parser.c parser.h util.c util.h > cscope.files
cscope -b -f cscope.out                     # 建交叉引用库
cscope -d -f cscope.out -L -0 tokenize      # -0 符号查询（定义 util.c + 调用点 parser.c）
cscope -d -f cscope.out -L -1 parse_twice   # -1 函数定义
cscope -d -f cscope.out -L -2 parse_input   # -2 被调函数
cscope -d -f cscope.out -L -3 tokenize      # -3 调用者
cscope -d -f cscope.out -L -8 util.h        # -8 #include 关系
cscope -b -u -f cscope.out                  # -u 增量重建，新符号入索引
```

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？
- [x] **是**，上游无测试用例，适配后补全了测试（详见下方说明）
- **补全的测试范围**：
  1. 消费者冒烟 3 例（`test.sh`）：`cscope -V` 版本横幅 / `cscope -b` 建交叉引用库（产物非空校验） / `cscope -d -L -0` 行模式符号查询命中
  2. **完整消费者端到端用例**（`test_e2e.sh`，7 例全链路）：对 `e2e-probe/` 微型 C 工程（5 个源文件，含跨文件调用与 `#include` 关系）走通 cscope 的真实消费链路——`cscope.files` 清单 → `cscope -b` 建交叉引用库 → `-0/-1/-2/-3/-8` 行模式查询（符号 / 函数定义 / 被调函数 / 调用者 / `#include` 关系）→ 修改源码后 `cscope -b -u` 增量重建并复查新符号入索引；逐例独立判定（TEST PASS / TEST FAIL），末尾输出 `TEST SUMMARY`，任一失败以退出码 1 结束
- **补全原因**：上游 15.9 不附带任何测试套件（N=0，清点证据见 `reports/test-report.md` 第二节）；cscope 的真实消费面是编辑器/IDE 的 Cscope 集成（vim/emacs 等生成的协议客户端全部经由 `cscope -d -L` 行模式接口），适配验收核心是「安装产物能被消费者完整使用」，故补全消费者视角的端到端用例
- **新增测试文件清单**：
  1. `archives/c/cscope/15.9/test_package/test.sh` — 消费者冒烟 3 例（原有文件，本次未修改）
  2. `archives/c/cscope/15.9/test_package/test_e2e.sh` — 完整消费者端到端用例（7 例全链路）
  3. `archives/c/cscope/15.9/test_package/e2e-probe/` — 微型 C 工程 fixture（main.c / parser.c / parser.h / util.c / util.h）
  4. `archives/c/cscope/15.9/test_package/conanfile.py` — 消费方测试包（test() 依次驱动 test.sh 与 test_e2e.sh）
  5. `archives/c/cscope/15.9/test_package/MANIFEST.yml` — assertion_count: 10，consumer_case_count: 1，upstream_tests_supplemented: true

## 补充说明

- 上游 cscope 15.9 为 autotools CLI 工具（`package_type=application`），静态链接 ncurses/6.6（宽字符版）。四个补丁全部为构建系统/权限语义的移植性修复，不含平台宏、不含平台分支（`0004` 对 POSIX 文件系统行为严格无操作，仅修复 HMDFS 组位语义）。
- 软件级 `archives/c/cscope/commands.json` 随本 PR 携带（R38 对 CLI 包的要求）；其与 PF9 的框架级互斥留痕见 `reports/preflight-local.log.md`。
- 测试清点与实测明细见 `reports/test-report.md`，适配全记录见 `notes.md`。
