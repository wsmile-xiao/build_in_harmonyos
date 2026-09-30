# tlog 14 适配笔记

## 编译环境
- 构建系统: autotools（发布 tarball 自带预生成 configure，**不跑 autoreconf**）
- 编译日期: 2026-09-27
- 编译器: clang / clang++（OHOS PC aarch64，aarch64-unknown-linux-ohos）
- 目标平台: HarmonyOS PC（OHOS aarch64，musl）
- 状态: published（本机 conan create + W3 本地 CI 模拟验证通过；制品上传由 CI release 流水线在 PR 合并后完成，见 manifest.yaml）

## 编译步骤

```sh
# 1) 取官方源（sha256 见 conandata.yml）
curl -L -o tlog-14.tar.gz \
  https://github.com/Scribery/tlog/releases/download/v14/tlog-14.tar.gz

# 2) 打 10 个适配补丁（见下）
# 3) 依赖注入（json-c 走 pkg-config，curl 走 curl-config）
export CPPFLAGS="-I<json-c>/include -I<curl>/include"
export LDFLAGS="-L<json-c>/lib -L<curl>/lib"
export PKG_CONFIG_PATH="<json-c>/lib/pkgconfig:<curl>/lib/pkgconfig"
export PATH="<curl>/bin:$PATH"                 # curl-config
export LD_LIBRARY_PATH="<json-c>/lib:<curl>/lib"   # configure 的 conftest 要能加载它们

# 4) OHOS 受限域不能 exec 缓存文件 → 经显式 shell 调 configure
CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh /system/bin/sh ./configure \
  --prefix="$DEFAULT_PREFIX" --enable-static --disable-shared
make -j1
make check          # 上游测试集：13/13 通过
make install DESTDIR="$TEST_PREFIX"
```

