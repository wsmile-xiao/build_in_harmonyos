# bti 034 适配笔记

## 编译环境

- 构建系统：autotools（发布 tarball 自带预生成 `configure`，未跑 autoreconf）
- 编译日期：2026-09-13
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`，OHOS aarch64）
- 目标：`os=OHOS os.version=6.0 arch=armv8 compiler=clang`（`ci/conan/profiles/ohos-aarch64`）
- 状态：built（本地 conan-verify 通过；尚未发布到制品仓）

## 编译步骤

权威命令写在 `manifest.yaml` 的 `validation.*.command`，此处只说明流程：

1. `conan create`（或 `conan-verify`）取 `conanfile.py` + `conandata.yml`；
   `source()` 下载 kernel.org 发布 tarball 并按 sha256 校验。
2. `apply_conandata_patches()` 依次打 0001（bti-shrink-urls）、0002（bti.c）与 0003（configure）。
3. `AutotoolsToolchain` 注入 `--prefix`/`CC`/`CFLAGS`；
   `PkgConfigDeps` 在 generators_folder 生成 `libcurl.pc`/`libxml-2.0.pc`/
   `json-c.pc`/`oauth.pc`/`libpcre.pc`，并通过 configure 变量
   `PKG_CONFIG_PATH=<generators_folder>` 提供给 `PKG_CHECK_MODULES`。
4. `configure` → `make -j1` → `make install`（`Autotools.install()` 自动带
   `DESTDIR=<package_folder>`）。
5. `test_package` 执行 `test.sh`，对安装出来的 `bin/bti` 做 4 项行为断言。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 失败：`./config.status[734]: can't create ./confjq6uRh/subs1.awk: Permission denied` | HMDFS：`config.status` 用 `umask 077` 建临时目录，落盘为 0700；setgid hmdfs 挂载上该目录对构建用户不可写（E114 同族） | 补丁 `0003-configure.patch` 把两处 `umask 077` 放宽为 `umask 022`（发布 tarball 只有预生成 configure，无法改 configure.ac 后 autoreconf） |
| 2 | 链接失败：`ld.lld: error: undefined symbol: is_error` | json-c 0.13 起移除了 `is_error` 宏，上游 2014 年的 `bti.c` 仍使用它 | 补丁 `0002-bti.c.patch` 把 3 处调用改为显式 `!= NULL` 比较（与 Debian `bti_034-6` 的 `replace_removed_is_error.patch` 同口径） |
| 3 | 依赖图计算失败：`Conflict between openssl/3.5.6.1 and openssl/1.1.1w` | 已发布 `liboauth/1.0.3` 钉 `openssl/1.1.1w`，已发布 `curl/8.15.0` 钉 `openssl/3.5.6.1`，且两者各自只发布了一个 package_id | 配方内 `self.requires("openssl/3.5.6.1", override=True)` 统一；liboauth 为静态小库，构建时从源码重建（设备实测通过） |
| 4 | `PKG_CHECK_MODULES(LIBOAUTH, oauth)` / `(LIBPCRE, libpcre)` 找不到模块 | pkg-config 模块名与 Conan 包名不同（包 `liboauth` → 模块 `oauth`；包 `pcre` → 模块 `libpcre`） | `PkgConfigDeps.set_property(dep, "pkg_config_name", ...)` 改名（Conan 2.29 的 `PkgConfigDeps` API，不是 `dependencies[...].set_property`） |
| 5 | 直接执行 `bin/bti-shrink-urls` 报 `bad interpreter: /bin/bash: No such file or directory`（rc=126） | OHOS 没有 `/bin/bash`（bash 只在 harmonybrew 的 `~/.harmonybrew/bin`） | 补丁 `0001-bti-shrink-urls.patch` 把 shebang 改为 `#!/bin/sh`；`/bin/sh -n` 语法检查与 `/bin/sh bti-shrink-urls --help` 运行均通过 |

## 源码修改

补丁见 `patches/`，逐字内容见 `reports/conan-create-log.md` 的 `Apply patch` 段：

1. `patches/0001-bti-shrink-urls.patch` — `bin_SCRIPTS` 安装的脚本 shebang
   `#!/bin/bash` → `#!/bin/sh`（OHOS 无 `/bin/bash`）。不涉及平台宏，无 `#ifdef` 守卫。
2. `patches/0002-bti.c.patch` — `json_object_object_foreach_alt` 宏内 1 处 +
   `parse_response_json`/`parse_timeline_json` 各 1 处 `is_error()` → 显式 NULL 比较。
   不涉及平台宏，无 `#ifdef` 守卫。
3. `patches/0003-configure.patch` — `configure` 中创建临时目录的两处
   `umask 077` → `umask 022`。这是生成文件，但发布 tarball 只提供它、
   CI worker 无 automake 无法 autoreconf，故就地修补（liboauth/a52dec 同法）。

## 依赖版本

- `liboauth/1.0.3`（静态；本配方 override 后按 openssl/3.5.6.1 重建）
- `curl/8.15.0`（共享，导出 `libcurl.pc`）
- `libxml2/2.15.3`（共享）
- `json-c/0.17`（共享）
- `pcre/8.45`（PCRE1，静态；注意不是 pcre2）
- `openssl/3.5.6.1`（curl 的传递依赖；被显式 override 统一）

- 运行期 readline 不是构建依赖：上游用 `dlopen` 尝试
  `libreadline.so.6/5/4`、`libedit.so.2`，找不到则回退 `fgets`。

## 验证结果

- 原生：`configure`（打补丁后）rc=0 → `make -j1` rc=0 → `make install` rc=0；
  `./bti --version` 输出 `bti - version 034`。
- 上游测试：**上游无测试套件**，`make check` 输出
  `make: Nothing to be done for 'check'.`（rc=0）；清点证据见
  `test_package/MANIFEST.yml` 与 `reports/notes-test-inventory.md`。
- Conan：`conan-verify` G0-G4/L2/L4/L5 结果见 `reports/conan-verify-report.md`；
  干净轮 `conan create` 日志逐字留档于 `reports/conan-create-log.md`。
- `test_package`：4 项行为断言（`--version` / `--help` / 缺失配置诊断 /
  离线 dry-run 请求构造），见 `test_package/test.sh`。

## 注意事项

- 上游发布 tarball 的 `configure` 是 autoconf 2.69 生成的；补丁 0003 打的就是
  这个预生成文件，`patch_strip` 用默认值。
- 制品版本号就是任务卡给的 `034`（ConanName 合法：3 字符、`[a-z0-9]` 开头），
  不需要 `set_version()` 归一化。
- 制品仓 `liboauth/1.0.3` 只按 `openssl/1.1.1w` 发布过，本包消费侧 override 到
  `3.5.6.1` 后该依赖的 package_id 在制品仓不存在，构建时由 `--build=missing`
  从源码重建；已登记到容器层 `feedback/pending/`。
