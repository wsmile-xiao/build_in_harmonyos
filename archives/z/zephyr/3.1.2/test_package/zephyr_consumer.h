/* Shared assertion body of the zephyr/3.1.2 consumer test.
 *
 * The same checks are driven through two different symbol-acquisition paths so
 * that neither the "can this package be linked and used?" question nor the
 * "does the packaged shared object actually work at run time?" question is
 * left unanswered:
 *
 *   test_link.c    links against zephyr::zephyr; the public symbols come from
 *                  the dynamic linker (DT_NEEDED on the packaged SONAME).
 *   test_dlopen.c  links nothing from the package and obtains the very same
 *                  entry points with dlsym() from a dlopen()ed absolute path.
 *
 * Why two: on HarmonyOS the loader resolves DT_NEEDED only from the namespace
 * paths listed in /etc/ld-musl-namespace-aarch64.ini; DT_RUNPATH, $ORIGIN,
 * LD_LIBRARY_PATH and LD_PRELOAD are all ignored (knowledge/doc/E088, measured
 * on this host - see notes.md).  A stand-alone consumer binary therefore cannot
 * be started here, while dlopen() with an absolute path works.  Keeping both
 * targets means the link-time contract is still verified (a missing
 * <com_err.h>, a broken -lzephyr or a wrong SONAME fails the build/"link"
 * gate), and the run-time behaviour is verified by the path that this platform
 * does allow.
 *
 * The checks only use the public API: no Zephyr server, HostManager (zhm) or
 * network peer is required.
 */
#ifndef ZEPHYR_CONSUMER_H
#define ZEPHYR_CONSUMER_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <zephyr/zephyr.h>

/* Public entry points exercised by both targets.  Signatures copied verbatim
 * from h/zephyr/zephyr.h (ZGetRealm() and ZGetSender() differ in constness). */
struct zephyr_api {
    Code_t      (*initialize)(void);
    const char *(*get_realm)(void);
    char       *(*get_sender)(void);
    int         (*get_fd)(void);
    int         (*compare_uid)(ZUnique_Id_t *, ZUnique_Id_t *);
    Code_t      (*format_notice)(ZNotice_t *, char **, int *, Z_AuthProc);
    Code_t      (*parse_notice)(char *, int, ZNotice_t *);
    Code_t      (*free_notice)(ZNotice_t *);
};

static int zephyr_consumer_failures;

#define ZCHECK(cond, msg)                        \
    do {                                         \
        if (cond) {                              \
            printf("ok   - %s\n", (msg));        \
        } else {                                 \
            printf("FAIL - %s\n", (msg));        \
            zephyr_consumer_failures++;          \
        }                                        \
    } while (0)

/* Runs every assertion against the supplied symbol table and returns 0 when all
 * of them passed.  ``label`` identifies the acquisition path in the output. */
static int zephyr_run_consumer_checks(const struct zephyr_api *api,
                                      const char *label)
{
    ZNotice_t notice, parsed;
    ZUnique_Id_t uid1, uid2;
    char *buf = NULL;
    int buflen = 0;
    int checks = 0;
    int code;

    memset(&notice, 0, sizeof(notice));
    memset(&parsed, 0, sizeof(parsed));
    memset(&uid1, 0, sizeof(uid1));
    memset(&uid2, 0, sizeof(uid2));
    zephyr_consumer_failures = 0;

    printf("== zephyr consumer test (%s) ==\n", label);

    /* ZInitialize() returns early when no Zephyr HostManager is running, so its
     * status is reported but never asserted. */
    code = api->initialize();
    printf("ZInitialize() -> %d\n", code);

    ZCHECK(api->get_realm() != NULL, "ZGetRealm() returns a realm pointer");
    ZCHECK(api->get_sender() != NULL && api->get_sender()[0] != '\0',
           "ZGetSender() returns a non-empty sender");
    ZCHECK(api->get_fd() >= -1, "ZGetFD() is callable from a consumer");
    ZCHECK(api->compare_uid(&uid1, &uid2) != 0, "two zero UIDs compare equal");

    code = api->format_notice(&notice, &buf, &buflen, ZNOAUTH);
    ZCHECK(code == 0, "ZFormatNotice() succeeds");
    ZCHECK(buf != NULL && buflen > 0, "ZFormatNotice() produced a buffer");
    if (buf != NULL) {
        ZCHECK(strncmp(buf, "ZEPH", 4) == 0, "notice header starts with ZEPH");
        code = api->parse_notice(buf, buflen, &parsed);
        ZCHECK(code == 0, "ZParseNotice() succeeds");
        if (code == 0 && parsed.z_version != NULL) {
            ZCHECK(strncmp(parsed.z_version, "ZEPH", 4) == 0,
                   "parsed notice version starts with ZEPH");
        }
    }
    /* ZFormatNotice() malloc()s the packet into `buf`; ZParseNotice() then
     * points parsed.z_packet at that same buffer, so this single release frees
     * it exactly once - adding free(buf) here would be a double free. */
    api->free_notice(&parsed);

    checks = 9; /* the ZCHECK() statements above; failures counted separately */
    printf("%s: %d assertion(s), %d failure(s)\n",
           label, checks, zephyr_consumer_failures);
    return zephyr_consumer_failures == 0 ? 0 : 1;
}

#endif /* ZEPHYR_CONSUMER_H */
