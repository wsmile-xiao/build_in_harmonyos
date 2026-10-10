/*
 * test_package/pd_ekext_test.c -- functional consumer test for pd-ekext 0.3.1.
 *
 * pd-ekext ships no public C API and no command line program: it installs 43
 * Pure Data externals, one ELF shared object per class
 * (lib/pd-externals/ekext/<class>.pd_linux), which Pd dlopen()s the first time
 * a patch instantiates the object.  A Pd external links against nothing -- Pd
 * is linked -rdynamic and the plugin's Pd symbols are resolved out of the
 * running Pd image at load time -- so there is nothing to link against and no
 * CLI to execute.
 *
 * This test therefore reproduces exactly what Pd does at load time:
 *
 *   Tier A, for all 43 packaged externals:
 *     1. the file is a 64-bit little-endian aarch64 ELF shared object;
 *     2. it dlopen()s with RTLD_NOW|RTLD_LOCAL -- RTLD_NOW proves every Pd
 *        symbol it imports is satisfiable from the loading image, RTLD_LOCAL
 *        proves it is satisfied by Pd alone and not by another external;
 *     3. it exports the documented `setup` entry point;
 *     4. calling setup() registers a Pd class whose name is the class the
 *        object is named after, with a non-zero instance size and at least one
 *        method -- i.e. real upstream code executed, not a file listing.
 *
 *   Tier B, for four externals whose state machines were read line by line in
 *   the upstream sources, the test then instantiates the object through the
 *   creation function Pd itself would call and drives its real methods,
 *   asserting the exact values that come out of the outlets:
 *     positive     float -> float wrapping, bang
 *     cup          float, bang (counter), setbang
 *     doubledelta  float -> delta and delta-of-delta, bang
 *     list_sum     "all" list method (uses t_atom + atom_getfloat), "clear"
 *
 * The Pd API the externals import is provided by the minimal Pure Data runtime
 * shim below.  It is deliberately faithful where behaviour is asserted
 * (atom_getfloat / atom_getfloatarg / outlet_new / outlet_float / outlet_list /
 * gensym / class registration) and inert elsewhere (clocks never fire, no DSP
 * graph is built), and it aborts if an externals' setup() ever reaches a shim
 * entry point the test does not model.
 *
 * The process exits non-zero if any check fails, so `conan create` fails the
 * package.
 */
#include "m_pd.h"

/* m_pd.h turns four of the class registration entry points into argument
 * casting macros (class_addfloat(x, y) is literally class_doaddfloat(...)), so
 * the header's own declarations have to be dropped before the shim defines the
 * real functions behind those names.  This mirrors what the externals see: a
 * "float" method arrives at the plugin as a call to class_doaddfloat(). */
#undef class_addbang
#undef class_addfloat
#undef class_addlist
#undef class_addsymbol

#include <dirent.h>
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ------------------------------------------------------------------ *
 * Minimal Pure Data runtime shim
 * ------------------------------------------------------------------ */

/* The externals import s_bang/s_float/s_list/s_signal; m_pd.h declares the
 * whole family EXTERN, and only these four are referenced. */
t_symbol s_float, s_bang, s_list, s_signal;
t_class *garray_class;

#define SHIM_MAX_CLASSES 16
#define SHIM_MAX_METHODS 64
/* Every setup() interns its class name, its selectors and its Pd help symbol
 * (copyarray's is "maxlib/copyarray\x73-help.pd"), and interning is global for
 * the whole run, so the pool has to cover all 43 externals. */
#define SHIM_MAX_SYMBOLS 2048
#define SHIM_MAX_OUTLETS 64
#define SHIM_MAX_EVENTS 256

typedef struct
{
    const char *selector;
    t_method fn;
} shim_method;

typedef struct
{
    t_class *c;
    const char *name;
    size_t binsize;
    t_newmethod newf;
    t_method m_bang;
    t_method m_float;
    t_method m_list;
    t_method m_symbol;
    shim_method meth[SHIM_MAX_METHODS];
    int nmeth;
} shim_class;

