# libfvde 20240502 适配笔记

## 当前状态

- 状态：built（真机 `conan create` 全流程通过：原生构建 + 上游 `make check` + `test_package`；制品尚未上传）
- 分支：`feat/libfvde-20240502`
- worktree：`/storage/Users/currentUser/ws/worktrees/libfvde-20240502`
- 任务目录：`/storage/Users/currentUser/tmp/libfvde-20240502`（证据与日志）
- 基线：`13ccffa4f57e0afea6aa15a97f135ed594fad059`（本地 `upstream/main` 已前进 4 个提交，均为 archives/ 与 knowledge/drafts/，不涉 `ci/`、`templates/`、`scripts/`）

## W0 依赖检查

上游 `configure.ac` 通过 `AX_*_CHECK_ENABLE` 把 17 个 libyal 组件作为**本地依赖**参与构建：

`libbfio libcaes libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit
libcthreads libfcache libfdata libfguid libfplist libfvalue libhmac libuna`

这些组件目录与预生成的 Autotools 文件都在发布包内（自包含发布包），且归档中没有它们的独立
Conan 包，`ohpcd` 远端也没有对应 recipe。按"一库一分支"约束，本 PR **不混入**这些依赖的适配，
也不调用未锁定的 `synclibs.sh`；配方在 `build()` 开头显式校验闭包完整性（17 个目录 +
`configure`/`aclocal.m4`/`config.guess`/`config.sub`/`Makefile.in`），缺失即报
`ConanInvalidConfiguration` 而不是静默联网补齐。

外部依赖：**零**。zlib 由 OHOS SDK sysroot 提供（`.../sysroot/usr/include/zlib.h` 实测存在），
libhmac/libcaes 走包内自带实现（见下），libfuse 显式关闭。

## W1 源码与构建系统

- 上游项目：`https://github.com/libyal/libfvde`
- 目标版本：`20240502`（GitHub release asset `libfvde-experimental-20240502.tar.gz`）
- SHA256：`c2d22eca9f646a5a388c6c22d6920292832384800ebeb519c03907bd5003c49b`
  （`curl` 下载后实测 gzip magic `1f 8b`、3 287 900 字节）
- tag → 提交：`git ls-remote https://github.com/libyal/libfvde 20240502` =
  `462a01d7af1732ca3bf1a12a16c0c5262d5ecd3e`（轻量 tag 直接指向提交）
- 构建系统：Autotools（发布包内含预生成 `configure`/`aclocal.m4`/`Makefile.in`）
- 上游测试入口：`make check`（`tests/Makefile.am`）

### 语言预检（R47）——已知误判的复核

`lang-preflight` 在**全量源码树**上判 `detected_language=mixed`（`expected=cpp`）并写
`env_unsupported` 终态。命中项是 libyal 发布包**根级**的 Python 绑定打包文件，不是主体语言：

| 文件 | 实测内容 |
|---|---|
| `pyproject.toml` | 仅 `[build-system] requires = ["setuptools", "wheel"]`，无 `[project]` 段 |
| `setup.cfg` | `[metadata] name = libfvde-python`、`description = Python bindings module for libfvde` |
| `setup.py` | 第 3 行自述 `Script to build and install Python-bindings.` |

源码统计 `c:271, bash:7, python:6, cpp:1`（c 占 97%），主体构建系统是 autotools。按 R47
边界规则"辅助脚本/绑定包不算主体"排除这 4 个绑定打包文件（`pyproject.toml`、`setup.py`、
`setup.cfg`、`setup.cfg.in`）后重跑：`detected=cpp`、`build_system=autotools`、
`manifest=configure.ac`、c 占 98%、rc=0（日志 `$TASK_DIR/lang-preflight-recheck.log`）。
结论：属已知误判类，不构成终止任务依据。上游测试与消费者测试在本 PR 中全部按 cpp/C 工具链执行。

## W2/W3 配方与 test_package

- `conandata.yml`：固定 `url` + `sha256` + 显式 `filename`（避免 Conan 由 URL 推断压缩格式）
- `conanfile.py`：`export_sources()` + `apply_conandata_patches()`；`requirements` 为空；
  `validate()` 限定 `Linux/OHOS`；`package_type=library`；`options shared/fPIC`
- configure 选项：`--disable-python --with-libfuse=no --enable-static-executables=no
  --with-openssl=no --enable-shared --disable-static
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
- **in-source 构建**：在该源码目录内 `configure` → `make -j1` → `make -j1 check` →
  `make install DESTDIR=<package_folder>`（`cwd=source_folder`）

### 为什么要 in-source + `--with-openssl=no`

发布包内置了维护者机器生成的 `common/config.h`：

- `common/config.h:239` `#define HAVE_LIBCRYPTO 1`、`:419` `#define HAVE_OPENSSL_EVP_H 1`
- 模板 `common/config.h.in:238/418` 对应的是 `#undef`
- `common/common.h:26` 用**引号包含** `#include "config.h"`，源树副本优先于构建树新副本
- OHOS SDK 26.0.0.18 sysroot **没有** `usr/include/openssl/evp.h`

即：只要构建发生在源树目录，陈旧的 `HAVE_OPENSSL_EVP_H=1` 就会让 libhmac/libcaes 去 include
一个不存在的头（同族 libbde/20240502 配方注释记录了完全相同的现象）。in-source 构建让
`config.status` 把新头写回**源树同一路径**（构建日志可见 `config.status: creating common/config.h`），
从物理上覆盖陈旧副本；`--with-openssl=no` 进一步让 libhmac/libcaes 固定走包内本地实现，
既消除该风险也不引入声明外依赖。构建日志中 libhmac/libcaes 全程无 `openssl/evp.h` 报错。

