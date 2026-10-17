# libcli 1.10.7 适配笔记

## 编译环境
- 构建系统: makefile（原生 Makefile，无 configure / CMake / meson）
- 编译日期: 2026-09-14
- 编译器: clang（真机 `/data/service/hnp` 工具链，经 HMBS 预检实测）
- 状态: built（首轮仅完成未提交工作树，待真机预检回填实测结论）

## 上游信息
- 上游仓库: https://github.com/dparrish/libcli
- 上游版本: V1.10.7（2021-02-25 发布，GitHub tag tarball）
- 源码包: `https://github.com/dparrish/libcli/archive/refs/tags/V1.10.7.tar.gz`
- sha256: `179f78592f73492c22cc1b544b6f8cb0f6630a2f670430c118b8e084e6562e74`（2026-09-14 下载 tarball 实测）
- 许可证: LGPL-2.1-only（COPYING）
- 依赖: 无（零运行时依赖；W0 检查天然满足）

## 上游测试审计（结论：上游无测试套件）
- `Makefile`：目标仅 `all/clean/install/rpmprep/rpm/lint`，无 `check/test` 目标；`TESTS` 变量仅控制是否编译 `clitest` 演示程序，不是测试开关。
- `.github/workflows/c.yml`：唯一 CI 步骤为 `make`（编译验证），无任何测试执行。
- `clitest.c`：交互式 telnet 演示服务器（监听 8000 端口，`fork()` 多进程），非自动化测试；`clitest.txt` 仅是一行示例输入 `show counters`，无断言。
- 源码树无 `tests/`、`test/` 目录，无 gtest/pytest/ctest 痕迹。
- 因此 `test_package/MANIFEST.yml` 记 `upstream_tests_exist: false` 并附完整审计，`test()` 复发 `HMBS_UPSTREAM_TEST_RESULT(status=no_tests)`。

## 编译步骤

```bash
make CC=<conan clang> AR=<llvm-ar> DYNAMIC_LIB=0 STATIC_LIB=1 TESTS=0 LIBS= -j1
```

产物拷贝（`package()`，不用 `make install`，保证布局确定性）：
- `libcli.h` → `include/`
- `libcli.a`（默认 static）→ `lib/`；shared 变体为 `lib/libcli.so.1.10.7` + 拷贝别名 `libcli.so.1.10` / `libcli.so`
- `COPYING` → `licenses/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 非 Darwin 平台硬编码 `LIBS=-lcrypt`，OHOS 设备无独立 libcrypt | 上游面向 glibc 发行版；OHOS 为 musl，`crypt()` 由 libc 自带简化实现（见 knowledge/musl-glibc-developer-impact.md） | `build()` 传 `LIBS=`（空）覆盖，不链接 libcrypt；若真机出现 `crypt` 未定义再回退补 `-lcrypt` 探测 |
| 2 | `clitest` 演示含 `fork()` + 阻塞式 socket 交互，不适合作为构建产物或测试 | 演示程序非库功能 | `TESTS=0` 跳过（与 OpenWrt `Build/Compile` 的 `TESTS=0` 一致），库本身无 fork/socket 强依赖 |
| 3 | Makefile 用 `override CFLAGS += ... -Werror`，真机 clang 报 `cli_init()` 无原型（`-Wstrict-prototypes`，`libcli.c:596`）导致 `-Werror` 失败 | 上游在旧 gcc 仅警告；新 clang 视为错误；`libcli.h` 原型已是 `(void)`，仅 `libcli.c` 定义滞后 | `build()` 内 `replace_in_file` 精确替换为 `(void)`（diff 补丁因 hunk 行号漂移应用失败，已删除），保留 `-Werror` 不动 |
| 4 | 上游对象统一 `-fPIC` 编译，`fPIC` 选项实际无区分度 | 上游编译规则 `%.o: %.c ... -fPIC` 写死 | 保留标准 `shared/fPIC` 选项（惯例），行为差异在 notes 与 manifest 中如实记录 |
| 5 | test_package 的 `conan_toolchain.cmake` 内嵌陈旧 `CMAKE_C_COMPILER=/data/service/hnp/bin/clang`，真机上该路径已失效导致 `cmake.configure()` 失败 | 预检工具链路径迁移，主配方已做 PATH 回退但 test_package 直接 `cmake.configure()` 未覆盖 | test_package 复用主配方解析逻辑：PATH 查可用 clang/clang++，先替换 toolchain 文件中的陈旧路径，再以 `-DCMAKE_C_COMPILER/CXX_COMPILER` 覆盖配置；不断言、不跳过测试 |

## 源码修改

- `conanfile.py build()` 内 `replace_in_file`：`libcli.c` 中 `struct cli_def *cli_init()` 改为 `struct cli_def *cli_init(void)`，与 `libcli.h` 已有的 `(void)` 原型一致。真机 clang（`-std=c99 -Werror -Wstrict-prototypes`）把无原型声明视为错误（`libcli.c:596`），旧版 gcc 仅警告故上游未察觉。曾尝试统一 diff 补丁，但 hunk 上下文与 `V1.10.7.tar.gz` 实际行号漂移导致 `apply_conandata_patches` 失败（`expected: return CLI_OK / actual: cli_init() {`），故改用精确字符串替换（无行号依赖）。`LIBS=` / `TESTS=` / `CC/AR` 仍经 make 命令行覆盖。

## 依赖版本

无运行时依赖；构建仅需 C 编译器与归档器（由真机工具链经 Conan conf 提供）。

## 验证结果

```bash
# 待 HMBS 真机预检回填（conan create 全量日志）：
# - 上游测试标记：HMBS_UPSTREAM_TEST_RESULT(status=no_tests, discovered=0, executed=0)
# - 消费者测试：test_libcli 10/10（见 test_package/test_libcli.c CHECK 清单）
```

test_package 覆盖（`test_libcli.c`，10 个 CHECK，全部经真实 libcli API）：
1. `cli_init()` 返回非空
2. 注册父命令 `show` 成功
3. 注册子命令 `show version` 成功
4. `cli_run_command("show version")` 返回 `CLI_OK`
5. 命令回调恰好执行一次
6. 裸命令回调 `argc == 0`
7. `cli_print` 输出经 `cli_print_callback` 回调捕获
8. `cli_unregister_command("show")` 返回 `CLI_OK`（仅匹配顶层名，子树随父节点释放，见 libcli.h 注释）
9. 已注销子树再次运行 `show version` 不再成功（`rc != CLI_OK`）
10. `cli_done()` 返回 `CLI_OK`（资源释放）

## 交付物

| 文件 | 说明 |
|------|------|
| include/libcli.h | 唯一公开头文件 |
| lib/libcli.a（默认）/ lib/libcli.so.1.10.7（shared） | 静态 / 共享库（链接名 `-lcli`） |
| licenses/COPYING | LGPL-2.1 许可证文本 |

## 注意事项

- 链接名是 `-lcli` 而非 `-llibcli`（产物 `libcli.so` 按惯例去 `lib` 前缀）；`package_info()` 已设 `cpp_info.libs=["cli"]`，test_package 经 `find_package(libcli)` / `libcli::libcli` 消费。
- 本库非系统同名库（R26 不适用），默认 static（`shared=False`，与仓库 Makefile 模板缺省一致）。
- 本轮严禁 commit/push；以上验证结论待真机 evidence 轮实测后回填，不得作为已验证引用。