typedef struct
{
    const char *kind;
    int outlet;
    double value;
} shim_event;

static shim_class g_reg[SHIM_MAX_CLASSES];
static int g_nreg;

static char g_symbol_names[SHIM_MAX_SYMBOLS][32];
static t_symbol g_symbol_pool[SHIM_MAX_SYMBOLS];
static int g_nsymbol;

static char g_outlet_pool[SHIM_MAX_OUTLETS][8];
static int g_noutlet;

static char g_inlet_pool[SHIM_MAX_OUTLETS][8];
static char g_clock_pool[8][8];
static int g_nclock;

static shim_event g_ev[SHIM_MAX_EVENTS];
static int g_nev;

static int g_post_count;

static int g_checks;
static int g_failures;

#define CHECK(cond, ...)                                                      \
    do {                                                                      \
        g_checks++;                                                           \
        if (cond) { printf("PASS: "); printf(__VA_ARGS__); printf("\n"); }    \
        else { g_failures++; printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); } \
    } while (0)

static void shim_reset(void)
{
    memset(g_reg, 0, sizeof(g_reg));
    g_nreg = 0;
    g_noutlet = 0;
    g_nclock = 0;
    g_nev = 0;
}

static shim_class *shim_lookup(const t_class *c)
{
    int i;
    for (i = 0; i < g_nreg; i++)
        if (g_reg[i].c == c)
            return &g_reg[i];
    return NULL;
}

/* Real t_symbol objects, not bare strings: setup() reads name->s_name straight
 * after class_new(), so the pool entry must be a genuine _symbol whose
 * s_name points at the interned text. */
t_symbol *gensym(const char *s)
{
    int i;
    for (i = 0; i < g_nsymbol; i++)
        if (strcmp(g_symbol_names[i], s) == 0)
            return &g_symbol_pool[i];
    if (g_nsymbol >= SHIM_MAX_SYMBOLS) {
        fprintf(stderr, "shim: gensym pool exhausted (%s)\n", s);
        exit(2);
    }
    strncpy(g_symbol_names[g_nsymbol], s, sizeof(g_symbol_names[0]) - 1);
    g_symbol_names[g_nsymbol][sizeof(g_symbol_names[0]) - 1] = '\0';
    memset(&g_symbol_pool[g_nsymbol], 0, sizeof(g_symbol_pool[0]));
    g_symbol_pool[g_nsymbol].s_name = g_symbol_names[g_nsymbol];
    return &g_symbol_pool[g_nsymbol++];
}

static void shim_record_method(t_class *c, const char *selector, t_method fn)
{
    shim_class *k = shim_lookup(c);
    if (!k || k->nmeth >= SHIM_MAX_METHODS)
        return;
    k->meth[k->nmeth].selector = selector;
    k->meth[k->nmeth].fn = fn;
    k->nmeth++;
}

t_class *class_new(t_symbol *name, t_newmethod newmethod, t_method freemethod,
                   size_t size, int flags, t_atomtype arg1, ...)
{
    static char dummy[SHIM_MAX_CLASSES][64];
    t_class *c;
    (void)freemethod; (void)flags; (void)arg1;
    if (g_nreg >= SHIM_MAX_CLASSES) {
        fprintf(stderr, "shim: class pool exhausted\n");
        exit(2);
    }
    c = (t_class *)dummy[g_nreg];
    memset(c, 0, sizeof(dummy[0]));
    g_reg[g_nreg].c = c;
    g_reg[g_nreg].name = name->s_name;
    g_reg[g_nreg].binsize = size;
    g_reg[g_nreg].newf = newmethod;
    g_nreg++;
    return c;
}

void class_addmethod(t_class *c, t_method fn, t_symbol *sel, t_atomtype arg1, ...)
{
    (void)arg1;
    shim_record_method(c, sel->s_name, fn);
}

void class_addbang(t_class *c, t_method fn)
{
    shim_class *k = shim_lookup(c);
    shim_record_method(c, "bang", fn);
    if (k) k->m_bang = fn;
}

