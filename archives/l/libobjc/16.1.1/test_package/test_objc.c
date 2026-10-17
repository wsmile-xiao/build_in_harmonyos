#include <stdio.h>
#include <string.h>
#include <objc/objc.h>
#include <objc/runtime.h>

/* L1 consumer test: link against the GNU Objective-C runtime (GCC libobjc)
 * and exercise its "modern" public runtime API (objc/runtime.h).
 *
 * GCC 16's libobjc ships the modern API (replacing the legacy objc-api.h):
 *   - sel_registerName / sel_getName   : selector registry
 *   - objc_getClass                    : class lookup (built-in Object root)
 *   - class_getName                    : class introspection
 *   - objc_getClassList                : class enumeration
 *   - class_createInstance / object_dispose : instance allocation
 *
 * The test is pure C (no @interface), so it compiles with a plain C toolchain.
 */

int main(void)
{
    int failures = 0;

    /* 1. Selector registry round-trip */
    SEL sel = sel_registerName("testSelector");
    if (sel == 0) {
        printf("FAIL: sel_registerName returned NULL\n");
        failures++;
    } else {
        const char *name = sel_getName(sel);
        if (name == NULL || strcmp(name, "testSelector") != 0) {
            printf("FAIL: sel_getName mismatch\n");
            failures++;
        } else {
            printf("OK: selector registry (%s)\n", name);
        }
    }

    /* 2. Class lookup (GNU runtime ships the Object root class) */
    Class cls = (Class)objc_getClass("Object");
    if (cls == 0) {
        printf("FAIL: objc_getClass(\"Object\") returned NULL\n");
        failures++;
    } else {
        const char *name = class_getName(cls);
        if (name == NULL || strcmp(name, "Object") != 0) {
            printf("FAIL: class_getName mismatch\n");
            failures++;
        } else {
            printf("OK: class lookup %s\n", name);
        }
    }

    /* 3. Class enumeration (at least Object/Protocol/NXConstantString) */
    int count = objc_getClassList(NULL, 0);
    if (count <= 0) {
        printf("FAIL: objc_getClassList returned %d\n", count);
        failures++;
    } else {
        printf("OK: %d classes registered\n", count);
    }

    /* 4. Instance allocation (requires a usable runtime) */
    if (cls != 0) {
        id obj = class_createInstance(cls, 0);
        if (obj == NULL) {
            printf("FAIL: class_createInstance returned NULL\n");
            failures++;
        } else {
            printf("OK: class_createInstance succeeded\n");
            object_dispose(obj);
        }
    }

    if (failures == 0) {
        printf("libobjc 16.1.1 runtime API test: ALL PASSED\n");
        return 0;
    }
    printf("libobjc 16.1.1 runtime API test: %d FAILURE(S)\n", failures);
    return 1;
}
