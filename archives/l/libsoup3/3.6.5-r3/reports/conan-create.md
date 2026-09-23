# libsoup3 3.6.5-r3 — conan create 构建证据（R12 由 conan-create.log 改写）

> 本文件为 R12 处置产物：原 `reports/conan-create.log` 因仓库禁止 `*.log`
> 提交而改写为 .md，证据要点完整保留（命令、cwd、退出码、关键输出）。

## 命令与退出码

- **命令**（cwd = `archives/l/libsoup3/3.6.5-r3`）：
  `python3 -c "from conans.conan import run; import sys; sys.argv=['conan','create','.','--user=ohpcd','--channel=stable','-pr:h=$HOME/.conan2/profiles/ohos','-pr:b=$HOME/.conan2/profiles/ohos','--build=missing']; run()"`
- **exit_code = 0**（conan create 成功，test_package L1 通过）

## 关键输出（要点摘录）

- 配方导出：`libsoup3/3.6.5-r3@ohpcd/stable` export 成功，含
  `conandata.yml`、`conanfile.py` 与补丁 `0001-hsts-g_uri_get_port-null-guard.patch`
  （`Copied 1 '.patch' file`）。
- 输入 profile：host/build 均为 OHOS armv8 clang15 Release，工具链
  `/data/service/hnp/bin/clang`、`/data/service/hnp/bin/clang++`。
- 依赖图：`glib/2.84.0.1.1#5a9bdf1a…`（Cache）、`libpsl/0.21.5.1`、
  `libnghttp2/1.70.0`、`sqlite3/3.49.1`、`zlib/1.3.1.1`、`libffi/3.4.4`、
  `libidn2/2.3.7.1` 等（均来自 ohpcd registry，无捎带适配）。
- 构建：meson（ninja）编译 libsoup-3.0.so.0.7.4 与 libsoup-3.0-static.a 完成，
  `Build folder: .../3.6.5-r3/builddir`。
- test_package：CMake 配置 + 构建 + 运行通过；测试输出
  `test libsoup3 3.6.5-r3: OK (host=example.com, session+message ok)`。

## 发布形态取证（同轮完成，见 reports/forensics/r2-vs-r3.md）

- `llvm-readelf -d libsoup-3.0.so.0.7.4 | grep NEEDED` 含
  `libgobject-2.0.so.0`（共享 glib/2.84.0.1.1）。
- `llvm-nm -D libsoup-3.0.so.0.7.4 | grep ' T g_type_register_fundamental'`
  无命中（消除静态内嵌 gobject）。