/* class_addfloat() in the externals is a macro over this function, so this is
 * where a Pd float method actually shows up. */
void class_doaddfloat(t_class *c, t_method fn)
{
    shim_class *k = shim_lookup(c);
    shim_record_method(c, "float", fn);
    if (k) k->m_float = fn;
}

void class_addlist(t_class *c, t_method fn)
{
    shim_class *k = shim_lookup(c);
    shim_record_method(c, "list", fn);
    if (k) k->m_list = fn;
}

void class_addsymbol(t_class *c, t_method fn)
{
    shim_class *k = shim_lookup(c);
    shim_record_method(c, "symbol", fn);
    if (k) k->m_symbol = fn;
}

void class_domainsignalin(t_class *c, int onset) { (void)c; (void)onset; }
void class_sethelpsymbol(t_class *c, t_symbol *s) { (void)c; (void)s; }
void dsp_add(t_perfroutine f, int n, ...) { (void)f; (void)n; }

t_pd *pd_new(t_class *cls)
{
    shim_class *k = shim_lookup(cls);
    size_t size = k ? k->binsize : 256;
    if (size == 0)
        size = 256;
    return (t_pd *)calloc(1, size);
}

t_pd *pd_findbyclass(t_symbol *s, const t_class *c) { (void)s; (void)c; return NULL; }

t_outlet *outlet_new(t_object *owner, t_symbol *s)
{
    (void)owner; (void)s;
    if (g_noutlet >= SHIM_MAX_OUTLETS) {
        fprintf(stderr, "shim: outlet pool exhausted\n");
        exit(2);
    }
    return (t_outlet *)g_outlet_pool[g_noutlet++];
}

t_inlet *inlet_new(t_object *owner, t_pd *dest, t_symbol *s1, t_symbol *s2)
{
    static int n = 0;
    (void)owner; (void)dest; (void)s1; (void)s2;
    if (n >= SHIM_MAX_OUTLETS)
        n = 0;
    return (t_inlet *)g_inlet_pool[n++];
}

/* Pd's floatinlet_new only points the inlet at *fp; it does not overwrite the
 * value, and upstream list_sum relies on that (it assigns maxlen/wrap first and
 * lets the inlet redirect writes), so the shim leaves *fp alone. */
t_inlet *floatinlet_new(t_object *owner, t_float *fp) { (void)owner; (void)fp; return inlet_new(owner, NULL, NULL, NULL); }
t_inlet *signalinlet_new(t_object *owner, t_float f) { (void)owner; (void)f; return inlet_new(owner, NULL, NULL, NULL); }
t_inlet *symbolinlet_new(t_object *owner, t_symbol **sp) { (void)owner; (void)sp; return inlet_new(owner, NULL, NULL, NULL); }

static int shim_outlet_id(const t_outlet *x)
{
    int i;
    for (i = 0; i < g_noutlet; i++)
        if ((const t_outlet *)g_outlet_pool[i] == x)
            return i;
    return -1;
}

static void shim_event_add(const char *kind, const t_outlet *x, double value)
{
    if (g_nev >= SHIM_MAX_EVENTS)
        return;
    g_ev[g_nev].kind = kind;
    g_ev[g_nev].outlet = shim_outlet_id(x);
    g_ev[g_nev].value = value;
    g_nev++;
}

void outlet_bang(t_outlet *x) { shim_event_add("bang", x, 0.0); }
void outlet_float(t_outlet *x, t_float f) { shim_event_add("float", x, (double)f); }
void outlet_list(t_outlet *x, t_symbol *s, int argc, t_atom *argv)
{
    (void)s; (void)argv;
    shim_event_add("list", x, (double)argc);
}
void outlet_pointer(t_outlet *x, t_gpointer *gp) { (void)x; (void)gp; }
void outlet_set(t_outlet *x, t_gpointer *gp) { (void)x; (void)gp; }

/* Clocks are created but never fire: firing them would re-enter the externals
 * from the middle of a test with no Pd clock queue to schedule them on. */
