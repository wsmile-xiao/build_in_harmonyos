/*
 * compat_defs.h —— rs 20200313 在 HarmonyOS PC(OHOS / musl + clang 15) 上的编译期
 * 兼容开关。由 conanfile.py 用 -include 注入每个编译单元，**不含任何功能代码**，
 * 只做两件事：打开上游自己预留的移植开关、补一个平台缺的声明。
 *
 * 1) 上游 rs.h 自带的两个移植开关（因此上游源码一个字节都不改）
 *    - NEED_STRTONUM：rs.h 把 strtonum(3) 的原型
 *        extern long long strtonum(const char *, long long, long long, const char **);
 *      包在 #ifdef NEED_STRTONUM 里（rs.h:85 的注释就写着 .linked/strtonum.c）。
 *      不开的话 rs.c 六处调用（395/405/417/424/463/470 行）走隐式声明、返回值被
 *      当成 int，clang 直接报 "call to undeclared function 'strtonum'"。
 *    - MBSDPORT_H：上游 .linked/strtonum.c 里的可选兼容头钩子
 *        #ifdef MBSDPORT_H
 *        #include MBSDPORT_H
 *        #endif
 *      指回 rs.h 即可：rs.h 里带着 MirBSD <sys/cdefs.h> 的后备定义（__IDSTRING /
 *      __RCSID / __COPYRIGHT / __SCCSID / __BEGIN_DECLS / __dead）。OHOS musl 的
 *      sys/cdefs.h **不定义 __RCSID**（实测裸编上游 strtonum.c 卡在第 29 行
 *      "__RCSID(\"$MirOS: …\");" 报 expected parameter declarator），所以必须经
 *      这个钩子把后备定义送到 strtonum.c 眼前。
 *    取值要写成带引号的头名（#include 需要 string-literal 或 <…>），这正是上游
 *    把它做成宏而不是写死文件名的原因。放进本头而不是命令行 -D，是为了避开
 *    shell 里的嵌套引号（-DMBSDPORT_H='"rs.h"' 过一层 shell 就会被吃掉引号）。
 *
 *    这两个开关是上游作者本人在 Debian 打包里用的同一对：
 *      OUR_CPPFLAGS += -DNEED_STRTONUM
 *      OUR_CPPFLAGS += -I. -DMBSDPORT_H=\"rs.h\"
 *
 * 2) 补 reallocarray(3) 的**声明**
 *    rs.c:345 调用 reallocarray()，而 OHOS sysroot 头里没有它的任何声明
 *    （rs.c 自己已经 #define _GNU_SOURCE，仍没有），于是返回值被当 int，赋值给
 *    指针触发 -Wint-conversion 硬错误。对应的**定义**见 compat_reallocarray.c。
 */

#ifndef RS_COMPAT_DEFS_H
#define RS_COMPAT_DEFS_H

#include <stddef.h>

/* 上游 rs.h 预留的移植开关 */
#ifndef NEED_STRTONUM
#define NEED_STRTONUM		1
#endif
#ifndef MBSDPORT_H
#define MBSDPORT_H		"rs.h"
#endif

/* OpenBSD reallocarray(3)：OHOS sysroot 未声明；定义见 compat_reallocarray.c */
#ifndef RS_HAVE_REALLOCARRAY_DECL
#define RS_HAVE_REALLOCARRAY_DECL	1
extern void *reallocarray(void *, size_t, size_t);
#endif

#endif	/* RS_COMPAT_DEFS_H */
