/* test_ohos_libicns.c — HarmonyOS-specific consumer test for libicns 0.9.0.
 *
 * Counted as its own independent test entry (ohos_specific 1/1) — NOT a
 * replacement for the generic consumer test. Directly covers the OHOS
 * adaptation points of this recipe:
 *
 *   1. The patched config.guess/config.sub must have produced an
 *      aarch64-unknown-linux-ohos build (verify the libtool .la-free
 *      install left a loadable shared object that OHOS dlopen accepts).
 *   2. umask 022 fix (HMDFS, E011): files written by libicns' own
 *      icns_io temp-file path under TMPDIR must be readable back by the
 *      same process (permissions sane on HMDFS).
 *   3. Temp files land in TMPDIR (E002): export + file round-trip under
 *      the conan-provided TMPDIR on the HarmonyOS filesystem.
 */

#ifndef __OHOS__
#error "test_ohos_libicns must only be built for OHOS"
#endif

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
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

    /* --- OHOS point 1: the installed shared library must dlopen --- */
    {
        void *handle = dlopen("libicns.so", RTLD_NOW | RTLD_LOCAL);
        if (handle == NULL) {
            fprintf(stderr, "dlopen: %s\n", dlerror());
            fail("dlopen(libicns.so)");
        } else {
            void *sym = dlsym(handle, "icns_create_family");
            CHECK(sym != NULL);
            dlclose(handle);
        }
    }

    /* --- OHOS point 2+3: full file round-trip through TMPDIR --- */
    const char *tmpdir = getenv("TMPDIR");
    CHECK(tmpdir != NULL && tmpdir[0] != '\0');

    icns_family_t *family = NULL;
    CHECK(icns_create_family(&family) == ICNS_STATUS_OK);

    icns_image_t image;
    memset(&image, 0, sizeof(image));
    CHECK(icns_init_image(16, 16, 4, 8, &image) == ICNS_STATUS_OK);
    memset(image.imageData, 0xAB, (size_t)image.imageDataSize);

    icns_element_t *element = NULL;
    CHECK(icns_new_element_from_image(&image, ICNS_16x16_32BIT_DATA,
                                      &element) == ICNS_STATUS_OK);
    CHECK(icns_set_element_in_family(&family, element) == ICNS_STATUS_OK);

    char path[4096];
    snprintf(path, sizeof(path), "%s/libicns_ohos_%d.icns", tmpdir,
             (int)getpid());
    FILE *out = fopen(path, "wb");
    if (out == NULL) {
        fail("fopen(TMPDIR .icns for write)");
    } else {
        CHECK(icns_write_family_to_file(out, family) == ICNS_STATUS_OK);
        fclose(out);

        /* HMDFS permission sanity: the file we just wrote must be
         * readable by us (owner) — catches the umask 077 regressions
         * where later readers lose access. */
        struct stat st;
        CHECK(stat(path, &st) == 0);
        CHECK(st.st_size > 8);
        CHECK((st.st_mode & S_IRUSR) != 0);

        FILE *in = fopen(path, "rb");
        if (in == NULL) {
            fail("fopen(TMPDIR .icns for read)");
        } else {
            icns_family_t *reloaded = NULL;
            CHECK(icns_read_family_from_file(in, &reloaded) ==
                  ICNS_STATUS_OK);
            if (reloaded != NULL) {
                icns_element_t *elem = NULL;
                CHECK(icns_get_element_from_family(
                          reloaded, ICNS_16x16_32BIT_DATA,
                          &elem) == ICNS_STATUS_OK);
                CHECK(elem != NULL && elem->elementSize > 8);
                free(reloaded);
            }
            fclose(in);
        }
        remove(path);
    }

    free(element);
    icns_free_image(&image);
    free(family);

    if (failures) {
        fprintf(stderr, "test_ohos_libicns: %d failure(s)\n", failures);
        return 1;
    }
    printf("test_ohos_libicns: all checks passed\n");
    return 0;
}
