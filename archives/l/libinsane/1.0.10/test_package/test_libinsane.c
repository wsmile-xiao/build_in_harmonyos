/*
 * Consumer test for libinsane 1.0.10 on HarmonyOS PC.
 *
 * Three layers of evidence, because this is a scanner access library and the
 * build host has no scanner attached:
 *   1. ABI / layout contract - _Static_assert pins the public struct sizes,
 *      member offsets and enum ordinals of the 1.0.10 headers, and linking this
 *      file proves every referenced symbol is actually exported by
 *      libinsane.so.1.0.10.
 *   2. Real API behaviour - lis_compare(), lis_getenv(), lis_free(),
 *      lis_get_version() run for real (pure logic, no hardware needed).
 *   3. Device surface - the SANE implementation is initialised and asked for a
 *      device that cannot exist, so the library must report the real failure
 *      form (an lis_error) instead of pretending a device is there.
 */
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libinsane/capi.h>
#include <libinsane/error.h>
#include <libinsane/sane.h>
#include <libinsane/util.h>

#define POINTER_SIZE ((size_t) sizeof(char *))

/* --- 1. ABI contract: pinned against include/libinsane/capi.h of 1.0.10 --- */
_Static_assert(sizeof(struct lis_device_descriptor) == 4 * POINTER_SIZE,
               "lis_device_descriptor must stay 4 pointers wide");
_Static_assert(offsetof(struct lis_device_descriptor, dev_id) == 0,
               "dev_id must stay the first member");
_Static_assert(offsetof(struct lis_device_descriptor, vendor) == POINTER_SIZE,
               "vendor must stay the second member");
_Static_assert(offsetof(struct lis_device_descriptor, model) == 2 * POINTER_SIZE,
               "model must stay the third member");
_Static_assert(offsetof(struct lis_device_descriptor, type) == 3 * POINTER_SIZE,
               "type must stay the fourth member");
_Static_assert(sizeof(union lis_value) == sizeof(double),
               "lis_value must stay double-sized");
_Static_assert(sizeof(struct lis_value_range) == 3 * sizeof(union lis_value),
               "lis_value_range must stay min/max/interval");
_Static_assert(offsetof(struct lis_value_range, max) == sizeof(union lis_value),
               "lis_value_range.max must stay the second slot");
_Static_assert(LIS_TYPE_BOOL == 0 && LIS_TYPE_INTEGER == 1 && LIS_TYPE_DOUBLE == 2
		&& LIS_TYPE_STRING == 3 && LIS_TYPE_IMAGE_FORMAT == 4,
		"lis_value_type ordinals must not drift");
_Static_assert(LIS_IMG_FORMAT_RAW_RGB_24 == 0 && LIS_IMG_FORMAT_GRAYSCALE_8 == 1
		&& LIS_IMG_FORMAT_BMP == 3 && LIS_IMG_FORMAT_PNG == 9
		&& LIS_IMG_FORMAT_TIFF == 16,
		"lis_img_format ordinals must not drift");
_Static_assert(LIS_UNIT_NONE == 0 && LIS_UNIT_PIXEL == 1,
		"lis_unit ordinals must not drift");
_Static_assert(LIS_OK == 0, "LIS_OK must stay the zero status code");

static int g_failed;
static int g_passed;

#define CHECK(cond, label)                                                    \
	do {                                                                  \
		if (cond) {                                                 \
			g_passed++;                                 \
			printf("PASS %s\n", label);                   \
		} else {                                                    \
			g_failed++;                                 \
			printf("FAIL %s (%s)\n", label, #cond);       \
		}                                                           \
	} while (0)

int main(void)
{
	union lis_value a;
	union lis_value b;

	printf("== libinsane consumer test ==\n");

	/* --- 2. real API behaviour ------------------------------------------ */
	/* lis_compare is an *equality* predicate, not an ordering comparator:
	 * include/libinsane/util.h:55-59 documents "\retval 1 if values are
	 * identical" / "\retval 0 if values are different", src/util.c:46-61
	 * returns `val1.x == val2.x`, and the only in-tree caller
	 * (src/workarounds/check_capabilities.c:33) branches on it as a boolean.
	 * The first draft of this file asserted ordering semantics (>0 / <0),
	 * which contradicts the upstream header; the seven assertions below were
	 * rewritten to the documented semantics with both directions covered. */
	a.integer = 7;
	b.integer = 3;
	CHECK(lis_compare(LIS_TYPE_INTEGER, a, b) == 0, "lis_compare: differing integers 7/3 -> 0");
	CHECK(lis_compare(LIS_TYPE_INTEGER, b, a) == 0, "lis_compare: differing integers 3/7 -> 0");
	a.integer = 5;
	b.integer = 5;
	CHECK(lis_compare(LIS_TYPE_INTEGER, a, b) == 1, "lis_compare: identical integers 5/5 -> 1");

	a.dbl = 1.5;
	b.dbl = 1.5;
	CHECK(lis_compare(LIS_TYPE_DOUBLE, a, b) == 1, "lis_compare: identical doubles 1.5/1.5 -> 1");
	b.dbl = 2.5;
	CHECK(lis_compare(LIS_TYPE_DOUBLE, a, b) == 0, "lis_compare: differing doubles 1.5/2.5 -> 0");

	a.boolean = 1;
	b.boolean = 0;
	CHECK(lis_compare(LIS_TYPE_BOOL, a, b) == 0, "lis_compare: differing bools true/false -> 0");

	a.string = "flatbed";
	b.string = "flatbed";
	CHECK(lis_compare(LIS_TYPE_STRING, a, b) == 1, "lis_compare: identical strings -> 1");

	CHECK(lis_getenv("LIBINSANE_TEST_UNSET_VARIABLE", 42) == 42,
		"lis_getenv: falls back to the default when unset");
	CHECK(lis_getenv("LIBINSANE_TEST_UNSET_VARIABLE", -1) == -1,
		"lis_getenv: honours a negative default");

	/* lis_free must own the string it is handed and not crash on it. */
	{
		union lis_value owned;
		owned.string = strdup("heap backed option value");
		CHECK(owned.string != NULL, "strdup available for lis_free case");
		lis_free(LIS_TYPE_STRING, &owned);
		CHECK(1, "lis_free: string value released without crashing");
	}

	CHECK(lis_get_version() != NULL, "lis_get_version: returns a string");

	/* --- 3. device surface: real failure form on a headless machine ------ */
	{
		struct lis_api *api = NULL;
		enum lis_error err = lis_api_sane(&api);

		if (LIS_IS_ERROR(err)) {
			printf("SKIP SANE implementation unavailable: 0x%X (%s)\n", err,
				lis_strerror(err));
		} else {
			struct lis_item *item = NULL;
			enum lis_error err2;

			CHECK(api != NULL && api->list_devices != NULL && api->get_device != NULL,
				"lis_api_sane: vtable populated");
			err2 = api->get_device(api, "libinsane-absent-device:0", &item);
			CHECK(LIS_IS_ERROR(err2),
				"get_device on an absent device reports an lis_error");
			printf("INFO absent device answer: 0x%X (%s)\n", err2, lis_strerror(err2));
			api->cleanup(api);
		}
	}

	printf("== assertions: %d passed, %d failed ==\n", g_passed, g_failed);
	return g_failed == 0 ? 0 : 1;
}
