# libeis 1.6.0 适配笔记

## 背景
- 上游：https://gitlab.freedesktop.org/libinput/libei（tag **1.6.0**，GitLab tags API 确认为 PGP 签名 tag）
- 上游项目一次构建三个库：libei（客户端）、**libeis（服务端，本包）**、liboeffis（RemoteDesktop portal 助手）
- 本包只交付 **libeis.so**：`-Dlibeis=enabled -Dlibei=disabled -Dliboeffis=disabled`
- 同族已合入先例：`archives/l/libei/1.5.0`（一次交付两个库），本包的构建裁剪与测试基建适配以它为底稿

## 编译环境
- 构建系统: meson 1.11.1 / ninja 1.12.1（设备 `~/usr/local/bin`）
- 交叉/本机: OHOS aarch64（clang 15.0.4，`ci/conan/profiles/ohos-aarch64`）
- conan: 2.29.1（OHOS 适配版），CONAN_HOME=`~/tmp/ch/home-hw-4-libeis`
- 编译日期: 2026-09-24
- 状态: built（conan create 全绿，G0–G4 PASS）

## 编译步骤

conan 驱动（非手工命令）：`MesonToolchain` 生成 native 配置后

```
meson setup <builddir> .. -Dlibeis=enabled -Dlibei=disabled \
    -Dliboeffis=disabled -Dtests=auto -Ddocumentation=[]
ninja -C <builddir>
meson test -C <builddir>          # build() 内真实执行，非零即构建失败
meson install -C <builddir>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机 `curl` 取 `gitlab.freedesktop.org/.../-/archive/1.6.0` 返回 7478B HTML 拦截页（api/v4 同），GitHub 镜像 404 | freedesktop GitLab 对无 JS 客户端反爬；不是 404，不代表源不存在 | 设备侧取包成功（HTTP 200 / 261509B / 187 文件），按 **E347** 以 sha256 预置共享 `core.sources:download_cache`，`conandata.yml` 保留官方 URL 标量（本机交叉下载同值，两源一致） |
| 2 | meson 在 `project()` 处报 `Unknown linker(s): [['/data/service/hnp/bin/llvm-ar']]` | 配方从 1.5.0 继承的 `_inject_native_file_ar()` 用 `shutil.which("ar") or "/data/..."` 兜底，conan 构建环境里 `which("ar")` 取不到 ⇒ 把 profile 中已正确的 `ar` 覆盖成不存在的路径 | 改为**只在 toolchain 文件没有 `ar` 条目且本机确有可用 ar 时**才注入（配方侧修，不动 profile、不写死路径） |
| 3 | `[77/83] FAILED: test/test-build-libeis.p/buildtest.c.o` → `clang-15: error: -Wl,--code-sign: 'linker' input unused [-Werror,-Wunused-command-line-argument]` | OHOS clang wrapper 给**每次调用**（含 `-c` 编译）追加 `-Wl,--code-sign`；上游该目标硬编码 `-Werror` | 补丁 0003 只把这个告警降级（`-Wno-error=unused-command-line-argument`），保留 `-Werror`，不删签名参数。同机制在 CMake（unittest-cpp 2.0.0）与裸 Makefile（usbrelay 1.0）已各自记录，本条是 meson 实例 |
| 4 | 上一处放行后紧接着 `error: unused parameter 'argc'/'argv' [-Werror,-Wunused-parameter]` | 该 build-test 桩是 `main(int argc, char **argv){return 0;}`，而项目 `warning_level=2`（`-Wall -Wextra`）+ 目标 `-Werror` | 同一补丁内一并 `-Wno-error=unused-parameter`（只降级、不静默删除用例，也不改上游桩代码） |
| 5 | `subprojects/munit.wrap` 是 `wrap-git`（`revision=head`），CI worker 离线不可拉取 | 上游测试基建用 wrap-git 拉 munit | 补丁 0002：vendor munit 三文件进 `subprojects/munit/`（并强制 `install: false`，测试库不得泄漏进包）——同族 1.5.0 先例原样适用，已在 1.6.0 pristine 树上 `patch -p1 --dry-run` 复核 |
| 6 | `src/util-io.c` 测试段 3 处 `tmpfile()` | musl 的 `tmpfile()` 硬编码只读 `/tmp` 且不读 `TMPDIR` ⇒ 恒失败（E002 变体，经验汇总 §4.2b） | 补丁 0001：`$TMPDIR` 唯一文件 + 立即 `unlink`（fd 到 `fclose` 前有效，语义等价），纯 POSIX 无平台宏。hunk 按 1.6.0 行号重基（锚点位置比 1.5.0 偏移 5 行） |
| 7 | `find_installation('python3', modules: ['pytest','structlog'])` 在 CI 无这些模块时会硬失败 | 上游用 `required: get_option('tests')` 门控 | **不需要补丁**：`-Dtests=auto`（feature=auto）即优雅降级为只跑 C 套件。探索期手改的 `test/meson.build` 已按 pristine 还原，未进任何补丁 |
| 8 | 消费者测试 `eis_setup_backend_socket()` 返回 `-1`（EPERM） | **E461**：路径型 AF_UNIX socket 在本机不可 bind。同进程内独立复现三态：`/storage/Users/currentUser/tmp=Operation not permitted`、`/tmp=Read-only file system`、`/dev/shm=Permission denied` | 不删用例、不放宽：测试先用裸 `socket()/bind()` 探能力，命中可用目录则跑完整正向序列（含 connect/握手前事件门/销毁 unlink），平台受限时改断言"errno 必须原样传出 + 走 ERROR 日志回调"，并打印 `PLATFORM-LIMITED` 证据行。上游推荐的 `eis_setup_backend_fd()`（socketpair，不 bind 路径）在本机**完全可用**，已被真实执行 |

## 源码修改（3 个补丁，全部只动测试面）

| 补丁 | 文件 | 内容 |
|---|---|---|
| `0001-test-tmpfile-portable.patch` | `src/util-io.c` | 测试段新增 `test_tmpfile()` 并 `#define tmpfile()`，改用 `$TMPDIR` 唯一文件（+29 行） |
| `0002-vendor-munit-subproject.patch` | `subprojects/munit/{munit.c,munit.h,meson.build}` | vendor 上游 munit（nemequ/munit master fbbdf14），内含同款 tmpfile 替代与 `install: false` |
| `0003-buildtest-werror-ohos-codesign.patch` | `test/meson.build` | `test-build-libeis` 目标追加 `-Wno-error=unused-command-line-argument` 与 `-Wno-error=unused-parameter` |

