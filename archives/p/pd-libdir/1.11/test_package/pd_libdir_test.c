/*
 * test_package/pd_libdir_test.c — functional consumer test for pd-libdir.
 *
 * pd-libdir ships no public C API of its own: it is a Pure Data *loader
 * library* that Pd dlopen()s as `libdir.pd_linux` and drives through its
 * exported `setup()` entry point.  The plugin's Pd symbols are resolved out
 * of Pd's own -rdynamic executable image at load time, so this test does
 * exactly the same thing: it embeds a minimal Pure Data runtime shim that
 * provides the 15 Pd symbols `libdir.pd_linux` imports, dlopen()s the
 * packaged plugin with RTLD_NOW, and then drives the real plugin code.
 *
 * Checked behaviour:
 *   1. dlopen + dlsym resolve the documented entry points setup/libdir_setup;
 *   2. setup() registers exactly one loader and emits the "libdir loader"
 *      banner plus the Pd version it was compiled against;
 *   3. the registered loader finds a real <lib>/<lib>-meta.pd on disk, and
 *      adds that directory to the global Pd search path via the "+<dir>"
 *      symbol sent to the "pd" object;
 *   4. a library whose meta file is missing is reported as not found and
 *      leaves the global path untouched;
 *   5. a *relative* directory is accepted as a source but rejected by
 *      sys_isabsolutepath(), so nothing is added to the global path.
 *
 * Any shim entry point that belongs to the legacy pre-0.48 loader path aborts
 * the run, which pins the plugin's call graph as well.  The process exits
 * non-zero if any check fails.
 */
#include "m_pd.h"
#include "s_stuff.h"
#include "g_canvas.h"

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

static int g_checks = 0;
static int g_failures = 0;

static void check(int cond, const char *what)
{
    g_checks++;
    if (cond) {
        printf("  ok   %s\n", what);
    } else {
        printf("  FAIL %s\n", what);
        g_failures++;
    }
}

static void check_str(const char *got, const char *want, const char *what)
{
    g_checks++;
    if (got && want && strcmp(got, want) == 0) {
        printf("  ok   %s\n", what);
    } else {
        printf("  FAIL %s (got \"%s\", want \"%s\")\n", what,
               got ? got : "(null)", want ? want : "(null)");
        g_failures++;
    }
}

/* ------------------------------------------------------------------ *
 * Minimal Pure Data runtime shim.
 *
 * One definition per undefined import of libdir.pd_linux, as reported by
 * `readelf --dyn-syms libdir.pd_linux`:
 *   sys_getversion, sys_register_loader, logpost, gensym, class_new,
 *   pd_new, pd_typedmess, namelist_append, sys_isabsolutepath,
 *   sys_trytoopenone, sys_close, sys_searchpath  +  canvas_open,
 *   open_via_path, canvas_getenv (legacy / canvas-only, must stay uncalled)
 * ------------------------------------------------------------------ */

/* libdir.c declares this itself (pre-0.48 global search path). */
t_namelist *sys_searchpath = NULL;

static loader_t g_loader = NULL;
static int g_loader_registrations = 0;

#define MAX_LOGS 32
static char g_logs[MAX_LOGS][256];
static int g_log_count = 0;

static int g_pd_typedmess_calls = 0;
static char g_pd_receiver[64];
static char g_pd_selector[64];
static char g_pd_arg0[512];

static void unexpected(const char *sym)
{
    printf("  FAIL plugin called %s(), which this code path must not reach\n", sym);
    exit(1);
}

void sys_getversion(int *major, int *minor, int *bugfix)
{
    if (major) *major = PD_MAJOR_VERSION;
    if (minor) *minor = PD_MINOR_VERSION;
    if (bugfix) *bugfix = PD_BUGFIX_VERSION;
}

void sys_register_loader(loader_t loader)
{
    g_loader = loader;
    g_loader_registrations++;
}

void logpost(const void *object, int level, const char *fmt, ...)
{
    va_list ap;
    (void)object;
    (void)level;
    if (g_log_count >= MAX_LOGS) return;
    va_start(ap, fmt);
    vsnprintf(g_logs[g_log_count], sizeof(g_logs[0]), fmt, ap);
    va_end(ap);
    g_log_count++;
}

