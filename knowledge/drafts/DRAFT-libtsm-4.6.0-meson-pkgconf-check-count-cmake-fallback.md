# DRAFT-libtsm-4.6.0-meson-pkgconf-check-count-cmake-fallback
> Meson+check库在OHOS下pkgconf供给注入与用例级计数及消费者CMake平台别名回退
## 问题特征（真实日志片段/标记）
- `../test/meson.build:3:12: ERROR: Dependency lookup for check with method 'pkg-config' failed: Pkg-config for machine host machine not found. Giving up.`
- `Run-time dependency check found: NO (tried cmake)`，`build()` 的 `meson.configure()` 报 `Error 1`。
- 中间态上游标记只报套件数：`HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "meson+check", "command": "TEMP=<build_folder> meson test -C builddir --print-errorlogs", "discovered": 7, "executed": 7, "passed": 7, "failed": 0, "skipped": 0}`，与审计44用例不符。
- 上游执行命令：`RUN: NINJA="/storage/Users/currentUser/usr/local/bin/ninja" meson test -C "/storage/Users/currentUser/preflight/clients/42a846a9be06/conan-home/p/b/libts1d51ada263738/b/builddir" --print-errorlogs`。
- 消费者侧：`CMake Error at CMakeLists.txt:2 (project):` + `-- Configuring incomplete, errors occurred!` + `System is unknown to cmake` + `CMAKE_C_COMPILER /data/service/hnp/bin/clang` 配置失败。
- 前置链路同仓曾出现：`/bin/sh: meson: inaccessible or not found`、`Unknown compiler(s): [['/data/service/hnp/bin/clang']]`、`Unable to detect linker`，本条目仅收敛pkgconf供给、计数与消费者别名三段。
## 根因
- 配方将 `tests` 打开并用 `test_requires check/0.15.2` + `PkgConfigDeps` 提供 `check.pc`，但 `build_requirements` 只有 `meson` 而无 `pkg-config` 可执行文件，真机 `PATH` 无系统 `pkg-config`，故 `meson` 的 `pkg-config` 与 `cmake` 两路探测均失败。
- 仅声明 `tool_requires pkgconf/3.0.5` 不够：未把 `conan` 供给的 `pkgconf` 的 `bindir` 加入 `_meson_environment` 的 `PATH`，也未向 `meson machine` 文件写入绝对 `pkgconfig` 条目，`worker` 无系统 `pkg-config` 时 `meson PATH` 探测必然失败。
- `meson` 默认隐藏通过用例 `stdout` 导致 `Checks:` 行缺失，回退到7套件 `Ok/Fail` 汇总冒充44用例；`cmake 4.4.3` 无 `Platform/HarmonyOS` 模块且该 `worker` 缺 `profile` 绝对编译器路径，消费者直接配置必然报 `System is unknown to cmake`。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/l/libtsm/4.6.0/conanfile.py:build_requirements()` 新增 `self.tool_requires("meson/1.11.0")`、`self.tool_requires("pkgconf/3.0.5")`、`self.test_requires("check/0.15.2")`，注释说明供给 `meson pkg-config` 探测。
2. `generate()` 新增 `PkgConfigDeps` 并将 `tests` 设为 `True`，保留 `ar` 绝对路径并注入 `ninja/ar/ranlib` 到 `machine` 文件；新增 `_pkgconf_exe_from_conan/_discover_pkg_config/_build_tool_bindirs`，从 `dependencies.build` 解析 `pkgconf/meson` 的 `bindir`。
3. 新增 `_inject_pkg_config()`：向 `conan_meson_native/cross.ini` 写入 `conan pkgconf` 绝对路径的 `pkgconfig` 条目（缺失时才写，不覆盖已有）；`_meson_environment()` 前置这些 `bindir` 到 `PATH`，使 `meson configure` 与 `meson test` 均可找到 `pkg-config`。
4. `build()` 在 `meson.build` 后以可写 `TEMP/TMP/TMPDIR=build_folder` 运行 `meson test -v -C builddir --print-errorlogs`，同步证据命令字符串；解析 `Checks/Failures/Errors` 与 `Ok/Fail` 汇总并输出 `HMBS_UPSTREAM_TEST_RESULT`，新增 `case_lines_found` 门禁：无 `Checks` 行时直接判失败，不再用套件数冒充通过。
5. `test_package/conanfile.py:generate()` 导出可写 `TEMP/TMP/TMPDIR`，`generators` 改仅 `CMakeDeps` 并显式 `CMakeToolchain`，置 `CMAKE_SYSTEM_NAME=Linux`；加 `profile` 编译器可用性检查，缺失时回退 `shutil.which` 的 `clang/clang++`；`test()` 验证后输出 `HMBS_TEST_PACKAGE_RESULT`。`MANIFEST.yml` 的 `upstream_test_in_build` 改为 `true`，`manifest.yaml:configure_options` 同步为 `-Dtests=true`。
## 禁止策略
- 禁止以7套件数冒充44用例数放行：`HMBS_UPSTREAM_TEST_RESULT={..."discovered":7..."status":"passed"}` 无 `Checks` 行时必须判失败并加 `-v` 重跑，否则审计44用例不符退回修复循环。
- 禁止删除 `-v` 回退到套件级计数；禁止 `Linux` 别名扩散到主库 `meson` 构建；编译器回退只在配置路径不可用时生效，不覆盖健康 `worker`。
## 与相近条目的边界（查重）
- 现有条目无 `meson+check+pkgconf` 场景覆盖，本条目为新增覆盖：`conan pkgconf bindir` 前置+`machine` 文件注入解决一类 `Meson pkg-config` 探测失败，`-v Checks` 计数解决套件数冒充用例数的一类证据问题。
- 与 `boost/buildtorrent` 的 `readonly_tmp` 仅构建系统相邻而方案不同：彼为 `temporary_directory_readonly` 下可写 `TMPDIR` 运行测试，本条目叠加 `pkgconf` 供给注入、用例级计数门禁与消费者 `CMake` 平台别名回退。
## 适用判断
- 适用：`meson` 加 `check` 测试只报 `Ok` 数而无 `Checks` 行时；`cmake` 消费者包在无 `HarmonyOS` 平台模块的 `cmake` 上报 `System is unknown to cmake` 时；`meson configure` 报 `Pkg-config for machine host machine not found` 但配方已有 `tool_requires pkgconf` 时。
- 不适用：`SSH` 网关熔断、锁槽排队超时、`github.com ConnectTimeout` 等环境/下载故障，不得借用本方案改配方；`make install DESTDIR` 拾取、`clunk` 头文件跨目录安装等非 `meson pkg-config` 失败域不适用。
