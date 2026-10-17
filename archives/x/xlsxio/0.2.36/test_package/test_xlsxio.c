/* Consumer test for xlsxio/0.2.36: write->read roundtrip through the
 * library API, exercising both libxlsxio_write and libxlsxio_read.
 * Any failed assertion makes the process exit non-zero.
 */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "xlsxio_read.h"
#include "xlsxio_version.h"
#include "xlsxio_write.h"

static int failures = 0;

#define CHECK(cond, msg)                          \
    do {                                          \
        if (cond) {                               \
            printf("ok: %s\n", msg);              \
        } else {                                  \
            printf("FAIL: %s\n", msg);            \
            failures++;                           \
        }                                         \
    } while (0)

static const char *kSheetName = "Roundtrip";
/* Full expected cell matrix including the header row. */
static const char *kExpected[3][2] = {
    {"Name", "Answer"},
    {"hello", "42"},
    {"world", "-7"},
};

int main(void) {
    /* 1. version API agrees with the compile-time header constants */
    int major = -1, minor = -1, micro = -1;
    xlsxiowrite_get_version(&major, &minor, &micro);
    printf("xlsxio version: %d.%d.%d (header %d.%d.%d)\n", major, minor,
           micro, XLSXIO_VERSION_MAJOR, XLSXIO_VERSION_MINOR,
           XLSXIO_VERSION_MICRO);
    CHECK(major == XLSXIO_VERSION_MAJOR && minor == XLSXIO_VERSION_MINOR &&
              micro == XLSXIO_VERSION_MICRO,
          "xlsxiowrite_get_version matches xlsxio_version.h");
    CHECK(xlsxiowrite_get_version_string() != NULL &&
              strstr(xlsxiowrite_get_version_string(), "0.2") != NULL,
          "xlsxiowrite_get_version_string non-null and plausible");

    const char *path = "test_roundtrip.xlsx";
    remove(path);

    /* 2. write a small sheet: header via add_column + two data rows with
     * string and int cells */
    xlsxiowriter writer = xlsxiowrite_open(path, kSheetName);
    CHECK(writer != NULL, "xlsxiowrite_open");
    if (writer) {
        xlsxiowrite_add_column(writer, kExpected[0][0], 0);
        xlsxiowrite_add_column(writer, kExpected[0][1], 0);
        xlsxiowrite_next_row(writer);
        for (int r = 1; r < 3; r++) {
            xlsxiowrite_add_cell_string(writer, kExpected[r][0]);
            xlsxiowrite_add_cell_int(writer, r == 1 ? 42 : -7);
            xlsxiowrite_next_row(writer);
        }
        CHECK(xlsxiowrite_close(writer) == 0, "xlsxiowrite_close rc=0");
    }

    /* 3. sheet list contains our sheet */
    xlsxioreader reader = xlsxioread_open(path);
    CHECK(reader != NULL, "xlsxioread_open");
    if (reader) {
        int found = 0;
        xlsxioreadersheetlist sheets = xlsxioread_sheetlist_open(reader);
        if (sheets) {
            const XLSXIOCHAR *name;
            while ((name = xlsxioread_sheetlist_next(sheets)) != NULL) {
                if (strcmp(name, kSheetName) == 0)
                    found = 1;
            }
            xlsxioread_sheetlist_close(sheets);
        }
        CHECK(found, "sheet list contains \"Roundtrip\"");

        /* 4. read every cell back and compare with the expected matrix */
        xlsxioreadersheet sheet = xlsxioread_sheet_open(
            reader, kSheetName, XLSXIOREAD_SKIP_EMPTY_ROWS);
        CHECK(sheet != NULL, "xlsxioread_sheet_open");
        if (sheet) {
            int row = 0;
            while (xlsxioread_sheet_next_row(sheet) && row < 3) {
                for (int col = 0; col < 2; col++) {
                    XLSXIOCHAR *value = xlsxioread_sheet_next_cell(sheet);
                    char msg[96];
                    snprintf(msg, sizeof(msg), "cell[%d][%d] == \"%s\"",
                             row, col, kExpected[row][col]);
                    CHECK(value != NULL &&
                              strcmp(value, kExpected[row][col]) == 0,
                          msg);
                    if (value)
                        xlsxioread_free(value);
                }
                row++;
            }
            CHECK(row == 3, "read exactly 3 rows (header + 2 data)");
            xlsxioread_sheet_close(sheet);
        }

        /* 5. typed read: the int cell parses as an integer */
        sheet = xlsxioread_sheet_open(reader, kSheetName,
                                      XLSXIOREAD_SKIP_EMPTY_ROWS);
        if (sheet) {
            int64_t v = 0;
            int ok_read = 0;
            /* row 0 = header, row 1 col 1 = 42 */
            if (xlsxioread_sheet_next_row(sheet) &&
                xlsxioread_sheet_next_row(sheet)) {
                XLSXIOCHAR *skip = xlsxioread_sheet_next_cell(sheet);
                if (skip)
                    xlsxioread_free(skip);
                ok_read = xlsxioread_sheet_next_cell_int(sheet, &v);
            }
            CHECK(ok_read && v == 42, "next_cell_int reads 42");
            xlsxioread_sheet_close(sheet);
        }
        xlsxioread_close(reader);
    }

    /* 6. negative contract: opening a non-xlsx file must fail cleanly */
    FILE *garbage = fopen("not_an_xlsx.bin", "wb");
    if (garbage) {
        fputs("this is not a zip archive", garbage);
        fclose(garbage);
    }
    xlsxioreader bad = xlsxioread_open("not_an_xlsx.bin");
    CHECK(bad == NULL, "xlsxioread_open rejects non-xlsx input");
    if (bad)
        xlsxioread_close(bad);
    remove("not_an_xlsx.bin");
    remove(path);

    printf("failed=%d\n", failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
