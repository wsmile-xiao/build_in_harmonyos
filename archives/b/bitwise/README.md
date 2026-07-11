# bitwise — OpenHarmony 编译档案

## 软件简介
bitwise 是一个终端位运算计算器，支持多进制转换（十六进制/十进制/八进制/二进制/Radix64）、位运算表达式求值、IPv4 地址转换、ASCII 显示和交互模式。

## OHOS 适配要点
- config.guess/config.sub 需添加 `linux-ohos*` 平台支持
- OHOS /tmp 只读，configure 脚本中 mktemp 需改用 `$TMPDIR`
- OHOS libc (musl) 不提供 `l64a()` 函数，需在 `src/misc.c` 中实现
- `l64a()` 调用需添加 `extern char *l64a(long)` 声明，避免 aarch64 上隐式 int 返回导致指针截断和 segfault
- 系统预构建 ncurses/readline 通过 CFLAGS/LDFLAGS 引用，不进 Conan requires (R26)
- 静态链接 (`-static`)，ELF 64-bit arm64 static (~1.9MB)

## 依赖关系
- 编译依赖: ncurses/6.4 (system prebuilt), readline/8.2 (system prebuilt)
- 无被依赖关系

## 参考资料
- [bitwise GitHub](https://github.com/mellowcandle/bitwise)
- [bitwise Savannah](https://download.savannah.nongnu.org/releases/bitwise/)