/* Pd interns one t_symbol per distinct name and hands back the same pointer
 * every time.  The plugin relies on that: it stores gensym("+<dir>") in an
 * atom and only afterwards calls gensym("pd")/gensym("add-to-path") for the
 * message selector, so a shim that reuses a single slot would silently
 * overwrite the stored atom. */
#define MAX_SYMBOLS 64
static t_symbol g_symbols[MAX_SYMBOLS];
static int g_symbol_count = 0;

t_symbol *gensym(const char *s)
{
    int i;
    if (!s) s = "";
    for (i = 0; i < g_symbol_count; i++) {
        if (strcmp(g_symbols[i].s_name, s) == 0) return &g_symbols[i];
    }
    if (g_symbol_count >= MAX_SYMBOLS) return &g_symbols[0];
    memset(&g_symbols[g_symbol_count], 0, sizeof(t_symbol));
    g_symbols[g_symbol_count].s_name = strdup(s);
    return &g_symbols[g_symbol_count++];
}

/* t_class / t_pd are only forward-declared in the public Pd headers, so hand
 * out over-aligned opaque storage rather than pretending to know the layout. */
static max_align_t g_class_storage[64];
static max_align_t g_object_storage[16];

t_class *class_new(t_symbol *name, t_newmethod newmethod, t_method freemethod,
                   size_t size, int flags, t_atomtype arg1, ...)
{
    (void)name;
    (void)newmethod;
    (void)freemethod;
    (void)size;
    (void)flags;
    (void)arg1;
    memset(g_class_storage, 0, sizeof(g_class_storage));
    return (t_class *)g_class_storage;
}

t_pd *pd_new(t_class *cls)
{
    (void)cls;
    memset(g_object_storage, 0, sizeof(g_object_storage));
    return (t_pd *)g_object_storage;
}

void pd_typedmess(t_pd *x, t_symbol *s, int argc, t_atom *argv)
{
    (void)x;
    g_pd_typedmess_calls++;
    snprintf(g_pd_receiver, sizeof(g_pd_receiver), "pd");
    snprintf(g_pd_selector, sizeof(g_pd_selector), "%s",
             s && s->s_name ? s->s_name : "");
    g_pd_arg0[0] = '\0';
    if (argc > 0 && argv && argv[0].a_type == A_SYMBOL &&
        argv[0].a_w.w_symbol && argv[0].a_w.w_symbol->s_name) {
        snprintf(g_pd_arg0, sizeof(g_pd_arg0), "%s", argv[0].a_w.w_symbol->s_name);
    }
}

/* Real behaviour: prepend to the namelist, honouring `allowdup`. */
t_namelist *namelist_append(t_namelist *listwas, const char *s, int allowdup)
{
    t_namelist *node;
    if (!s) return listwas;
    if (!allowdup) {
        for (node = listwas; node; node = node->nl_next) {
            if (node->nl_string && strcmp(node->nl_string, s) == 0) return listwas;
        }
    }
    node = (t_namelist *)calloc(1, sizeof(t_namelist));
    if (!node) return listwas;
    node->nl_string = strdup(s);
    node->nl_next = listwas;
    return node;
}

/* Real behaviour, same rule Pd uses in s_path.c. */
int sys_isabsolutepath(const char *dir)
{
    return dir && dir[0] == '/';
}

/* Mirrors Pd's src/s_path.c:sys_trytoopenone() — it first builds the whole
 * candidate path into `dirresult`, and on success rewinds `dirresult` at the
 * last '/' and points `*nameresult` at the basename.  Getting this right
 * matters: libdir adds `dirresult` (not the search-path entry it was given)
 * to Pd's global path, so a shim that just echoed `dir` back would make the
 * plugin add the wrong directory.  (`sys_expandpath`/`sys_unbashfilename` are
 * omitted: they only expand "~", which the test never uses.) */
