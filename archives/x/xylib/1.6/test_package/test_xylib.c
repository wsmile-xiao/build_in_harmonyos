/*
 * test_xylib.c — xylib 1.6 consumer test (HarmonyOS PC)
 *
 * Links against the packaged libxy and exercises the real public C API
 * (xylib/xylib.h).  Each CHECK() is one genuine assertion against the
 * library: version string, registered format table, and end-to-end parse of
 * a small whitespace-separated text data file (the "text" format), verifying
 * block/column/row counts and actual data values.
 *
 * Prints a per-assertion [PASS]/[FAIL] line and a final HMBS marker so the
 * machine-evidence gate can verify the numbers came from a real run.
 */

#include <stdio.h>
#include <string.h>
#include <math.h>

#include <xylib/xylib.h>

static int g_discovered = 0;
static int g_passed = 0;
static int g_failed = 0;

#define CHECK(cond, name)                                                 \
    do {                                                                  \
        g_discovered++;                                                   \
        if (cond) {                                                       \
            g_passed++;                                                   \
            printf("[OK] %s\n", name);                                    \
        } else {                                                          \
            g_failed++;                                                   \
            printf("[FAIL] %s (line %d)\n", name, __LINE__);              \
        }                                                                 \
    } while (0)

int main(void)
{
    const char *ver = xylib_get_version();
    CHECK(ver != NULL && strncmp(ver, "1.6", 3) == 0,
          "xylib_get_version() reports 1.6.x");

    const struct xylibFormat *f0 = xylib_get_format(0);
    CHECK(f0 != NULL && f0->name != NULL && f0->name[0] != '\0',
          "xylib_get_format(0) returns a named format");

    /* Scan the full format table — upstream registers many formats. */
    int format_count = 0;
    for (int n = 0; xylib_get_format(n) != NULL; ++n)
        format_count++;
    CHECK(format_count >= 10, "format table registers 10+ formats");

    const char *sample_paths[] = {
        "sample.txt",
        NULL,
    };
    const char *sample = NULL;
    for (int i = 0; sample_paths[i] != NULL; ++i) {
        FILE *fp = fopen(sample_paths[i], "r");
        if (fp) {
            fclose(fp);
            sample = sample_paths[i];
            break;
        }
    }
    CHECK(sample != NULL, "sample data file is readable");

    if (sample == NULL) {
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,"
               "\"command\":\"./test_xylib\",\"discovered\":%d,"
               "\"passedCount\":%d}\n", g_discovered, g_passed);
        return 1;
    }

    void *ds = xylib_load_file(sample, "text", NULL);
    CHECK(ds != NULL, "xylib_load_file() parses the text data file");

    if (ds) {
        void *blk = xylib_get_block(ds, 0);
        CHECK(blk != NULL, "xylib_get_block(0) returns a block");

        if (blk) {
            int ncols = xylib_count_columns(blk);
            /* The C API exposes 1-based columns: real data columns are
             * 1..ncols, while column 0 is a pseudo "index" column returning
             * the point index.  So query the row count against column 1. */
            int nrows = xylib_count_rows(blk, 1);
            CHECK(ncols == 2, "text file parsed as 2 columns");
            CHECK(nrows == 3, "text file parsed as 3 rows");

            if (ncols == 2 && nrows == 3) {
                /* col 1 = first data column (1.0,2.0,3.0), row 0 == 1.0 */
                CHECK(fabs(xylib_get_data(blk, 1, 0) - 1.0) < 1e-6,
                      "data[1][0] == 1.0");
                /* col 2 = second data column (2.0,4.0,6.0), row 2 == 6.0 */
                CHECK(fabs(xylib_get_data(blk, 2, 2) - 6.0) < 1e-6,
                      "data[2][2] == 6.0");
            }
        }
        xylib_free_dataset(ds);
    }

    printf("RESULT: %d/%d checks passed\n", g_passed, g_discovered);
    if (g_failed != 0) {
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,"
               "\"command\":\"./test_xylib\",\"discovered\":%d,"
               "\"passedCount\":%d}\n", g_discovered, g_passed);
        return 1;
    }
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
           "\"command\":\"./test_xylib\",\"discovered\":%d,"
           "\"passedCount\":%d}\n", g_discovered, g_passed);
    return 0;
}
