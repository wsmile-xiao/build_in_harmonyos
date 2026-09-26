# minmea 0.3.0 适配笔记

## 编译环境
- 构建系统: makefile（上游为裸 Makefile，无 configure/cmake）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）+ llvm-ar / lld
- 目标平台: HarmonyOS PC arm64（os=OHOS, os.version=6.0, arch=armv8, compiler.libcxx=libc++）
- 状态: built

## 编译步骤

配方 `build()`（全部命令行显式传参，不依赖 shell 环境变量，R33）：

1. `make CC=<clang> AR=<llvm-ar> minmea.o` —— 编译库对象（上游 Makefile 内置规则）。
2. `llvm-ar rcs libminmea.a minmea.o` —— 上游 Makefile 不产出归档，配方自行打包静态库
   （`shared=True` 时改为 `clang -shared -fPIC -o libminmea.so`）。
3. `make CC=<clang> CFLAGS="…-Wno-error=format-security …" LDLIBS="<check>/lib/libcheck.a -lm -lrt -pthread" tests`
   —— 按上游 `test` 入口构建 Check 测试程序，随后执行 `./tests`。
4. `make … example` —— 构建上游示例程序（`all` 目标的另一产物）。
5. `package()` 拷贝 `minmea.h` → `include/`、`libminmea.a` → `lib/`、`COPYING` → `licenses/`
   （上游 Makefile 无 install 目标）。

`scan-build` 目标不执行：设备与 CI worker 均不提供 `scan-build` 包装器（上游 `all`
目标的三个子目标中，`test` 与 `example` 都已构建执行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make: cc: No such file or directory` | 设备无 `cc` 别名（§一.16 同族） | 配方从 `self.conf.get("tools.build:compiler_executables")` 取 `clang`，以 `CC=` 显式传给 make |
| 2 | `tests.c:58: error: format string is not a string literal [-Werror,-Wformat-security]` | 上游 Makefile 写死 `-Werror`；clang 15 对 Check 宏 `ck_assert_msg(expr, 非字面量格式)` 报该诊断，旧编译器放行 | `CFLAGS` 追加 `-Wno-error=format-security` 降级该单条诊断，其余上游告警设置原样保留；**不改上游源文件、不产生补丁** |
| 3 | 设备无 `check.h` / `libcheck` | 上游 `tests.c` 依赖 Check 框架，系统未安装 | `build_requirements()` 声明 `self.test_requires("check/0.15.2")`（ohpcd 已发布 armv8/OHOS 二进制，`conan install --requires=check/0.15.2 --build=never` 实测直接命中缓存/制品仓） |
| 4 | 运行 `./tests` 报 `check_msg.c:317: Unable to create temporary file for communication` | Check 0.15.2 取临时目录的优先级是 `TEMP` → `P_tmpdir`（bionic 为 `/tmp`）→ `TMPDIR`，因此 `TMPDIR` 形同虚设，落到 OHOS 只读 `/tmp` | `build()` 里把 `TEMP`/`TMP`/`TMPDIR` 一起 define 到 `<build_folder>/tmp` 再运行测试 |
| 5 | 链接 `./tests` 报 `unable to find library -lcheck`，运行时报 `Error loading shared library libcheck.so` | 默认 `LDLIBS=-lcheck` 命中共享库，运行期无 `LD_LIBRARY_PATH` | `LDLIBS` 直接给 Check 的静态归档绝对路径 `<check>/lib/libcheck.a -lm -lrt -pthread`，测试程序自包含 |
| 6 | 上游 Makefile 无 `install` 目标 | 上游面向嵌入式源码集成 | `package()` 显式拷贝头文件、静态库与许可证 |

## 源码修改

无。本次适配 **0 个补丁**（`patches_applied: []`）：全部适配都在配方侧完成，
上游 `minmea.c` / `minmea.h` / `tests.c` / `Makefile` 逐字节保持上游 v0.3.0 原貌。

## 依赖版本

- 运行/链接依赖：无（核心库 0 依赖，只用 ISO C99 头文件）。
- 测试依赖：`check/0.15.2`（ohpcd 制品仓，package id `21b17f8b2bc0e9511e276e3d57a23893067cefe5`，
  settings: os=OHOS / arch=armv8 / clang 15 / libc++ / Release）。
- 构建工具：GNU Make 4.4.1、clang 15.0.4、llvm-ar（均来自设备工具链，配方未声明 tool_requires）。

## 测试计数口径

- **上游用例数 N = 23**，口径 = Check 框架注册的测试用例：`tests.c` 中 `tcase_add_test`
  共 23 处（5 个 tcase），与 `srunner` 实际输出 `Checks: 23` 完全一致。
- 同一文件内另有 234 处 `ck_assert*` **断言**，属另一统计口径，不与用例数混用。
- 鸿蒙特有测试 = `test_package/test.c` 消费者断言 **14** 项（不进上游分母）。

## 验证结果

```bash
# 上游测试（配方 build() 内执行，等价命令）
make … tests && ./tests
# → Running suite(s): minmea
#   100%: Checks: 23, Failures: 0, Errors: 0        (23/23)

# 消费者测试（conan create 的 test_package 环节）
./test_minmea
# → minmea test_package: 14/14 checks passed         (14/14)

# 配方自包含验证
conan create <包目录> -pr:h=…/ci/conan/profiles/ohos-aarch64 -pr:b=同上 \
      --build=missing --user=ohpcd --channel=stable
# → rc=0，Package id 构建成功，test_package 通过
```

采信轮（清缓存四步 → conan-verify G0-G4/L2/L4/L5 → 证据副本）的完整日志与报告留档在
`reports/`（`conan-create.log`、`conan-verify-report.md`、`w3-local-ci.log` 等，工作区
ignored 证据，不进提交面）。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/minmea.h` | 公开头文件（上游原样） |
| `lib/libminmea.a` | 静态库（`shared=True` 时为 `lib/libminmea.so`） |
| `licenses/COPYING` | WTFPL v2 许可证文本 |
