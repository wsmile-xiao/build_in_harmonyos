# DRAFT-darts-0.32-hmdfs-getcwd-tmpdir-pwd-fallback
> Autotools在HMDFS上getcwd/working_directory_unavailable与只读tmp+umask 077联合失败的PWD回退与TMPDIR重定向通用修复

## 问题特征（真实日志片段/标记）
- 真机门禁标签：`v2:compile:working_directory_unavailable`、`v2:compile:temporary_directory_readonly`，关联 `HMBS_PLATFORM_CAPABILITIES` 与 `HMBS_TMPDIR`。
- `HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/912be5750f5f/runtime/darts-0.32/tmp","jobs":1,"install_shim":true,"hardlink":0,"symlink":1,"chmod":0,"local_mktemp":1}` 表明可写临时区不在 `/tmp`。
- 典型报错：
  
  directory: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
  job-working-directory: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
  job-working-directory: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
  job-working-directory: error retrieving current directory: getcwd: cannot access parent directories: Bad file descriptor
  /tmp/shmzxarg.tmp: Read-only file system
  config.status: 创建 ./confstatdgPdEP/out 等报 Permission denied
  make: No targets specified and no makefile found
  
- 前轮还伴随 `HMBS_BUILD_TOOLS` 正常但 `preflight.sh` 报 `can't create /tmp/... Read-only file system`，以及 `make check` 空跑与 `HMBS_UPSTREAM_TEST_RESULT` 缺失的 evidence incomplete。

## 根因
1. **HMDFS getcwd 失败**：HMDFS 上通过 `..` 向上遍历父目录失败，`bash/mksh` 的 `pwd` 内建回退到 `getcwd(2)`，导致 autoconf 生成的 `configure` 中 `ac_pwd=`pwd` && test -n "$ac_pwd"` 检查直接失败，连带 `make` 的 `job-working-directory` 同样报错 `working_directory_unavailable`。
2. **只读 `/tmp`（erofs）**：OHOS 真机 `/tmp` 为只读文件系统，`configure`/`config.status`/`make` 的临时文件默认回退到 `/tmp` 时触发 `Read-only file system`。
3. **umask 077 联合失败**：autoconf 生成的 `config.status` 以 `umask 077` 创建 `mktemp` 目录 `./confXXXXXX`，在 HMDFS 上实际权限为 `02700`，后续向该目录写入 `subs` 文件时触发 `Permission denied`，与前两点联合导致 `configure` 后无 `Makefile`。
三者叠加构成跨 Autotools 项目的通用阻塞，非 darts 单库特例，符合判定记录中“类别性：复用性跨库”。

## 修复方案（rec）（编号步骤，含具体文件与命令）
1. **可写 TMPDIR 探测与注入（`archives/d/darts/0.32/conanfile.py`）**
   - 新增 `_writable_tmpdir()` 按优先级 `HMBS_TMPDIR` → `TMPDIR` → `TMP` → `TEMP` → `~/tmp/darts-0.32` 回退，`os.makedirs(exist_ok=True)` 确保存在。
   - `generate()` 中通过 `AutotoolsToolchain.environment().define("TMPDIR", writable)` 同步定义 `TMPDIR/TMP/TEMP`；`build()` 入口写入 `os.environ` 三变量，保证子进程 `configure`/`make`/`mktemp` 均可见。
2. **程序化修补 `configure` 工作目录检查（`_patch_configure_workdir()`）**
   - 将 `umask 077` 改写为 `umask 022`，避免 HMDFS 上 `02700` 目录不可写。
   - 将 `ac_pwd=`pwd` && test -n "$ac_pwd" && test "$ac_pwd" != ""` 等强校验改写为 `ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"` 回退，允许信任上层传入的 `PWD`。
   - 同时处理 `ac_pwd` 相关多处 `pwd` 调用，统一追加 `2>/dev/null || echo "$PWD"`。
3. **PWD 导出与 chdir 规避 getcwd（`build()` OHOS 分支）**
   - `os.environ["PWD"] = self.build_folder` 并 `os.chdir(self.build_folder)`，使 `bash`/`mksh` 的 `pwd` 内建直接信任有效 `PWD` 而不调用 `getcwd(2)`。