三个补丁都只作用于**测试/构建校验**目标，不改库本体逻辑，也不放宽任何真实诊断（`-Werror` 仍在）。

## 依赖版本

核心库**零硬外部依赖**：`meson.build:87-112` 对 `epoll-shim`/`xkbcommon`/`libevdev`/`sd-bus`
全部 `required: false`，且这些探测只服务于 `tools/`（不安装）与 `liboeffis`（本包裁剪）。
构建期工具由 profile 提供：clang 15 / llvm-ar / meson 1.11.1 / ninja 1.12.1。
`pkg-config` 缺失不影响本包（`--build=missing` 未拉任何依赖）。

## 验证结果

```bash
# 设备：conan-verify（G0 预扫 / G1 配方 / G2 conan create 干净构建 / G3 / G4）
$ python3 scripts/ohc-run.py conan-verify libeis 1.6.0     # VERIFY_RC=0
**Verdict**: PASS   ## G0 ✅  ## G1 ✅  ## G2 ✅  ## G3 ✅  ## G4 ✅

# 上游测试（build() 内 meson test 真实执行，日志 meson-logs/testlog.txt）
Ok: 3   Fail: 0
  libei:dtdcheck            exit status 0   (0.06s)
  libei:unit-tests-eis      exit status 0   (0.07s)  → 7 of 7 (100%) successful, 0 skipped
  libei:unit-tests-utils    exit status 0   (0.22s)  → 36 of 36 (100%) successful, 0 skipped
合计 44/44 原子用例通过，0 跳过

# 消费者测试（test_package，真实链接 -leis 并调用公共 API）
libeis consumer test: 18 assertions, 0 failed
libeis test_package: PASS
```

