- **三方库名称**：cpu（Change Password Utility）
- **上游版本**：v1.4.3
- **上游仓库地址**：https://cpu.sourceforge.net/（源码取自 Debian pool：https://deb.debian.org/debian/pool/main/c/cpu/cpu_1.4.3.orig.tar.gz）
- **适配路径**：路径 B（贡献创新 —— 知识库扩展：新增 6 条知识草稿 E568/E569/E570/E571/E572/E573）
- **使用知识库**：build_in_harmonyos（openharmony-compile-agent）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无测试框架：`src/**/Makefile.in` 的 `TESTS` 为空，`make check` 无任何用例（输出 `Nothing to be done for 'check-am'`，rc=0） |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | 仅有 `doc/test.ldif`（LDAP fixture 数据，非可执行测试） |
| **合计** | **0** | 上游不带任何自动化测试 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | +1 | `test_package/consumer.c`：消费者程序，链接 `libcputil.so` 并调用其公开 API（10 个断言：`CPU_getUserId`/`CPU_getUserName`/用户名与 UID 互查/`CPU_init` 分发等） |
| 集成测试 | 7 | +7 | `test_package/test.sh`：`cpu --version` 报上游版本 1.4.3、`cpu --help` 用法行与 `--method=` 选项说明、`-M bogus` 负向控制（`CPU_loadLibrary` 报错路径，用于证明后续断言可失败）、`-M ldap` 插件经 `dlopen("libcpu_ldap.so", RTLD_NOW)` 实际加载接管（2 项断言：不出现 `CPU_loadLibrary` 失败、不出现 “error loading the ldap library”）、`consumer.c` 与 `libcputil.so` 编译链接成功 |
| 鸿蒙特有测试 | 3 | 新增 | 平台安装布局/加载路径专有断言：①`bin/cpu` 按 OHOS 布局（`bin/` 而非上游 `sbin/`）随包安装，并在 CLI 用例中被实际执行（HMDFS 忽略 chmod → E490）；②`lib/libcputil.so` 按 E522 私有 prefix 影子布局随包发布、可被消费者程序链接与运行时加载；③`lib/libcpu_ldap.so` 以 `-module -avoid-version` 插件形态随包发布且可被 `dlopen` 加载（库与插件的加载路径全在包内，零写 `/usr/local` 共享树） |
| **合计** | **11** | **+11** | conan 测试实跑输出：`== 11 passed, 0 failed ==`（`test_package` 由 `conan create`/`conan test` 驱动，W3 与 CI 同源） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 `make check` 无任何用例可执行，因此不存在“修改上游测试用例”的情形；
> 适配过程中的源码补丁仅用于构建/平台适配，未触碰测试代码。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为核心功能补全 11 项检查（1 个消费者单元程序 + 10 项集成/CLI 检查），覆盖库 API、主程序 CLI、插件 `dlopen` 加载路径、LDAP 配置解析与安装布局。
> - **补全原因**：上游为 2003 年代码库，仅有 `Makefile.in` 中空置的 `TESTS` 变量与一份 LDIF fixture，无任何自动化测试框架；同时 `cpu` 是插件式（`dlopen`）程序，插件加载失败在无测试时完全静默。
> - **新增测试文件清单**：
>   1. `archives/c/cpu/1.4.3/test_package/conanfile.py` — conan 测试入口（`test_type = "explicit"`，经 Python `subprocess` 启动 `test.sh`）。
>   2. `archives/c/cpu/1.4.3/test_package/consumer.c` — 消费者程序：对已安装的 `libcputil` 做 10 个 API 断言。
>   3. `archives/c/cpu/1.4.3/test_package/test.sh` — 检查脚本：11 项检查（含以 `consumer` 消费者程序驱动的单元用例），`== N passed, M failed ==` 汇总。
>   4. `archives/c/cpu/1.4.3/test_package/MANIFEST.yml` — 声明上游测试来源与补全边界（满足 L0e）。

## 验证结果

- 编译状态：通过（`conan create` 全流程：configure → make → install → package 均 rc=0；W3 记录 `.ci-result.json` `exit_code=0`，`integrity_hash=128aad70199c0872`）
- 上游测试用例通过率：—（上游 0 个用例，`make check` 为空操作 rc=0）
- 新增测试用例通过率：11/11（100%）

## 补充说明

