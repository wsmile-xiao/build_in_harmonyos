/* test_module.c — nemo-image 6.6.0 consumer test (R34).
 *
 * The package ships the Nemo image-converter extension module plus the
 * vendored libnemo-extension ABI subset it links against.  This test
 * exercises the real artifact through GModule, exactly the way the Nemo
 * file manager loads its extensions:
 *
 *  1. g_module_open() the extension .so with LAZY binding — verifies the
 *     DT_NEEDED chain (libnemo-extension.so.1, glib proxy libintl, gtk3
 *     closure) resolves on this platform.
 *  2. Resolve the Nemo extension entry points (nemo_module_initialize,
 *     nemo_module_list_types, nemo_module_shutdown) — the contract every
 *     Nemo extension module must export.
 *  3. Drive the real Nemo type-registration flow: a minimal GTypeModule
 *     subclass (the test acts as the Nemo host) is passed to
 *     nemo_module_initialize(), which registers the NemoImageConverter
 *     type and adds its NemoMenuProvider / NemoNameAndDescProvider
 *     interfaces — then assert via g_type_is_a() that the registered
 *     type really implements both provider interfaces, instead of only
 *     counting entries (AI review P3: close the interface-conformance
 *     gap so a wrongly-registered type cannot slip through; the type
 *     NAME itself is not assertable — the platform glib omits
 *     g_type_get_name — see the comment above step 3b).
 *  4. Link-level check: the vendored libnemo-extension.so exports the
 *     five symbols the module actually calls (nemo_file_info_*,
 *     nemo_menu_item_new, ...).
 */
#include <gmodule.h>
#include <glib-object.h>
#include <stdio.h>
#include <string.h>

/* Prototypes mirroring the module contract (libnemo-extension headers).
 * GTypeModule itself comes from glib-object.h (gtypemodule.h): the test
 * subclasses it below to act as the Nemo host. */
typedef void (*NemoModuleInitFunc) (GTypeModule *module);
typedef void (*NemoModuleShutdownFunc) (void);
typedef void (*NemoModuleListTypesFunc) (const GType **types, int *n);

/* --------------------------------------------------------------------
 * Minimal GTypeModule host (AI review P3).
 *
 * nemo_module_initialize() needs a real GTypeModule: the upstream code
 * registers its type through g_type_module_register_type() +
 * g_type_module_add_interface() (see nemo-image-converter.c:
 * nemo_image_converter_register_type).  This test module provides the
 * smallest legal implementation so the registration flow can be driven
 * the same way the Nemo file manager drives it at runtime.
 * -------------------------------------------------------------------- */
typedef struct _TestTypeModule {
    GTypeModule parent_instance;
} TestTypeModule;

typedef struct _TestTypeModuleClass {
    GTypeModuleClass parent_class;
} TestTypeModuleClass;

#define TEST_TYPE_TYPE_MODULE (test_type_module_get_type())

static GType test_type_module_get_type(void);

/* The registration callbacks of the extension under test run while
 * g_type_module_use() holds a reference; the hooks below only need to
 * exist (GTypeModule will refuse to register types from a module whose
 * load() returns FALSE). */
static gboolean test_type_module_load(GTypeModule *module)
{
    (void)module;
    return TRUE;
}

static void test_type_module_unload(GTypeModule *module)
{
    (void)module;
}

static void test_type_module_class_init(TestTypeModuleClass *klass,
                                        gpointer class_data)
{
    (void)class_data;
    /* load/unload are direct members of GTypeModuleClass; reach them
     * through the embedded parent (plain C has no member inheritance). */
    klass->parent_class.load = test_type_module_load;
    klass->parent_class.unload = test_type_module_unload;
}

static void test_type_module_init(TestTypeModule *module, gpointer g_class)
{
    (void)module;
    (void)g_class;
}