t_clock *clock_new(void *owner, t_method fn)
{
    (void)owner; (void)fn;
    if (g_nclock >= (int)(sizeof(g_clock_pool) / sizeof(g_clock_pool[0])))
        g_nclock = 0;
    return (t_clock *)g_clock_pool[g_nclock++];
}
void clock_delay(t_clock *x, double delaytime) { (void)x; (void)delaytime; }
void clock_free(t_clock *x) { (void)x; }

int garray_getfloatwords(t_garray *x, int *size, t_word **vec)
{
    (void)x;
    if (size) *size = 0;
    if (vec) *vec = NULL;
    return 0;
}
void garray_redraw(t_garray *x) { (void)x; }

t_float sys_getsr(void) { return (t_float)44100.0f; }

/* Faithful: these three decide what the externals actually compute. */
t_float atom_getfloat(const t_atom *a)
{
    return (a->a_type == A_FLOAT) ? a->a_w.w_float : (t_float)0.0f;
}

t_float atom_getfloatarg(int which, int argc, const t_atom *argv)
{
    return (which >= 0 && which < argc && argv[which].a_type == A_FLOAT)
               ? argv[which].a_w.w_float
               : (t_float)0.0f;
}

t_symbol *atom_getsymbolarg(int which, int argc, const t_atom *argv)
{
    return (which >= 0 && which < argc && argv[which].a_type == A_SYMBOL)
               ? argv[which].a_w.w_symbol
               : &s_float;
}

void *getbytes(size_t nbytes) { return calloc(1, nbytes ? nbytes : 1); }
void freebytes(void *x, size_t nbytes) { (void)nbytes; free(x); }
void *copybytes(const void *src, size_t nbytes)
{
    void *dst = calloc(1, nbytes ? nbytes : 1);
    if (dst && src)
        memcpy(dst, src, nbytes);
    return dst;
}

void post(const char *fmt, ...) { (void)fmt; g_post_count++; }
void pd_error(const void *object, const char *fmt, ...) { (void)object; (void)fmt; g_post_count++; }
void logpost(const void *object, int level, const char *fmt, ...)
{
    (void)object; (void)level; (void)fmt; g_post_count++;
}

/* ------------------------------------------------------------------ *
 * Test driver
 * ------------------------------------------------------------------ */

#define EM_AARCH64 183

/* The symbol Pd looks up in an external, reproduced verbatim from Pd's own
 * loader (pure-data 0.54-1 src/s_loader.c, sys_do_load_lib): alphanumerics and
 * '_' pass through, a trailing '~' becomes "_tilde", anything else is
 * hex-munged and the whole name is then prefixed with "setup_" instead of
 * getting the "_setup" suffix.  Pd tries this name first and only falls back to
 * a plain "setup".  Getting this wrong would mean testing a symbol Pd never
 * calls, so it is implemented rather than assumed. */