1. **补丁规模：最小补丁替代整文件替换（无平台宏）**：`patches/0001-config.guess.patch`（+3 行）在 `case` 首插入 `aarch64|arm64:HarmonyOS|HongMeng` 命中分支，直接输出 `aarch64-unknown-linux-ohos`；`patches/0002-config.sub.patch`（+4/-1 行）在 `maybe_os` 白名单加入 `linux-ohos*`，并在通用 `-linux*)` 之前截住，避免 `linux`→`linux-gnu` 改写。守卫条件是 `uname` 文本，**不含 `__OHOS__` 等平台宏**，因此无需 R8 例外申报，也不再触发 PF5 预检。此前使用的整文件替换（`config.guess` +1235/-810、`config.sub` +1687/-1232，补丁文件合计 5841 行）已移除，PR 体量从 8420 行降至 2671 行（38 文件 +2671/-26），AI 检视不再因体量跳审；两个补丁产出的 triplet 与替换方案逐字等价（`aarch64-unknown-linux-ohos`），测试结果一致（11/11）。
2. **平台适配要点**：`E007`（config.guess/config.sub 不识别 OHOS）、`E046`（HMDFS 上 chmod 无效 → 直接 patch 生成的 `configure`，umask 077→022）、`E063`（`-Werror` 放大警告 → 按类别精准降级）、`E522`（openldap 的 `.la` 闭包残留 `libdir='//lib'` → 影子目录实体拷贝 + 改写 `.la` 闭包）。
3. **真 bug 修复（上游缺陷）**：`src/util/cgetpwent.c` 缺 `<stdlib.h>`（`malloc` 隐式声明在 64 位下截断指针）；`src/util/hash.c` 的 `#ifndef crypt` 守卫错误 → 改为 `#ifdef HAVE_CRYPT_H`。
4. **已知限制**：`passwd` 插件在上游即为 stub（`CPU_init`/`passwdOperation` 为空实现，源码自述 "Do not use me. I don't work!"），因此测试改为验证其**加载与分发路径**而非功能；LDAP 测试在无 LDAP 服务器时止步于连接阶段（不发真实请求）。
5. **知识库扩展（路径 B）**：新增 6 条知识草稿（`.kv` 结构化条目 + 配套 `.md` 详解）：`E568`（`AC_FUNC_MALLOC` 运行期探针误判 → `config.h` 定义 `malloc=rpl_malloc` → 隐式声明在 aarch64 上截断指针；方案 = 配方向 configure 注入 autoconf 标准 cache 变量）、`E569`（上游 `Makefile.in` 写死 in-tree 相对 include 路径 `-I../../src/include`，conan 独立 build 目录下头文件找不到；方案 = `extra_cflags` 注入绝对 include 根）、`E570`（本平台 conan `self.run()` 恒 SIGSEGV（`Error -11`），与命令内容无关——runner 层限制；方案 = `test_package` 改用 Python `subprocess` 直启）、`E571`（手写 `install-data-local` 缺 `$(DESTDIR)` 且未用 `$(srcdir)`，staging 下装到宿主 `/etc` 使包内缺文件、out-of-tree 时找不到源文件；方案 = 补丁 `0004-doc-Makefile.in.patch`，可上游化）、`E572`（老式 `config.guess`/`config.sub` 不识别 HarmonyOS/aarch64：最小补丁（+7/-1 行）替代整文件替换（补丁文件 5841 行）；方案 = `case` 首插入 `HarmonyOS`/`HongMeng` 命中分支 + `maybe_os` 白名单与 `-linux*)` 两处守卫，产出 triplet 与仓库事实标准 OHOS-aware 探针逐字等价）、`E573`（`test_package` 现场编译消费者程序时，clang 驱动的链接器 `lld` 自身动态依赖 SDK `llvm/lib` 下的 `libxml2.so.16`：conan test 的 runenv 只导出包目录，lld 能否启动取决于调用它的 shell 环境（同一提交重跑时红时绿），叠加 musl "命中同名但不可加载条目即硬失败" 语义；方案 = 测试脚本用 `command -v` + `readlink -f` 前置工具链 lib 目录、必要时 `-fuse-ld=bfd` 兜底、链接产物 `chmod +x`，recipe 侧把 `LD_LIBRARY_PATH/PATH` 由相对 `cpp_info` 目录改为绝对包目录）。
6. **预检（PF1-PF6）说明**：改用最小补丁后 `patches/` 中不再出现 `__OHOS__` 等平台宏，PF5 自然通过；本包此前使用 `OHC_PREFLIGHT=0` 规避的只是基线分支落后 origin/main 时 PF1/PF5/PF6 把他处改动计入本包的框架误报（见第 1 条），与本次改动无关。
