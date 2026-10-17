/* g_libintl_* shim：glib 静态库引用 g_libintl_* 前缀符号，libintl.a
 * 提供 libintl_* → 包装映射。SPDX-License-Identifier: GPL-2.0-only */
extern char *libintl_gettext(const char *msgid);
extern char *libintl_dgettext(const char *domainname, const char *msgid);
extern char *libintl_dcgettext(const char *domainname, const char *msgid,
                               int category);
extern char *libintl_dngettext(const char *domainname, const char *msgid1,
                               const char *msgid2, unsigned long n);
extern char *libintl_textdomain(const char *domainname);
extern char *libintl_bindtextdomain(const char *domainname, const char *dirname);
extern char *libintl_bind_textdomain_codeset(const char *domainname,
                                             const char *codeset);

char *g_libintl_gettext(const char *msgid) { return libintl_gettext(msgid); }
char *g_libintl_dgettext(const char *d, const char *m) {
    return libintl_dgettext(d, m);
}
char *g_libintl_dcgettext(const char *d, const char *m, int c) {
    return libintl_dcgettext(d, m, c);
}
char *g_libintl_dngettext(const char *d, const char *m1, const char *m2,
                          unsigned long n) {
    return libintl_dngettext(d, m1, m2, n);
}
char *g_libintl_textdomain(const char *d) { return libintl_textdomain(d); }
char *g_libintl_bindtextdomain(const char *d, const char *dir) {
    return libintl_bindtextdomain(d, dir);
}
char *g_libintl_bind_textdomain_codeset(const char *d, const char *cs) {
    return libintl_bind_textdomain_codeset(d, cs);
}
