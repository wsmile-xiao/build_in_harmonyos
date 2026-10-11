# tpm-tools 1.3.9.2 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 只带 `configure.ac`/`Makefile.am`，需要 autoreconf）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`），原生构建 aarch64 / HarmonyOS 6.0
- 状态: built

## 版本说明
- 上游: https://trousers.sourceforge.net/ （SourceForge 项目 `tpm-tools`），版本 `1.3.9.2`
- 源码: SourceForge 镜像在本网络超时，使用 Debian 官方归档同一 release：
  `https://deb.debian.org/debian/pool/main/t/tpm-tools/tpm-tools_1.3.9.2.orig.tar.gz`，
  sha256 `8af837949a2ec30b195389ac8a2b31bc49fe315050751b7d4d0d432bf7812a97`
- 版本号沿用赛事清单 `1.3.9.2`（首次适配，遵循 R37）

## 编译步骤
```bash
# 运行依赖：trousers/0.3.15（libtspi）、openssl/3.5.6.1、gettext/0.22.5（libintl）
# 构建期工具：automake/1.18、libtool/2.5.4、pkg-config/0.29.2
#               工作机自带 autoconf 2.72 与 gettext 前缀里的 autopoint
conan create archives/t/tpm-tools/1.3.9.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包没有 `configure` | release tarball 只带 `configure.ac`；上游 `bootstrap.sh` 依赖 gettextize | `build()` 里按 bootstrap.sh 的步骤准备 `po/`（从 `po_/` 复制）与 `m4/`，再执行 `autoreconf -fi` |
| 2 | `autoreconf` 报 `Can't exec "autopoint"` | `AM_GNU_GETTEXT_VERSION` 会触发 autopoint，但工作机的 autopoint 不在 PATH（位于独立 gettext 前缀） | 把工作机 gettext 前缀里的 `autopoint` 显式传给 autoreconf（`AUTOPOINT=…`）并把它所在目录加入 PATH |
| 3 | `autopoint` 报 `archive.dir.tar.xz: No such file` | autopoint 脚本内建了构建机的安装前缀（`/home/lycium++/…`），与实际安装位置不符 | 同时设置 autopoint 支持的 `gettext_datadir` 指向实际数据目录，autopoint 即可解出 0.15 时代的 gettext 基础设施 |
| 4 | `autoreconf` 报 `Cwd.so: Perl_my_cxt_init: symbol not found` | 系统 perl（运行工作机 autoreconf）通过 PERL5LIB 载入 registry perl 的 XS 模块 | `PERL5LIB` 收敛为 automake 自己的模块目录（与同批 trousers 配方一致） |
| 5 | `configure` 报 `working directory cannot be determined` | HMDFS 下 `getcwd()` 失败 | 生成 configure 后打运行时补丁：`pwd` 失败回退 `$PWD`；config.status 临时目录 `umask 077 → 022` |
| 6 | 无法执行 conftest（E064） | 鸿蒙只运行已签名二进制 | 显式传 `--build/--host=aarch64-unknown-linux-gnu` |
| 7 | `tpm_utils.c` 报 `incompatible integer to pointer conversion` | `getpass()` 是 BSD/glibc 扩展，musl/HarmonyOS 既未声明也未导出 | 补丁 0001：用 termios 实现无回显口令读取（保持 getpass 的静态缓冲区语义） |
| 8 | 静态构建时 libtool 报 `cannot build a shared library` | `lib/Makefile.am` 把 `-shared` 硬编码进 `libtpm_unseal_la_LDFLAGS` | 补丁 0002：去掉该硬编码，交由 libtool 按 configure 选项决定产物类型（共享/静态均可构建） |
| 9 | 消费者拿不到头文件 | 起初声明 `package_type = "application"`，Conan 不会向消费者导出 include/lib | 改为 `package_type = "library"` + `shared`/`fPIC` 选项；头文件位于 `include/tpm_tools/` |
| 10 | 上游没有测试套件 | `Makefile.am` 未注册 `check_PROGRAMS`/`TESTS`；`test/tpm_changeownerauth01.sh` 只在 `EXTRA_DIST` 里且需要真实 TPM | `build()` 内置 `grep`/`ls` 审计留证（R51 口径 N=0），补充消费者用例 |
| 11 | `tpm_nvinfo --help` 无法作为冒烟用例 | 该工具的用法路径打印后以 255 退出 | 冒烟只使用返回 0 的 `tpm_version --version/--help`；已在 test_package/conanfile.py 注释说明 |
| 12 | 产物带 libtool `.la` 包装 | libtool 默认安装 `.la`（记录构建机路径） | `package()` 清理 `lib/*.la` |

