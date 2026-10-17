# libdsme 0.67.0 适配笔记

## 软件信息

- 软件: libdsme 0.67.0（Sailfish OS / Jolla）
- 上游: https://github.com/sailfishos/libdsme （tag 0.67.0, commit 67e57c5）
- 源码: https://github.com/sailfishos/libdsme/archive/refs/tags/0.67.0.tar.gz
  （sha256 `58908591d652f6505cebeb126664950cf9337d70a963b2f03cd6e80e91578e46`）
- 构建系统: 手写 Makefile（无 configure/CMake/Meson）
- 产物: 三个共享库
  - `libdsme.so.0.3.0`（SONAME `libdsme.so.0`）
  - `libdsme_dbus_if.so.0.3.0`（SONAME `libdsme_dbus_if.so.0`）
  - `libthermalmanager_dbus_if.so.0.3.0`（SONAME `libthermalmanager_dbus_if.so.0`）
- 依赖: `glib/2.84.0.1`（libdsme.so 内部用 GSList 记录连接）
- 测试依赖: `check/0.15.2`（上游 `tests/ut_libdsme.c`，test_requires）

## 编译步骤

```bash
# 1. PkgConfigDeps 生成 glib-2.0 / check 的 .pc 到 generators 目录
# 2. make（Makefile 用 pkg-config 取 glib-2.0 的 cflags/libs）
CC=<profile tools.build:compiler_executables:c> make -j1
# 3. 运行上游测试（Makefile 只构建不执行 tests/ut_libdsme）
TEMP=<build>/tmp TMP=<build>/tmp TMPDIR=<build>/tmp ./tests/ut_libdsme -o <build>/ut_libdsme.xml
# 4. 打包：将三个 .so + SONAME 软链、include/dsme 头文件、.pc 安装到 package 目录
```

Makefile 使用 `$$(pkg-config --cflags glib-2.0)` 做 target-specific CFLAGS
注入，因此构建环境必须提供 `PKG_CONFIG_PATH`（recipe 指向 Conan
generators 目录，内含按包路径生成的 `glib-2.0.pc`/`check.pc`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试写 `/tmp/ut_libdsme.sock` 失败 `Read-only file system` | OHOS `/tmp` 为只读 erofs 挂载（E002） | 测试补丁改为抽象套接字 `@ut_libdsme`（见 #2），不再需要文件系统路径 |
| 2 | AF_UNIX 文件系统套接字 `bind()` 返回 `EPERM`（HMDFS / `$HOME` 全域） | OHOS/HMDFS 禁止在文件系统上创建 unix socket（`/dev/shm` 也 EACCES） | 库补丁：`dsmesock_connect()` 支持 `@name` 抽象套接字前缀（Linux/OHOS 内核原生支持，无需文件系统路径）；测试补丁：mock daemon 绑定 `@ut_libdsme`，抽象名下跳过 unlink/chmod |
| 3 | Check 报 `Unable to create temporary file for communication` | Check 0.15.2 探测顺序为 `TEMP` → `P_tmpdir` → `TMPDIR`，musl 把 `P_tmpdir` 定义为只读 `/tmp`，因此只设 TMPDIR 无效 | recipe 在 OHOS 上同时设置 `TEMP`/`TMP`/`TMPDIR` 指向构建目录；fork 模式即可通过（无需 `CK_FORK=no`） |
| 4 | 上游 `make install` 失败 `install: No such file or directory` | OHOS toybox 没有 GNU `install(1)` | `package()` 不调用上游 install 规则，显式复制产物（.so + SONAME 软链、头文件、.pc） |
| 5 | `make` 构建的测试二进制运行时找不到 `libdsme.so.0` | Makefile 只生成 `libdsme.so.0.3.0`，SONAME 软链只在 install 规则里创建 | recipe 在 build 目录创建指向源目录产物的 SONAME 软链，并把 build 目录加入 `LD_LIBRARY_PATH` |
| 6 | 自带 `glib-2.0.pc` 的 `prefix=/`（把 `-I` 指向 `/include`） | glib 包内 .pc 面向系统根安装，不能直接用于 Conan 构建环境 | build 阶段使用 `PkgConfigDeps` 生成的包内 .pc（绝对包路径，正确）；`package()` 把发行包里的三个 .pc 改写为 `prefix=${pcfiledir}/../..` 使其可重定位 |

## 源码修改（补丁）

1. `patches/0001-protocol.c.patch`（+26/-3）
   - `dsmesock_connect()` 支持 `@` 前缀的抽象 AF_UNIX 套接字名：
     `sun_path[0]='\0'` + 名字拷贝，`connect()` 地址长度按抽象命名空间
     计算；普通路径行为完全不变。附带对超长名称做长度检查（原实现
     直接 `strcpy` 到 108 字节 `sun_path`，为潜在溢出）。
   - 这是 OHOS 沙箱/ HMDFS 下唯一可用的 AF_UNIX 传输方式，不是 stub：
     有实际连接逻辑，测试（上游 + 消费者）均覆盖该路径。
