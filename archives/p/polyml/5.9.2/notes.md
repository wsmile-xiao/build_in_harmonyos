# Poly/ML 5.9.2 HarmonyOS PC 适配笔记

## 上游与许可证

- 官方源码：`https://github.com/polyml/polyml/releases/tag/v5.9.2`
- 源码 SHA-256：`5cf5f77767568c25cf880acc2d0a32ee3d399e935475ab1626e8192fc3b07390`
- 许可证：`LGPL-2.1-or-later`

## 构建配置

使用原生 OHOS/aarch64 工具链自举，不传 `--build/--host/--target`。采用静态构建、关闭 X11，并因 GMP 6.3.0 尚未发布而显式使用 `--without-gmp`。配方先应用源码补丁，再执行 `autoreconf -fi` 从 patched `configure.ac` 重新生成 `configure`，遵守 R6。

## 平台适配

- `config.guess/config.sub` 识别 HarmonyOS triplet。
- `configure.ac` 覆盖 config.status 的临时目录生成逻辑：HarmonyOS 使用应用私有缓存 `/data/storage/el2/base/cache`，不再将安全性建立在 HMDFS 的 `umask` 结果上；其他平台保持上游当前目录逻辑。设备探测确认该缓存父目录为进程 UID/GID 所有、mode 0700、标签 `hishell_hap_data_file`，其下以 `umask 077` 创建的目录为 0700。
- `OS.FileSys.tmpName()` 优先读取非空 `$TMPDIR`，否则保留上游 `P_tmpdir`/`/tmp` fallback。
- FaultLogger 将早期 bootstrap 崩溃定位到 `TaskData::~TaskData()` 释放仍注册的 alternate signal stack。当前修复保留注册，在拥有者线程退出时以 `SS_DISABLE` 注销；注销成功后主线程 join 并正常释放。在具备 SA_ONSTACK 与 HAVE_SIGALTSTACK 能力的平台上，若注销失败，则只避免危险释放而保留该小块内存。
- 当前 HarmonyOS 用户沙盒对 pathname AF_UNIX `bind()` 返回 EPERM。Test193 仅将已实测 EPERM 视为运行时能力不适用；其他 `OS.SysErr` 原样重抛。支持 bind 的平台仍执行 listen/connect/send/recv 完整闭环。
- 未修改 JIT 或 AArch64 code generation。RWX mmap、RW→RX mprotect 与最小生成代码执行均已实测成功。

## 包契约

上游 `make install` 明确安装 `libpolymain.a`、`libpolyml.a` 和描述“run-time and main program libraries”的 `polyml.pc`，因此它们是可公开消费的静态库契约，而不只是 CLI 内部对象。Conan 按静态链接真实依赖顺序声明 `cpp_info.libs = ["polymain", "polyml"]`；`test_package` 使用 CMakeDeps 生成的 `polyml::polyml` target 编译、链接并运行 C++ consumer，不硬编码包目录或 `-l` 参数。

## test_package 布局

`test_package` 不依赖 CI 私有 `BUILD_DIR`。它使用 Conan 2 test-package 特殊布局 `cmake_layout(self, build_folder="$TMP")`；Conan 2.29.1 通过 `tempfile.mkdtemp()` 为每次调用创建遵循 `TMPDIR` 的唯一 out-of-source 根。`CMakeToolchain.user_presets_path=False` 保留，避免在源码目录生成 `CMakeUserPresets.json`。因此标准 `conan create`、独立 `conan test` 和并发测试均不需要 launcher 注入额外变量。 这里的“不依赖”仅指 recipe/test_package 执行层；当前基线 `ci/conan/build_and_test.sh:749` 的预下载实现自身仍读取命令作用域 `BUILD_DIR`，Round 18 仅为该 launcher 提供可写目录，这不构成 test_package 对 `BUILD_DIR` 的依赖。

## 测试口径

上游 `make check -j1` 枚举 202 个预期成功与 71 个预期静态失败的 `.ML` 文件，共 273 个回归测试文件。Test193 在当前设备为 N/A，不应声明为 Unix socket 闭环 PASS。`test_package` 运行安装后的 `poly --script test_polyml.ML`，包含 4 项真实 Standard ML 功能检查。

`polyimport` 是 bootstrap/import 工具，不提供标准 `--version`/`--help` 契约；CI L2 因此给出非阻塞 warning。L4 的 dangerous-functions 扫描也属于静态 warning，补丁仍需按文本和最小语义审查。
