/* test.c — Consumer test for libicns 0.8.1.
 *
 * Builds against the installed <icns.h> + libicns.so and exercises the
 * public API end to end: create a family, synthesize a 32-bit ARGB icon
 * element via icns_new_element_from_image, round-trip it through
 * icns_set_element_in_family / icns_get_element_from_family, decode it
 * back with icns_get_image_from_element, export the family to an
 * in-memory icns blob with icns_export_family_data, then re-import it
 * with icns_import_family_data and verify the bytes survived.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <icns.h>

static int failures = 0;

static void fail(const char *what)
{
    fprintf(stderr, "FAIL: %s\n", what);
    failures++;
}

#define CHECK(cond) do { if (!(cond)) fail(#cond); } while (0)

int main(void)
{
    icns_set_print_errors(1);

    /* --- 1. create an empty family --- */
    icns_family_t *family = NULL;
    if (icns_create_family(&family) != ICNS_STATUS_OK || family == NULL) {
        fail("icns_create_family");
        return 1;
    }
    CHECK(family->resourceType == ICNS_FAMILY_TYPE);

    /* --- 2. synthesize a 32x32 ARGB image and wrap it in an element --- */
    icns_image_t image;
    memset(&image, 0, sizeof(image));
    if (icns_init_image(32, 32, 4, 8, &image) != ICNS_STATUS_OK) {
        fail("icns_init_image");
        return 1;
    }
    CHECK(image.imageWidth == 32 && image.imageHeight == 32);
    CHECK(image.imageDataSize == (icns_uint64_t)32 * 32 * 4);
    /* paint a recognizable pattern: channel value = x^y per channel */
    for (unsigned y = 0; y < 32; y++) {
        for (unsigned x = 0; x < 32; x++) {
            icns_byte_t *px =
                image.imageData + ((icns_uint64_t)y * 32 + x) * 4;
            px[0] = (icns_byte_t)(x ^ y);
            px[1] = (icns_byte_t)(x + y);
            px[2] = (icns_byte_t)(x * 2);
            px[3] = 0xFF;
        }
    }

    icns_element_t *element = NULL;
    if (icns_new_element_from_image(&image, ICNS_32x32_32BIT_DATA,
                                    &element) != ICNS_STATUS_OK) {
        fail("icns_new_element_from_image");
        return 1;
    }
    CHECK(element != NULL);
    CHECK(element->elementType == ICNS_32x32_32BIT_DATA);
    CHECK(element->elementSize > 8);

    /* --- 3. insert into the family and read it back --- */
    if (icns_set_element_in_family(&family, element) != ICNS_STATUS_OK) {
        fail("icns_set_element_in_family");
        return 1;
    }
    icns_sint32_t count = 0;
    CHECK(icns_count_elements_in_family(family, &count) == ICNS_STATUS_OK);
    CHECK(count == 1);

    icns_element_t *found = NULL;
    CHECK(icns_get_element_from_family(family, ICNS_32x32_32BIT_DATA,
                                       &found) == ICNS_STATUS_OK);
    CHECK(found != NULL && found->elementType == ICNS_32x32_32BIT_DATA);

    /* --- 4. decode the element back to an image and compare pixels --- */
    icns_image_t decoded;
    memset(&decoded, 0, sizeof(decoded));
    CHECK(icns_get_image_from_element(found, &decoded) == ICNS_STATUS_OK);
    CHECK(decoded.imageWidth == 32 && decoded.imageHeight == 32);
    {
        int pixel_mismatch = 0;
        for (unsigned y = 0; y < 32 && !pixel_mismatch; y++) {
            for (unsigned x = 0; x < 32; x++) {
                icns_byte_t *orig =
                    image.imageData + ((icns_uint64_t)y * 32 + x) * 4;
                icns_byte_t *dec =
                    decoded.imageData + ((icns_uint64_t)y * 32 + x) * 4;
                if (orig[0] != dec[0] || orig[1] != dec[1] ||
                    orig[2] != dec[2]) {
                    pixel_mismatch = 1;
                    break;
                }
            }
        }
        CHECK(!pixel_mismatch);
    }
    icns_free_image(&decoded);

    /* --- 5. utils API --- */
    icns_icon_info_t info = icns_get_image_info_for_type(ICNS_32x32_32BIT_DATA);
    CHECK(info.iconWidth == 32 && info.iconHeight == 32);
    CHECK(icns_get_type_from_image_info(info) == ICNS_32x32_32BIT_DATA);
    char typestr[5];
    const char *r = icns_type_str(ICNS_FAMILY_TYPE, typestr);
    CHECK(r != NULL && strcmp(typestr, "icns") == 0);

    /* --- 6. export to a blob, re-import, verify element survives --- */
    icns_size_t exported_size = 0;
    icns_byte_t *blob = NULL;
    CHECK(icns_export_family_data(family, &exported_size, &blob) ==
          ICNS_STATUS_OK);
    CHECK(blob != NULL && exported_size > 8);

    icns_family_t *reimported = NULL;
    CHECK(icns_import_family_data(exported_size, blob, &reimported) ==
          ICNS_STATUS_OK);
    CHECK(reimported != NULL);
    icns_element_t *refound = NULL;
    CHECK(icns_get_element_from_family(reimported, ICNS_32x32_32BIT_DATA,
                                       &refound) == ICNS_STATUS_OK);
    CHECK(refound != NULL && refound->elementSize == element->elementSize);

    /* --- 7. write/read round-trip through a real temp file --- */
    const char *tmpdir = getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0')
        tmpdir = "/tmp";
    char path[4096];
    snprintf(path, sizeof(path), "%s/libicns_test_%d.icns", tmpdir,
             (int)getpid());
    FILE *out = fopen(path, "wb");
    if (out == NULL) {
        fail("fopen(tmp .icns for write)");
    } else {
        CHECK(icns_write_family_to_file(out, family) == ICNS_STATUS_OK);
        fclose(out);

        FILE *in = fopen(path, "rb");
        if (in == NULL) {
            fail("fopen(tmp .icns for read)");
        } else {
            icns_family_t *from_disk = NULL;
            CHECK(icns_read_family_from_file(in, &from_disk) ==
                  ICNS_STATUS_OK);
            if (from_disk != NULL) {
                icns_element_t *disk_elem = NULL;
                CHECK(icns_get_element_from_family(
                          from_disk, ICNS_32x32_32BIT_DATA,
                          &disk_elem) == ICNS_STATUS_OK);
                CHECK(disk_elem != NULL &&
                      disk_elem->elementSize == element->elementSize);
                free(from_disk);
            }
            fclose(in);
        }
        remove(path);
    }

    /* --- cleanup --- */
    free(reimported);
    free(blob);
    icns_free_image(&image);
    free(element);
    free(family);

    if (failures) {
        fprintf(stderr, "test_libicns: %d failure(s)\n", failures);
        return 1;
    }
    printf("test_libicns: all checks passed\n");
    return 0;
}
