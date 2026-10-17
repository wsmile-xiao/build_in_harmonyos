- **三方库名称**：ytnef
- **上游版本**：v2.1.2
- **上游仓库地址**：https://github.com/Yeraze/ytnef
- **适配路径**：路径 A（基础适配）
- **使用知识库**：skill `openharmony-compile-agent`（§0~§9 + 铁律 R1-R52 + W0-W5）；命中知识条目 **E007**（config.guess 无 HarmonyOS 分支）、**E114**（HMDFS 下 `umask 077 && mktemp -d` 目录不可写）、**E074**（make jobserver FIFO EPERM）、**E205**（禁止用 `--build/--host` 绕过）、**E490**（autotools 生成脚本执行位）、**E533**（config.guess 缺 HarmonyOS 分支同类案例）；参考 `references/patch-pipeline.md`、`knowledge/operations/build-systems.md`、`knowledge/ARCHIVE-SPEC.md`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游无单元测试框架（仓库内无 tests/、无 ctest/pytest 注册） |
| 集成测试 | 8 | 来源：test-data/test.sh（1 组附件提取 + 1 组 `diff results data` 字节级比对 + 5 组 ytnefprint 字段断言 + 1 组畸形输入健壮性断言） |
| 其他测试 | 0 | 上游无其他测试载体；`test-data/Makefile.am` 仅有 `EXTRA_DIST`，**不存在 `make check` 目标**，上游 travis-build.sh 即直接 `cd test-data && ./test.sh` |
| **合计** | **8** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试，未虚构补全 |
| 集成测试 | 8 | 不变 | test-data/test.sh 原样执行，且已集成进 `conanfile.py` 的 `build()`，CI 每次构建都会重跑 |
| 鸿蒙特有测试 | 10 | 新增 | conan test_package：`test.c` 链接 libytnef 的 8 项 API 断言（R34 真实调用被测 API，解析真实上游 TNEF 夹具）+ 已安装 CLI 的 2 项冒烟（`ytnef -h` / `ytnefprint -h`） |
| **合计** | **18** | **+10** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> `test-data/test.sh`、6 个 `*.tnef`、`winmail.dat`、`results/` 全部按上游原样保留并使用，未做任何改动。
> 适配所需的处置都在配方运行时完成（config.guess/config.sub 补全、configure 中 `umask 077` 处置），不落 `patches/`，`patches/` 为空。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游已有可运行的集成测试套件，适配后完整保留并通过。新增的 10 项属**消费者视角**的鸿蒙特有测试
> （conan test_package），不替代上游用例。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：8/8（100%）
- 新增测试用例通过率：10/10（100%）

## 补充说明

**产物清单**（`shared=False` 默认，静态；`-o ytnef/*:shared=True` 可产出 `libytnef.so.0.0.0`）
- `lib/libytnef.a`、`lib/pkgconfig/libytnef.pc`
- `include/`：ytnef.h、mapi.h、mapidefs.h、mapitags.h、tnef-types.h、tnef-errors.h
- `bin/`：ytnef、ytnefprint、ytnefprocess（上游 perl 脚本，原样安装）
- 软件级 `commands.json` 已声明（R38，type=tool）

**依赖与工具链**
- 上游依赖：**无第三方库**（configure.ac 仅 `AC_PROG_CC`/`AC_PROG_LIBTOOL`，无 `AC_CHECK_LIB`、无 pkg-config），W0 依赖链为空，无需先发布任何依赖。
- `tool_requires`：`automake/1.18` + `libtool/2.5.4`。上游 tag 快照为 git-archive，**不含 `configure`**，必须 `autoreconf -fi` 引导；本机与 CI 均无系统 automake/aclocal/libtoolize（HNP 只提供 autoconf 套件），故用 tool_requires 补齐（与 `archives/a/abiword-plugin-*/3.0.8` 同款）。

**OHOS 适配要点（全部在配方内完成，无源码补丁）**
1. **E007 — config.guess 不识别 HarmonyOS**：`uname -s = HarmonyOS` 无法匹配任何已知系统，configure 报 `cannot guess build type`。按知识库要求补 config.guess（新增 `*:HarmonyOS:*:*)` → `${MACHINE}-unknown-linux-ohos`），**未使用 `--build/--host`**（E205/R1 禁止）。实测 configure 输出 `checking build system type... aarch64-unknown-linux-ohos`、`checking whether we are cross compiling... no`。
   - config.guess/config.sub 由 `autoreconf` **生成**，pristine tarball 中不存在（`.orig` 无此文件），无法用 conandata 补丁表达，故在 `build()` 中 autoreconf 之后就地进行（幂等）；`config.sub`（automake 1.18 版）已支持 `linux-ohos`，仅在缺失时补齐。
   - 注入分支不含 `__OHOS__` 平台宏（HarmonyOS 不进入 Linux/GNU 段，无需 LIBC 探针），因此不触发 R8/PF5 平台宏闸。