## 源码修改
- `patches/0001-tpm-utils-termios-password.patch` — `lib/tpm_utils.c`：用 termios 无回显读取口令，
  替代 musl 不提供的 `getpass()`
- `patches/0002-lib-makefile-let-libtool-decide.patch` — `lib/Makefile.am`：移除硬编码的 `-shared`

## 依赖版本
- `trousers/0.3.15`（libtspi，本仓库同批适配）、`openssl/3.5.6.1`（libcrypto）、`gettext/0.22.5`（libintl）
- 构建期工具：`automake/1.18`、`libtool/2.5.4`、`pkg-config/0.29.2`（tool_requires）+ 工作机 autoconf 2.72 / autopoint

## 验证结果
```bash
conan create archives/t/tpm-tools/1.3.9.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0
# 交付：lib/libtpm_unseal.a、include/tpm_tools/tpm_unseal.h、bin/tpm_*（20+ 个命令）、
#       share/man（手册页 27 个）、licenses/LICENSE（共 25 个打包文件 + 手册）

# 消费者用例
ok 1 - tpmUnsealStrerror(0) returns a non-empty message
ok 2 - tpmUnsealStrerror(0) reports Success
2 checks, 0 failures
# CLI 冒烟（无需 TPM）
bin/tpm_version --version  → "…/tpm_version version: 1.3.9.2"（rc=0）
bin/tpm_version --help     → Usage …（rc=0）
```

上游测试：该版本**不含测试套件**（各 `Makefile.am` 无 `check` 目标，`test/tpm_changeownerauth01.sh`
未注册且需要真实 TPM），因此按 TEST_QUALITY_SPEC 的要求在 `build()` 内置审计命令留证，并补充消费者
用例（库 API + 两个无需 TPM 的 CLI 路径）。详见 `test_package/MANIFEST.yml` 与 `reports/test-report.md`。

## 注意事项
- 交付静态库 `libtpm_unseal.a`（默认 `shared=False`；也可用 `-o tpm-tools/*:shared=True` 构建共享版本）。
- `tpm_*` 管理命令实际执行需要 TPM 设备；CI/消费者测试只覆盖无需设备的 `--version/--help` 路径。
- 本包依赖同批适配的 `trousers/0.3.15`（在制品仓发布前，CI 的依赖闸会等待其入库）。

---

### 对话 #1 — 编译协作者 (implementer)

**请求**: 在鸿蒙 PC 上完成 tpm-tools 1.3.9.2 的适配并按赛事流程提交 PR。

**执行摘要**:
1. 依赖预检（W0/R36）：`trousers`（同批适配）、`openssl`、`gettext` 与构建工具均在制品仓/工作机可用。
2. 构建链路：准备 gettext 工程骨架（`po_/` → `po/`、`m4/`）→ `autoreconf -fi`（显式传入工作机 autopoint +
   `gettext_datadir`、收窄 PERL5LIB）→ 运行时修补生成的 `configure`（HMDFS pwd/umask）→ `conan create` rc=0。
3. 上游测试清点（R51）：无 `check` 目标、唯一 shell 用例未注册且需真实 TPM → N=0 并在 `build()` 内置审计留证。
4. 关键问题与证据：autopoint 内建前缀失效（用 `gettext_datadir` 修正）；`getpass()` 在 musl 缺失（静态化
   termios 实现）；`-shared` 硬编码阻断静态构建；`tpm_nvinfo --help` 以 255 退出（冒烟改用 tpm_version）。
5. 质量门禁：conan-verify、W3 本地 CI 模拟、W4 独立审计（见 `reports/`）。

**产出文件**: `conanfile.py`、`conandata.yml`、`patches/`（2 个）、`test_package/`（4 个文件）、`notes.md`、
`manifest.yaml`、`commands.json`、`README.md`、`reports/test-report.md`。