### 测试期处理

- `tests/test_runner.sh` 的 libtool 包装脚本要解析到真实 ELF：配方改写其两个分发分支指向
  `<dir>/.libs/<name>`（替换次数断言为 2，上游布局变化即显式失败）
- `make check` 通过 `LOG_COMPILER="<CONFIG_SHELL 绝对路径>"` 启动 shell 驱动（HMDFS 禁止直接执行脚本）
- `make check` 前把 `libfvde/.libs` 注入 `LD_LIBRARY_PATH`（本包默认 shared）

### test_package

- `test_libfvde.c`（通用消费者，11 项断言）：版本字符串、只读访问标志、`libfvde_get_codepage`
  正常与错误路径、`libfvde_set_codepage(0)`、`libfvde_check_volume_signature(NULL)` 错误路径、
  通知流 set/close、`libfvde_volume_initialize/free`
- `test_ohos.c`（鸿蒙特有，5 项断言，仅 `__OHOS__` 编译）：编译目标为 HarmonyOS、包版本、
  `TMPDIR` 非 `/tmp` 且可写、临时文件创建-写入-读回、清理后不可访问
- 首轮实测发现 `libfvde_notify_stream_close()` 成功返回 **0**（上游文档：仅当流由库自己
  `open` 时才关闭并返回 0），断言写 1 时消费者测试如实 FAIL（`FAIL: notify_stream_close failed`）；
  按上游 API 语义修正断言后 11/11 通过。该失败被完整保留在开发轮日志里，说明消费者测试
  是真断言而非空壳

## W4 本机验证（设备真机，W3 同源）

```sh
. "$HOME/tmp/libfvde-20240502/env.sh"
cd "$TARGET_REPO"
conan create "$PACKAGE_DIR" \
  -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE" \
  --build=missing --user=ohpcd --channel=stable -c tools.build:jobs=2
```

实测结果（开发轮 `$TASK_DIR/dev-build1.log` + `dev-build2.log`）：

- 上游 `make check`：`PASS: test_library.sh`、`PASS: test_tools.sh`、`SKIP: test_fvdeinfo.sh`；
  `test-suite.log` 汇总 `# TOTAL: 3 / # PASS: 2 / # SKIP: 1 / # FAIL: 0 / # ERROR: 0`
- 27 个 `fvde_test_*` 二进制逐个执行并 PASS（`test_library.sh.log` 25 行
  `Testing: <name> (PASS)` + `test_tools.sh.log` 2 行）
- `test_fvdeinfo.sh` exit 77：发布包 `EXTRA_DIST` 只含 `check_SCRIPTS`、不含 `tests/data`，
  无 `tests/input` 固件，属**上游设计**（非 OHOS 缺组件）
- `test_package`：`libfvde 20240502 consumer test: 11 assertions passed` +
  `libfvde OHOS-specific test: 5 assertions passed`

## W5 真机问题与处理

1. **陈旧 `common/config.h` 遮蔽新生成头**（见 W2）：改 in-source 构建 + `--with-openssl=no`。
2. **`config.guess/config.sub` 不识别 HarmonyOS**：显式传 GNU 三元组
   `--build/--host=aarch64-unknown-linux-gnu`，不跑 `autoreconf`（设备有 automake，
   CI worker 没有 → 设备全绿不等于 CI 绿）。
3. **autoconf 的 `umask 077` 临时目录在 HMDFS 上不可用**：构建全程 `umask 022`，
   并把 `configure` 里的 `umask 077` 就地改成 `022`。
4. **libtool 测试目标是包装脚本**：改写 `tests/test_runner.sh`（见上），注入 `libfvde/.libs`。
5. **脚本不可直接执行**：`configure` 与 `make check` 驱动一律经 `CONFIG_SHELL` 解释器启动。
6. **`init-build` 首次下载 TLS 失败**（urllib `CERTIFICATE_VERIFY_FAILED`，同 URL `curl`
   可达）：改用 overlay 的任务私有离线种子 `OHC_INIT_BUILD_TARBALL` 完成源码获取，
   种子已核 gzip magic 与 sha256；工具侧问题另见 `feedback/pending/2026-09-19-libfvde-20240502.md`。

## Path B 知识扩展候选

- `knowledge/drafts/DRAFT-E588-libyal-bundled-configsh-ssl-shadow.kv`
- `knowledge/drafts/DRAFT-E588-libyal-bundled-configsh-ssl-shadow.md`

候选主题：**发布包内置的陈旧生成头（`common/config.h`）遮蔽 configure 新生成头**。
判据链：发布包 `config.h` 是维护者机器内容（`HAVE_LIBCRYPTO=1`/`HAVE_OPENSSL_EVP_H=1`）→
`common.h` 引号 include 使源树副本优先 → 目标 sysroot 无 `openssl/evp.h` → 编译期 fatal error。
与既有条目的边界已在草稿里写明：E412 是 configure **自动探测**到未声明的可选后端；E284 是
交叉编译需要**生成** target config header；`DRAFT-libfsntfs-release-archive-closure` 管的是
组件目录/生成文件**齐不齐**与镜像身份——本条管的是"生成文件齐全但**内容是宿主机的**"。

## 注意事项

- 提交面只有 `conanfile.py`/`conandata.yml`/`manifest.yaml`/`notes.md`/`test_package/`，
  不含 `*.log`、二进制与 Conan 生成物（`test_package/conan*.sh`、编译出的
  `test_libfvde`/`test_ohos` 已在验证后清理）
- `reports/` 下的证据文件不进 PR（`.gitignore` 覆盖）
