- **三方库名称**：jgraph
- **上游版本**：83（上游 Jim Plank's jgraph，README `$Revision: 8.3 $`；Debian 源码包 83-26 与其同源）
- **上游仓库地址**：https://web.eecs.utk.edu/~jplank/plank/jgraph/jgraph.html
- **适配路径**：路径 A（基础适配，10 个可移植性补丁）
- **使用知识库**：无直接命中（G2 阶段引擎自动匹配的 E063 与本例根因不符——本包未启用 `-Werror`，属误报）；本次新增知识草稿 E430（aarch64 隐式函数声明截断指针/浮点，`knowledge/drafts/E430-draft-9C4A.kv`）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 83 tarball 无 `tests/` 目录 |
| 集成测试 | 0 | makefile 无 `check`/`test` 目标（`make -n check` → `No rule to make target 'check'`） |
| 其他测试 | 0 | makefile 的 `examples` 目标仅用刚构建的二进制渲染示例，无断言或结果比对 |
| **合计** | **0** | 清点证据见 `notes.md` 与 `test_package/MANIFEST.yml`（R51 三步法） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无测试套件 |
| 集成测试 | 0 | 不变 | 上游无测试套件 |
| 鸿蒙特有测试 | 25 | 新增 | `test_package/test_jgraph.sh` 消费者断言：渲染与确定性、`-p` show 模式、`-L` landscape 平移数值、EPS 边界框（含截断负向对照）、多页、`-comments`、非法输入、AArch64 ELF 产物；25 条断言在鸿蒙 PC（aarch64，OHOS clang 15）实机执行，按平台特有测试口径全部计入本行 |
| **合计** | **25** | **+25** | 上游 0 项 + 新增 25 条鸿蒙消费者用例（即鸿蒙特有测试行，不重复计数） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（上游无测试用例；10 个补丁均为可移植性修改，未触碰测试）
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为 jgraph CLI 补全 25 条消费者断言 —— PostScript 渲染与
>   逐字节确定性（sha256 两次一致）、`-p` show 模式回显、`-L` landscape 平移
>   数值精确等于 `-bb[2]-bb[0]`、EPS 标记正常渲染与截断 `%%BoundingBox` 必须报错
>   （补丁负向对照）、`newpage` 多页输出、`-comments` 注释、非法 token 诊断、
>   AArch64 ELF 产物校验。
> - **补全原因**：上游 83 仅含 C 源码、man 页与示例 `.jgr`（无 `tests/` 目录，
>   makefile 无 `check`/`test` 目标，见 `notes.md` 实测证据）。
> - **新增测试文件清单**：
>   1. `test_package/test_jgraph.sh` — 25 断言消费者测试脚本（真实执行安装后的二进制）
>   2. `test_package/conanfile.py` — 通过 `conanrun` 环境驱动测试脚本（R34）
>   3. `test_package/inputs/{simple,twopage,eps-good,eps-bad}.jgr` 与 `eps-{good,bad}.eps` — 确定性输入

## 验证结果

- 编译状态：**通过**（`conan create` 干净构建；conan-verify G0-G4 全 PASS）
- 上游测试用例通过率：不适用（上游 N=0，清点证据见上表与 `notes.md`）
- 新增测试用例通过率：**25/25（100%）**（test_package 断言逐条实跑于鸿蒙 PC）
- 本地 CI（W3，与平台同脚本）：L0 pass / L1 pass（test_package 被真实执行）/
  L1e 破坏性反向验证 pass（移走 `bin/` 后断言确实失败）/ L5 pass；
  L2 与 L4 为非阻塞 warn（原因见补充说明）
- 上游示例回归（`.orig` 原始输入）：20/21 渲染成功；唯一失败 `ad.jgr` 依赖
  `cube.eps` 与 `disk.eps` 两个示例产物，生成后亦通过（示例间依赖，非代码缺陷）

## 补充说明

- **源码 URL（R39 说明）**：上游官网已下架 83（`jgraph-83.tar.gz`/`jgraph-8.3.tar.gz`
  均 404），现仅提供 8.4-8.6（`2024-02-15-Jgraph.tar`）。本配方使用 Debian 83-26
  的 orig tarball：sha256 `e413b98a…546`（109419 字节）与 Debian `.dsc` 的
  Checksums-Sha256 及实际下载字节完全一致；官网仍可下载的 2007 快照 `jgraph.tar.gz`
  中 `jgraph.c`/`jgraph.1`/`README` 与 Debian orig 逐字节相同，证明其为上游 83 正源。
  已合并先例：`archives/l/libmm`、`archives/l/libbrahe`、`archives/c/choose-mirror`、`archives/x/xe`。
- **10 个补丁均为可移植性修改**（无 `__OHOS__` 平台宏、无 `usr/local`/SYS_PREFIX 注入、
  无行为特性引入），分三类：
  1. K&R 过程改 `void` + 补前置声明（补丁 0001/0002/0003/0006/0007/0008/0009/0010），
     同上游 8.5 与 Debian 83-26 的做法；
  2. 无条件包含标准头 + 声明返回指针的链表原语（补丁 0003/0004/0005/0010），
     修复 aarch64 上 malloc/get_node/atof/sin 等隐式声明的指针/浮点截断
     （修复前二进制启动即 SIGSEGV）；
  3. 两处上游真实缺陷：EPS `%%BoundingBox` 的 EOF 检测（`fscanf == NULL` 恒假，
     上游 2007 快照同款修复）与 landscape 平移的 `%f` 传 `int`（64 位可变参数 ABI
     未定义，Debian 83-26 同款修复）。
- **L2 warn（非阻塞）**：jgraph 无 `--version`/`--help` 选项（任何非选项参数被当作
  输入文件名），CI smoke test 对其记 warn；真实功能由 25 条消费者断言覆盖。
- **L4 warn（非阻塞）**：`0010-token.c.patch` 命中 `strcpy`，均为上游 token.c 的
  上下文行（补丁只改函数返回类型与 include），非本适配新增代码。
- **已知限制**：编译仍有 31 条告警（K&R 非原型定义、部分内部函数隐式声明、个别格式串），
  均为上游 1992 年代码风格遗留；本适配只消除错误与 64 位截断/UB，未整体重构为
  原型式定义（上游 8.4-8.6 才做该重构），以保持补丁面最小。
- 构建与测试详情见 `reports/test-report.md`、`reports/conan-verify-report.md` 与 `notes.md`。