2. **E114 — HMDFS 权限**：系统 autoconf 生成的 `config.status` 走 `umask 077 && mktemp -d "./confXXXXXX"`，HMDFS 把 0700 目录变成 `drwx--S---`（属主亦不可写），报 `./config.status: ... subs1.awk: Permission denied`。运行 configure 前去掉生成脚本中的 `umask 077`（abiword-plugin-*、abook 同款）；不改上游源码。
3. **perl 一致性**：conan `automake/1.18` 的 `aclocal`/`automake` 包装脚本指向系统 perl，而 `VirtualBuildEnv` 的 `PERL`/`PERL5LIB` 指向 conan perl（不同 ABI），混用会报 `Cwd.so: Permission denied` / `Perl_my_cxt_init: symbol not found`。引导阶段统一到系统 perl 并把 conan automake 的 `share/automake-*` 加入 `PERL5LIB`。
4. **E074 — make jobserver FIFO**：HMDFS 禁止创建 jobserver FIFO，所有 `make`（含 `make install`）统一 `-j1`。
5. **E490 — 生成脚本执行位**：autoreconf 后对 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`/`compile`/`depcomp` 显式 `chmod +x`，防止某些拷贝路径丢执行位。
6. **R51 — 上游套件进 CI**：`build()` 内执行 `cd test-data && bash ./test.sh`。Conan 使用 out-of-source 构建（build 目录在 source 目录之下），`test.sh` 以 `../ytnef/ytnef` 相对路径取二进制，故先把 `test-data/` 夹具镜像进 build 目录再运行。

**源码与校验**
- `sources.url`: `https://codeload.github.com/Yeraze/ytnef/tar.gz/refs/tags/v2.1.2`（GitHub 官方 codeload；**不使用** `https://github.com/...` 形式以避免 ghfast.top 镜像注入依赖）
- `sources.filename`: `ytnef-2.1.2.tar.gz`（codeload URL 以裸 tag 结尾，不给 filename 会被按 zip 解压并报 `BadZipFile`）
- `sources.sha256`: `340f03f495884611209e9c0bc943fad06ce920e8c79655aa228d5ca7418dc360`（= 上游 tag v2.1.2 / commit d9f089144414d3b0912c29ab96f8f1c591d00319）

**CI 注意事项（实测教训）**
- 本 PR **不含任何二进制文件**：GitCode 的 MR `.diff` 端点不携带二进制补丁数据（无 `GIT binary patch` 段），
  而 CI 的 `checkout-pr` 步骤用 `git apply pr.diff` 重建工作区，只要 PR 新增二进制文件该步就必然失败
  （`error: missing binary patch data for ...`，并误导性提示"PR 与 main 分支存在冲突"，整个构建约 5 秒即终止）。
  因此 test_package 的上游 TNEF 夹具以上游原始文件 `one-file.tnef`（2272 B）的 **base64 文本** `one-file.tnef.b64`
  分发，由 `test_package/conanfile.py` 的 `_materialise_fixture()` 在 ctest 前还原为二进制再喂给 `TNEFParseFile`。

**已知限制 / TODO**
1. `ytnefprocess` 为上游遗留 perl 脚本，硬编码 `/usr/bin/ytnef` 且依赖 `MIME::Parser`/`Mail::Mailer` 等 CPAN 模块；本包按上游 `make install` 原样安装，未改动、未在 CI 执行（仅验证 `ytnef -h`/`ytnefprint -h`）。
2. 默认静态链接（与仓库 autotools 模板一致）；libytnef 非系统同名库，不受 R26 强制约束，`shared` 选项可自由切换。
3. `test-data/` 的 6 个 `*.tnef` + `winmail.dat`（约 300KB 夹具）随源码包进入构建，属上游测试资产，未打包进制品。
4. 无 `patches/`（无源码补丁）；`conan-verify` G0-G4 + L2/L4/L5 全绿。
