/* libratbag OHOS/musl shim — glibc 扩展 program_invocation_short_name 在 musl 下
 * 不可用：它由 glibc 的 <errno.h> 在 _GNU_SOURCE 下声明为 `char *` 变量，musl
 * 既不声明也不定义。musl 的动态加载器提供了语义完全相同的 __progname
 * （同样是 argv[0] 的 basename），因此这里把它别名为 __progname，而不是像
 * 旧补丁 0002 那样 #define 成各工具名的字符串字面量。
 *
 * 该头由 conanfile.py 的 generate() 以 `-include` 强制注入（见
 * _progname_shim_args()），**不再改动上游 tools/*.c 与 ratbagd/ratbagd.c**：
 * .gitcode/review-memory.md R8 要求 patches/ 补丁文件默认不得引入平台条件
 * 编译宏，此类 libc 差异应在配方层用 feature detection 解决。
 */
#ifndef LIBRATBAG_PROGNAME_SHIM_H
#define LIBRATBAG_PROGNAME_SHIM_H

#ifndef __GLIBC__
extern char *__progname;
#define program_invocation_short_name __progname
#endif

#endif /* LIBRATBAG_PROGNAME_SHIM_H */
