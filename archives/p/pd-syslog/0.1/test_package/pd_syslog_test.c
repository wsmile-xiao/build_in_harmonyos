/*
 * pd_syslog_test.c — functional consumer test for pd-syslog 0.1 on OHOS.
 *
 * pd-syslog ships no tests at all (see test_package/MANIFEST.yml), and there is
 * nothing to link against: the deliverable is a Pure Data plugin, an ELF shared
 * object that Pd dlopen()s and whose Pd symbols are resolved from Pd's own
 * -rdynamic image.  This program therefore reproduces exactly what Pd does:
 *
 *   1. it is linked with -rdynamic and *defines* the nine Pd entry points the
 *      plugin imports (gensym, class_new, class_addanything, floatinlet_new,
 *      getbytes, freebytes, atom_string, pd_new and the global `s_`), plus the
 *      three libc syslog(3) entry points the plugin calls;
 *   2. it dlopen()s the packaged syslog.pd_linux with RTLD_NOW, so the load
 *      itself proves every one of those imports resolves;
 *   3. it calls the plugin's real `syslog_setup()`, then drives the real object
 *      lifecycle through the recorded Pd callbacks — construct, set the severity
 *      inlet, bang/send messages, destruct.
 *
 * Because `openlog`/`syslog`/`closelog` are interposed by the executable (the
 * executable comes first in the dynamic symbol lookup scope), the assertions are
 * made on what the plugin *actually forwarded*: the priority, the ident passed
 * to openlog, and the fully formatted message text.  No real syslogd is needed,
 * which also keeps the test independent of the host's /dev/log.
 *
 * The program exits non-zero if any check fails, so `conan create` fails.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <syslog.h>
#include <dlfcn.h>

#include "m_pd.h"

/* ------------------------------------------------------------------ *
 * Minimal Pure Data runtime shim.
 *
 * Signatures and constants come from the real m_pd.h shipped by
 * puredata/0.54.1 and re-exported by this package, so the shim cannot
 * drift from what the plugin was compiled against.
 * ------------------------------------------------------------------ */

#define MAX_SYMS 64
#define MAX_CALLS 16
#define MSG_MAX 1024

/* `struct _class` is an incomplete type in m_pd.h, so the single class record
 * the plugin registers lives in a byte blob we hand back as a t_class *. */
static long g_class_blob[64];
static long g_inlet_blob[8];

static int n_class_new;
static t_symbol *cls_name;
static t_newmethod cls_newmethod;
static t_method cls_freemethod;
static size_t cls_size;
static int cls_flags;
static t_atomtype cls_arg1;
static void *cls_anything;
static int n_class_addanything;

static void *g_last_obj;
static t_object *g_inlet_owner;
static t_float *g_inlet_level;

static size_t g_last_getbytes;
static int n_getbytes;
static int n_freebytes;

static t_symbol *g_symtab[MAX_SYMS];
static int g_nsyms;

static int n_openlog;
static char g_openlog_id[MSG_MAX];
static int g_openlog_option;
static int g_openlog_facility;

static int n_closelog;

static int n_syslog;
static int g_syslog_pri[MAX_CALLS];
static char g_syslog_msg[MAX_CALLS][MSG_MAX];

/* Pd's global empty symbol.  m_pd.h declares `EXTERN t_symbol s_...` and only
 * defines the `s_` macro when PDINSTANCE is set; this build does not define
 * PDINSTANCE (the Makefile adds just -DPD -DVERSION), so `s_` is a plain
 * global and `&s_` — which syslog.c compares against — is its address. */
t_symbol s_;

/* gensym() interns by name in Pd and never frees; interning matters here
 * because the plugin stores the returned symbol inside atoms, so a shim that
 * handed out a fresh slot per call would let a later gensym() clobber a
 * symbol an earlier atom still points at. */
t_symbol *gensym(const char *s)
{
    int i;
    t_symbol *sym;

    for (i = 0; i < g_nsyms; i++)
        if (strcmp(g_symtab[i]->s_name, s) == 0)
            return g_symtab[i];

    sym = (t_symbol *)calloc(1, sizeof(t_symbol));
    sym->s_name = strdup(s);
    sym->s_thing = NULL;
    sym->s_next = NULL;
    if (g_nsyms < MAX_SYMS)
        g_symtab[g_nsyms++] = sym;
    return sym;
}

