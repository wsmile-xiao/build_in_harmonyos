/*
 * combined_libintl.c — 合并 libintl.so.8（OHOS GI 运行时基础设施）
 *
 * 背景：g-ir-scanner 是 Python 进程，必须同时加载系统 libpython（需
 * libintl_* 符号，如 libintl_gettext）与共享 libglib-2.0.so.0（需其自带
 * libintl.so.8 仅导出的 g_libintl_* 符号）。两套符号风格在同一进程内互斥，
 * LD_LIBRARY_PATH 只能二选一 → 本 shim 同时导出两套符号，且均包装 musl
 * libc 的 gettext，置于 LD_LIBRARY_PATH 首位即可两全。
 *
 * 无上游源码（自研 shim）。LGPL-2.1-or-later。
 */
#define _GNU_SOURCE
#include <stddef.h>

/* musl libc 提供的裸 gettext 系函数（系统 libintl.h 未声明） */
extern char *gettext(const char *msgid);
extern char *dgettext(const char *domainname, const char *msgid);
extern char *dcgettext(const char *domainname, const char *msgid, int category);
extern char *ngettext(const char *msgid1, const char *msgid2, unsigned long int n);
extern char *dngettext(const char *domainname, const char *msgid1, const char *msgid2, unsigned long int n);
extern char *dcngettext(const char *domainname, const char *msgid1, const char *msgid2, unsigned long int n, int category);
extern char *bindtextdomain(const char *domainname, const char *dirname);
extern char *textdomain(const char *domainname);
extern char *bind_textdomain_codeset(const char *domainname, const char *codeset);

/* ---- libintl_*（系统 python 需要）---- */
char *libintl_gettext(const char *m) { return gettext(m); }
char *libintl_dgettext(const char *d, const char *m) { return dgettext(d, m); }
char *libintl_dcgettext(const char *d, const char *m, int c) { return dcgettext(d, m, c); }
char *libintl_ngettext(const char *a, const char *b, unsigned long n) { return ngettext(a, b, n); }
char *libintl_dngettext(const char *d, const char *a, const char *b, unsigned long n) { return dngettext(d, a, b, n); }
char *libintl_dcngettext(const char *d, const char *a, const char *b, unsigned long n, int c) { return dcngettext(d, a, b, n, c); }
char *libintl_bindtextdomain(const char *d, const char *dir) { return bindtextdomain(d, dir); }
char *libintl_textdomain(const char *d) { return textdomain(d); }
char *libintl_bind_textdomain_codeset(const char *d, const char *cs) { return bind_textdomain_codeset(d, cs); }

/* ---- g_libintl_*（共享 glib 需要）---- */
char *g_libintl_gettext(const char *m) { return gettext(m); }
char *g_libintl_dgettext(const char *d, const char *m) { return dgettext(d, m); }
char *g_libintl_dcgettext(const char *d, const char *m, int c) { return dcgettext(d, m, c); }
char *g_libintl_ngettext(const char *a, const char *b, unsigned long n) { return ngettext(a, b, n); }
char *g_libintl_dngettext(const char *d, const char *a, const char *b, unsigned long n) { return dngettext(d, a, b, n); }
char *g_libintl_dcngettext(const char *d, const char *a, const char *b, unsigned long n, int c) { return dcngettext(d, a, b, n, c); }
char *g_libintl_bindtextdomain(const char *d, const char *dir) { return bindtextdomain(d, dir); }
char *g_libintl_textdomain(const char *d) { return textdomain(d); }
char *g_libintl_bind_textdomain_codeset(const char *d, const char *cs) { return bind_textdomain_codeset(d, cs); }