### 测试口径（五维账本）

| 维度 | 数 | 说明 |
|---|---|---|
| `N_static` | **44** | 本包交付面（libeis 本体 + 共享 util + 协议 DTD）真实注册入口逐项统计：`src/util-*.c` 36 个 `MUNIT_TEST` + libeis/brei 侧 7 个 + `proto/meson.build` 的 `dtdcheck` 1 个 |
| `N_registered` | **44** | 本配置（`tests=auto`）下 `meson test` 注册 3 个入口，展开即 44 |
| `N_executed` | **44** | 全部在 `build()` 内执行，44/44 通过、0 跳过 |
| 未执行分类 | **0**（交付面内） | 交付面外不注册的项逐条列在下方，不计入本包分母 |
| `N_consumer` | **18** | `test_package` 消费者断言（18 执行 / 0 失败）；另有 8 项正向 socket-path 断言因 E461 平台受限未执行，已打印 `PLATFORM-LIMITED` 证据并改断言 errno 传出路径 |

交付面之外、本配置不注册的上游测试入口（逐项原因，未静默删除）：

| 上游入口 | 静态声明 | 不注册原因 |
|---|---|---|
| `test('unit-tests-ei')` | libei 源码内 6 个 munit | `-Dlibei=disabled`，属客户端库面 |
| `test('unit-tests-oeffis')` | 2 个 munit | `-Dliboeffis=disabled`（需 sd-bus，OHOS 无） |
| `test('eierpecken')` / `eierpecken-no-sigalrm` | `test/test-ei.c` 26 + `test/test-eis.c` 15 | 门控 `build_libei and build_libeis`，需客户端库配合 |
| `test('protocol-test')` / `scanner-pytest` / `oeffis-pytest` | 23 + 4（`def test_`） | 需 python `pytest`+`structlog`；`tests=auto` 下优雅跳过 |
| `test('protocol-test-valgrind')` | 同上 | 需 valgrind |
| `executable('test-build-lib*')` × 4 | 编译期自包含校验 | `test-build-libeis`（C）在本包构建内编译通过；`-Dlibei=disabled` 使另外 2 个不生成，C++ 变体不吃 `-Werror` |

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libeis.so.1.6.0`（+ `.so.1`/`.so` 别名） | 服务端库本体 |
| `include/libei-1.0/libeis.h` | 唯一公共头 |
| `lib/pkgconfig/libeis-1.0.pc` | pkg-config 名 `libeis-1.0` |

## 注意事项

- **运行期能力边界**：`eis_setup_backend_socket()`（路径型 UNIX socket 监听）在 OHOS 上因
  E461 不可用；`eis_setup_backend_fd()` + `eis_backend_fd_add_client()`（上游推荐、合成器实际
  使用的那条）完全可用。下游若要对外提供 socket 端点，需自行解决路径套接字限制。
- 本包**不安装任何可执行文件**（`tools/eis-demo-server` 未 `install: true`），故不含
  `commands.json`；`/dev/uinput` 只出现在那个不安装的 demo server 里（且需可选依赖 libevdev），
  不在交付面上。
- 上游 `test-eis.c` 的 `eistest_socket_overflow` 在 1.5.0 记录过"OHOS Unix socket 缓冲区语义
  不同"的平台差异豁免；本包配置不注册 `eierpecken`，因此**不涉及**该项，未沿用其结论。
- `brei-shared.h` 会 `#warning` 提示项目依赖 `assert()`（Release 带 `-DNDEBUG`）——上游自身
  提示，1.5.0 同现，非本包引入。

## 知识沉淀

本单**未新增草稿**（B 判定 = `hit`），理由与精确引用见任务登记表备注：所有踩到的机制都已有条目
——E347（GitLab 反爬 ⇒ dlcache 预置）、E002/§4.2b（musl `tmpfile()`）、E461（路径型 AF_UNIX
bind 三态）、以及已在 unittest-cpp / usbrelay PR 里落地的 `-Wl,--code-sign` × 上游 `-Werror`
机制（本条是其 meson 实例）。
---

**编译结束**: 2026-09-24 13:09
**最终状态**: built
