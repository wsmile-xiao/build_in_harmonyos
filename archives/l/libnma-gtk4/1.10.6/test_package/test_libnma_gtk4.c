/* Validates libnma-gtk4 1.10.6 through its real public API (R34: no
 * empty-shell test).
 *
 * nma_bar_code_new()/nma_bar_code_set_text()/nma_bar_code_get_size() run the
 * whole QR-encoding pipeline (vendored qrcodegen.c) in memory — no display,
 * no windowing backend, no D-Bus — so they are exercisable end to end on a
 * headless OHOS PC. The barcode widget is compiled into the gtk4 variant
 * exactly like into the gtk3 one; the call chain runs the GType
 * registration, the qrcodegen encoder and the module constructor
 * (_libnma_init bindtextdomain) that every consumer of libnma-gtk4.so hits
 * at load time.
 *
 * Version macros are asserted from the installed nma-version.h so the
 * package headers and the recipe version must agree. */
#include <libnma/nma-bar-code.h>
#include <libnma/nma-version.h>
#include <glib.h>
#include <stdio.h>

static int failures;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            g_printerr("FAIL %s:%d: %s\n", __FILE__, __LINE__, (msg));       \
            failures++;                                                      \
        }                                                                    \
    } while (0)

int
main(void)
{
    NMABarCode *barcode = NULL;

    /* 1. The installed headers must report the recipe version. */
    CHECK(NMA_MAJOR_VERSION == 1 && NMA_MINOR_VERSION == 10 && NMA_MICRO_VERSION == 6,
          "installed headers do not report version 1.10.6");

    /* 2. GType registration works (load-time GObject boilerplate). */
    CHECK(nma_bar_code_get_type() != G_TYPE_INVALID,
          "nma_bar_code_get_type() returned G_TYPE_INVALID");
    CHECK(g_type_name(nma_bar_code_get_type()) != NULL,
          "NMABarCode GType has no registered name");

    /* 3. The QR encoder really encodes: a non-empty text must produce a
     *    positive module count. (nma_bar_code_set_text exists in the header
     *    but is not in the upstream version-script export list
     *    src/libnma.ver — only draw/get_size/get_type/new/widget_* are
     *    exported — so the consumer test sticks to the exported surface.) */
    barcode = nma_bar_code_new("libnma-gtk4-ohos-test");
    CHECK(barcode != NULL, "nma_bar_code_new() returned NULL");
    if (barcode) {
        int size = nma_bar_code_get_size(barcode);
        CHECK(size > 0, "nma_bar_code_get_size() returned a non-positive size");
        /* a longer payload must also encode: build a second instance */
        NMABarCode *barcode2 = nma_bar_code_new(
            "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/"
            "libnma-gtk4-1.10.6-consumer-test-with-a-much-longer-payload");
        CHECK(barcode2 != NULL, "nma_bar_code_new() returned NULL for a longer payload");
        if (barcode2) {
            int size2 = nma_bar_code_get_size(barcode2);
            CHECK(size2 > 0, "nma_bar_code_get_size() returned non-positive for longer payload");
            CHECK(size2 >= size, "a longer payload produced a smaller QR module matrix");
            g_object_unref(barcode2);
        }
        g_object_unref(barcode);
    }

    if (failures > 0) {
        g_printerr("libnma-gtk4 1.10.6: %d check(s) FAILED\n", failures);
        return 1;
    }

    g_print("libnma-gtk4 1.10.6 OK: QR pipeline verified (type=%s, modules>0, size monotonic)\n",
            g_type_name(nma_bar_code_get_type()));
    return 0;
}