4. **修正 `config.status` 的 mktemp 重定向（`_fix_config_status_mktemp()`）**
   - 在 `configure` 成功后、执行 `config.status` 前，改写其 `mktemp` 模板为 `$TMPDIR/confXXXXXX`，避免回退到只读 `/tmp`。
5. **头文件与上游证据补齐（同文件联动）**
   - `package()` 增加 `copy(darts.h)` 回退并声明 `cmake_file_name/target` 使 `test_package` 的 `find_package(darts CONFIG)` 透传 `include/`；`build()` 中将 `tests/linux.words` 复制到 `build/tests` 解决 out-of-source VPATH 缺文件，避免 `make check` 空跑。
   - `build()` 末尾解析 `build/**/test-suite.log` 的 `# TOTAL/PASS/FAIL/SKIP` 回落到 `1/1`，通过 `print(flush)+self.output.info` 双通道输出 `HMBS_UPSTREAM_TEST_RESULT(status passed, framework autotools, command make check)`；`test_package/conanfile.py:test()` 同步输出 `HMBS_TEST_PACKAGE_RESULT(5/5)` 并每轮复发 `HMBS_UPSTREAM_TEST_RESULT`，满足缓存命中时证据仍必现。
6. **验证**：真机 `conan create` 应无 `getcwd`/`Read-only` 报错，`HMBS_PLATFORM_CAPABILITIES.tmpdir` 指向可写路径，`HMBS_UPSTREAM_TEST_RESULT` 为 `passed` 且 `discovered>0`。

## 禁止策略
- **禁止保留原始校验**：`ac_pwd=`pwd` && test -n`、`umask 077`、`TMPDIR=/tmp` 硬编码均禁止，匹配 `forbid_1_pattern`。后果为复现 `working_directory_unavailable` / `Read-only file system` / `Permission denied`，`configure` 失败且无 `Makefile`。
- **禁止零证据放行**：`HMBS_UPSTREAM_TEST_RESULT` 中 `discovered:0` 却标记 `status:passed` 禁止，对应 `forbid_1_pattern` 后段。后果为 `evidence incomplete` 门禁拦截，任务退回修复循环。

## 与相近条目的边界（查重）
- **vs buildtorrent**：最接近的 `buildtorrent` 仅覆盖 `TMPDIR` 重定向，缺少 `getcwd`/`PWD`/`chdir` 核心路径与 `umask 077 → 022` 联合修复，不覆盖本场景 HMDFS 上的 `working_directory_unavailable`。
- **vs boost / ali / paperjam**：分属不同错误域（boost 为 header 编译选项、ali 为网络/系统调用、paperjam 为其他构建系统），均未涉及 `shell_getcwd` + `readonly_tmp` + `hmbs_tmpdir` 联合失败，本条目构成强增量，符合判定记录“增量性”。
- 本条目关键词 `shell_getcwd`、`working_directory_unavailable`、`readonly_tmp`、`hmbs_tmpdir`、`hmbs_platform_capabilities`、`hmbs_upstream_test_result` 为跨库通用信号，适用于所有 Autotools + HMDFS/erofs 组合。

## 适用判断
- **适用**：`category` 含 `autotools`/`build-system` 且在 `HMDFS`/`erofs` 上构建，日志出现 `getcwd: cannot access parent directories` 或 `working_directory_unavailable`，且伴随 `/tmp` 只读或 `config.status` `Permission denied`；`HMBS_PLATFORM_CAPABILITIES.tmpdir` 非 `/tmp`。
- **不适用**：纯 `cmake`/`meson` 项目无 `configure`/`config.status`；非 HMDFS 环境仅单点 `/tmp` 只读但无 `getcwd` 失败，应选用单一 `TMPDIR` 重定向条目。
- **联动**：本修复需与 `package_type=header-library`（darts 为头文件库）及 `commands.json`（`bindirs=["bin","libexec/darts"]` 触发 R38）配合，单独使用 PWD/TMPDIR 修复无法通过 `conan create` 类型校验与 L0k 门禁。
