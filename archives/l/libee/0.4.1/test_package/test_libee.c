/* test_libee.c — libee API consumer test (R34: must call real API).
 *
 * Exercises the core event lifecycle against the packaged library:
 * version query, context init, event creation, string-field append,
 * RFC5424 formatting and JSON decoding (the headline feature of 0.4.1).
 * Each check prints one "CHECK-OK: <name>" line and aborts with a
 * diagnostic on failure, so a zero exit status proves all 6 checks.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libestr.h"
#include "libee/libee.h"

static int failures = 0;

#define CHECK(cond, name) do { \
    if (!(cond)) { \
        fprintf(stderr, "CHECK-FAIL: %s (line %d)\n", name, __LINE__); \
        failures++; \
    } else { \
        printf("CHECK-OK: %s\n", name); \
    } \
} while (0)

int main(void) {
    /* 1. Library version must be queryable and match this release. */
    char *ver = ee_version();
    CHECK(ver != NULL && strcmp(ver, "0.4.1") == 0, "version-query");

    /* 2. A library context must be creatable. */
    ee_ctx ctx = ee_initCtx();
    CHECK(ctx != NULL, "ctx-init");

    /* 3. An event must be creatable inside the context. */
    struct ee_event *event = ee_newEvent(ctx);
    CHECK(event != NULL, "event-new");

    /* 4. A string field must be appendable to the event. */
    es_str_t *val = es_newStrFromCStr("hello hmbs", 10);
    int rc = ee_addStrFieldToEvent(event, "msg", val);
    CHECK(rc == 0, "field-append");

    /* 5. The event must format to a non-empty RFC5424 string.
     * NOTE: upstream ee_fmtEventToRFC5424() in src/syslog_enc.c starts
     * with `r = -1` and only updates it via CHKR on the tagged path, so
     * a tagless event always returns -1 even though *out is correctly
     * populated (upstream tests/ezapi1.c ignores the return value and
     * prints the string unconditionally). Assert on the real output
     * content — including the field payload — instead of the buggy code.
     */
    es_str_t *out = NULL;
    ee_fmtEventToRFC5424(event, &out);
    char *cstr = (out != NULL) ? es_str2cstr(out, NULL) : NULL;
    CHECK(cstr != NULL && strlen(cstr) > 0
          && strstr(cstr, "msg=") != NULL
          && strstr(cstr, "hello hmbs") != NULL, "rfc5424-format");
    if (cstr != NULL)
        printf("Formatted event: '%s'\n", cstr);
    if (out != NULL)
        es_deleteStr(out);
    free(cstr);

    /* 6. An event must be decodable from a JSON string (0.4.1 feature). */
    struct ee_event *jev = ee_newEventFromJSON(ctx, "{\"msg\":\"hi\"}");
    CHECK(jev != NULL, "json-decode");
    if (jev != NULL)
        ee_deleteEvent(jev);

    ee_deleteEvent(event);
    ee_exitCtx(ctx);

    if (failures != 0) {
        fprintf(stderr, "test_libee: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("test libee 0.4.1: OK\n");
    return 0;
}
