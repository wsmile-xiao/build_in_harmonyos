/* pdlog_dlopen_test.c — native functional test for the packaged pd-log
 * externals.
 *
 * For every object the pd-log package is supposed to install, this program
 *   1. verifies the file really is a 64-bit ELF for the expected machine,
 *   2. dlopen()s it the same way Pure Data does when it instantiates the
 *      corresponding object in a patch, and
 *   3. resolves the externals "<name>_setup" entry point Pd calls on load.
 *
 * A stub package that shipped text files, or externals built for the wrong
 * architecture, fails here instead of silently "passing".
 *
 * Pure Data publishes its whole C API through the process-global symbol
 * table (the pd binary links with -rdynamic) and the externals import every
 * Pd symbol from the loading process instead of linking a libpd — readelf on
 * the artefacts shows 17 GLOBAL UND Pd functions plus the data symbol s_.
 * This program plays that host: it defines the same symbols and is linked
 * with -rdynamic so the dynamic linker can bind them, exactly like pd.
 * The load uses RTLD_NOW because OHOS musl resolves R_AARCH64_JUMP_SLOT
 * relocations eagerly — RTLD_LAZY defers nothing there — so a loader that
 * exports no Pd symbols can never dlopen a correct external on the device
 * (CI build #73602 failed precisely there with "Error relocating
 * logpost.pd_linux: gensym: symbol not found").  RTLD_NOW also makes the
 * glibc path prove the same full resolution instead of deferring it.
 *
 * The expected ELF machine number arrives in the PDLOG_EXPECT_MACHINE
 * environment variable (183 = EM_AARCH64, 62 = EM_X86_64).  When it is unset
 * or 0 only the ELF64 class check runs.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *const kObjects[] = {
    "logpost", "debug", "normal", "error", "fatal",
};
#define N_OBJECTS ((int)(sizeof(kObjects) / sizeof(kObjects[0])))

#define EM_X86_64_ 62
#define EM_AARCH64_ 183

static int g_pass;
static int g_fail;

static void ok(const char *what)
{
    printf("PASS: %s\n", what);
    g_pass++;
}

static void bad(const char *what)
{
    printf("FAIL: %s\n", what);
    g_fail++;
}

/* --- the Pd host contract --------------------------------------------------
 * The 18 symbols every pd-log external imports from the hosting Pd process
 * (readelf --dyn-syms on the packaged *.pd_linux: 17 GLOBAL UND functions
 * plus the t_symbol object s_, whose address serves as the default tag
 * sentinel).  The pd binary exports them by linking with -rdynamic; this
 * binary is linked the same way (see test_package/conanfile.py build()), so
 * even OHOS musl — which binds every relocation at load time — can resolve
 * them all.  None of the stubs ever runs: the test resolves "<name>_setup"
 * and returns without calling it, so the externals' code paths stay dormant
 * and the bodies are irrelevant; only the exported names matter.
 */
void atom_getfloatarg(void) {}
void atom_getsymbolarg(void) {}
void binbuf_add(void) {}
void binbuf_free(void) {}
void binbuf_gettext(void) {}
void binbuf_new(void) {}
void class_addanything(void) {}
void class_addbang(void) {}
void class_addpointer(void) {}
void class_doaddfloat(void) {}  /* m_pd.h maps class_addfloat onto this */
void class_new(void) {}
void floatinlet_new(void) {}
void freebytes(void) {}
void gensym(void) {}
void logpost(void) {}
void pd_new(void) {}
void resizebytes(void) {}

/* t_symbol is { const char *s_name; struct _class **s_thing; } — 16 bytes on
 * LP64.  Only &s_ is ever taken by the externals; it is never dereferenced
 * by this test. */
long long s_[2];

/* Returns 1 when path is an ELF64 file whose e_machine matches want_machine
 * (want_machine == 0 disables the machine comparison). */
static int check_elf(const char *path, int want_machine)
{
    unsigned char hdr[20];
    FILE *f = fopen(path, "rb");
    int machine;

    if (!f) {
        printf("      cannot open %s\n", path);
        return 0;
    }
    if (fread(hdr, 1, sizeof(hdr), f) != sizeof(hdr)) {
        printf("      short read on %s\n", path);
        fclose(f);
        return 0;
    }
    fclose(f);

    if (hdr[0] != 0x7f || hdr[1] != 'E' || hdr[2] != 'L' || hdr[3] != 'F') {
        printf("      %s is not an ELF file\n", path);
        return 0;
    }
    if (hdr[4] != 2) {
        printf("      %s is not ELFCLASS64 (EI_CLASS=%u)\n", path,
               (unsigned)hdr[4]);
        return 0;
    }
    /* e_machine is a 16-bit field at offset 18, files are little endian on
     * every platform pd-log targets. */
    machine = (int)hdr[18] | ((int)hdr[19] << 8);
    if (want_machine != 0 && machine != want_machine) {
        printf("      %s has e_machine=%d, expected %d\n", path, machine,
               want_machine);
        return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    char path[1024];
    char symbol[64];
    const char *dir;
    const char *env_machine;
    int want_machine = 0;
    int i;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <pd-externals-dir>\n", argv[0]);
        return 2;
    }
    dir = argv[1];

    env_machine = getenv("PDLOG_EXPECT_MACHINE");
    if (env_machine && atoi(env_machine) != 0) {
        want_machine = atoi(env_machine);
    }

    printf("[native] pd externals dir: %s\n", dir);
    printf("[native] expected ELF e_machine: %d\n", want_machine);

    for (i = 0; i < N_OBJECTS; i++) {
        const char *name = kObjects[i];
        void *handle;
        void *sym;
        char label[256];

        snprintf(path, sizeof(path), "%s/%s.pd_linux", dir, name);

        snprintf(label, sizeof(label), "%s.pd_linux is ELF64 for the target",
                 name);
        if (check_elf(path, want_machine)) {
            ok(label);
        } else {
            bad(label);
            continue;
        }

        /* RTLD_NOW mirrors the OHOS musl loader, which binds every
         * relocation eagerly (there is no lazy PLT on the device), and it
         * makes glibc prove the same full resolution instead of deferring
         * the Pd imports.  The stubs above satisfy those imports the same
         * way the real pd process does. */
        handle = dlopen(path, RTLD_NOW);
        if (!handle) {
            printf("      dlopen failed: %s\n", dlerror());
            snprintf(label, sizeof(label), "%s.pd_linux loads via dlopen",
                     name);
            bad(label);
            continue;
        }
        snprintf(label, sizeof(label), "%s.pd_linux loads via dlopen", name);
        ok(label);

        snprintf(symbol, sizeof(symbol), "%s_setup", name);
        dlerror();
        sym = dlsym(handle, symbol);
        if (!sym) {
            printf("      dlsym(%s) failed: %s\n", symbol, dlerror());
            snprintf(label, sizeof(label), "%s exports %s", name, symbol);
            bad(label);
        } else {
            snprintf(label, sizeof(label), "%s exports %s", name, symbol);
            ok(label);
        }
        dlclose(handle);
    }

    printf("[native] %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