static void pd_setup_symbol(const char *classname, char *out, size_t outsz)
{
    char munged[512];
    size_t i = 0;
    const char *p;
    int hexmunge = 0;

    for (p = classname; i < sizeof(munged) - 8 && *p; p++) {
        char c = *p;
        if ((c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') ||
            (c >= 'a' && c <= 'z') || c == '_') {
            munged[i++] = c;
        } else if (c == '~' && p[1] == '\0') {
            memcpy(munged + i, "_tilde", 6);
            i += 6;
        } else {
            snprintf(munged + i, sizeof(munged) - i, "0x%02x", (unsigned char)c);
            i += strlen(munged + i);
            hexmunge = 1;
        }
    }
    munged[i] = '\0';
    if (hexmunge)
        snprintf(out, outsz, "setup_%s", munged);
    else
        snprintf(out, outsz, "%s_setup", munged);
}

static int is_aarch64_shared_object(const char *path)
{
    unsigned char head[20];
    FILE *f = fopen(path, "rb");
    size_t got;
    unsigned machine;
    if (!f)
        return 0;
    got = fread(head, 1, sizeof(head), f);
    fclose(f);
    if (got < sizeof(head))
        return 0;
    if (memcmp(head, "\177ELF", 4) != 0)
        return 0;
    if (head[4] != 2 /* ELFCLASS64 */ || head[5] != 1 /* ELFDATA2LSB */)
        return 0;
    if (head[16] != 3 /* ET_DYN */)
        return 0;
    machine = (unsigned)head[18] | ((unsigned)head[19] << 8);
    return machine == EM_AARCH64;
}

static shim_class *load_and_setup(const char *path, const char *expect_class)
{
    void *handle;
    void (*setup)(void);
    char symname[600];
    int i;
    shim_class *found = NULL;

    handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        CHECK(0, "dlopen %s (%s)", path, dlerror());
        return NULL;
    }
    pd_setup_symbol(expect_class, symname, sizeof(symname));
    dlerror();
    *(void **)(&setup) = dlsym(handle, symname);
    if (!setup)
        *(void **)(&setup) = dlsym(handle, "setup");
    CHECK(setup != NULL, "%s exports '%s', the entry point Pd calls", expect_class, symname);
    if (!setup)
        return NULL;
    shim_reset();
    setup();
    for (i = 0; i < g_nreg; i++)
        if (strcmp(g_reg[i].name, expect_class) == 0)
            found = &g_reg[i];
    CHECK(found != NULL, "%s setup() registers the Pd class '%s'", expect_class, expect_class);
    if (!found)
        return NULL;
    CHECK(found->binsize > 0, "%s declares a non-zero Pd instance size (%lu bytes)",
          expect_class, (unsigned long)found->binsize);
    CHECK(found->nmeth >= 1, "%s registers at least one Pd method (%d)", expect_class, found->nmeth);
    return found;
}

static t_method find_selector(const shim_class *k, const char *selector)
{
    int i;
    for (i = 0; i < k->nmeth; i++)
        if (strcmp(k->meth[i].selector, selector) == 0)
            return k->meth[i].fn;
    return NULL;
}

static void expect_event(int index, const char *kind, int outlet, double value)
{
    if (index >= g_nev) {
        CHECK(0, "event %d: expected %s, but only %d events were emitted", index, kind, g_nev);
        return;
    }
    CHECK(strcmp(g_ev[index].kind, kind) == 0 && g_ev[index].outlet == outlet &&
              (value == value ? (g_ev[index].value - value < 1e-9 && value - g_ev[index].value < 1e-9)
                              : (g_ev[index].value != g_ev[index].value)),
          "event %d is %s on outlet %d with value %g (actual: %s on outlet %d with value %g)",
          index, kind, outlet, value,
          g_ev[index].kind, g_ev[index].outlet, g_ev[index].value);
}

static void check_no_event(const char *what)
{
    CHECK(g_nev == 0, "%s emits nothing on the outlets", what);
}

/* ---- positive: float wrapping ------------------------------------- */
static void test_positive(const char *dir)
{
    char path[4096];
    shim_class *k;
    void *obj;
    snprintf(path, sizeof(path), "%s/positive.pd_linux", dir);
    k = load_and_setup(path, "positive");
    if (!k || !k->newf || !k->m_float || !k->m_bang)
        return;
    obj = ((void *(*)(void *, t_floatarg))k->newf)(NULL, 0.0);
    CHECK(obj != NULL, "positive object instantiated through its Pd creation function");

    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(obj, 3.0);
    expect_event(0, "float", 0, 3.0);

    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(obj, -5.0);
    expect_event(0, "float", 0, 1.0); /* (int)-5 * -1 + 1 == 6; -5 + 6 == 1 */

    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(obj, -1.0);
    expect_event(0, "float", 0, 1.0); /* (int)-1 * -1 + 1 == 2; -1 + 2 == 1 */

    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(obj, 2.5);
    expect_event(0, "float", 0, 2.5);

    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_event(0, "float", 0, 2.5); /* bang repeats the stored value */
    free(obj);
}

