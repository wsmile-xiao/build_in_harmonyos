#include <stdio.h>
#include <stdlib.h>
#include <objc/runtime.h>
#include <objc/objc-api.h>

/* L1 consumer test: link against libobjc2 and exercise its runtime API.
 * Uses pure C entry points so the test compiles with a plain C toolchain:
 *   - sel_registerName / sel_getName : selector registry
 *   - objc_getClassList               : class enumeration
 *   - objc_getClass                   : class lookup
 *   - class_createInstance/objc_dispose : instance allocation
 */
int main(void) {
    int failures = 0;

    /* 1. Selector registry round-trip */
    SEL sel = sel_registerName("testSelector");
    if (sel == 0) {
        printf("FAIL: sel_registerName returned NULL\n");
        failures++;
    } else if (sel_getName(sel) == NULL) {
        printf("FAIL: sel_getName returned NULL\n");
        failures++;
    } else {
        printf("OK: selector registry (%s)\n", sel_getName(sel));
    }

    /* 2. Class enumeration */
    int count = objc_getClassList(NULL, 0);
    if (count <= 0) {
        printf("FAIL: objc_getClassList returned %d\n", count);
        failures++;
    } else {
        printf("OK: objc_getClassList found %d classes\n", count);
    }

    /* 3. Class lookup (libobjc2 runtime ships the Object class) */
    Class cls = (Class)objc_getClass("Object");
    if (cls == 0) {
        printf("FAIL: objc_getClass(\"Object\") returned NULL\n");
        failures++;
    } else {
        const char *name = class_getName(cls);
        if (name == NULL || name[0] == '\0') {
            printf("FAIL: class_getName returned empty\n");
            failures++;
        } else {
            printf("OK: class lookup %s\n", name);
        }
    }

    /* 4. Instance allocation (requires a usable runtime) */
    Class any = (Class)objc_getClass("Object");
    if (any != 0) {
        id obj = class_createInstance(any, 0);
        if (obj == NULL) {
            printf("FAIL: class_createInstance returned NULL\n");
            failures++;
        } else {
            printf("OK: class_createInstance succeeded\n");
            object_dispose(obj);
        }
    }

    if (failures == 0) {
        printf("libobjc2 2.2.1 runtime API test: ALL PASSED\n");
        return 0;
    }
    printf("libobjc2 2.2.1 runtime API test: %d FAILURE(S)\n", failures);
    return 1;
}