int sys_trytoopenone(const char *dir, const char *name, const char *ext,
                     char *dirresult, char **nameresult, unsigned int size,
                     int bin)
{
    size_t need;
    int fd;
    struct stat statbuf;
    char *slash;

    (void)bin;
    if (!dir || !name || !ext || !dirresult) return -1;
    need = strlen(dir) + strlen(name) + strlen(ext) + 4;
    if (need > size) return -1;

    snprintf(dirresult, size, "%s", dir);
    {
        size_t len = strlen(dirresult);
        if (len && dirresult[len - 1] != '/') strncat(dirresult, "/", size - len - 1);
    }
    strncat(dirresult, name, size - strlen(dirresult) - 1);
    strncat(dirresult, ext, size - strlen(dirresult) - 1);

    fd = open(dirresult, O_RDONLY);
    if (fd < 0) return -1;
    /* Pd rejects directories here too. */
    if (fstat(fd, &statbuf) < 0 || S_ISDIR(statbuf.st_mode)) {
        close(fd);
        return -1;
    }

    slash = strrchr(dirresult, '/');
    if (slash) {
        *slash = '\0';
        *nameresult = slash + 1;
    } else if (nameresult) {
        *nameresult = dirresult;
    }
    return fd;
}

int sys_close(int fd)
{
    return fd >= 0 ? close(fd) : -1;
}

/* Legacy pre-0.48 loader path and canvas handling: unreachable here. */
int canvas_open(const t_canvas *x, const char *name, const char *ext,
                char *dirresult, char **nameresult, unsigned int size, int bin)
{
    (void)x; (void)name; (void)ext; (void)dirresult;
    (void)nameresult; (void)size; (void)bin;
    unexpected("canvas_open");
    return -1;
}

int open_via_path(const char *dir, const char *name, const char *ext,
                  char *dirresult, char **nameresult, unsigned int size, int bin)
{
    (void)dir; (void)name; (void)ext; (void)dirresult;
    (void)nameresult; (void)size; (void)bin;
    unexpected("open_via_path");
    return -1;
}

t_canvasenvironment *canvas_getenv(const t_canvas *x)
{
    (void)x;
    unexpected("canvas_getenv");
    return NULL;
}

/* ------------------------------------------------------------------ *
 * Test driver
 * ------------------------------------------------------------------ */

static int logs_contain(const char *needle)
{
    int i;
    for (i = 0; i < g_log_count; i++) {
        if (strstr(g_logs[i], needle)) return 1;
    }
    return 0;
}

static int file_exists(const char *dir, const char *name)
{
    char path[1024];
    struct stat st;
    snprintf(path, sizeof(path), "%s/%s", dir, name);
    return stat(path, &st) == 0 && S_ISREG(st.st_mode);
}

static int mkdir_p(const char *path)
{
    char tmp[1024];
    size_t i, len;

    snprintf(tmp, sizeof(tmp), "%s", path);
    len = strlen(tmp);
    if (len && tmp[len - 1] == '/') tmp[len - 1] = '\0';
    for (i = 1; tmp[i]; i++) {
        if (tmp[i] == '/') {
            tmp[i] = '\0';
            if (mkdir(tmp, 0755) != 0 && errno != EEXIST) return -1;
            tmp[i] = '/';
        }
    }
    if (mkdir(tmp, 0755) != 0 && errno != EEXIST) return -1;
    return 0;
}

static void write_fixture(const char *path, const char *text)
{
    FILE *f = fopen(path, "w");
    if (!f) {
        printf("  FAIL cannot create fixture %s\n", path);
        g_failures++;
        return;
    }
    fputs(text, f);
    fclose(f);
    g_checks++;
    printf("  ok   created fixture %s\n", path);
}