> 配方里 prefix 是 conan 默认的 `/`（DESTDIR 安装后 `<pkg>/bin`、`<pkg>/lib`、
> `<pkg>/share`、`<pkg>/etc` 即最终布局）；上面写 `$DEFAULT_PREFIX` 是探索阶段
> 的手工编译，便于直接跑 CLI 观察运行时行为。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `unrecognized host system` | 上游 config.guess/config.sub 不认 aarch64-unknown-linux-ohos | 补丁 0001/0002 注入 OHOS 三元组（**不传 --build/--host**，R15/E007） |
| 2 | `make` 报 `struct timespec`/`ssize_t`/`pthread_t` 未声明 | musl/OHOS 公开头未连带声明这些 POSIX 类型，上游头也没 include | 补丁 0004-0010 在 7 个公开头补 `#include <time.h>` 等最小声明，**不改任何逻辑**（R8） |
| 3 | HMDFS 上构建目录不可写（`mkdir: Permission denied`） | 上游 configure 内 `umask 077` → 新建目录 0700（E114/E129 族） | 补丁 0003 把 `umask 077` 放宽为 `022`（打在 configure 本体，与 bti 034 同法） |
| 4 | configure 的探测程序报 `cannot run C compiled programs` | conftest 链了 libcurl/libjson-c 的 .so，构建进程找不到 | generate() 里 `Environment.save_script` 注入依赖 libdirs→LD_LIBRARY_PATH（**不能**用 -Wl,-rpath，会把 conan 缓存路径烤进产物 RPATH） |
| 5 | `PKG_CHECK_MODULES(JSON, json-c)` 探测失败 | 只把依赖包自带 pkgconfig 目录塞进 PKG_CONFIG_PATH 不够：libcurl.pc 的 Requires.private 会牵出 openssl/zlib，而它们包内无 pkgconfig 目录 | 用 `PkgConfigDeps(self).generate()` 为整条依赖链生成 .pc（elfutils 0.195.1 同法） |
| 6 | `autotools.configure()` 报 `Error 126 Permission denied` | OHOS 受限域（u:r:adhoc_bin:s0）不能 exec 缓存目录里的文件 | 经显式 `/system/bin/sh <configure>` 调用（只读不 exec；全仓 28 个包在用） |
| 7 | CLI 报 `Failed loading default configuration` / `Failed finding system configuration`（rc=1） | 上游要求**默认配置**（share/tlog/*.default.conf）与**本地配置**（etc/tlog/*.conf）同时存在；查找路径按「二进制自身路径」判定（构建树 .libs → 相对路径；否则编译期绝对路径） | 运行时层面：部署时把两组配置放到对应位置；测试层面：test_cli.sh 按上游构建树布局摆放后真实加载（见下） |
| 8 | `tlog-rec` 真实录制报 `User entry not found` | lib/tlog/rec.c:712 `getpwuid(getuid())` 返回 NULL（UID 20020093 不在 /etc/passwd） | 环境限制，无法在录制/replay E2E 上取断言；如实记录（MANIFEST.yml platform_notes），CLI 断言改用 `--version/--help/--configuration` 功能性输出 |

## 源码修改

10 个补丁（`patches/`，均由 `refresh-patch --auto` 从工作树与原始 tarball 的
逐文件 diff 生成，每个文件一个补丁）：

| 补丁 | 目标 | 内容 |
|------|------|------|
| 0001-config.guess.patch | config.guess | 增加 aarch64-unknown-linux-ohos 识别（E007） |
| 0002-config.sub.patch | config.sub | 同上（os 段接受 ohos） |
| 0003-configure.patch | configure | `umask 077` → `022`（E114/HMDFS） |
| 0004-…-json_msg.h.patch | include/tlog/json_msg.h | 补 POSIX 类型声明的最小 include |
| 0005-…-json_stream.h.patch | include/tlog/json_stream.h | 同上 |
| 0006-…-pkt.h.patch | include/tlog/pkt.h | 同上（`struct timespec`） |
| 0007-…-rl_json_writer.h.patch | include/tlog/rl_json_writer.h | 同上 |
| 0008-…-source.h.patch | include/tlog/source.h | 同上 |
| 0009-…-timestr.h.patch | include/tlog/timestr.h | 同上（`struct timespec`） |
| 0010-…-tty_source.h.patch | include/tlog/tty_source.h | 同上 |

补丁均为平台适配（platform_only），不含平台宏 `__OHOS__`（R8，也不含空壳 stub）。

## 依赖版本

| 依赖 | 版本 | 发现方式 |
|------|------|----------|
| json-c | 0.18 | configure.ac:86 `PKG_CHECK_MODULES(JSON, json-c)`（必备，无开关） |
| curl | 8.15.0 | configure.ac:106 `LIBCURL_CHECK_CONFIG([yes],[7.15.4],…)`（必备） |

> 上游可选特性均未启用：`--enable-utempter` 默认 no（OHOS 无 libutempter），
> journal 写入器为运行期可选，不引构建期依赖，保持上游默认不干预。

## 验证结果

```sh
# ① 上游测试集（配方 build() 内 make check；原样保留并真实执行）
make check                # → 13/13 PASS（PASS: tltest-fd-json-reader … tltest-timestr）

# ② 消费者侧 libtlog API 探针（test_package/test_libtlog.c）
./test_probe              # → libtlog: 18 passed, 0 failed

# ②' OHOS/musl 特有：7 个补丁头的自包含编译断言（test_package/conanfile.py build()）
#    未打补丁 2/7，打补丁 7/7 → 补丁 0004-0010 的直接回归网
clang -fsyntax-only … -include tlog/<h>.h -x c /dev/null   # → 7/7

# ③ 三个 CLI 功能 + 默认配置真实加载（test_package/test_cli.sh）
sh test_cli.sh <work> <package_folder>
                          # → tlog CLI: 7 passed, 0 failed
```

实测输出与命令记录见 `reports/test-report.md`。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/tlog-rec`、`bin/tlog-play`、`bin/tlog-rec-session` | 三个 CLI（软件级 `commands.json` 已声明，R38） |
| `lib/libtlog.a` | 库（默认静态；`-o shared=True` 则产 libtlog.so） |
| `include/tlog/*.h` | 公开头 |
| `share/tlog/*.default.conf` | 上游默认配置（运行时必需，见问题 7） |
| `etc/tlog/*.conf` | 本地配置（运行时必需，见问题 7） |

## 注意事项

- **默认静态**（R26）：CLI 因此不依赖 libtlog.so；若以 `-o shared=True` 构建，
  CLI 会 `NEEDED libtlog.so.0`，消费者需让加载器能找到包内 `lib/`（conan 的
  runenv 已处理）。
- **运行时配置**：CLI 启动即要求默认配置与本地配置同时存在。conan 包的
  `share/tlog/`、`etc/tlog/` 即上游的安装位置内容，部署时按上游约定放置
  （编译期路径为 `/share/tlog/`、`/etc/tlog/`）。
- **不做真实录制/回放 E2E**：本机构建用户无 /etc/passwd 条目，录制路径必然失败
  （见问题 8），属环境限制而非适配缺陷。

## 适配踩坑（本次新增，均已在 conan create 上复现并修掉）

1. **json-c 的公开头在 `include/json-c/` 下**：上游 `lib/tlog/es_json_reader.c:28`
   写的是扁平 `#include <json_tokener.h>`，靠的是 json-c 自带 .pc 里的
   `Cflags: -I${includedir} -I${includedir}/json-c`。而 `PkgConfigDeps` 只能按
   `cpp_info.includedirs` 生成 `-I${includedir}`，于是编译报
   `fatal error: 'json_tokener.h' file not found`。
   修法：`generate()` 里对每个依赖的每个 includedir，若同名子目录
   （`<includedir>/<dep.name>`）存在就一并加入 CPPFLAGS。
2. **json-c 包内自带 .pc 的 prefix 是坏的**：`.../p/<id>/p/lib/pkgconfig/json-c.pc`
   的 prefix 仍指向打包时的构建目录（`.../p/b/json-<id>/p`，事后已不存在）。
   所以 `PKG_CONFIG_PATH` 必须让 **PkgConfigDeps 生成器目录排在依赖自带 .pc 之前**，
   否则 -I/-L 全指到死路径上。
3. **依赖链/环境会注入相对搜索目录（`-Llib`、`-Iinclude`）**：autotools 会在每个
   构建子目录里重放这些标志，相对路径在那里不存在；链接期 libtool 更会硬失败
   `error: cannot determine absolute directory name of 'lib'`。
   修法：构造 CPPFLAGS/LDFLAGS 时只保留绝对路径（`_drop_relative_dirs` + 列表过滤）。
4. **OHOS 无 systemd/journal**：configure 默认 `journal=yes`，缺 `libsystemd-journal`
   时直接 `AC_MSG_ERROR`，必须显式 `--disable-journal`（已在 `generate()`）。
5. **上游测试集全程保留**：`make check` 13/13 PASS，用例**未经任何修改**；
   本次新增的 `test_package/` 测试（3 用例 / 32 断言）与上游测试分开统计。
6. **头文件自包含是鸿蒙特有的坑（本次新增回归网）**：上游 7 个公开头只 include
   `<stdbool.h>`/`<stdlib.h>`/`<stdint.h>`，靠它们**间接**拿到 `struct timespec`
   /`ssize_t`/`clockid_t`——glibc 会顺带定义、musl(OHOS) 不会。实测同一组
   `-fsyntax-only -include tlog/<h>.h -x c /dev/null`：未打补丁 2/7 通过
   （`pkt.h:85 field has incomplete type 'struct timespec'`、`pkt.h:379 unknown
   type name 'ssize_t'`、`rl_json_writer.h:62 unknown type name 'clockid_t'`），
   打补丁后 7/7。`test_package/conanfile.py::build()` 已把这 7 条固化为断言。
7. **finish step 3 的 G0 clean-verify 在本平台会以 getcwd 失败，非本包问题**：
   该步用裸 `./configure`（不注入 conan 工具链环境）执行，日志为
   `shell-init: error retrieving current directory: getcwd: cannot access parent
   directories` → `configure: error: working directory cannot be determined`，
   属 E386（同族草稿 DRAFT-6487）记录的 HMDFS 工作目录判定问题；同一次适配里
   G2 `conan create`（配方 `generate()` 显式 `CONFIG_SHELL`）与 W3 本地 CI 模拟
   均通过，故 G0 失败不影响结论，本步在 finish 中亦为非阻塞。
8. **Conan 2 API 两处易踩点（本次实测踩中，已沉淀草稿 E548）**：`ConanException`
   只能 `from conan.errors import`（`from conan import ConanException` 会在加载
   test_package 时 ImportError）；`self.dependencies.items()` 的 key 是
   `Requirement`，包名要经 `ref.ref.name` 取（`ref.name` 抛 AttributeError）。
---

**编译结束**: 2026-09-27 22:17
**最终状态**: published
