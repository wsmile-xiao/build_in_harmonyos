# csvprintf 1.3.4 适配笔记

## 编译环境
- 构建系统: manual（CMake不在，autotools不完整）
- 编译日期: 2026-09-10
- 编译器: aarch64-unknown-linux-ohos-clang（/data/service/hnp/bin）
- 状态: built

## 适配背景

csvprintf 1.3.4 是 Archie Cobbs 编写的命令行 CSV 转换工具，支持 CSV→XML、CSV→JSON、CSV→bash变量三种输出模式。上游使用 GNU Autotools，但发布包（GitHub release tarball）不含预生成的 `configure` 脚本，需要本地 `autoreconf`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 `automake`/`aclocal`/`libtoolize` | OHOS HNP 只提供 `autoconf` 2.72，未装 `automake`；`autoreconf -fi` 失败于 `aclocal` | 跳过 autoreconf，手工生成 `config.h` + `gitrev.c`，用 clang 直接编译 |
| 2 | `err.h` 头文件不存在于 sysroot | OHOS bionic 不暴露 `err.h`（libbsd 扩展） | `err.h` 在 `/data/service/hnp/ohos-sdk.org/.../usr/include/err.h`，clang triplet 自动能找到 |
| 3 | `PRINTF_PROGRAM` 指向 toybox `printf` | 上游 configure.ac 检测 `which printf` 返回 toybox（`/usr/bin/printf → ../../bin/toybox`），toybox 不支持 `%[N]s` 位置参数 | 配方中用 Python 探测 GNU coreutils `printf`（`~/usr/local/bin/printf`），将其路径写入 `PRINTF_PROGRAM` 宏；若找不到则降级到 `/usr/bin/printf` 并警告 |
| 4 | bash `getcwd` 异常污染测试输出 | OHOS bash 5.3 在跨 SSH 会话时 cwd 判定失败，`run2.sh` 每次调用都打印大量 `job-working-directory` 噪声 | 用 Python 脚本重写测试逻辑（直接读 `.tst` 文件并 exec），绕过 bash 环境问题；run.sh 也改为 Python 驱动 |
| 5 | run.sh 的 xml2csv round-trip 测试依赖 xsltproc | xsltproc 在 `/data/service/hnp/bin/xsltproc` 可用，但 ISO-8859-1 编码转换在 toybox iconv 下不稳定 | 配方 build() 中 run.sh 全部变体均通过 Python subprocess 执行，不依赖 shell 环境 |

## 构建步骤

```bash
# 手工创建 config.h（含 PRINTF_PROGRAM 和 PACKAGE_* 宏）
cat > config.h << 'EOF'
#define _DEFAULT_SOURCE 1
#define _GNU_SOURCE 1
#define _BSD_SOURCE 1
#define _XOPEN_SOURCE 500
#define PRINTF_PROGRAM "/storage/Users/currentUser/usr/local/bin/printf"
#define PACKAGE_TARNAME "csvprintf"
#define PACKAGE_VERSION "1.3.4"
EOF

# 手工创建 gitrev.c
echo 'const char *const csvprintf_version = "1.3.4";' > gitrev.c

# 编译链接
aarch64-unknown-linux-ohos-clang -g -O3 \
  -D_DEFAULT_SOURCE=1 -D_GNU_SOURCE=1 -D_BSD_SOURCE=1 -D_XOPEN_SOURCE=500 \
  -DPRINTF_PROGRAM=\"/storage/Users/currentUser/usr/local/bin/printf\" \
  -c main.c -o main.o
aarch64-unknown-linux-ohos-clang main.o gitrev.c -o csvprintf
```

## 上游测试套件

| 套件 | 来源 | 用例数 | 说明 |
|------|------|--------|------|
| `tests/run.sh` | 9 × `.in` 文件 × 8 flag 变体 | 72 | XML/plain、XML/names、ISO-8859-1→XML、JSON、bash 赋值等输出模式 |
| `tests/run2.sh` | 11 × `.tst` 文件 | 11 | 高级用法：bash 变量命名、列名选择、重复列、JSON skip、tab分隔等 |
| **合计** | | **83** | |

测试通过标准：`run.sh` 对每个 `.in` 文件调用 csvprintf 后与预期 `.out?` 文件逐字节比对（`diff`）；`run2.sh` 解析 `.tst` 变量后比较 stdout/stderr/exitcode。

## 真机验证结果

在 HarmonyOS PC 真机 (`ohos@c1.sermc.net`，aarch64) 实测：
- 编译：`aarch64-unknown-linux-ohos-clang` 直接编译成功，无 patch
- 上游测试：83/83 通过（run.sh 72 + run2.sh 11）
- test_package：5 个 smoke test 全部通过

```
tests/run.sh: *** all tests passed (72/72)
tests/run2.sh: 11/11 tests passed (no failures)
test_package: --help OK, --version OK, XML OK, JSON OK, BASH OK
```

## 依赖

无外部依赖（纯 libc 工具，仅用 iconv 做编码转换，由 OHOS bionic 提供）。

## 验证命令（真机）

```bash
# 编译
ssh ohos@c1.sermc.net 'cd ... && \
  aarch64-unknown-linux-ohos-clang -g -O3 \
    -D_DEFAULT_SOURCE=1 -D_GNU_SOURCE=1 -D_BSD_SOURCE=1 -D_XOPEN_SOURCE=500 \
    -DPRINTF_PROGRAM="/storage/Users/currentUser/usr/local/bin/printf" \
    -I. -c main.c && \
  aarch64-unknown-linux-ohos-clang main.o gitrev.c -o csvprintf'

# 运行上游测试（Python wrapper）
ssh ohos@c1.sermc.net 'cd .../tests && python3 run_tests.py'

# test_package
conan test test_package/ csvprintf/1.3.4@ --build=missing
```