int main(int argc, char **argv)
{
    const char *plugin;
    const char *root;
    char demolib[1024];
    char metafile[1024];
    char expected_arg[1200];
    void *handle;
    void (*setup)(void);
    void (*libdir_setup)(void);
    int rc;

    if (argc < 3) {
        fprintf(stderr, "usage: %s <libdir.pd_linux> <scratch-dir>\n", argv[0]);
        return 2;
    }
    plugin = argv[1];
    root = argv[2];

    printf("pd-libdir consumer test (Pd API headers %d.%d.%d)\n",
           PD_MAJOR_VERSION, PD_MINOR_VERSION, PD_BUGFIX_VERSION);

    /* 0. the packaged library ships its data files next to the plugin */
    {
        char datadir[1024];
        char *slash;
        snprintf(datadir, sizeof(datadir), "%s", plugin);
        slash = strrchr(datadir, '/');
        if (slash) *slash = '\0'; else snprintf(datadir, sizeof(datadir), ".");
        check(file_exists(datadir, "libdir.pd_linux"),
              "packaged plugin libdir.pd_linux is in place");
        check(file_exists(datadir, "libdir-meta.pd"),
              "packaged libdir-meta.pd marker is installed");
        check(file_exists(datadir, "libdir-help.pd"),
              "packaged libdir-help.pd help patch is installed");
        check(file_exists(datadir, "README.txt"),
              "packaged README.txt is installed");
        check(file_exists(datadir, "LICENSE.txt"),
              "packaged LICENSE.txt is installed");
    }

    /* 1. the packaged plugin loads and exports its entry points */
    handle = dlopen(plugin, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        printf("  FAIL dlopen(%s): %s\n", plugin, dlerror());
        return 1;
    }
    printf("  ok   dlopen(%s)\n", plugin);
    g_checks++;

    dlerror();
    *(void **)(&setup) = dlsym(handle, "setup");
    if (!setup) {
        printf("  FAIL dlsym(setup): %s\n", dlerror());
        return 1;
    }
    printf("  ok   dlsym(setup)\n");
    g_checks++;

    dlerror();
    *(void **)(&libdir_setup) = dlsym(handle, "libdir_setup");
    if (!libdir_setup) {
        printf("  FAIL dlsym(libdir_setup): %s\n", dlerror());
        return 1;
    }
    printf("  ok   dlsym(libdir_setup)\n");
    g_checks++;

    /* 2. setup() executes the real plugin code and registers a loader */
    setup();
    check(g_loader_registrations == 1,
          "setup() registered exactly one Pd loader");
    check(g_loader != NULL, "registered loader is a non-NULL pointer");
    check(logs_contain("libdir loader"),
          "setup() logged the \"libdir loader\" banner");
    check(logs_contain("compiled against Pd version"),
          "setup() logged the Pd version it was compiled against");

    if (!g_loader) {
        printf("pd-libdir test: %d/%d checks passed, %d failed\n",
               g_checks - g_failures, g_checks, g_failures);
        return 1;
    }

    /* 3. the loader resolves a real <lib>/<lib>-meta.pd directory */
    snprintf(demolib, sizeof(demolib), "%s/demolib", root);
    if (mkdir_p(demolib) != 0) {
        printf("  FAIL cannot create %s\n", demolib);
        return 1;
    }
    snprintf(metafile, sizeof(metafile), "%s/demolib-meta.pd", demolib);
    write_fixture(metafile, "# dummy libdir meta file for the consumer test\n");

    g_pd_typedmess_calls = 0;
    g_pd_selector[0] = '\0';
    g_pd_arg0[0] = '\0';
    rc = g_loader(NULL, "demolib", root);
    check(rc == 1, "loader() accepted the on-disk demolib library");
    check(g_pd_typedmess_calls == 1,
          "loader() sent exactly one message to Pd");
    check_str(g_pd_receiver, "pd", "the message goes to the \"pd\" object");
    check_str(g_pd_selector, "add-to-path",
              "the selector is \"add-to-path\"");
    snprintf(expected_arg, sizeof(expected_arg), "+%s", demolib);
    check_str(g_pd_arg0, expected_arg,
              "the added path is encoded as \"+<library-dir>\"");

    /* 4. a library without a meta file is reported as not found */
    g_pd_typedmess_calls = 0;
    rc = g_loader(NULL, "nolib", root);
    check(rc == 0, "loader() rejected a library with no meta file");
    check(g_pd_typedmess_calls == 0,
          "loader() left the global path alone for the missing library");

    /* 5. a relative directory is found but not added to the global path */
    if (chdir(root) != 0) {
        printf("  FAIL cannot chdir to %s\n", root);
        g_failures++;
    } else {
        g_pd_typedmess_calls = 0;
        rc = g_loader(NULL, "demolib", ".");
        check(rc == 1, "loader() found demolib through the relative path \".\"");
        check(g_pd_typedmess_calls == 0,
              "relative directory was rejected by sys_isabsolutepath()");
    }

    dlclose(handle);

    printf("pd-libdir test: %d/%d checks passed, %d failed\n",
           g_checks - g_failures, g_checks, g_failures);
    return g_failures ? 1 : 0;
}
