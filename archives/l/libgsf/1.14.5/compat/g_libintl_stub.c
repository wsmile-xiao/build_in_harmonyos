/* compat/g_libintl_stub.c — glibintl g_libintl_* 符号 stub for HarmonyOS
 *
 * libgsf 通过 glibintl.h 的宏映射把 gettext/bindtextdomain 等编译为
 * g_libintl_* 符号，但制品仓 glib 包 --disable-nls 构建未提供这些符号
 * （libgsf 亦 --disable-nls，调用无实际作用）——提供空实现满足链接。
 */
#include <stddef.h>

char *g_libintl_gettext(const char *msgid)
{
    (void)msgid;
    return (char *)msgid;
}

char *g_libintl_dgettext(const char *domainname, const char *msgid)
{
    (void)domainname;
    (void)msgid;
    return (char *)msgid;
}

char *g_libintl_dcgettext(const char *domainname, const char *msgid, int category)
{
    (void)domainname;
    (void)msgid;
    (void)category;
    return (char *)msgid;
}

char *g_libintl_ngettext(const char *msgid, const char *msgid_plural, unsigned long n)
{
    (void)msgid_plural;
    (void)n;
    return (char *)msgid;
}

char *g_libintl_dngettext(const char *domainname, const char *msgid,
                          const char *msgid_plural, unsigned long n)
{
    (void)domainname;
    (void)msgid_plural;
    (void)n;
    return (char *)msgid;
}

char *g_libintl_dcngettext(const char *domainname, const char *msgid,
                           const char *msgid_plural, unsigned long n, int category)
{
    (void)domainname;
    (void)msgid_plural;
    (void)n;
    (void)category;
    return (char *)msgid;
}

char *g_libintl_textdomain(const char *domainname)
{
    (void)domainname;
    return NULL;
}

char *g_libintl_bindtextdomain(const char *domainname, const char *dirname)
{
    (void)domainname;
    (void)dirname;
    return NULL;
}

char *g_libintl_bind_textdomain_codeset(const char *domainname,
                                        const char *codeset)
{
    (void)domainname;
    (void)codeset;
    return NULL;
}