2. `patches/0002-tests-ut_libdsme.c.patch`（+24/-7）
   - mock daemon 由 `/tmp/ut_libdsme.sock` 改为抽象名 `@ut_libdsme`；
     抽象名下跳过 `unlink()`/`chmod()`，`bind()` 使用抽象地址长度；
   - 结果 XML 默认路径支持 `TMPDIR`（musl `/tmp` 只读）；
   - 测试逻辑、用例数量与断言不变（上游 2 个 Check 用例原样保留）。

补丁不使用任何平台宏（无 `__OHOS__` 注入），运行时按 `@` 前缀与
`TMPDIR` 环境变量自适应，Linux 上同样成立。

## 依赖版本

- `glib/2.84.0.1`（ohpcd 已发布二进制，W0 已用 `conan download` 验证）
- `check/0.15.2`（test_requires，仅上游测试使用；ohpcd 已发布）

## 验证结果

```text
$ conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64
upstream ut_libdsme: 2/2 Check cases passed
100%: Checks: 2, Failures: 0, Errors: 0
```

- 上游测试: `tests/ut_libdsme` 的 2 个 Check 用例（test_message、
  test_send_receive）全部通过（2/2 = 100%），recipe 解析 XML 强制校验。
- 消费者测试: `test_package/test.c`（35 个 CHECK 断言）全部通过，
  包括抽象套接字双向收发、extra 载荷、负向控制（不存在的端点返回 NULL）。
- 鸿蒙特有: OHOS 产物契约（ELF64/AArch64/DYN、SONAME、DT_NEEDED、
  无 RPATH、导出符号）全部通过。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 手写 Makefile 配方（PkgConfigDeps + VirtualBuildEnv；构建/测试/打包） |
| `conandata.yml` | 官方源码 URL + sha256 + 2 个补丁声明 |
| `test_package/` | 消费者测试（test.c + CMakeLists.txt + conanfile.py + MANIFEST.yml） |
| `patches/` | 0001-protocol.c.patch、0002-tests-ut_libdsme.c.patch |
| `reports/` | test-report.md、audit-result.json、conan-verify 记录 |

## 注意事项

- 设备侧 `/tmp` 只读、HMDFS 不允许文件系统 unix socket，是本次适配的
  两个核心平台差异；抽象套接字方案对真实 DSME 守护进程同样适用。
- 上游 `tests.xml` 的 `/opt/tests/libdsme/ut_libdsme` 安装路径面向
  Maemo 打包，本包不安装测试二进制（Conan 包只含库/头文件/.pc）。
- `make -j1` 保持上游 Makefile 的串行构建约定（R9）。
## 对话记录

### 对话 #1 [2026-09-21]

- 问题: `init-build` 阶段 GitHub 直连下载超时（设备侧 urllib timeout）
- 操作: 在 Windows 侧下载官方 tarball 并预置到 `$TMPDIR/builds/libdsme-0.67.0.tar.gz`
- 结果: init-build 识别缓存 tarball，解压/骨架/环境检查全部通过

### 对话 #2 [2026-09-21]

- 问题: 手工 make 成功，但上游测试写 `/tmp/ut_libdsme.sock` 报 Read-only file system
- 操作: 记录 E002；确认 `/tmp` 为只读 erofs 挂载
- 结果: 放弃 /tmp 方案，转向测试路径改造

### 对话 #3 [2026-09-21]

- 问题: 改用 `$TMPDIR` 后 bind() 返回 EPERM（HMDFS 全域拒绝文件系统 unix socket）
- 操作: 系统探测 `/tmp`、`$HOME`、`/dev/shm`、HMDFS 根与抽象命名空间
- 结果: 仅抽象套接字（`\0name`）可 bind+connect；决定库侧支持 `@` 前缀

### 对话 #4 [2026-09-21]

- 问题: 抽象套接字补丁后，Check 报 "Unable to create temporary file for communication"（CK_FORK=no 也无效）
- 操作: 设备侧拉取 check 0.15.2 源码定位 `check_msg.c` 探测顺序 TEMP → P_tmpdir → TMPDIR
- 结果: musl 的 P_tmpdir=/tmp 抢先生效；设置 TEMP/TMP/TMPDIR 后 2/2 通过

### 对话 #5 [2026-09-21]

- 问题: conan create 首轮 G2 失败——`iter("test")` 解析不到 check 结果 XML
- 操作: 定位 XML 默认命名空间（`{http://check.sourceforge.net/ns}test`）
- 结果: 改为按 local tag 匹配，recipe 内 XML 校验 2/2 生效

### 对话 #6 [2026-09-21]

- 问题: 打包后 `lib/pkgconfig/` 混入生成的依赖 .pc（basic_layout 构建树位于 source 内，glob `*.pc` 递归命中）
- 操作: 改为显式复制三个上游 .pc，并改写 `prefix=${pcfiledir}/../..`
- 结果: 产物树干净（3 库 + 8 头 + 3 pc + COPYING），conan-verify G0–G4 全绿

### 对话 #7 [2026-09-21]

- 问题: 上游 `make install` 在设备上 Error 127（toybox 无 GNU install(1)）
- 操作: package() 显式安装；build/package 阶段分别创建 SONAME 软链
- 结果: 安装树契约通过；staging 拷贝 + 消费者测试 + 产物契约检查全绿
---

**编译结束**: 2026-09-21 18:08
**最终状态**: built
