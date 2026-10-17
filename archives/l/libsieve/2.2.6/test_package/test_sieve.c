/* Consumer test for libsieve: validate + execute a keep/discard script.
 * Exercises the real public API: sieve2_alloc, sieve2_callbacks,
 * sieve2_validate, sieve2_execute, sieve2_getvalue_*, sieve2_setvalue_*,
 * sieve2_errstr, sieve2_credits, sieve2_license, sieve2_free.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sieve2.h"
#include "sieve2_error.h"

static const char *g_script =
    "if header :contains \"Subject\" \"hello\" {\n"
    "    keep;\n"
    "} else {\n"
    "    discard;\n"
    "}\n";

static const char *g_headers =
    "From: tester@example.com\n"
    "To: me@example.com\n"
    "Subject: hello world\n"
    "\n";

struct ctx {
    int action_taken;
    int error_parse;
    int error_runtime;
    char *sub_user;
    char *sub_local;
};

static int on_getscript(sieve2_context_t *s, void *u)
{
    (void)u;
    sieve2_setvalue_string(s, "script", (char *)g_script);
    return SIEVE2_OK;
}

static int on_getsize(sieve2_context_t *s, void *u)
{
    (void)u;
    sieve2_setvalue_int(s, "size", (int)strlen(g_headers));
    return SIEVE2_OK;
}

static int on_getheaders(sieve2_context_t *s, void *u)
{
    (void)u;
    sieve2_setvalue_string(s, "allheaders", (char *)g_headers);
    return SIEVE2_OK;
}

static int on_envelope(sieve2_context_t *s, void *u)
{
    (void)u;
    sieve2_setvalue_string(s, "to", "me@example.com");
    sieve2_setvalue_string(s, "from", "tester@example.com");
    return SIEVE2_OK;
}

static int on_subaddress(sieve2_context_t *s, void *u)
{
    struct ctx *c = (struct ctx *)u;
    const char *addr = sieve2_getvalue_string(s, "address");
    const char *at;
    if (!addr)
        return SIEVE2_ERROR_BADARGS;
    at = strchr(addr, '@');
    free(c->sub_user);
    free(c->sub_local);
    c->sub_local = strdup(addr);
    c->sub_user = strdup(at ? at + 1 : addr);
    if (!c->sub_user || !c->sub_local)
        return SIEVE2_ERROR_NOMEM;
    sieve2_setvalue_string(s, "user", c->sub_user);
    sieve2_setvalue_string(s, "localpart", c->sub_local);
    sieve2_setvalue_string(s, "domain", at ? (char *)at + 1 : "");
    sieve2_setvalue_string(s, "detail", "");
    return SIEVE2_OK;
}

static int on_keep(sieve2_context_t *s, void *u)
{
    (void)s;
    ((struct ctx *)u)->action_taken = 1;
    printf("action: keep\n");
    return SIEVE2_OK;
}

static int on_discard(sieve2_context_t *s, void *u)
{
    (void)s;
    ((struct ctx *)u)->action_taken = 1;
    printf("action: discard\n");
    return SIEVE2_OK;
}

static int on_redirect(sieve2_context_t *s, void *u)
{
    (void)s;
    ((struct ctx *)u)->action_taken = 1;
    printf("action: redirect\n");
    return SIEVE2_OK;
}

static int on_fileinto(sieve2_context_t *s, void *u)
{
    (void)s;
    ((struct ctx *)u)->action_taken = 1;
    printf("action: fileinto\n");
    return SIEVE2_OK;
}

static int on_errparse(sieve2_context_t *s, void *u)
{
    ((struct ctx *)u)->error_parse = 1;
    printf("parse error at line %d: %s\n",
           sieve2_getvalue_int(s, "lineno"),
           sieve2_getvalue_string(s, "message"));
    return SIEVE2_OK;
}

static int on_errexec(sieve2_context_t *s, void *u)
{
    ((struct ctx *)u)->error_runtime = 1;
    printf("exec error: %s\n", sieve2_getvalue_string(s, "message"));
    return SIEVE2_OK;
}

static int on_erraddr(sieve2_context_t *s, void *u)
{
    (void)u;
    printf("address note: %s\n", sieve2_getvalue_string(s, "message"));
    return SIEVE2_OK;
}

static int on_errheader(sieve2_context_t *s, void *u)
{
    (void)u;
    printf("header note: %s\n", sieve2_getvalue_string(s, "message"));
    return SIEVE2_OK;
}

static int on_debug(sieve2_context_t *s, void *u)
{
    (void)s;
    (void)u;
    return SIEVE2_OK;
}

static int on_getbody(sieve2_context_t *s, void *u)
{
    (void)s;
    (void)u;
    return SIEVE2_ERROR_UNSUPPORTED;
}

static sieve2_callback_t g_callbacks[] = {
    { SIEVE2_DEBUG_TRACE, on_debug },
    { SIEVE2_ERRCALL_PARSE, on_errparse },
    { SIEVE2_ERRCALL_RUNTIME, on_errexec },
    { SIEVE2_ERRCALL_ADDRESS, on_erraddr },
    { SIEVE2_ERRCALL_HEADER, on_errheader },
    { SIEVE2_ACTION_REDIRECT, on_redirect },
    { SIEVE2_ACTION_DISCARD, on_discard },
    { SIEVE2_ACTION_KEEP, on_keep },
    { SIEVE2_ACTION_FILEINTO, on_fileinto },
    { SIEVE2_SCRIPT_GETSCRIPT, on_getscript },
    { SIEVE2_MESSAGE_GETHEADER, NULL },
    { SIEVE2_MESSAGE_GETALLHEADERS, on_getheaders },
    { SIEVE2_MESSAGE_GETSUBADDRESS, on_subaddress },
    { SIEVE2_MESSAGE_GETENVELOPE, on_envelope },
    { SIEVE2_MESSAGE_GETBODY, on_getbody },
    { SIEVE2_MESSAGE_GETSIZE, on_getsize },
    { 0, NULL }
};

int main(void)
{
    sieve2_context_t *s = NULL;
    struct ctx u;
    int res;
    int ok = 1;

    memset(&u, 0, sizeof(u));

    res = sieve2_alloc(&s);
    if (res != SIEVE2_OK || !s) {
        printf("FAIL sieve2_alloc: %s\n", sieve2_errstr(res));
        return 1;
    }
    printf("PASS sieve2_alloc\n");

    res = sieve2_callbacks(s, g_callbacks);
    if (res != SIEVE2_OK) {
        printf("FAIL sieve2_callbacks: %s\n", sieve2_errstr(res));
        ok = 0;
    } else {
        printf("PASS sieve2_callbacks\n");
    }

    res = sieve2_validate(s, &u);
    if (res != SIEVE2_OK || u.error_parse) {
        printf("FAIL sieve2_validate: res=%d(%s) error_parse=%d\n",
               res, sieve2_errstr(res), u.error_parse);
        ok = 0;
    } else {
        printf("PASS sieve2_validate (keep/discard script valid)\n");
    }

    res = sieve2_execute(s, &u);
    if (res != SIEVE2_OK || !u.action_taken || u.error_runtime) {
        printf("FAIL sieve2_execute: res=%d(%s) action=%d err=%d\n",
               res, sieve2_errstr(res), u.action_taken, u.error_runtime);
        ok = 0;
    } else {
        printf("PASS sieve2_execute (Subject matched, action taken)\n");
    }

    if (!sieve2_errstr(SIEVE2_OK) || !sieve2_credits() || !sieve2_license()) {
        printf("FAIL info strings\n");
        ok = 0;
    } else {
        printf("PASS info strings: %s\n", sieve2_errstr(SIEVE2_OK));
    }

    res = sieve2_free(&s);
    if (res != SIEVE2_OK || s) {
        printf("FAIL sieve2_free\n");
        ok = 0;
    } else {
        printf("PASS sieve2_free\n");
    }

    free(u.sub_user);
    free(u.sub_local);
    printf(ok ? "ALL TESTS PASSED\n" : "TESTS FAILED\n");
    return ok ? 0 : 1;
}
