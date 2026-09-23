- **三方库名称**：libgda5（GNU Data Access 5，GLib/GObject 数据库抽象层；运行库名 libgda-5.0）
- **上游版本**：5.2.10（tag `LIBGDA_5_2_10` → commit `85a2532df64698306fd3be324bb2052fb1b80fd3`）
- **上游仓库地址**：https://gitlab.gnome.org/GNOME/libgda （源码 tarball：https://ftp.gnome.org/pub/GNOME/sources/libgda/5.2/libgda-5.2.10.tar.xz，sha256 `6f6cdf7b8053f553b907e0c88a6064eb48cf2751852eb24323dcf027792334c8`）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（编译 SKILL）；知识图谱命中 E114（HMDFS 上 `config.status` 临时目录 `umask 077` 不可写 → 用 configure 单文件补丁消除）、G0 预查报告 E490（autotools helper 脚本可执行位，实测未触发）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 34 | 来源：`tests/`（顶层 9 + data-models 9 + meta-store 2 + multi-threading 5 + parser 6 + value-holders 3） |
| 集成测试 | 4 | 来源：`tests/providers` 与 `tests/meta-store`（check_sqlite、check_mysql、check_meta_store_postgresql、check_meta_store_mysql） |
| 其他测试 | 7 | `tests/ui` 2 项（`--without-ui`）+ `providers` 5 项（bdb/firebird/mdb/oracle/postgres，对应 provider 全部关闭）→ 本合同不适用 |
| **合计** | **45** | 其中**适用 38**（37 可运行 + 1 `check_mysql` 因 MySQL provider 未启用而未构建） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 34 | 不变 | 未修改上游任何用例，逐项直接执行（日志见下） |
| 集成测试 | 4 | 不变 | check_sqlite **PASS**；check_meta_store_postgresql/mysql **SKIP**（需真实服务端）；check_mysql 未构建（MySQL provider 未启用） |
| 鸿蒙特有测试 | 4 | 新增 | `test_package/test_ohos.c`：`__OHOS__` 平台守卫 / provider 插件 `dlopen(RTLD_NOW)` / 中文+emoji UTF-8 往返 / HMDFS 文件型数据库落盘与重开（15 断言） |
| **合计** | **42** | **+4** | 上游适用 38（35 PASS / 2 SKIP / 1 未构建 / 0 FAIL）+ 鸿蒙特有 4 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明（非修改）：本平台 automake 并行测试 harness 不可用（libtool wrapper 报
> `getcwd: cannot access parent directories` → `providers/.libs/check_xxx: No such file`），
> 因此以 runner 直接执行**同一批**测试二进制（`make -C tests -k check` 负责构建），
> `tests/` 源码零改动。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：①消费者视角功能测试（provider 发现 + 连接 + DDL/DML/DQL 往返 + 值校验）；
>   ②HarmonyOS 平台特性测试 4 组共 15 条断言。
> - **补全原因**：上游只有库内测试，没有"消费者按 conan 依赖消费"的验证，也没有平台特性用例
>   （插件动态加载、UTF-8、HMDFS 文件 I/O）。
> - **新增测试文件清单**：
>   1. `test_package/test_libgda.c` — 消费者功能测试（11 条断言，`test_libgda: ALL PASS`）
>   2. `test_package/test_ohos.c` — 鸿蒙专项测试（4 组 / 15 条断言，`test_ohos: ALL PASS`）
>   3. `test_package/CMakeLists.txt`、`test_package/conanfile.py`、`test_package/MANIFEST.yml` — L1 测试工程与声明

## 验证结果

- 编译状态：**通过**（`conan create` exit 0：手工流程与工具流程各一次；conan-verify G2 PASS、finish 内 W3 本地 CI `Pass rate 100.0% (1/1)`）
- 上游测试用例通过率：**35/38（92.1%）**（2 项 SKIP 因环境无 PostgreSQL/MySQL 服务端；1 项 `check_mysql` 因 MySQL provider 未启用而未构建；**0 FAIL**）
- 新增测试用例通过率：**2/2（100%）**（test_libgda 11 断言 + test_ohos 15 断言全部通过）

## 补充说明

**关键平台适配点（均在配方内完成，未改动上游源码）**

1. glib 必须用 **shared** 变体（glib/2.88.3）：静态 glib 会被 `-export-symbols-regex` 隐藏后内嵌进
   `libgda-5.0.so`，消费者进程出现两套 GObject 类型系统（上游测试 6 PASS → 换 shared 后 27 PASS）。
2. SQLite 走 libgda **自带内嵌** sqlite（`--disable-system-sqlite`）：libgda 5.x 的 provider 在运行期
   `g_module_open("libsqlite3.so")`（`libgda/sqlite/gda-symbols-util.c:110`），而制品仓 sqlite3 只有静态
   `libsqlite3.a`（无 shared 变体）→ 系统 sqlite 模式下 provider 无法实例化（27 PASS → 内嵌后 35 PASS）。
3. 补丁 `patches/0001-configure-remove-umask-077.patch`：HMDFS 上 `umask 077 && mktemp -d ./confXXXXXX`
   产生的目录不可写，`config.status` 报 `subs1.awk: Permission denied`（知识 E114 同款处理，无平台宏）。
4. 构建环境适配（generate()）：PATH 前置 `gettext.org/*/bin`（`msgmerge`）、PATH 前置 conan glib 的
   `bin`（系统 glib-mkenums 的 `#!/usr/bin/perl` 在 OHOS 失效）、注入最小 `XML::Parser` stub 与
   `intltool-merge` shim（XML 模式需 perl XML::Parser，OHOS 无该模块）、`intltool` 的 `ITSTOOL` 探测 stub、
   注入 `libintl.h` shim（sysroot 的 libintl.h 缺 `ngettext`）、重定位 pcre2 `.la`（`libdir='//lib'`）、
   `--build/--host=aarch64-linux`（tarball 内 config.guess 不识别 HarmonyOS）。
5. 关闭项与原因：`--disable-tools`（`AC_CHECK_LIB(ncurses)` 需 `libncurses.so`，ncurses 包只有静态
   `libncursesw.a`）；`--disable-vala`（无 OHOS valac/vapigen 验证）；introspection 保持默认 auto
   （OHOS 无 `gobject-introspection-1.0.pc`；且 upstream `configure.ac:494` 未加引号的 test 会让
   `--disable-introspection` 反而使 `ENABLE_GDA_GI` 恒真 → `No rule to make target 'Gda-5.0.typelib'`）。
6. 未启用 provider：MySQL（`mysql-client/9.7.1` 与 glib 存在 zlib 版本硬冲突）、PostgreSQL
   （探测入口 `pg_config`，libpq 包不提供）——对应上游用例因此未构建/跳过。

**已知限制 / TODO**

- `prefix=/`（conan autotools + DESTDIR 安装）导致包内 `.pc` 与编译期路径指向根目录；运行期由
  test_package 的 `GDA_TOP_BUILD_DIR` 指向包内 `lib/libgda-5.0` 解决 provider 定位。若后续需要
  非 conan 消费者直接使用包内 `.pc`，可在 `package()` 中把 `.pc` 的 `prefix` 改写为 package folder。
- 证据日志与逐用例结果：`archives/l/libgda5/5.2.10/notes.md`、`reports/test-report.md`、
  `reports/conan-verify-report.md`、`reports/w3-local-ci.log`、`reports/conan-create.log`
  （`reports/` 被仓库 `.gitignore` 忽略，随 PR 提交时用 `git add -f`）。
