// Consumer test for nanoarrow 0.9.0 (R34: substantive API usage).
// Builds and validates Arrow arrays through the public C Data interface:
// version query, int32 array build/verify, string array build/verify,
// schema deep-copy. Each check prints PASS/FAIL; the final SUMMARY line
// is parsed by conanfile.py for the HMBS evidence marker.
#include <stdio.h>
#include <string.h>

#include "nanoarrow/nanoarrow.h"

static int g_passed = 0;
static int g_failed = 0;

#define CHECK(cond, label)                                                     \
  do {                                                                         \
    if (cond) {                                                                \
      printf("PASS %s\n", label);                                              \
      g_passed++;                                                              \
    } else {                                                                   \
      printf("FAIL %s (line %d)\n", label, __LINE__);                          \
      g_failed++;                                                              \
    }                                                                          \
  } while (0)

int main(void) {
  // 1. Version query: library is linked and callable.
  const char* version = ArrowNanoarrowVersion();
  CHECK(version != NULL && version[0] != '\0', "version-non-empty");
  printf("INFO nanoarrow version: %s\n", version ? version : "(null)");

  // 2. Int32 array: build [10, 20, 30] and verify length/content.
  {
    struct ArrowSchema schema;
    struct ArrowArray array;
    struct ArrowError error;
    struct ArrowArrayView view;
    int ok = 1;

    if (ArrowSchemaInitFromType(&schema, NANOARROW_TYPE_INT32) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && strcmp(schema.format, "i") != 0) {
      ok = 0;
    }
    if (ok && ArrowArrayInitFromType(&array, NANOARROW_TYPE_INT32) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayStartAppending(&array) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayAppendInt(&array, 10) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayAppendInt(&array, 20) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayAppendInt(&array, 30) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayFinishBuildingDefault(&array, &error) != NANOARROW_OK) {
      printf("INFO finish error: %s\n", error.message);
      ok = 0;
    }
    if (ok && array.length != 3) {
      ok = 0;
    }
    if (ok && array.null_count != 0) {
      ok = 0;
    }
    if (ok) {
      ArrowArrayViewInitFromType(&view, NANOARROW_TYPE_INT32);
      {
        if (ArrowArrayViewSetArray(&view, &array, &error) != NANOARROW_OK) {
          printf("INFO view error: %s\n", error.message);
          ok = 0;
        } else if (ArrowArrayViewGetIntUnsafe(&view, 0) != 10 ||
                   ArrowArrayViewGetIntUnsafe(&view, 1) != 20 ||
                   ArrowArrayViewGetIntUnsafe(&view, 2) != 30) {
          ok = 0;
        }
        ArrowArrayViewReset(&view);
      }
    }
    CHECK(ok, "int32-build-verify");
    ArrowArrayRelease(&array);
    ArrowSchemaRelease(&schema);
  }

  // 3. String array: build ["hi", "ohos"] and verify length.
  {
    struct ArrowArray array;
    struct ArrowError error;
    int ok = 1;

    if (ArrowArrayInitFromType(&array, NANOARROW_TYPE_STRING) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayStartAppending(&array) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayAppendString(&array, ArrowCharView("hi")) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayAppendString(&array, ArrowCharView("ohos")) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowArrayFinishBuildingDefault(&array, &error) != NANOARROW_OK) {
      printf("INFO string finish error: %s\n", error.message);
      ok = 0;
    }
    if (ok && array.length != 2) {
      ok = 0;
    }
    CHECK(ok, "string-build-verify");
    ArrowArrayRelease(&array);
  }

  // 4. Schema deep-copy: struct schema with one int32 child survives copy.
  {
    struct ArrowSchema schema;
    struct ArrowSchema copy;
    struct ArrowSchemaView view;
    struct ArrowError error;
    int ok = 1;

    if (ArrowSchemaInitFromType(&schema, NANOARROW_TYPE_STRUCT) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowSchemaAllocateChildren(&schema, 1) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowSchemaInitFromType(schema.children[0], NANOARROW_TYPE_INT32) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowSchemaSetName(schema.children[0], "value") != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && ArrowSchemaDeepCopy(&schema, &copy) != NANOARROW_OK) {
      ok = 0;
    }
    if (ok && (copy.n_children != 1 || copy.children[0] == NULL ||
               strcmp(copy.children[0]->format, "i") != 0)) {
      ok = 0;
    }
    if (ok && ArrowSchemaViewInit(&view, &schema, &error) != NANOARROW_OK) {
      ok = 0;
    }
    CHECK(ok, "schema-deep-copy");
    ArrowSchemaRelease(&copy);
    ArrowSchemaRelease(&schema);
  }

  printf("SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
  return g_failed == 0 ? 0 : 1;
}
