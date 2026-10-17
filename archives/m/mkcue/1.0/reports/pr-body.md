- **三方库名称**：mkcue
- **上游版本**：1（上游为 SVN、无版本递增；Conan 侧归一化为 1.0 —— 见「补充说明」第 1 条）
- **上游仓库地址**：https://diplodocus.org/ （SVN：svn+ssh://diplodocus.org/svn/projects/release/mkcue-1/，无公开 git/commit）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E007（config.guess/config.sub 的 OHOS 三元组识别）、E011 / E110 / E052（HMDFS 下 config.status 临时目录 Permission denied）、E141（manifest configure_options 空列表被解析为字面 `[]`）、E490（autotools 脚本可执行位）、R33（编译标志取自 Conan toolchain）、R47（语言预检：cpp）、DRAFT-btyacc-3.0-conan-single-char-version（版本号长度约束的既有草稿先例）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无测试框架；tarball 文件清单无 `tests/`、无 `*.test` |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | `GNUmakefile.in` 仅 `all / clean / maintainer-clean / install / dist`，无 `check`/`test` 目标；Debian `debian/rules` 亦无 `TEST_TARGET` |
| **合计** | **0** | 清点证据见 `archives/m/mkcue/1.0/reports/upstream-test-entry.md` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无 |
| 集成测试（消费者验证 `test_package/`） | 6 | +6 | 由 `README:7-10` 用法 + `mkcue.cc` 参数校验派生，**实际执行打包后的二进制** |
| 鸿蒙特有测试 | 3 | 新增 | AArch64 ELF / `.codesign` 段（E077）/ OHOS musl 解释器 |
| **合计** | **9** | **+9** | 实跑结果 `TOTAL=9 PASS=9 FAIL=0 SKIP=0` |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（上游不存在任何测试用例，无可修改对象）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试

> - **补全的测试范围**：6 例上游文档化行为（默认设备 `/dev/cdrom` 打开失败、显式设备参数、`-t 0` 拒绝、`-t 100` 拒绝、`-t 1` 接受后设备失败、未知选项打印 usage）+ 3 例鸿蒙平台特性（ELF 架构 AArch64、`.codesign` 签名段、OHOS musl 解释器）
> - **补全原因**：上游 tarball 无 `tests/` 目录、`GNUmakefile.in` 无 `check`/`test` 目标、Debian 打包无测试目标 ⇒ 不存在可运行的上游测试入口；只能依据「上游文档化用法 + 源码参数校验」派生消费者用例
> - **新增测试文件清单**：
>   1. `archives/m/mkcue/1.0/test_package/test_mkcue.py` — 9 例用例运行器（逐例执行打包后二进制，输出 PASS/FAIL/SKIP 统计与日志）
>   2. `archives/m/mkcue/1.0/test_package/conanfile.py` — Conan 消费者测试配方（`test_type = "explicit"`，`can_run` 守卫）
>   3. `archives/m/mkcue/1.0/test_package/MANIFEST.yml` — 用例清单与断言数（`assertion_count: 9`）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：N/A（上游无测试套件）；可执行的上游样例 **6/6（100%）**
- 新增测试用例通过率：**9/9（100%）**

## 补充说明