t_class *class_new(t_symbol *name, t_newmethod newmethod, t_method freemethod,
                   size_t size, int flags, t_atomtype arg1, ...)
{
    n_class_new++;
    cls_name = name;
    cls_newmethod = newmethod;
    cls_freemethod = freemethod;
    cls_size = size;
    cls_flags = flags;
    cls_arg1 = arg1;
    memset(g_class_blob, 0, sizeof(g_class_blob));
    return (t_class *)g_class_blob;
}

/* m_pd.h carries a legacy, self-referential
 *     #define class_addanything(x, y) class_addanything((x), (t_method)(y))
 * which rewrites *this function's own definition* (its two parameters match the
 * macro's two arguments).  Drop the macro and define the real prototype that
 * m_pd.h already declares above. */
#ifdef class_addanything
#undef class_addanything
#endif

void class_addanything(t_class *c, t_method fn)
{
    (void)c;
    n_class_addanything++;
    cls_anything = (void *)fn;
}

t_pd *pd_new(t_class *cls)
{
    void *obj;

    (void)cls;
    if (cls_size == 0 || cls_size > (1u << 20))
        return NULL;
    obj = calloc(1, cls_size);
    g_last_obj = obj;
    return (t_pd *)obj;
}

t_inlet *floatinlet_new(t_object *owner, t_float *fp)
{
    g_inlet_owner = owner;
    g_inlet_level = fp;
    memset(g_inlet_blob, 0, sizeof(g_inlet_blob));
    return (t_inlet *)g_inlet_blob;
}

void *getbytes(size_t nbytes)
{
    void *p = malloc(nbytes ? nbytes : 1);

    g_last_getbytes = nbytes;
    n_getbytes++;
    if (p)
        memset(p, 0, nbytes);
    return p;
}

void freebytes(void *x, size_t nbytes)
{
    (void)nbytes;
    n_freebytes++;
    free(x);
}

void atom_string(const t_atom *a, char *buf, unsigned int bufsize)
{
    if (a->a_type == A_SYMBOL && a->a_w.w_symbol)
        snprintf(buf, bufsize, "%s", a->a_w.w_symbol->s_name);
    else if (a->a_type == A_FLOAT)
        snprintf(buf, bufsize, "%g", (double)a->a_w.w_float);
    else
        snprintf(buf, bufsize, "%s", "");
}

/* ------------------------------------------------------------------ *
 * Interposed libc syslog(3) entry points.
 *
 * These are the plugin's only outward-facing effect, so they are where the
 * behavioural assertions are made.
 * ------------------------------------------------------------------ */

void openlog(const char *ident, int option, int facility)
{
    n_openlog++;
    snprintf(g_openlog_id, sizeof(g_openlog_id), "%s", ident ? ident : "(null)");
    g_openlog_option = option;
    g_openlog_facility = facility;
}

void syslog(int pri, const char *fmt, ...)
{
    char buf[MSG_MAX];
    va_list ap;

    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    if (n_syslog < MAX_CALLS) {
        g_syslog_pri[n_syslog] = pri;
        snprintf(g_syslog_msg[n_syslog], MSG_MAX, "%s", buf);
    }
    n_syslog++;
}

void closelog(void)
{
    n_closelog++;
}

/* ------------------------------------------------------------------ *
 * Assertions
 * ------------------------------------------------------------------ */

static int checks;
static int failures;

static void check(int ok, const char *name)
{
    checks++;
    printf("%s %d - %s\n", ok ? "ok" : "not ok", checks, name);
    if (!ok)
        failures++;
}

static int file_exists(const char *dir, const char *name)
{
    char path[MSG_MAX];

    snprintf(path, sizeof(path), "%s/%s", dir, name);
    return access(path, R_OK) == 0;
}

/* Drive one "anything" method call the way Pd dispatches a message. */
static void send_anything(void *obj, t_symbol *sel, int argc, t_atom *argv)
{
    void (*fn)(void *, t_symbol *, int, t_atom *) =
        (void (*)(void *, t_symbol *, int, t_atom *))cls_anything;

    fn(obj, sel, argc, argv);
}

