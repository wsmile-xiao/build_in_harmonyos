# thrulay 0.9 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，GNU Autoconf 2.69 生成的老式 configure）
- 编译日期: 2026-09-30
- 编译器: clang 15（OHOS SDK，`/data/service/hnp/bin/clang`），target `aarch64-linux-ohos`
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / libcxx=libc++）
- 状态: built

## 编译步骤

上游未提供构建文档，按 autotools 惯例（并与 conan `AutotoolsToolchain` 一致）执行：

```bash
# 1) 替换 config.guess / config.sub（补丁 0001/0002，见下）
# 2) 去掉 configure 中的 umask 077（补丁 0003，见下）
./configure --enable-static --disable-shared \
    --host=aarch64-linux-ohos --build=x86_64-linux-gnu --prefix=$DEFAULT_PREFIX
make -j1                      # E525：OHOS SELinux 拒绝用户态创建 FIFO，禁 make jobserver
make install DESTDIR=$TEST_PREFIX
make check                    # 上游无测试套件：Nothing to be done for 'check'（0 用例）
```

产物布局（`make install` 实测）：`bin/thrulay`、`bin/thrulayd`、`lib/libthrulay.a`、
`include/thrulay/client.h`、`include/thrulay/server.h`、`share/man/man1/thrulay.1`、
`share/man/man8/thrulayd.8`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure` 报 `cannot guess build type; you must specify one` | 上游 config.guess/config.sub 是 2006-07-02 版本，早于 HarmonyOS/aarch64-linux-ohos，设备上 `uname -s` 返回 `HarmonyOS` 无法识别（E007） | 补丁 0001/0002：替换为 autoconf 2.72 的 config.guess/config.sub，并在 config.guess 的 HarmonyOS 分支硬编码 `aarch64-unknown-linux-ohos` |
| 2 | config.sub 拒绝 `aarch64-unknown-linux-ohos` | 2.72 版 config.sub 的 OS/内核组合校验表不含 `linux-ohos`（E072） | 补丁 0002 在 OS/kernel 组合白名单中加入 `linux-ohos*` |
| 3 | `config.status` 报 `mv: bad './confXXXXXX/config.h': Permission denied` | configure 内含 `umask 077`；HMDFS 下临时目录被建成 `drwx--S---`，无 x 权限无法进入/mv（E114） | 补丁 0003：删除该 `umask 077` 语句 |
| 4 | make 报 jobserver/FIFO 相关错误（或挂起） | OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO（E525） | `make -j1`（不启用 jobserver） |
| 5 | 打包的可执行文件带不可移植的绝对 RUNPATH（libtool 自建 .so） | libtool 默认动态链接自建库，RUNPATH 指向构建期绝对路径 | `--enable-static --disable-shared`：两个可执行文件静态内嵌 libthrulay（R26 同族口径），消费方仍可用 `libthrulay.a` |

## 源码修改

三处补丁（`patches/`，均由 `refresh-patch --auto` 生成，`patch_type=backport`）：

| 补丁 | 内容 | 说明 |
|------|------|------|
| `0001-config.guess.patch` | 用 autoconf 2.72 的 config.guess 整体替换 2006 老版本；HarmonyOS 分支输出 `aarch64-unknown-linux-ohos` | 补丁内**不含**平台宏（`__OHOS__` 分支已删除：设备 `uname -s=HarmonyOS` 走专用分支，libc 探针无需 OHOS 判定——实测加/删该分支输出的三元组完全一致） |
| `0002-config.sub.patch` | 用 autoconf 2.72 的 config.sub 整体替换；OS/kernel 组合白名单增加 `linux-ohos*` | 使 `aarch64-unknown-linux-ohos` 通过校验 |
| `0003-configure.patch` | 删除 configure 中的 `umask 077` | 规避 HMDFS 下临时目录无 x 权限（E114） |

`config.guess`/`config.sub` 的替换方式参照同仓先例（`archives/e/ezstream/1.0.2`）。
E007 的通用脚本 `patch-autotools-ohos.pl` 对本 tarball 不适用（2006 版脚本锚点不匹配，1/5 hunk 命中），故采用整体替换。

## 依赖版本

**无三方依赖。** 逐符号核验（OHOS sysroot `usr/lib/aarch64-linux-ohos`）：

- libc 已导出：`log`、`nanosleep`、`herror`、`gethostbyname`、`socket`、`pthread_create` 等；
- `libm` / `libpthread` / `librt` / `libresolv` 在 sysroot 中提供（静态库）。
- 源码语言构成：`configure.ac` 仅 `AC_PROG_CC`，源码纯 C（无 C++ 文件）。

## 验证结果

```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify thrulay 0.9
G1: PASS  G0: PASS  G2: PASS（干净 conan create）  G3: PASS（R26 系统同名库隔离）
G4/L2/L4/L5: 通过
✅ 配方验证通过: thrulay 0.9   → 可标记 status: built
```

消费者测试（`test_package/`，两层，均由 conan create 执行）：

| 测试 | 用例 | 结果 |
|------|------|------|
| `test_lib_consumer.c`（库 API 消费者：fork 服务端 + 客户端 API 回环测量） | 13 | 13/13 通过（回环吞吐 14242.118 Mb/s） |
| `test_cli_e2e.py`（命令行消费者：打包的 thrulayd + thrulay 真实测量） | 17 | 17/17 通过（客户端 rc=0，吞吐 14054.227 Mb/s） |
| **合计** | **30** | **30/30 (100%)** |

上游测试清点：`test`/`tests` 目录 0 个、`test*.{c,sh,py}` 0 个、`make check` →
`Nothing to be done for 'check'`（**上游无测试套件**，非环境问题）。详见
`test_package/MANIFEST.yml` 与 `reports/test-report.md`。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/thrulay` | 客户端 CLI（容量/时延/丢包测量） |
| `bin/thrulayd` | 服务端 CLI（上游安装到 `$(bindir)`，故与 thrulay 同目录） |
| `lib/libthrulay.a` | 静态库（消费方可嵌入协议实现） |
| `include/thrulay/client.h`、`include/thrulay/server.h` | 公开 API 头 |
| `share/man/man1/thrulay.1`、`share/man/man8/thrulayd.8` | man 页 |

## 注意事项

1. **`acl_allow_add()` 会就地改写实参**（`server.c`：`*pmask++ = '\0'` 拆掉 `/32` 掩码）。
   调用方必须传可写缓冲，传字符串字面量会写只读段并 SIGSEGV。`test_package/test_lib_consumer.c`
   已按可写缓冲（`char acl[] = "127.0.0.1/32"`）调用并固定该用法。
2. 设备 `uname -s` 为 `HarmonyOS`（非 `OHOS`），故 config.guess 走 `*:HarmonyOS:*:*` 专用分支；
   交叉编译时若显式传 `--build/--host`（conan 默认行为），config.guess 仅用于 build 三元组。
3. 两个可执行文件均静态内嵌 libthrulay，运行时仅依赖 OHOS 自带 libc/libm/librt/libresolv，
   便于直接在设备上执行。
