/* Consumer test for libgta (test_package, R34).
 *
 * Exercises the *installed* package the same way doc/example-basic.c does:
 * build a 16x8 RGB header, tag it, write a .gta file, read it back and
 * verify header fields, tag roundtrip and pixel data byte-for-byte.
 *
 * Prints one "ASSERT <n> OK/FAIL: <name>" line per assertion plus a final
 * machine-parseable summary line "test_package: N/M assertions passed".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gta/gta.h>

static int checks;
static int failures;

static void check(int cond, const char *name)
{
    checks++;
    if (cond) {
        printf("ASSERT %d OK: %s\n", checks, name);
    } else {
        failures++;
        printf("ASSERT %d FAIL: %s\n", checks, name);
    }
}

int main(void)
{
    gta_type_t components[] = { GTA_UINT8, GTA_UINT8, GTA_UINT8 };
    uintmax_t dimensions[] = { 16, 8 };
    const char *path = "test_package_consumer.gta";
    gta_header_t *header = NULL;
    gta_result_t r;
    void *data = NULL;
    FILE *f;
    uintmax_t x, y;
    int match;

    /* Build the header. */
    r = gta_create_header(&header);
    check(r == GTA_OK && header != NULL, "gta_create_header");

    r = gta_set_components(header, 3, components, NULL);
    check(r == GTA_OK, "gta_set_components(3xUINT8)");

    r = gta_set_dimensions(header, 2, dimensions);
    check(r == GTA_OK, "gta_set_dimensions(16x8)");

    check(gta_get_data_size(header) == 16u * 8u * 3u,
          "gta_get_data_size == 384");

    r = gta_set_tag(gta_get_component_taglist(header, 0),
                    "INTERPRETATION", "RED");
    check(r == GTA_OK, "gta_set_tag(INTERPRETATION=RED)");

    /* Fill the pixel data. */
    data = malloc(gta_get_data_size(header));
    check(data != NULL, "malloc(data)");
    if (!data) {
        gta_destroy_header(header);
        printf("test_package: %d/%d assertions passed\n", checks - failures, checks);
        return 1;
    }
    for (y = 0; y < 8; y++) {
        for (x = 0; x < 16; x++) {
            uintmax_t indices[] = { x, y };
            unsigned char *pixel = gta_get_element(header, data, indices);
            pixel[0] = (unsigned char)x;
            pixel[1] = (unsigned char)(2 * y);
            pixel[2] = 128;
        }
    }

    /* Write the file. */
    f = fopen(path, "wb");
    check(f != NULL, "fopen(write)");
    if (f) {
        r = gta_write_header_to_stream(header, f);
        check(r == GTA_OK, "gta_write_header_to_stream");
        r = gta_write_data_to_stream(header, data, f);
        check(r == GTA_OK, "gta_write_data_to_stream");
        check(fclose(f) == 0, "fclose(write)");
    } else {
        check(0, "gta_write_header_to_stream");
        check(0, "gta_write_data_to_stream");
        check(0, "fclose(write)");
    }

    free(data);
    data = NULL;
    gta_destroy_header(header);
    header = NULL;

    /* Read the file back and verify. */
    f = fopen(path, "rb");
    check(f != NULL, "fopen(read)");
    if (!f) {
        printf("test_package: %d/%d assertions passed\n", checks - failures, checks);
        return 1;
    }
    r = gta_create_header(&header);
    check(r == GTA_OK && header != NULL, "gta_create_header(reread)");
    r = gta_read_header_from_stream(header, f);
    check(r == GTA_OK, "gta_read_header_from_stream");

    check(gta_get_components(header) == 3
              && gta_get_component_type(header, 0) == GTA_UINT8
              && gta_get_component_type(header, 1) == GTA_UINT8
              && gta_get_component_type(header, 2) == GTA_UINT8,
          "header: 3xUINT8 components reread");

    check(gta_get_dimensions(header) == 2
              && gta_get_dimension_size(header, 0) == 16
              && gta_get_dimension_size(header, 1) == 8,
          "header: 16x8 dimensions reread");

    check(gta_get_tag(gta_get_component_taglist(header, 0),
                      "INTERPRETATION") != NULL
              && strcmp(gta_get_tag(gta_get_component_taglist(header, 0),
                                    "INTERPRETATION"), "RED") == 0,
          "tag roundtrip (INTERPRETATION=RED)");

    data = malloc(gta_get_data_size(header));
    check(data != NULL, "malloc(data, reread)");
    if (data) {
        r = gta_read_data_from_stream(header, data, f);
        check(r == GTA_OK, "gta_read_data_from_stream");

        match = 1;
        for (y = 0; y < 8 && match; y++) {
            for (x = 0; x < 16 && match; x++) {
                uintmax_t indices[] = { x, y };
                const unsigned char *pixel =
                    gta_get_element_const(header, data, indices);
                if (pixel[0] != (unsigned char)x
                        || pixel[1] != (unsigned char)(2 * y)
                        || pixel[2] != 128) {
                    match = 0;
                }
            }
        }
        check(match, "pixel data roundtrip byte-for-byte");
        free(data);
        data = NULL;
    } else {
        check(0, "gta_read_data_from_stream");
        check(0, "pixel data roundtrip byte-for-byte");
    }
    check(fclose(f) == 0, "fclose(read)");
    gta_destroy_header(header);
    remove(path);

    printf("test_package: %d/%d assertions passed\n",
           checks - failures, checks);
    return failures ? 1 : 0;
}