1. **版本号归一化 1 → 1.0**：Conan `RecipeReference.validate_ref()` 的校验正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}$` 要求版本号至少 2 字符；上游字面版本 `1` 在 `conan create` 的导出阶段被拒（`ERROR: Invalid package version '1'`，制品仓同样拒绝）。故版本目录与分支统一为 `1.0` / `feat/mkcue-1.0`。
2. **源码来源（R39）**：上游仅有 SVN，其官网发行包链接 `https://diplodocus.org/dist/audio/mkcue-1.tar.bz2` 已失效（实测 **HTTP 404**，下载体为 373 字节 HTML）。故 `sources.url` 取 **Debian 官方主归档** `https://ftp.debian.org/debian/pool/main/m/mkcue/mkcue_1.orig.tar.gz` 上的上游原始发行包：`Last-Modified: 2005-08-11`、`Content-Length: 80650`、sha256 `2aaf57da4d0f2e24329d5e952e90ec182d4aa82e4b2e025283e42370f9494867`（与 Debian 源包 `1-9.dsc` 的 `Checksums-Sha256` 逐字一致），解包即上游树 `mkcue-1.orig/`；**非** `+dfsg` / `.debian.tar.xz` 形式的重打包。未使用任何第三方镜像/代理/个人 fork 源（同路径 `deb.debian.org` 命中 PF7 主机黑名单，故不采用）。
3. **5 枚适配补丁（均为平台/工具链必需；`mkcue.cc`、`osdep/*.cpp`、`osdep/*.h` 业务逻辑零改动）**：
   - `0001-GNUmakefile.in.patch` — install 规则补 `${INSTALL_DIR} ${DESTDIR}${bindir}`（上游 Makefile 定义了 `INSTALL_DIR` 却从未使用，导致 `make install` 报 `No such file or directory`）
   - `0002-build-config.guess.patch` / `0003-build-config.sub.patch` — 增加 HarmonyOS 识别分支与 `aarch64`/`arm64`、`linux-ohos` KERNEL-OS 组合（E007/E072）
   - `0004-configure.patch` — `configure` 中 `umask 077 → 022`（HMDFS 目录属主 UID 映射导致 config.status 临时目录不可写，E011/E110/E052）
   - `0005-diskid.h.patch` — 局部 `typedef unsigned char byte` 更名 `byte_t`（`diskid.h` 含 `using namespace std;`，C++17 下与 `std::byte` 二义）
   另有两处配方侧适配：`generate()` 追加 `-I<source> -I<build>`（上游手写 Makefile 非 VPATH-clean，`AC_LINK_FILES` 生成的 `mb.cc/mb.h` 与 `diskid.h` 分处两目录）；`build()` 恢复 autotools 脚本可执行位（E490）。
4. **第三方依赖 = 0**：链接行仅 `mkcue.o mb.o`（无 `-l`），`configure.ac` 的 `*-linux*` 分支不设 `LIBS`；仅使用 libc / libstdc++ / Linux 内核头（`<linux/cdrom.h>` 由 OHOS SDK sysroot 提供）。本 PR **不含任何依赖库文件**。
5. **不可测项（如实记录，未伪装通过）**：TOC 读取 happy path 需要真实 CD 设备与 `CDROMREADTOCHDR` / `CDROMMULTISESSION` / `CDROMREADTOCENTRY` ioctl，本机与 CI 均无光驱，故未纳入用例；已确认其编译依赖在 OHOS sysroot 中存在且通过编译。
6. **W3 本地 CI 结果**：`L0/L1/L5/JC/KC = pass`；`L2 = skip`（mkcue 无 `--version`/`--help` 长选项，属上游设计）；`L4 = warn`（补丁文本中含 shell 构造，非阻塞）；打包通过率 100%（1/1）。`.ci-result.json` 由 `finish` 写入，`exit_code=0`，含 W3 日志 SHA256 绑定。
7. **R40（深度适配库完整性）不适用**：mkcue 为命令行工具，产物为单个可执行文件，无图形渲染 / UI 框架 / 多媒体 / 外设 / 系统底层类库的平台适配代码（`mkcue.cc`、`osdep/mb_linux.cpp` 业务逻辑零改动），故不属需验证"实质性平台适配代码"的类别。
8. **本 PR 未改动 `knowledge/`**：适配中发现的框架级问题（旧版 `patch-autotools-ohos.pl` 在 2002 版 `config.guess`/`config.sub` 上失效、`refresh-patch` 因 `_SKIP_DIRS` 含 `build` 而漏采 `AC_CONFIG_AUX_DIR(build)` 下的脚本、`finalize-archive` 的 notes 一致性检查噪音、`gen_summary` 崩溃、本地 W3 不执行 L0n）记录于 `archives/m/mkcue/1.0/reports/framework-findings.md`，如需沉淀为知识库条目将另行以【知识库扩展】提交。
