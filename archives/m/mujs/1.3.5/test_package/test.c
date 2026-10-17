/*
 * test_package for mujs 1.3.5 — real public API usage (R34).
 * Uses mujs.h public API: create a state, run a JS snippet, read result
 * via globals (mujs js_dostring does not leave expression values on stack).
 */
#include <stdio.h>
#include <string.h>
#include <mujs.h>

int main(void) {
    js_State *J = js_newstate(NULL, NULL, JS_STRICT);
    if (!J) {
        fprintf(stderr, "FAIL: js_newstate returned NULL\n");
        return 1;
    }

    /* public API: run a JS program computing a value into a global */
    int rc = js_dostring(J, "var x = 1 + 2 * 3; var s = 'MuJS'.toLowerCase();");
    if (rc != 0) {
        fprintf(stderr, "FAIL: js_dostring returned %d\n", rc);
        js_freestate(J);
        return 1;
    }

    js_getglobal(J, "x");
    if (!js_isnumber(J, -1)) {
        fprintf(stderr, "FAIL: global x is not a number\n");
        js_freestate(J);
        return 1;
    }
    double v = js_tonumber(J, -1);
    printf("mujs eval x -> %g\n", v);
    js_pop(J, 1);
    if (v != 7.0) {
        fprintf(stderr, "FAIL: expected 7, got %g\n", v);
        js_freestate(J);
        return 1;
    }

    js_getglobal(J, "s");
    if (!js_isstring(J, -1)) {
        fprintf(stderr, "FAIL: global s is not a string\n");
        js_freestate(J);
        return 1;
    }
    const char *s = js_tostring(J, -1);
    printf("mujs string op -> '%s'\n", s);
    js_pop(J, 1);
    if (strcmp(s, "mujs") != 0) {
        fprintf(stderr, "FAIL: expected 'mujs', got '%s'\n", s);
        js_freestate(J);
        return 1;
    }

    js_freestate(J);
    printf("mujs test_package: PASS\n");
    return 0;
}