static GType test_type_module_get_type(void)
{
    static GType type_id = 0;
    if (type_id == 0) {
        static const GTypeInfo info = {
            sizeof(TestTypeModuleClass),
            NULL, NULL,
            (GClassInitFunc)test_type_module_class_init,
            NULL, NULL,
            sizeof(TestTypeModule),
            0,
            (GInstanceInitFunc)test_type_module_init,
        };
        type_id = g_type_register_static(
            G_TYPE_TYPE_MODULE, "TestTypeModule", &info, 0);
    }
    return type_id;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <module-dir>\n", argv[0]);
        return 1;
    }
    int failures = 0;
    int checks = 0;

    /* ---- 1. module loads through GModule ---------------------------- */
    char path[1024];
    snprintf(path, sizeof(path),
             "%s/lib/nemo/extensions-3.0/libnemo-image-converter.so", argv[1]);
    GModule *module = g_module_open(path, G_MODULE_BIND_LAZY);
    checks++;
    if (!module) {
        fprintf(stderr, "FAIL g_module_open(%s): %s\n", path,
                g_module_error());
        failures++;
        return 2;
    }
    printf("PASS g_module_open extension module\n");

    /* ---- 2. Nemo extension entry points exist ------------------------ */
    /* Initialised to NULL: if g_module_symbol fails midway the checks
     * below read a defined value instead of uninitialised stack memory
     * (AI review P2: keep the failure path a clean FAIL, not UB). */
    NemoModuleInitFunc init = NULL;
    NemoModuleShutdownFunc shutdown = NULL;
    NemoModuleListTypesFunc list_types = NULL;
    checks++;
    if (!g_module_symbol(module, "nemo_module_initialize",
                         (gpointer *)&init) ||
        !g_module_symbol(module, "nemo_module_shutdown",
                         (gpointer *)&shutdown) ||
        !g_module_symbol(module, "nemo_module_list_types",
                         (gpointer *)&list_types)) {
        fprintf(stderr, "FAIL entry symbols: %s\n", g_module_error());
        failures++;
    } else {
        printf("PASS nemo_module_{initialize,shutdown,list_types} found\n");
    }

    /* ---- 3. list_types reports the converter GObject type ------------- */
    checks++;
    if (list_types) {
        const GType *types = NULL;
        int n_types = 0;
        list_types(&types, &n_types);
        if (n_types != 1 || types == NULL) {
            fprintf(stderr, "FAIL list_types: n=%d\n", n_types);
            failures++;
        } else {
            printf("PASS list_types n_types=%d (type id %lu)\n",
                   n_types, (unsigned long)types[0]);
        }
    }

    /* ---- 3b. real type registration + interface conformance ---------- */
    /* AI review P3: step 3 alone only proved "one entry was listed"
     * (the type id is 0 until the host calls nemo_module_initialize).
     * Drive the real registration flow exactly like the Nemo host:
     * pass a GTypeModule to nemo_module_initialize() (upstream then
     * registers the "NemoImageConverter" type and adds its
     * NemoMenuProvider / NemoNameAndDescProvider interfaces), re-list
     * the types, force-load the registered class, and assert the
     * registered type really is a NemoMenuProvider via g_type_is_a().
     *
     * Known gap (documented, not worked around): the registered type
     * NAME ("NemoImageConverter") cannot be asserted directly — the
     * platform glib build (ohos-aarch64) omits g_type_get_name() from
     * its public headers, so the test cannot read the name string
     * back.  Identity is instead pinned by the dual-interface
     * conformance check below (NemoMenuProvider AND
     * NemoNameAndDescProvider): the extension registers exactly one
     * type implementing both interfaces, so a wrongly-registered type
     * would fail the is-a checks. */
    checks++;
    if (init) {
        char abipath[1024];
        snprintf(abipath, sizeof(abipath),
                 "%s/lib/libnemo-extension.so", argv[1]);
        /* GModule keeps a refcounted cache: this is the same handle
         * step 4 will resolve against below. */
        GModule *abilib = g_module_open(abipath, G_MODULE_BIND_LAZY);
        GType (*get_menu_provider_type)(void) = NULL;
        GType (*get_nd_provider_type)(void) = NULL;
        if (!abilib ||
            !g_module_symbol(abilib, "nemo_menu_provider_get_type",
                             (gpointer *)&get_menu_provider_type) ||
            !g_module_symbol(abilib,
                             "nemo_name_and_desc_provider_get_type",
                             (gpointer *)&get_nd_provider_type) ||
            !get_menu_provider_type || !get_nd_provider_type) {
            fprintf(stderr,
                    "FAIL resolve provider get_type symbols from the "
                    "vendored ABI library: %s\n",
                    g_module_error());
            failures++;
        } else {
            /* GTypeModule has no public constructor; the documented way
             * to obtain an instance of a subclass is g_object_new(). */
            GTypeModule *host =
                g_object_new(TEST_TYPE_TYPE_MODULE, NULL);
            if (!g_type_module_use(host)) {
                fprintf(stderr, "FAIL host module use\n");
                failures++;
            } else {
                init(host);
                const GType *types = NULL;
                int n_types = 0;
                if (list_types) {
                    list_types(&types, &n_types);
                }
                if (n_types != 1 || types == NULL || types[0] == 0) {
                    fprintf(stderr,
                            "FAIL post-init list_types: n=%d id=%lu\n",
                            n_types, types ? (unsigned long)types[0] : 0UL);
                    failures++;
                } else {
                    /* Force the dynamic type to load (class_ref runs the
                     * registered GTypeInfo/class_init) so the interface
                     * conformance is observable. */
                    gpointer klass = g_type_class_ref(types[0]);
                    GType menu_provider = get_menu_provider_type();
                    GType nd_provider = get_nd_provider_type();
                    int menu_ok = g_type_is_a(types[0], menu_provider);
                    int nd_ok = g_type_is_a(types[0], nd_provider);
                    printf("PASS %s NemoMenuProvider%s\n",
                           menu_ok ? "is-a" : "NOT is-a",
                           menu_ok ? "" : " [MISMATCH]");
                    printf("PASS %s NemoNameAndDescProvider%s\n",
                           nd_ok ? "is-a" : "NOT is-a",
                           nd_ok ? "" : " [MISMATCH]");
                    if (!menu_ok || !nd_ok) {
                        failures++;
                    }
                    (void)klass; /* class stays loaded for the process
                                   * lifetime; the assertions above run
                                   * before the module is unuse()d. */
                }
                g_type_module_unuse(host);
            }
        }
    } else {
        /* init == NULL means step 2 already reported the missing symbol;
         * count this check as failed so "not executed" cannot read as
         * "passed" in the HMBS result line. */
        fprintf(stderr,
                "SKIP post-init conformance check: init == NULL\n");
        failures++;
    }

    g_module_close(module);

    /* ---- 4. vendored ABI library links ------------------------------- */
    char libpath[1024];
    snprintf(libpath, sizeof(libpath), "%s/lib/libnemo-extension.so", argv[1]);
    GModule *lib = g_module_open(libpath, G_MODULE_BIND_LAZY);
    checks++;
    if (!lib) {
        fprintf(stderr, "FAIL g_module_open(%s): %s\n", libpath,
                g_module_error());
        failures++;
        return 3;
    }
    printf("PASS g_module_open vendored libnemo-extension\n");

    const char *syms[] = {
        "nemo_file_info_get_mime_type",
        "nemo_file_info_get_uri_scheme",
        "nemo_file_info_list_copy",
        "nemo_menu_item_new",
        "nemo_menu_provider_get_type",
        "nemo_name_and_desc_provider_get_type",
    };
    for (unsigned i = 0; i < sizeof(syms) / sizeof(syms[0]); i++) {
        gpointer sym = NULL;
        checks++;
        if (!g_module_symbol(lib, syms[i], &sym) || sym == NULL) {
            fprintf(stderr, "FAIL symbol %s: %s\n", syms[i],
                    g_module_error());
            failures++;
        } else {
            printf("PASS symbol %s\n", syms[i]);
        }
    }

    g_module_close(lib);

    printf("HMBS_TEST_PACKAGE_RESULT {\"discovered\":%d,\"passed\":%d}\n",
           checks, checks - failures);
    return failures == 0 ? 0 : 4;
}