/* ---- cup: bang counter -------------------------------------------- */
static void test_cup(const char *dir)
{
    char path[4096];
    shim_class *k;
    t_method setbang;
    void *obj;
    snprintf(path, sizeof(path), "%s/cup.pd_linux", dir);
    k = load_and_setup(path, "cup");
    if (!k || !k->newf || !k->m_float || !k->m_bang)
        return;
    obj = ((void *(*)(void *, t_floatarg))k->newf)(NULL, 0.0);
    CHECK(obj != NULL, "cup object instantiated through its Pd creation function");

    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(obj, 10.0);
    check_no_event("cup float 10 (it only sets the counter)");

    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_event(0, "float", 0, 10.0);
    ((void (*)(void *))k->m_bang)(obj);
    expect_event(1, "float", 0, 11.0);
    CHECK(g_nev == 2, "cup bang outputs the counter and then increments it (%d events)", g_nev);

    setbang = find_selector(k, "setbang");
    CHECK(setbang != NULL, "cup registers the setbang message");
    if (setbang) {
        g_nev = 0;
        ((void (*)(void *, t_floatarg))setbang)(obj, 5.0);
        expect_event(0, "float", 0, 5.0);
        CHECK(g_nev == 1, "cup setbang outputs the value it sets (%d events)", g_nev);
    }
    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_event(0, "float", 0, 6.0);
    free(obj);
}

/* ---- doubledelta: first and second difference --------------------- */
static void test_doubledelta(const char *dir)
{
    char path[4096];
    shim_class *k;
    void *obj;
    snprintf(path, sizeof(path), "%s/doubledelta.pd_linux", dir);
    k = load_and_setup(path, "doubledelta");
    if (!k || !k->newf || !k->m_float || !k->m_bang)
        return;
    obj = ((void *(*)(void *, t_floatarg))k->newf)(NULL, 0.0);
    CHECK(obj != NULL, "doubledelta object instantiated through its Pd creation function");

    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(obj, 10.0);
    expect_event(0, "float", 1, 10.0); /* doubledelta outlet: 10 - 0 */
    expect_event(1, "float", 0, 10.0);  /* delta outlet: 10 - 0 */

    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(obj, 13.0);
    expect_event(0, "float", 1, -7.0); /* doubledelta: 3 - 10 */
    expect_event(1, "float", 0, 3.0);  /* delta: 13 - 10 */

    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_event(0, "float", 1, -7.0);
    expect_event(1, "float", 0, 3.0);
    free(obj);
}

/* ---- list_sum: t_atom list arithmetic ------------------------------ */
static void test_list_sum(const char *dir)
{
    char path[4096];
    shim_class *k;
    t_method m_all, m_clear;
    void *obj;
    t_atom argv[4];
    int i;
    static const double first[4] = {1.0, 2.0, 3.0, 4.0};
    static const double second[2] = {10.0, 20.0};
    static const double third[2] = {5.0, 6.0};

    snprintf(path, sizeof(path), "%s/list_sum.pd_linux", dir);
    k = load_and_setup(path, "list_sum");
    if (!k || !k->newf)
        return;
    obj = ((void *(*)(void *, int, t_atom *))k->newf)(NULL, 0, NULL);
    CHECK(obj != NULL, "list_sum object instantiated through its Pd creation function");

    m_all = find_selector(k, "all");
    m_clear = find_selector(k, "clear");
    CHECK(m_all != NULL, "list_sum registers the 'all' list method");
    CHECK(m_clear != NULL, "list_sum registers the 'clear' method");
    if (!m_all || !m_clear)
        return;

    for (i = 0; i < 4; i++) SETFLOAT(&argv[i], first[i]);
    g_nev = 0;
    ((void (*)(void *, void *, int, t_atom *))m_all)(obj, NULL, 4, argv);
    expect_event(0, "float", 1, 4.0); /* length outlet */
    expect_event(1, "float", 0, 10.0); /* sum outlet */

    for (i = 0; i < 2; i++) SETFLOAT(&argv[i], second[i]);
    g_nev = 0;
    ((void (*)(void *, void *, int, t_atom *))m_all)(obj, NULL, 2, argv);
    expect_event(0, "float", 1, 2.0);
    expect_event(1, "float", 0, 30.0);

    g_nev = 0;
    ((void (*)(void *, t_floatarg))m_clear)(obj, 0.0);
    check_no_event("list_sum clear");

    for (i = 0; i < 2; i++) SETFLOAT(&argv[i], third[i]);
    g_nev = 0;
    ((void (*)(void *, void *, int, t_atom *))m_all)(obj, NULL, 2, argv);
    expect_event(0, "float", 1, 2.0);
    expect_event(1, "float", 0, 11.0); /* clear really zeroed the stored list */
    free(obj);
}

