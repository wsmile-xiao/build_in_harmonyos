# xine-lib 1.2.13 适配笔记

> 上游工程：xine（SourceForge 项目 `xine`）中的 **xine-lib**（库 `libxine`）。
> 任务口径说明：请求的 `xine/0.99.14` 中，版本号 `0.99.14` 实际属于同项目的前端
> **xine-ui**；xine-lib 没有 0.99.x 版本。依赖分析阶段（`.dep-analysis/xine_0.99.14/`）
> 依 Debian 源包线索认定目标工程为 xine-lib，上游真实版本 **1.2.13**（`xine-ui` 任务
> 的依赖清单也把 `xine-lib/1.2.13` 列为 next_dep）。本适配按 **xine-lib 1.2.13** 产出。

## 编译环境
- 构建系统: autotools（`configure` + `make`，tarball 内已带预生成 `configure`）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4 / clang++（sysroot: ohos-sdk 26.0.0.18，`aarch64-linux-ohos`，musl libc）
- 平台: OpenHarmony PC / aarch64，原生构建（build == host）
- 工作路径: 源码 `/storage/Users/currentUser/tmp/builds/xine-lib-1.2.13.work`；归档 `<worktree>/archives/x/xine-lib/1.2.13`
- 状态: built（conan-verify 全绿，未上传制品仓）

## 编译步骤

```bash
# 1) 源码核验：tarball sha256 与官方一致
sha256sum xine-lib-1.2.13.tar.xz
# 5f10d6d718a4a51c17ed1b32b031d4f9b80b061e8276535b2be31e5ac4b75e6f  （与 SF 公布一致）

# 2) init-build
python3 <SKILL_ROOT>/scripts/ohc-run.py init-build xine-lib 1.2.13 \
    --url="https://downloads.sourceforge.net/project/xine/xine-lib/1.2.13/xine-lib-1.2.13.tar.xz"

# 3) 语言预检（R47）：task=cpp / detected=c（兼容族，继续）

# 4) 配置 + 编译（探索阶段，参数最少化）
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make check          # 上游无测试目标 → 全部 "Nothing to be done"

# 5) 固化配方
python3 <SKILL_ROOT>/scripts/ohc-run.py refresh-patch --auto xine-lib 1.2.13
python3 <SKILL_ROOT>/scripts/ohc-run.py conan-verify xine-lib 1.2.13   # G0-G4 全 PASS
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `./config.guess[1430]: can't create .../tmp/cgXXXXXX/dummy.c: Permission denied` → `configure: error: cannot guess build type; you must specify one` | setgid HMDFS 挂载下，`umask 077` 创建的临时目录权限为 `drwx--S---`（owner 无有效 x 位），进程实际按 other 规则访问 → 不可写；叠加 2009 版 config.guess 不认识 HarmonyOS | `0001-config.guess.patch`：`umask 077`→`022`，并新增 `aarch64:HarmonyOS:*:*` 分支输出 `aarch64-linux-ohos`；`0002-config.sub.patch`：接受 `aarch64` CPU 与 `linux-ohos` OS |
| 2 | `configure` 收尾阶段 `can't create confcache: No space left on device` / `could not make ./config.status` | 环境瞬时 **inode 耗尽**（`files_avail` 5000/48M，多会话并发建 worktree 所致），非本包问题；稍后恢复（467780） | 无源码改动；重跑 configure 即通过（日志：`configure-2.log` 失败、`configure-3.log` 成功） |
| 3 | `broadcaster.c:385:5: error: call to undeclared function 'pthread_cancel'` | OHOS sysroot 的 `pthread.h` 不声明 pthread 取消 API；实测 sysroot `libc.so` **也不导出** `pthread_cancel`（`ld.lld: undefined symbol`），故不能只补声明 | `0006-...broadcaster.c.patch`：manager 线程 `select()` 加 1s 超时轮询 `running`，`_x_close_broadcaster` 去掉 `pthread_cancel` |
| 4 | `input_rtp.c:312/609`：`pthread_testcancel` / `pthread_cancel` 未声明 | 同上（musl/OHOS 无 pthread 取消 API） | `0004-...input_rtp.c.patch`：读线程改 `while (this->rtp_running)`，去掉两处 `pthread_testcancel`，dispose 改置标志后 join |
| 5 | `input_vdr.c:235/237/332/334/1903`：`pthread_testcancel` / `pthread_cancel` | 同上 | `0005-...input_vdr.c.patch`：删除 4 处 `pthread_testcancel`；rpc 线程关停去掉 `pthread_cancel`（该线程本就在 50ms `select` 超时里轮询 `rpc_thread_shutdown`，会自行退出） |
| 6 | G0 命中 E490：autotools helper 脚本可执行位可能丢失 | 补丁应用/检出可能丢 mode 位，`config.guess`/`configure` 报 Permission denied | conanfile `build()` 开头对 `configure/config.guess/config.sub/install-sh/missing/compile/depcomp/ar-lib` 条件 `chmod +x` |

