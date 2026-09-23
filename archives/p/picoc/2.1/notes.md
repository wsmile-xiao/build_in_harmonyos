# picoc 2.1 — 适配笔记 (OHOS PC / aarch64)

## 1. 结论
- OHOS aarch64 交叉编译成功；产物 `picoc`（ELF arm64, musl 动态）。
- 上游测试 `make test`：**51/51 通过**。
- conan create + test_package 全绿；conan-verify PASS；W3/W2 通过（见 .ci-result.json）。

## 2. 构建系统
- 纯 Makefile（无 configure/autotools）。顶层 `make` 产出 `picoc`；`make test` 委派 `tests/Makefile`。
- 上游 Makefile 硬编码 `CC=gcc`、`CFLAGS=-DUNIX_HOST`、`LIBS=-lm -lreadline`。命令行覆盖变量即可交叉编译。

## 3. 依赖
- `readline/8.3`（直接，链接期 + 头文件；静态）→ 传递 `ncurses/6.6`。
- 由于 readline 静态库需 termcap 符号，最终链接追加 `-lncursesw`；`-lm` 由 OHOS musl libc 提供（无独立 libm.so）。
- 前置 conan download 验证均成功（recipe + 二进制从 ohpcd 下载），无 R36 阻塞。

## 4. OHOS/musl 适配点（3 个补丁，均为 libc 能力检测/标准函数替换，无 __OHOS__ 平台宏）
1. `cstdlib/stdio.c`：musl 的 `FILE` 是不透明类型，`sizeof(FILE)` 非法。
   → `PICOC_SYSTEM_FILE_SIZE`：glibc 分支保留 `sizeof(FILE)`，其他 libc 用固定上限 512
   （解释器侧 __FILEStruct/__va_listStruct 仅做存储布局，真实 FILE/va_list 全走指针）。
   守卫宏：`__GLIBC__`（libc 能力检测，非平台宏，符合 R8 口径）。
2. `cstdlib/string.c`：`index`/`rindex` 为 BSD 别名，musl 只导出 `index` 不导出 `rindex`。
   → 底层改 `strchr`/`strrchr`（标准函数，全 libc 通用）；解释器可见注册名 `index`/`rindex` 不变。
   无平台宏。
3. `cstdlib/unistd.c`：`gethostid`/`getpass`/`ualarm` 为 glibc 专有遗留 API，
   OHOS musl 头文件与 libc.so 符号均缺失。
   → 函数实现与注册表项用 `#if defined(__GLIBC__)` 守卫剔除。
   守卫宏：`__GLIBC__`。

编译告警均为上游 `-Wall -pedantic` 下旧式 C 风格告警（strict-prototypes 等），非错误。

## 5. 关键命令（复现）
```bash
# 探索构建（含 readline/ncurses 本地缓存包）
make CC=clang CFLAGS="-Wall -pedantic -DUNIX_HOST -O2 -I<readline>/include" \
     LIBS="-L<readline>/lib -L<ncurses>/lib -lreadline -lncursesw -lm" -j1

# 上游测试
make CC=clang CFLAGS="..." LIBS="..." test   # 51/51 通过

# 干净构建
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=picoc/2.1
```

## 6. 产物
- 单可执行文件 `bin/picoc` + `licenses/README`（README 内含上游 New BSD 许可全文）。
- 无 --version/--help；L2 smoke 为 warn 级（非阻塞）。test_package 以真实 C 程序验证解释器功能。

## 7. 日志
- 探索构建: 见本地 logs（build-exploratory-*.log）
- 上游测试: upstream-make-test.log（51 项）
- conan create 最终: reports/conan-create.log（conan-verify 拷贝）
- 测试报告: reports/test-report.md
## 知识积累
- ✅ picoc 2.1 为纯 Makefile 项目（无 configure），产物为单个 picoc 可执行文件
- ✅ UNIX_HOST 默认启用 USE_READLINE 链接 GNU readline；readline 静态包需在最终链接追加 -lncursesw 提供 termcap 符号
- ✅ musl 的 FILE 为不透明类型，sizeof(FILE) 非法；用 PICOC_SYSTEM_FILE_SIZE（glibc 分支保留 sizeof(FILE)，其他 libc 用固定上限 512）
- ✅ gethostid/getpass/ualarm 为 glibc 专有遗留 API，OHOS musl 头文件与符号均缺失，需用 __GLIBC__ 守卫剔除注册与实现
- ✅ index/rindex BSD 别名在 musl 缺失（仅导出 index），底层改用 strchr/strrchr，解释器注册名不变
- ✅ 上游测试入口 make test 为 .c 运行输出与 .expect diff 的差分回归套件，51 项在 OHOS 全部通过
## 8. 2026-09-06 全量复验（本会话，独立重跑源码→构建→51 用例→create→verify→W3）
复验全部通过（conan create exit 0；make test 51/51；逐用例日志
`/storage/Users/currentUser/tmp/builds/picoc-2.1-v2/testlogs/`；统计见 reports/test-report.md）。
新增三条关键坑（test_package 6 连 fix 提交螺旋的根因）：
- ❌ **picoc 无 stdin 模式**：usage 只有 `picoc <file.c>... [- <args>]`、`-s` 脚本模式、`-i` 交互模式。
  `echo 'int main(){...}' | picoc -` 中 `-` 仅为参数分隔符，文件列表为空 → PicocCallMain 报
  "main() is not defined" 退出 1 → conan create test 阶段必炸。正确写法：commit 真实 `smoke.c`
  （`#include <stdio.h>` + main + printf），`test()` 执行 `picoc smoke.c | grep -q "picoc-test-ok 42"`。
- ⚠️ 上游 Makefile `.PHONY: clibrary.c` → clibrary.o 在**每次** make 调用（含 `make test`）强制重编；
  CFLAGS/LIBS 必须完整传入所有 make 调用，漏传（空 CFLAGS 即缺 `-DUNIX_HOST`）会以
  implicit-declaration 错误炸在 clibrary.o，与主二进制是否已构建无关。
- ⚠️ OHPCD conan 2.29.1 fork 的 `ConanFile.run()` 无 `output=`/`capture_output=` 关键字
  （签名仅 command/stdout/cwd/ignore_errors/env/quiet/shell/scope/stderr）；需断言输出时用
  shell 管道 `grep -q`（管道退出码=最后命令）或重定向文件+`conan.tools.files.load`。
- 另：探索期 `CC=$(conan profile show | grep ...)` 若命中 host+build 双 profile，变量含换行会把
  make recipe 首行变成裸 clang（"no input files"）。CC 必须单行。
---

**编译结束**: 2026-09-06 16:31
**最终状态**: built
