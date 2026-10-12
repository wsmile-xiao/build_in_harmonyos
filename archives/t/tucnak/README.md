# tucnak

业余无线电竞赛日志与电台控制程序，终端界面（TUI）。

- 上游：https://github.com/Tucnak/tucnak
- 版本：4.67
- 平台：OpenHarmony / HarmonyOS PC（aarch64）

## 依赖

| 依赖 | 说明 |
| --- | --- |
| `glib/2.88.0` | 经由 libzia 引入的**硬**依赖 |
| `pcre2/10.45` | glib 的传递依赖 |
| `zlib/1.3.1` | glib 的传递依赖 |

**不依赖** ncurses，也不依赖 gettext。tucnak 自带终端处理，`src/` 中没有任何
`<curses.h>`；`intl/` 目录只有 `.lng` 语言文件而非 gettext 的 `.po`。

## 构建结构

上游把 tucnak 与它的配套库 libzia 作为**两个**发布 tarball 发布，设计上就是并排
解包使用：

- `tucnak_4.67.orig.tar.gz` → `src/tucnak/`
- `tucnak_4.67.orig-libzia.tar.gz` → `src/libzia/`

tucnak 的 `configure.ac` 先找已安装的 `libzia.pc`，找不到就检查 `../libzia`
**目录**；找到时静态链接 `../libzia/src/.libs/libzia.a`，并从
`../libzia/bin/zia-config` 读取编译/链接标志。所以配方先构建 libzia，再在源目录
内构建 tucnak，让 `../libzia` 正好解析成功。

## 源码来源说明（重要）

编写本配方时（2026-10-04）上游两个官方入口都不可用：

- `https://gitlab.com/tucnak/tucnak/-/archive/4.67/tucnak-4.67.tar.gz` → HTTP 403，
  Cloudflare「Just a moment...」JS 挑战；git smart-HTTP 端点同样超时。
- `https://www.tucnak.org/tucnak-4.67.tar.gz` → HTTP 502
  `WEDOS.protection – Origin server error`；该站点根页面同样 502，即源站宕机。

因此 `conandata.yml` 使用 Debian pool 中**未经修改的上游发布 tarball**。Debian 从
不重打包 `.orig.tar.gz`，且在已签名的 `tucnak_4.67-1.dsc` 中记录了 sha256，
sha256 匹配即证明字节与上游 4.67 发布版一致。校验值：

| 文件 | sha256 |
| --- | --- |
| `tucnak_4.67.orig.tar.gz` | `d2c62691df7ddd1154930e2341449501630fc02a81f31dd5b8da81b3c009f4f8` |
| `tucnak_4.67.orig-libzia.tar.gz` | `305b505abad5b0258a31c7aca190ff4de9bcf6c133d3bc5802ef8b980feb2f38` |

## OHOS 适配要点

1. **libzia 的 `strerror_r` 探测失效（真实上游 bug）**
   `configure` 把探测结果写进 `config.h` 的 `Z_STRERROR_R_RETURNS_INT`，但**没有**
   任何 libzia 源文件 include `config.h`（它们只读 `include/zconfig.h`）。glibc 上
   `strerror_r` 返回 `char *`，恰好就是代码落入的 `#else` 分支，所以这个 bug 一直
   隐身；OHOS 的 XSI/musl 版本返回 `int`，于是 `src/zerror.c` 编译失败：

   ```
   zerror.c:190:11: error: incompatible integer to pointer conversion
                      initializing 'char *' with an expression of type 'int'
   ```

   配方传入 configure 自己算出的同一个值 `-DZ_STRERROR_R_RETURNS_INT`，而不是整个
   include `config.h`，以免顺带激活该文件里其它同样失效的 `AC_DEFINE`。

2. **`PKG_CONFIG_LIBDIR` 必须指向生成目录**
   不设置时 libzia 会去用构建主机上的 `/usr/include/glib-2.0`（x86_64）。必须指向
   PkgConfigDeps 生成的 `conan/` 目录，而不是包目录里的 `.pc` —— 后者的
   `glib-2.0.pc` 是裸的 `prefix=/`，会解析到 `/lib`。

3. **修正 pcre2 的 `.la`**
   制品仓的 `pcre2/10.45` 附带 `libpcre2-8.la`，其中 `libdir='//lib'`、
   `dependency_libs` 指向鸿蒙设备前缀（设备上构建的残留）。libtool 会判定库「被移动」
   然后去 sed 那个失效路径，报
   `'//lib/libpcre2-8.la' is not a valid libtool archive`。配方把修正后的 `.la` 副本
   放进构建目录并置于 `LDFLAGS` 最前，**不修改 Conan 缓存**。

4. **libzia 只能静态构建，且不能 `make all`**
   共享库会让 libtool 试图嵌入依赖，而 glib/pcre2 只有普通归档文件。反过来
   `src/Makefile.am` 里有个无条件的 `libzia-4.67.so.d: libzia.la map2d` 目标，它
   sed 的链接映射只有共享构建才会产出，所以静态下 `make all` 必然失败。配方改为
   `make -C src libzia.la`。

5. **tucnak 的 `config.sub` 太旧**
   它捆绑的是 2018-02-22 版，拒绝任何 `-ohos` 三元组。tucnak 的 `configure.ac`
   完全没有 `host_os`/`host_cpu` 分支，因此用不带 `-ohos` 的拼写是惰性的，只要能
   通过 `config.sub` 校验即可；实际代码生成不受影响（`CC` 与 sysroot 都是 OHOS 的）。

6. **autoconf 的 `config.status` 临时目录在 HMDFS 上不可读**
   生成的 `configure` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建 config.status
   的暂存目录。在 OHOS 的 HMDFS 构建工作区上，`077` 建出的目录/文件对构建用户不可读，
   `config.status` 随即失败：

   ```
   ./config.status: line 824: ./conffAdKch/subs1.awk: Permission denied
   config.status: error: could not setup config files machinery
   ```

   该片段是 autoconf 由 `AC_OUTPUT` 生成的样板代码，**并不存在于**任何一个
   `configure.ac` 中，因此只能修改生成的 `configure`（libzia 与 tucnak 各一处），
   见 `patches/0001-fix-config-status-hmdfs-umask.patch`（`umask 077` → `022`）。

## 产物

`bin/tucnak` —— AArch64 PIE，动态依赖仅 `libc.so`（glib/pcre2 为静态归档，
因此除平台 libc 外自包含）。