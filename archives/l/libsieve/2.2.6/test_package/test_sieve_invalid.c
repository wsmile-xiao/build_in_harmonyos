/* Negative consumer test: a broken script must be rejected.
 * Passes (exit 0) only when libsieve reports the parse problem.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sieve2.h"
#include "sieve2_error.h"

/* Unclosed if-block: must not validate. */
static const char *g_bad_script = "if header :contains \"From\" {\n";

static int g_error_parse;

static int on_getscript(sieve2_context_t *s, void *u)
{
    (void)u;
    sieve2_setvalue_string(s, "script", (char *)g_bad_script);
    return SIEVE2_OK;
}

static int on_errparse(sieve2_context_t *s, void *u)
{
    (void)s;
    (void)u;
    g_error_parse = 1;
    return SIEVE2_OK;
}

static int on_errexec(sieve2_context_t *s, void *u)
{
    (void)s;
    (void)u;
    return SIEVE2_OK;
}

static sieve2_callback_t g_callbacks[] = {
    { SIEVE2_ERRCALL_PARSE, on_errparse },
    { SIEVE2_ERRCALL_RUNTIME, on_errexec },
    { SIEVE2_SCRIPT_GETSCRIPT, on_getscript },
    { 0, NULL }
};

int main(void)
{
    sieve2_context_t *s = NULL;
    int dummy = 0;
    int res;

    res = sieve2_alloc(&s);
    if (res != SIEVE2_OK || !s) {
        printf("FAIL sieve2_alloc: %s\n", sieve2_errstr(res));
        return 1;
    }
    res = sieve2_callbacks(s, g_callbacks);
    if (res != SIEVE2_OK) {
        printf("FAIL sieve2_callbacks: %s\n", sieve2_errstr(res));
        return 1;
    }
    res = sieve2_validate(s, &dummy);
    sieve2_free(&s);
    if (res != SIEVE2_OK || g_error_parse) {
        printf("PASS invalid script rejected (res=%d %s)\n",
               res, sieve2_errstr(res));
        return 0;
    }
    printf("FAIL invalid script was accepted\n");
    return 1;
}