## 源码修改（6 个补丁，均由 `refresh-patch --auto` 从 .orig/.work 差分生成）

| 补丁 | 文件 | 内容 |
|---|---|---|
| 0001-config.guess.patch | `config.guess` | umask 077→022（3 处）；新增 `aarch64:HarmonyOS:*:*` 分支 |
| 0002-config.sub.patch | `config.sub` | CPU 列表加 `aarch64`；OS 列表加 `linux-ohos*`（2 处） |
| 0003-configure.patch | `configure` | `config.status` 临时目录 umask 077→022（2 处） |
| 0004-src-input-input_rtp.c.patch | `src/input/input_rtp.c` | 去 pthread 取消 API，改运行标志轮询（-11/+3） |
| 0005-src-vdr-input_vdr.c.patch | `src/vdr/input_vdr.c` | 去 4 处 pthread_testcancel + 取消调用（-18/+1） |
| 0006-src-xine-engine-broadcaster.c.patch | `src/xine-engine/broadcaster.c` | select 超时轮询替代 pthread_cancel（-2/+7） |

> 无 `__OHOS__` 平台宏（PF5 已校验通过）。补丁全部为可移植性修复，不改变上游语义。

## 依赖版本

| 依赖 | 版本 | 类型 | 可消费性（W0 实测） |
|---|---|---|---|
| zlib | 1.3.1.1 | 直接强制（configure.ac:298 `AC_CHECK_LIB([z],[gzsetparams])`） | `conan download zlib/1.3.1.1 -r=ohpcd --only-recipe` → `Download completed`，**rc=0** |
| perl / gettext / pkgconf / libtool / autoconf / automake | 构建工具 | tool | 均 rc=0（可消费） |

- 传递强制依赖（TR）：**无**。
- 其余第三方依赖（ffmpeg/libpng/x11/alsa/… 共 45+ 项）全部为 configure **可选特性**，OHOS 上探测失败即关闭，不影响核心库；缺失的可选项（libaom/libpostproc/libmpeg2/faad2/libbluray/libcaca/directfb/xcb-shm… 等）均为门控、非阻塞。
- 系统库（工具链 sysroot 提供）：libc/libm/libdl/libpthread/librt、socket/nsl/resolv、iconv（musl 内建）、dirent。

## 验证结果

```bash
# conan create（干净源码，profile ohos-aarch64）
conan create archives/x/xine-lib/1.2.13 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → xine-lib/1.2.13@ohpcd/stable: Build succeeded   （zlib 为已发布二进制，未触发源码构建）

# 上游唯一测试入口 xmltest（build() 内自动运行）
./src/xine-utils/xmltest ".../xmltest-sample.xml" > xmltest.out 2>&1     # rc=0

# 消费者 test_package
# → 8/8 assertions passed, 0 failed（含 2 条鸿蒙特有断言）

# conan-verify
# → G0/G1/G2/G3/G4 全部 PASS，Verdict: PASS
```

上游样例实测（详见 `reports/test-report.md`）：`xmltest` 2/2、`xine-list` 2/2（`-a` 枚举全部支持格式）、`cdda_server` 2/2 通过；`xine-fontconv`（缺可选 freetype2）与 `contrib/libdha/test`（x86 DGA）不适用。

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libxine.so.2.11.0` | 核心库（动态；插件体系要求共享库） |
| `lib/xine/plugins/2.11/*.so` | 插件（解码器/输入/输出/后处理，OHOS 可用子集） |
| `include/xine.h`、`include/xine/*.h` | 公共头文件 |
| `bin/xine-list-1.2`、`bin/xine-config` | 随包 CLI（非 commands.json 声明的 tool 包，见下） |
| `lib/pkgconfig/libxine.pc` | pkg-config 元数据（Name: libxine，`-lxine`） |

## 注意事项

- **插件路径**：libxine 运行期通过 `XINE_PLUGIN_PATH` 定位插件目录；配方在 `package_info()` 中为该环境变量 `prepend_path`（各 ABI 子目录），`VirtualRunEnv` 会自动导出。
- **必须动态链接**：xine 的插件（`xineplug_*.so`）通过 dlopen 依赖 `libxine.so`，核心库不能静态化，故 `shared=True`。
- **可选依赖**：如需 freetype/ffmpeg/alsa 等可选插件能力，需先发布相应依赖并按需开启 configure 特性；本次适配仅保证核心库 + 默认可用插件。
- **E490 防御**：`build()` 中对 autotools helper 脚本条件 `chmod +x`，避免补丁/检出丢 mode 位后在 HMDFS 上报 Permission denied。
- 上游无自动化测试套件（`make check` 为空）；已在 `build()` 内集成唯一测试入口 `xmltest`。
---

**编译结束**: 2026-10-03 14:20
**最终状态**: built