/* ---- packaging invariants ----------------------------------------- */
static int file_has(const char *path, const char *needle)
{
    char buf[8192];
    size_t n;
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = '\0';
    return strstr(buf, needle) != NULL;
}

/* Names of the *.pd_linux files in `dir`, at most `max` of them. */
static int list_externals(const char *dir, char **out, int max)
{
    DIR *d = opendir(dir);
    struct dirent *entry;
    int n = 0;
    if (!d)
        return -1;
    while ((entry = readdir(d)) != NULL && n < max) {
        size_t len = strlen(entry->d_name);
        if (len > 9 && strcmp(entry->d_name + len - 9, ".pd_linux") == 0)
            out[n++] = strdup(entry->d_name);
    }
    closedir(d);
    return n;
}

int main(int argc, char **argv)
{
    const char *dir;
    char path[4096];
    char cls[256];
    char *names[256];
    int count, i, loaded;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <externals-dir>\n", argv[0]);
        return 2;
    }
    /* Unbuffered: if an external crashes the loader, the checks printed before
     * it must already be in the log rather than lost in a stdio buffer. */
    setvbuf(stdout, NULL, _IONBF, 0);
    dir = argv[1];

    /* Tier A: every packaged external must be a loadable aarch64 Pd class. */
    count = list_externals(dir, names, 256);
    if (count < 0) {
        fprintf(stderr, "cannot open externals dir %s\n", dir);
        return 2;
    }
    CHECK(count == 43, "pd-ekext 0.3.1 packages 43 externals (found %d)", count);

    loaded = 0;
    for (i = 0; i < count; i++) {
        const char *name = names[i];
        size_t len = strlen(name);
        snprintf(path, sizeof(path), "%s/%s", dir, name);
        snprintf(cls, sizeof(cls), "%.*s", (int)(len - 9), name);
        CHECK(is_aarch64_shared_object(path),
              "%s is a 64-bit little-endian aarch64 ELF shared object", cls);
        if (load_and_setup(path, cls) != NULL)
            loaded++;
    }
    CHECK(loaded == count,
          "all %d externals dlopen() and register their Pd class (%d did)", count, loaded);

    /* Tier B: drive four externals' real code through the Pd API. */
    test_positive(dir);
    test_cup(dir);
    test_doubledelta(dir);
    test_list_sum(dir);

    /* The library must ship what its -meta patch and the Pd help system need. */
    snprintf(path, sizeof(path), "%s/ekext-meta.pd", dir);
    CHECK(file_has(path, "NAME ekext"), "the ekext-meta.pd library marker is installed");
    snprintf(path, sizeof(path), "%s/bmt~-help.pd", dir);
    CHECK(file_has(path, "canvas"), "help patches are installed next to the externals");
    snprintf(path, sizeof(path), "%s/README.txt", dir);
    CHECK(file_has(path, "ekext"), "README.txt is installed");
    snprintf(path, sizeof(path), "%s/LICENSE", dir);
    CHECK(file_has(path, "Redistribution and use"), "the BSD licence text is installed");

    printf("PD_EKEXT_TEST post() calls observed: %d\n", g_post_count);
    printf("PD_EKEXT_TEST checks: %d, failures: %d\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}