/* t_newmethod is declared as the generic `void *(*)(void)`, but Pd invokes a
 * class constructor with the creation selector, which syslog_new() reads to
 * decide the syslog ident.  Cast to the real signature. */
static void *construct(t_symbol *sel)
{
    void *(*nm)(t_symbol *) = (void *(*)(t_symbol *))cls_newmethod;

    return nm ? nm(sel) : NULL;
}

int main(int argc, char **argv)
{
    const char *plugin;
    const char *dir;
    char pdir[MSG_MAX];
    void *handle;
    void (*setup)(void);
    void *obj;
    t_atom atoms[2];
    const char *last;
    size_t i;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-syslog.pd_linux>\n", argv[0]);
        return 2;
    }
    plugin = argv[1];

    /* Pd's empty symbol: the "no selector" atom, name "". */
    s_.s_name = strdup("");
    s_.s_thing = NULL;
    s_.s_next = NULL;

    /* --- the data files Pd needs must ship next to the plugin --- */
    snprintf(pdir, sizeof(pdir), "%s", plugin);
    for (i = strlen(pdir); i > 0; i--) {
        if (pdir[i - 1] == '/') {
            pdir[i - 1] = '\0';
            break;
        }
    }
    dir = pdir;
    check(file_exists(dir, "syslog-meta.pd"),
          "packaged plugin directory carries syslog-meta.pd");
    check(file_exists(dir, "syslog-help.pd"),
          "packaged plugin directory carries syslog-help.pd");
    check(file_exists(dir, "README.txt"),
          "packaged plugin directory carries README.txt");
    check(file_exists(dir, "LICENSE.txt"),
          "packaged plugin directory carries LICENSE.txt");

    /* --- load the real packaged artifact --- */
    handle = dlopen(plugin, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "Bail out! dlopen failed: %s\n", dlerror());
        return 1;
    }
    check(1, "packaged syslog.pd_linux dlopen()s with RTLD_NOW (all Pd imports resolve)");

    /* Pd looks for `setup` first and falls back to `<classname>_setup`. */
    check(dlsym(handle, "setup") == NULL,
          "plugin exports no bare `setup` symbol (Pd uses the <name>_setup fallback)");
    setup = (void (*)(void))dlsym(handle, "syslog_setup");
    check(setup != NULL, "dlsym resolves the plugin's syslog_setup entry point");
    if (!setup)
        return 1;

    /* --- register the class, exactly as Pd does at plugin load time --- */
    setup();
    check(n_class_new == 1, "syslog_setup() registers exactly one Pd class");
    check(cls_name != NULL && cls_name->s_name != NULL
              && strcmp(cls_name->s_name, "syslog") == 0,
          "the registered class is named `syslog`");
    check(cls_arg1 == A_DEFSYM,
          "class_new() first vararg is A_DEFSYM, so the selector is optional");
    check(cls_size > 0, "class_new() reports a non-zero instance size");
    check(cls_newmethod != NULL && cls_freemethod != NULL,
          "class_new() receives both a constructor and a destructor");
    check(n_class_addanything == 1 && cls_anything != NULL,
          "class_addanything() registers the object's message handler");

    /* --- construct with the empty selector: ident defaults to "puredata" --- */
    n_openlog = 0;
    obj = construct(&s_);
    check(obj != NULL, "constructing the object with the empty selector succeeds");
    check(n_openlog == 1, "the constructor opens the log exactly once");
    check(strcmp(g_openlog_id, "puredata") == 0,
          "empty selector makes the constructor openlog(\"puredata\", ...)");
    check(g_openlog_option == 0 && g_openlog_facility == LOG_USER,
          "openlog() is called with option 0 and facility LOG_USER");

    /* --- the severity inlet is a real float inlet inside the object --- */
    check(g_inlet_owner != NULL && g_inlet_level != NULL,
          "floatinlet_new() is called with an owner and a float pointer");
    check(g_inlet_owner != NULL && g_inlet_level != NULL
              && (char *)g_inlet_level > (char *)obj
              && (char *)g_inlet_level < (char *)obj + cls_size,
          "the severity inlet points inside this object's own storage");

    /* --- default severity --- */
    n_syslog = 0;
    n_getbytes = 0;
    send_anything(obj, gensym("bang"), 0, NULL);
    check(n_syslog == 1 && g_syslog_pri[0] == LOG_NOTICE,
          "with the inlet untouched a bang is logged at the default LOG_NOTICE");

    /* --- set the severity through the inlet, the way a Pd float does --- */
    if (g_inlet_level)
        *g_inlet_level = (t_float)LOG_ERR;
    n_syslog = 0;
    send_anything(obj, gensym("bang"), 0, NULL);
    check(n_syslog == 1 && g_syslog_pri[0] == LOG_ERR,
          "writing LOG_ERR into the inlet changes the forwarded severity");

    /* --- message formatting: selector and atoms joined by single spaces --- */
    SETFLOAT(&atoms[0], 42);
    SETSYMBOL(&atoms[1], gensym("hello"));
    n_syslog = 0;
    n_getbytes = 0;
    n_freebytes = 0;
    send_anything(obj, gensym("bang"), 2, atoms);
    check(n_syslog == 1, "a float+symbol message is forwarded exactly once");
    last = (n_syslog > 0) ? g_syslog_msg[0] : "";
    check(strcmp(last, "bang 42 hello") == 0,
          "selector and atoms are joined with single spaces: \"bang 42 hello\"");
    check(n_getbytes == 1 && g_last_getbytes == strlen(last) + 1,
          "the message buffer is allocated at exactly strlen(message)+1 bytes");
    check(n_freebytes == 1,
          "the message buffer is released again (getbytes/freebytes balanced)");

    /* --- consecutive messages keep their order and their own priority --- */
    n_syslog = 0;
    send_anything(obj, gensym("first"), 0, NULL);
    if (g_inlet_level)
        *g_inlet_level = (t_float)LOG_WARNING;
    send_anything(obj, gensym("second"), 0, NULL);
    check(n_syslog == 2
              && strcmp(g_syslog_msg[0], "first") == 0
              && strcmp(g_syslog_msg[1], "second") == 0,
          "two consecutive messages are forwarded in order with their own text");
    check(n_syslog == 2 && g_syslog_pri[0] == LOG_ERR
              && g_syslog_pri[1] == LOG_WARNING,
          "each message carries the severity set at the time it was sent");

    /* --- construct with a named selector: ident becomes that name --- */
    n_openlog = 0;
    n_closelog = 0;
    {
        void *named = construct(gensym("logger"));

        check(named != NULL, "constructing the object with a named selector succeeds");
        check(n_openlog == 1 && strcmp(g_openlog_id, "logger") == 0,
              "a named selector makes the constructor openlog() with that name");
        if (cls_freemethod)
            ((void (*)(void *))cls_freemethod)(named);
        check(n_closelog == 1, "destroying the object closes the log exactly once");
    }

    /* --- NULL selector: upstream's `length -= 1` defensive branch --- */
    n_syslog = 0;
    n_getbytes = 0;
    send_anything(obj, NULL, 1, &atoms[1]);
    check(n_syslog == 1, "a message with no selector is still forwarded");
    last = (n_syslog > 0) ? g_syslog_msg[0] : "";
    check(strcmp(last, "hello") == 0,
          "with no selector only the atom text is logged");

    /* --- empty message is suppressed before anything is allocated --- */
    n_syslog = 0;
    n_getbytes = 0;
    send_anything(obj, &s_, 0, NULL);
    check(n_syslog == 0, "an empty selector with no atoms logs nothing");
    check(n_getbytes == 0, "an empty message allocates no buffer at all");

    /* --- destruction closes the log --- */
    n_closelog = 0;
    if (cls_freemethod)
        ((void (*)(void *))cls_freemethod)(obj);
    check(n_closelog == 1, "the destructor closes the log exactly once");

    dlclose(handle);

    printf("1..%d\n", checks);
    if (failures) {
        printf("# %d of %d checks FAILED\n", failures, checks);
        return 1;
    }
    printf("# all %d checks passed\n", checks);
    return 0;
}