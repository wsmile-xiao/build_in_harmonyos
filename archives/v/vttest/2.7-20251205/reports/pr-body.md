## PR 信息
- **三方库名称**：vttest
- **上游版本**：2.7-20251205（上游 patchlev.h: RELEASE 2 / PATCHLEVEL 7 / PATCH_DATE 20251205；发行 tarball 名 vttest-20251205.tgz）
- **上游仓库地址**：https://invisible-island.net/vttest/（官方归档站 https://invisible-island.net/archives/vttest/）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E160（config.guess 不识别 HarmonyOS，cannot guess build type）、E129 / E112 / E136（HMDFS 对 umask 077 新建目录强制 setgid → config.status 临时目录不可写）、E011（config.guess 探测目录 umask）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无 tests/ 目录、无测试脚本与基准数据 |
| 集成测试 | 0 | makefile.in 无 check/test 目标，configure.in 未注册测试 |
| 其他测试 | 0 | vttest 本身即终端测试工具，用例由操作者在被测终端上菜单驱动 |
| **合计** | **0** | 清点证据见 test_package/MANIFEST.yml（R51） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无 |
| 集成测试 | 0 | 不变 | 上游无 |
| 鸿蒙特有测试 | 9 | 新增 | test_package 消费者回归：6 条 CLI 断言（二进制存在、`-V` 版本横幅逐字符匹配、`-V` 退出码 0、未知选项用法文本、未知选项非零退出、man page 安装）+ 3 条 PTY 交互断言（真实伪终端上启动、主菜单出现、选择 Exit 后退出码 0）；全部在 OHOS 真机实跑 |
| **合计** | **9** | **上游 0 + 新增 9** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游没有测试用例可修改；两个补丁只涉及 config.guess（平台识别）与
> configure（临时目录 umask），不改任何 C 源码与测试资产。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）
- [ ] **否**，上游已有测试用例覆盖

> - **补全的测试范围**：9 条消费者断言（6 条 CLI + 3 条 PTY 交互），覆盖"包可安装、二进制可执行、版本接口精确、错误输入按文档拒绝、man page 随包、真实终端下的菜单启动与干净退出"。
> - **补全原因**：上游自动化用例数 N=0——vttest 是交互式终端测试工具，没有预期输出基准（makefile 无 check 目标、tarball 无 tests/ 目录、vttest.1 说明用例由操作者驱动），只能以消费者视角在目标真机上回归。
> - **新增测试文件清单**：
>   1. `test_package/conanfile.py` — 消费者断言主体（`self.run` 实跑包内二进制；L1e 负向测试确认移除包产物后断言确实失败）
>   2. `test_package/pty_smoke.py` — PTY 交互冒烟（vttest 核心功能面；无 `/dev/ptmx` 的宿主显式 skip 77，不伪装通过）
>   3. `test_package/MANIFEST.yml` — 上游测试清点证据与断言计数申报

## 验证结果

- 编译状态：**通过**（conan create 干净构建；conan-verify G0–G4 全 PASS；`clean-verify` 仅凭官方 tarball + 两个补丁完成 configure → make → make install，G0 干净构建复现通过）
- 上游测试用例通过率：**N/A（上游 N=0，已附清点证据）**
- 新增测试用例通过率：**9/9（100%）**（test_package 在 OHOS 真机逐条实跑，含 PTY 交互）
- W3 本地 CI 模拟（与平台 CI 同脚本）：L0 pass / L1 pass（test_package executed）/ L1e 负向测试 pass（移除 bin/ 后 test() 确实失败）/ L2 skip（脚本探测 `--version/--help`，vttest 上游接口为 `-V`，脚本声明非阻塞）/ L4 pass（补丁无危险函数）/ L5 pass（bin/ 有产物）
- 独立 staging 回放：官方 tarball + 两个补丁（`patch -p1` dry-run 干净）→ `./configure && make -j1 && make install DESTDIR=...` → 安装出的 `bin/vttest -V` 输出 `VT100 test program, version 2.7 (20251205)`（rc=0），PTY 冒烟通过
- 产物：`bin/vttest`、`share/man/man1/vttest.1`、`licenses/COPYING`

## 补充说明

- **适配方式**：仅 2 个补丁，不改任何 C 源码、不注入 `__OHOS__`/`-D__OHOS__`：
  1. `patches/0001-config.guess.patch`：config.guess（GNU 2025-07-10）增加 HarmonyOS 平台识别（`aarch64:HarmonyOS` → `aarch64-unknown-linux-$LIBC`），并把 `set_cc_for_build()` 三处 `umask 077` 改为 022。没有该补丁时 configure 以 `cannot guess build type; you must specify one` 退出（E160）；同时 HMDFS 会把 umask 077 目录变成 owner 也不可写的 `drwx--S---`，导致探测编译失败（E011）。
  2. `patches/0002-configure.patch`：configure 内两处 `(umask 077 && mktemp -d "$TMPDIR/csXXXXXX")` → `umask 022`。HMDFS 对 umask 077 新建目录强制 setgid，config.status 会报 `could not setup config files machinery`（E129/E112/E136；与已合入的 a52dec/0.7.4、teseq/1.1.1 同款）。
- **构建依赖**：无外部库依赖（纯 C + POSIX tty API）；configure 随 tarball 发布，构建期无需 autoconf/automake。
- **平台特性验证**：vttest 的功能面只有真实终端能驱动，因此消费者回归中专门加入 PTY 冒烟（Python pty，不依赖外部 expect/script 工具），在 HarmonyOS PC 真机上实测启动主菜单并干净退出。
- **已知限制**：L2 通用冒烟脚本按 `--version/--help` 探测，vttest 上游接口为 `-V`，该项在 CI 中记录为 skip（脚本内明确非阻塞）；PTY 断言在无 `/dev/ptmx` 的宿主会显式 SKIP（exit 77）。
