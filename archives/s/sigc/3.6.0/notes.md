# sigc (libsigc++) 3.6.0 适配笔记

## Scope

- Conan reference: `sigc/3.6.0`（包名 = 平台任务名 = 归档目录名；上游项目为 libsigc++）
- Target: HarmonyOS / OHOS armv8（aarch64），SDK Clang 15.0.4 工具链
- Build system: Meson + Ninja
- Third-party Conan dependencies: none（不声明 `tool_requires`，沿用 3.0.6 线：Meson 由构建机提供）
- Delivery: shared library, headers, pkg-config metadata, license

> 命名说明：同一上游在仓库中有多条历史归档（`libsigc` 2.10.8/2.12.1/3.0.6、`libsigc-2` 2.12.2 等）。
> 本包按平台任务名 `sigc` 发布，使 CI 的 L0n 门禁（分支名 = 包目录名-版本号）与平台任务绑定
>（分支名 = 任务详情中的 `feat/sigc-3.6.0`）同时成立。

## Source

GNOME 官方发布目录（上游权威源，R39）：
`https://download.gnome.org/sources/libsigc++/3.6/libsigc++-3.6.0.tar.xz`
（HTTP 200，991392 字节）

Full SHA-256：`c3d23b37dfd6e39f2e09f091b77b1541fbfa17c4f0b6bf5c89baef7229080e17`
Archive root：`libsigc++-3.6.0/`（单一根目录）
Version evidence：`meson.build project('libsigc++', 'cpp', version: '3.6.0')`、
`ChangeLog` / `NEWS` 3.6.0 条目。

## Build

上游为 `meson dist` 生成的官方 tarball（无 configure 脚本），构建链为
Meson + Ninja，由 `conanfile.py` 的 `MesonToolchain` / `Meson` 驱动：

```bash
meson setup build --cross-file <conan machine file> --prefix=/ \
  -Ddefault_library=shared -Dmaintainer-mode=false \
  -Dbuild-documentation=false -Dvalidation=false -Dbuild-pdf=false \
  -Dbuild-examples=false -Dbenchmark=false -Dwrap_mode=nodownload
meson compile -C build
meson test -C build      # 上游 41 个测试程序
meson install -C build   # 由 Meson.install() 带 --destdir 隔离到 package 目录
```

OHOS 交叉构建复用 3.0.6 线（`archives/l/libsigc/3.0.6`）已验证的 meson 形态：
POSIX prefix（`/` + `--destdir` 隔离）、llvm-ar/llvm-ranlib 注入 machine file、
以及 Windows 宿主下的 target/sysroot/`-D__MUSL__` 显式补全分支。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 宿主未预装 meson 时 `Meson.configure()` 找不到 `meson` | Meson 是 Python 工具，OHOS SDK 只带 ninja 不带 meson | 由构建机（CI worker / 开发机）提供 meson；**不**声明 `tool_requires("meson/...")`——实测 `meson/1.11.0` 会引入 zlib 依赖链，在目标 profile 无二进制时被迫源码构建，反而增加 CI 风险。本库 2.10.8/2.12.1/3.0.6 三条已合入配方同此约定 |
| 2 | 消费者编译报 `implicit instantiation of undefined template`（`sigc::signal<int,int>` / `sigc::slot<int>`） | libsigc++ 3.x 的 signal/slot 模板改为函数类型语法 `signal<T_return(T_arg...)>`，2.x 形态仅保留前向声明 | test_package 使用 3.x 语法：`sigc::signal<int(int)>`、`sigc::slot<int()>`、`sigc::signal<void(const std::string&)>`（与上游 `tests/test_signal.cc`、`tests/test_slot.cc` 一致） |
| 3 | 交叉构建产物在宿主上无法直接执行，`meson test` 不能跑 | OHOS 动态加载器只在真机上存在 | 本地验证用 qemu-user + OHOS 运行根作为 meson `exe_wrapper`（41/41 通过）；配方内 `can_run()` 为真（真机/CI 原生）时才执行 `meson test`，交叉构建仅编译测试 |

## 依赖版本

无第三方运行时依赖（`requirements()` 为空）；运行期仅依赖 libc++ 与系统 libc（musl）。
benchmark 需要 boost、文档需要 doxygen/xsltproc，二者均通过 meson 选项关闭。

## 验证结果

- 上游测试（本机 qemu + OHOS 运行根，`meson test -C build`）：`Ok: 41 / Fail: 0`（41/41，通过率 100%）
- `conan create . -pr:h=ohos-aarch64-run -pr:b=default`：EXIT=0，产出 `sigc/3.6.0` 包，test_package 链接成功
- 产物核对：`libsigc-3.0.so`（SONAME `libsigc-3.0.so.0`，实体 `libsigc-3.0.so.0.0.0`）、
  头文件 `include/sigc++-3.0/sigc++/`、配置头 `lib/sigc++-3.0/include/sigc++config.h`、
  pkg-config `sigc++-3.0.pc`
- 语言预检：`lang-preflight` → `detected=cpp`（与任务语言一致）

## 注意事项

libsigc++ 3.x 与 2.x ABI 不兼容（`sigc++-3.0` vs `sigc++-2.0`），本配方为独立的
3.6.0（`sigc++-3.0` ABI）包；glibmm 2.68+/gtkmm 4.x 等消费者链接 `sigc++-3.0`。
安装的 `.so` 名字里带 `-3.0` 是上游 API 版本号，与包版本 3.6.0 无关。
