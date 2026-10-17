/*
 * test_runtime.c — consumer-side C test for libobjfwhid1 1.5.7
 *
 * Plain C consumer that genuinely exercises the packaged ObjFW runtime
 * (libobjfwrt) Objective-C runtime C API:
 *   - objc_allocateClassPair(NULL, ...)  -> allocate a root class pair
 *   - objc_registerClassPair(...)        -> register it
 *   - objc_getClass(...)                 -> prove it is found afterwards
 * This works even though the package is static (libobjfwrt.a): the test does
 * not depend on libobjfw classes being force-linked in, so it is a reliable
 * C-consumer link+runtime check (R34: no empty-shell tests; L0c genuine .c).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ObjFWRT/ObjFWRT.h>

int main(void)
{
	Class cls = objc_allocateClassPair(NULL, "TestRuntimeClass", 0);
	if (cls == NULL) {
		fprintf(stderr, "FAIL: objc_allocateClassPair returned NULL\n");
		return 1;
	}

	objc_registerClassPair(cls);

	Class found = objc_getClass("TestRuntimeClass");
	if (found == NULL) {
		fprintf(stderr, "FAIL: registered class not found via objc_getClass\n");
		return 1;
	}

	const char *name = class_getName(found);
	if (name == NULL || strcmp(name, "TestRuntimeClass") != 0) {
		fprintf(stderr, "FAIL: class_getName mismatch: %s\n", name ? name : "(null)");
		return 1;
	}

	unsigned int count = 0;
	Class *list = objc_copyClassList(&count);
	if (list == NULL || count == 0) {
		fprintf(stderr, "FAIL: objc_copyClassList returned no classes\n");
		return 1;
	}
	free(list);

	printf("libobjfwrt OK: root class pair allocated/registered/found (%s)\n",
	    name);
	return 0;
}
