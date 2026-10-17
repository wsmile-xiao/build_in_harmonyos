/* Consumer test for libfixbuf 2.4.1 (R34: real API calls, no network).
 *
 * Exercises the core object lifecycle off the wire:
 *   1. fbInfoModelAlloc() returns a model
 *   2. fbSessionAlloc(model) returns a session
 *   3. fbTemplateAlloc(model) returns a template
 *   4. template starts empty + session still points at the model
 *   5. cleanup (free unused template/session/model) completes
 * Prints one PASS line per assertion plus a machine-readable summary
 * "FIXBUF_TEST assertions=N failures=M" parsed by conanfile.py.
 */
#include <stdio.h>
#include <fixbuf/public.h>

int main(void)
{
    int assertions = 0;
    int failures = 0;

#define CHECK(cond, label) do { \
        assertions++; \
        if (cond) { printf("PASS: %s\n", label); } \
        else { printf("FAIL: %s\n", label); failures++; } \
    } while (0)

    fbInfoModel_t *model = fbInfoModelAlloc();
    CHECK(model != NULL, "fbInfoModelAlloc returns model");

    fbSession_t *session = NULL;
    if (model != NULL) {
        session = fbSessionAlloc(model);
    }
    CHECK(session != NULL, "fbSessionAlloc returns session");

    fbTemplate_t *tmpl = NULL;
    if (model != NULL) {
        tmpl = fbTemplateAlloc(model);
    }
    CHECK(tmpl != NULL, "fbTemplateAlloc returns template");

    if (tmpl != NULL && session != NULL) {
        int empty_ok = (fbTemplateCountElements(tmpl) == 0);
        int model_ok = (fbSessionGetInfoModel(session) == model);
        CHECK(empty_ok && model_ok, "new template empty and session keeps model");
    } else {
        CHECK(0, "new template empty and session keeps model");
    }

    /* Cleanup must run without crashing; reaching here is the assertion. */
    if (tmpl != NULL) {
        fbTemplateFreeUnused(tmpl);
    }
    if (session != NULL) {
        fbSessionFree(session);
    }
    if (model != NULL) {
        fbInfoModelFree(model);
    }
    CHECK(1, "cleanup completed");

    printf("FIXBUF_TEST assertions=%d failures=%d\n", assertions, failures);
    return failures == 0 ? 0 : 1;
}
