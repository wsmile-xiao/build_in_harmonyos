/*
 * test_package/pd_cxc_test.c -- functional consumer test for pd-cxc 0.5.2.
 *
 * pd-cxc ships no public C API and no command line program: it installs 26
 * Pure Data externals, one ELF shared object per class
 * (lib/pd-externals/cxc/<class>.pd_linux), which Pd dlopen()s the first time a
 * patch instantiates the object.  A Pd external links against nothing -- Pd is
 * linked -rdynamic and the plugin's Pd symbols are resolved out of the running
 * Pd image at load time -- so there is nothing to link against and no CLI to
 * execute.
 *
 * This test therefore reproduces exactly what Pd does at load time:
 *
 *   Tier A, for all 26 packaged externals:
 *     1. the file is a 64-bit little-endian aarch64 ELF shared object;
 *     2. it dlopen()s with RTLD_NOW|RTLD_LOCAL -- RTLD_NOW proves every Pd
 *        symbol it imports is satisfiable from the loading image, RTLD_LOCAL
 *        proves it is satisfied by Pd alone and not by another external;
 *     3. it exports the documented `setup` entry point;
 *     4. calling setup() registers a Pd class whose name is the class the
 *        object is named after, with a non-zero instance size and at least one
 *        method -- i.e. real upstream code executed, not a file listing.
 *
 *   Tier B, for five externals whose state machines were read line by line in
 *     the upstream sources, the test then instantiates the object through the
 *     creation function Pd itself would call and drives its real methods,
 *     asserting the exact values that come out of the outlets:
 *       hex2dec     float/symbol in -> symbol out, sprintf'd with the creation
 *                   argument (default "file.%d")
 *       cxc_prepend anything/list in -> selector-prefixed list out, plus the
 *                   `set` message that changes the prefix
 *       cxc_split   symbol in -> list out, split on a one-character splitter
 *                   (numeric fields become floats, the rest stay symbols)
 *       cxc_counter bang count up/down, wrap, the wrap bang, reset and clear
 *       ENV         RAND_MAX, a getenv of a variable this test sets, getenv of
 *                   an unset variable
 *
 * The Pd API the externals import is provided by the minimal Pure Data runtime
 * shim below.  It is deliberately faithful where behaviour is asserted
 * (gensym / class registration / outlet_* / atom_getfloat / atom_getsymbol /
 * atom_string / the real libc getenv+setenv) and inert elsewhere (clocks never
 * fire, no DSP graph is built, no garray is ever handed out), so nothing
 * re-enters an external from the middle of an assertion.
 *
 * The process exits non-zero if any check fails, so `conan create` fails the
 * package.
 */
#include "m_pd.h"

/* m_pd.h turns several of the class registration entry points into argument
 * casting macros (class_addfloat(x, y) is literally class_doaddfloat(...)), so
 * the header's own declarations have to be dropped before the shim defines the
 * real functions behind those names.  This mirrors what the externals see: a
 * "float" method arrives at the plugin as a call to class_doaddfloat(). */
#undef class_addbang
#undef class_addfloat
#undef class_addlist
#undef class_addsymbol
#undef class_addanything
#undef class_addpointer

#include <dirent.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ------------------------------------------------------------------ *
 * Minimal Pure Data runtime shim
 * ------------------------------------------------------------------ */

/* The externals import the whole selector family; m_pd.h declares it EXTERN.
 * Real Pd interns these with exactly these names, and several upstream methods
 * pass &s_list / &s_symbol on to outlet_list()/outlet_anything(), so the names
 * have to be right or every recorded selector comes out empty.  s_ is Pd's
 * "null symbol": its s_name is NULL, which upstream checks for in
 * cxc_prepend_new()/cxc_split_new() ("if (s != &s_)"). */
t_symbol s_float = {"float"};
t_symbol s_bang = {"bang"};
t_symbol s_list = {"list"};
t_symbol s_symbol = {"symbol"};
t_symbol s_signal = {"signal"};
t_symbol s_anything = {"list"};
t_symbol s_pointer = {"pointer"};
t_symbol s_;
t_class *garray_class;

#define SHIM_MAX_CLASSES 16
#define SHIM_MAX_METHODS 64
/* Every setup() interns its class name, its selectors and hex2dec's
 * sprintf()ed results, so the pool is sized for the whole run, not per object. */
#define SHIM_MAX_SYMBOLS 4096
#define SHIM_MAX_OUTLETS 64
#define SHIM_MAX_EVENTS 256
#define SHIM_MAX_ATOMS 8
#define SHIM_SYM_LEN 64

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
    t_method m_anything;
    shim_method meth[SHIM_MAX_METHODS];
    int nmeth;
} shim_class;

/* One emitted message, as Pd would hand it to the patch: selector plus atoms. */
typedef struct
{
    int is_float;
    double f;
    char sym[SHIM_SYM_LEN];
} shim_atom;

typedef struct
{
    const char *kind; /* bang | float | symbol | list | anything */
    int outlet;
    char sel[SHIM_SYM_LEN];
    double f;
    int argc;
    shim_atom at[SHIM_MAX_ATOMS];
} shim_event;

static shim_class g_reg[SHIM_MAX_CLASSES];
static int g_nreg;

static char g_symbol_names[SHIM_MAX_SYMBOLS][SHIM_SYM_LEN];
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
static int g_fopen_count;

static int g_checks;
static int g_failures;

/* Measured on the packaged payload with the real 26 externals in place:
 * `PD_CXC_TEST checks: 254`.  main() refuses to report success on fewer. */
#define PD_CXC_TEST_MIN_CHECKS 254

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

/* Pd numbers an object's outlets by creation order -- m_obj.c's outlet_new()
 * chains them with o_next starting at owner->ob_outlet -- so the shim's pool
 * index is the outlet number Pd would report.  Calling this before every
 * instantiation gives each object its own numbering from 0, exactly as a fresh
 * object gets, instead of letting the second hex2dec in a test come out as
 * "outlet 1". */
static void shim_new_object(void)
{
    g_noutlet = 0;
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
 * after class_new(), and cxc_prepend_new()/cxc_split_new() compare the
 * creation argument against &s_, so the pool entry must be a genuine _symbol
 * whose s_name points at the interned text. */
t_symbol *gensym(const char *s)
{
    int i;
    if (s == NULL)
        return &s_;
    for (i = 0; i < g_nsymbol; i++)
        if (strcmp(g_symbol_names[i], s) == 0)
            return &g_symbol_pool[i];
    if (g_nsymbol >= SHIM_MAX_SYMBOLS) {
        fprintf(stderr, "shim: gensym pool exhausted (%s)\n", s);
        exit(2);
    }
    strncpy(g_symbol_names[g_nsymbol], s, SHIM_SYM_LEN - 1);
    g_symbol_names[g_nsymbol][SHIM_SYM_LEN - 1] = '\0';
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

void class_addanything(t_class *c, t_method fn)
{
    shim_class *k = shim_lookup(c);
    shim_record_method(c, "anything", fn);
    if (k) k->m_anything = fn;
}

/* cxc registers no pointer methods and no abstract creators, but the imports
 * are in the objects, so the shim has to answer them. */
void class_addpointer(t_class *c, t_method fn) { shim_record_method(c, "pointer", fn); }
void class_addcreator(t_newmethod creator, t_symbol *s, t_atomtype type1, ...)
{
    (void)creator; (void)s; (void)type1;
}
void class_sethelpsymbol(t_class *c, t_symbol *s) { (void)c; (void)s; }

/* No DSP graph is built: mean~/reson~/delta~ register their perform routines
 * here, and a build gate must not start a signal thread. */
void dsp_add(t_perfroutine f, int n, ...) { (void)f; (void)n; }
void nullfn(void) { }

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
    t_outlet *u;
    (void)s;
    if (g_noutlet >= SHIM_MAX_OUTLETS) {
        fprintf(stderr, "shim: outlet pool exhausted\n");
        exit(2);
    }
    u = (t_outlet *)g_outlet_pool[g_noutlet++];
    /* Pd's outlet_new (m_obj.c) makes the first outlet reachable as
     * owner->ob_outlet, which is how the externals that discard the return
     * value -- hex2dec_new, cxc_split_new, ENV_new -- still reach their outlet
     * later as x->x_obj.ob_outlet.  Without this every such message came out
     * with outlet id -1.  Later outlets are chained by the object itself
     * (cxc_counter stores them in t_out1/t_out2), and the pool order matches
     * Pd's creation order, so the indices line up. */
    if (owner && !owner->ob_outlet)
        owner->ob_outlet = u;
    return u;
}

t_inlet *inlet_new(t_object *owner, t_pd *dest, t_symbol *s1, t_symbol *s2)
{
    static int n = 0;
    (void)owner; (void)dest; (void)s1; (void)s2;
    if (n >= SHIM_MAX_OUTLETS)
        n = 0;
    return (t_inlet *)g_inlet_pool[n++];
}

t_inlet *floatinlet_new(t_object *owner, t_float *fp) { (void)owner; (void)fp; return inlet_new(owner, NULL, NULL, NULL); }

static int shim_outlet_id(const t_outlet *x)
{
    int i;
    for (i = 0; i < g_noutlet; i++)
        if ((const t_outlet *)g_outlet_pool[i] == x)
            return i;
    return -1;
}

static shim_event *shim_event_new(const char *kind, const t_outlet *x)
{
    shim_event *e;
    if (g_nev >= SHIM_MAX_EVENTS)
        return NULL;
    e = &g_ev[g_nev++];
    memset(e, 0, sizeof(*e));
    e->kind = kind;
    e->outlet = shim_outlet_id(x);
    return e;
}

static void shim_capture_atoms(shim_event *e, int argc, t_atom *argv)
{
    int i, n = argc < SHIM_MAX_ATOMS ? argc : SHIM_MAX_ATOMS;
    e->argc = argc;
    for (i = 0; i < n; i++) {
        if (argv[i].a_type == A_FLOAT) {
            e->at[i].is_float = 1;
            e->at[i].f = (double)argv[i].a_w.w_float;
        } else {
            e->at[i].is_float = 0;
            if (argv[i].a_type == A_SYMBOL && argv[i].a_w.w_symbol && argv[i].a_w.w_symbol->s_name)
                snprintf(e->at[i].sym, SHIM_SYM_LEN, "%s", argv[i].a_w.w_symbol->s_name);
        }
    }
}

void outlet_bang(t_outlet *x) { shim_event_new("bang", x); }
void outlet_float(t_outlet *x, t_float f)
{
    shim_event *e = shim_event_new("float", x);
    if (e) e->f = (double)f;
}
void outlet_symbol(t_outlet *x, t_symbol *s)
{
    shim_event *e = shim_event_new("symbol", x);
    if (e && s && s->s_name)
        snprintf(e->sel, SHIM_SYM_LEN, "%s", s->s_name);
}
void outlet_list(t_outlet *x, t_symbol *s, int argc, t_atom *argv)
{
    shim_event *e = shim_event_new("list", x);
    if (!e)
        return;
    if (s && s->s_name)
        snprintf(e->sel, SHIM_SYM_LEN, "%s", s->s_name);
    shim_capture_atoms(e, argc, argv);
}
void outlet_anything(t_outlet *x, t_symbol *s, int argc, t_atom *argv)
{
    shim_event *e = shim_event_new("anything", x);
    if (!e)
        return;
    if (s && s->s_name)
        snprintf(e->sel, SHIM_SYM_LEN, "%s", s->s_name);
    shim_capture_atoms(e, argc, argv);
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
void clock_unset(t_clock *x) { (void)x; }
double clock_getlogicaltime(void) { return 0.0; }
double clock_getsystime(void) { return 0.0; }
double clock_getsystimeafter(double delaytime) { (void)delaytime; return 0.0; }
double clock_gettimesince(double prevsystime) { (void)prevsystime; return 0.0; }

/* No garray is ever handed to an external; the shim only has to answer the
 * imports ascseq/ascwave make. */
int garray_getfloatwords(t_garray *x, int *size, t_word **vec)
{
    (void)x;
    if (size) *size = 0;
    if (vec) *vec = NULL;
    return 0;
}
int garray_getfloatarray(t_garray *x, int *size, t_float **vec)
{
    (void)x;
    if (size) *size = 0;
    if (vec) *vec = NULL;
    return 0;
}
void garray_redraw(t_garray *x) { (void)x; }
void garray_usedindsp(t_garray *x) { (void)x; }

/* Faithful: these decide what the externals actually compute. */
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

t_symbol *atom_getsymbol(const t_atom *a)
{
    return (a->a_type == A_SYMBOL) ? a->a_w.w_symbol : &s_symbol;
}

t_symbol *atom_getsymbolarg(int which, int argc, const t_atom *argv)
{
    return (which >= 0 && which < argc && argv[which].a_type == A_SYMBOL)
               ? argv[which].a_w.w_symbol
               : &s_float;
}

void atom_string(const t_atom *a, char *buf, unsigned int bufsize)
{
    if (a->a_type == A_FLOAT)
        snprintf(buf, bufsize, "%g", (double)a->a_w.w_float);
    else if (a->a_type == A_SYMBOL && a->a_w.w_symbol && a->a_w.w_symbol->s_name)
        snprintf(buf, bufsize, "%s", a->a_w.w_symbol->s_name);
    else
        snprintf(buf, bufsize, "%s", "");
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

/* ixprint reads a file; the shim forwards to the real fopen and counts the
 * calls so the log shows the import really was reached. */
FILE *sys_fopen(const char *filename, const char *mode)
{
    g_fopen_count++;
    return fopen(filename, mode);
}

void post(const char *fmt, ...) { (void)fmt; g_post_count++; }
void startpost(const char *fmt, ...) { (void)fmt; }
void postatom(int argc, const t_atom *argv) { (void)argc; (void)argv; }
void endpost(void) { }
/* cxc_counter.c calls error(), which Pd exports; m_pd.h 0.54 does not declare
 * it, so the externals reach it through an implicit declaration and the shim
 * supplies the definition. */
void error(const char *fmt, ...) { (void)fmt; g_post_count++; }
void pd_error(const void *object, const char *fmt, ...) { (void)object; (void)fmt; g_post_count++; }
void logpost(const void *object, int level, const char *fmt, ...)
{
    (void)object; (void)level; (void)fmt; g_post_count++;
}

/* ------------------------------------------------------------------ *
 * Test driver
 * ------------------------------------------------------------------ */

#define EM_AARCH64 183
#define CXC_EXTERNALS 26

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

/* How Pd calls a class's creation function (t_newmethod), which is what decides
 * the shape of this cast in every test below:
 *   class created with no creation args  ->  (*newf)(0)
 *   class created with A_DEFSYM          ->  (*newf)(symbol)   in the FIRST
 *       argument slot -- hex2dec_new()/cxc_prepend_new()/cxc_split_new() all
 *       read their t_symbol * there, so passing NULL would dereference NULL;
 *   class created with A_DEFFLOAT...     ->  (*newf)(f1, f2, ...)
 * Verified by the segfault this comment replaces: calling a 1-argument
 * A_DEFSYM constructor as (*newf)(NULL, sym) crashed in hex2dec_new's
 * `if (!s->s_name)` with a NULL `s`.
 */
typedef void *(*t_new_sym)(t_symbol *);
typedef void *(*t_new_f3)(t_floatarg, t_floatarg, t_floatarg);

/* ---- assertions over the emitted event stream ------------------------
 *
 * expect_message() compares one emitted message against what the upstream
 * source says it must be.  `kinds` is one 'f' or 's' per atom and indexes
 * `floats` and `syms` in parallel, so all three arrays have `argc` entries and
 * only the entries named by `kinds` are read.  On mismatch the whole actual
 * message is printed, so a failure says what really came out.
 */
static void expect_message(int index, const char *kind, int outlet, const char *sel,
                           int argc, const char **kinds, const double *floats,
                           const char **syms)
{
    const shim_event *e;
    int i, ok;

    if (index >= g_nev) {
        CHECK(0, "event %d: expected a %s, but only %d events were emitted",
              index, kind, g_nev);
        return;
    }
    e = &g_ev[index];
    ok = (strcmp(e->kind, kind) == 0) && (e->outlet == outlet);
    if (ok && sel)
        ok = (strcmp(e->sel, sel) == 0);
    if (ok && strcmp(kind, "float") == 0)
        ok = (e->f == floats[0]);
    if (ok && (strcmp(kind, "list") == 0 || strcmp(kind, "anything") == 0)) {
        ok = (e->argc == argc);
        for (i = 0; ok && i < argc && i < SHIM_MAX_ATOMS; i++) {
            if (kinds[i][0] == 'f')
                ok = e->at[i].is_float && e->at[i].f == floats[i];
            else
                ok = !e->at[i].is_float && strcmp(e->at[i].sym, syms[i]) == 0;
        }
    }
    CHECK(ok, "event %d is a %s '%s' with %d atoms on outlet %d", index, kind,
          sel ? sel : "", argc, outlet);
    if (!ok) {
        printf("      actual: kind=%s sel='%s' argc=%d outlet=%d",
               e->kind, e->sel, e->argc, e->outlet);
        if (strcmp(e->kind, "float") == 0)
            printf(" value=%.10g", e->f);
        for (i = 0; i < e->argc && i < SHIM_MAX_ATOMS; i++) {
            if (e->at[i].is_float)
                printf(" [f %.10g]", e->at[i].f);
            else
                printf(" [s %s]", e->at[i].sym);
        }
        printf("\n      wanted: sel='%s' argc=%d outlet=%d atoms:", sel ? sel : "",
               argc, outlet);
        for (i = 0; kinds && i < argc && i < SHIM_MAX_ATOMS; i++) {
            if (kinds[i][0] == 'f')
                printf(" [f %.10g]", floats[i]);
            else
                printf(" [s %s]", syms[i]);
        }
        printf("\n");
    }
}

static void expect_float(int index, int outlet, double value)
{
    static const char *none[] = {NULL};
    expect_message(index, "float", outlet, NULL, 0, NULL, &value, none);
}

static void expect_bang(int index, int outlet)
{
    static const char *none[] = {NULL};
    expect_message(index, "bang", outlet, NULL, 0, NULL, NULL, none);
}

static void expect_symbol(int index, int outlet, const char *name)
{
    static const char *none[] = {NULL};
    expect_message(index, "symbol", outlet, name, 0, NULL, NULL, none);
}

static void expect_count(int index, const char *what, int expected)
{
    CHECK(g_nev == expected, "%s (after %d driven message(s)) emits exactly %d "
          "message(s), got %d", what, index, expected, g_nev);
}

static void expect_nothing(const char *what)
{
    CHECK(g_nev == 0, "%s emits nothing on the outlets", what);
}

/* ---- hex2dec: format-driven symbol output --------------------------- */
static void test_hex2dec(const char *dir)
{
    char path[4096];
    shim_class *k;
    void *def, *hex, *tag;

    snprintf(path, sizeof(path), "%s/hex2dec.pd_linux", dir);
    k = load_and_setup(path, "hex2dec");
    if (!k || !k->newf || !k->m_float || !k->m_symbol)
        return;

    /* No creation argument -> upstream falls back to the "file.%d" format
     * (hex2dec_new: `if (!s->s_name) s = gensym("file.%d")`), which is exactly
     * what Pd passes for a bare [hex2dec] in a patch. */
    shim_new_object();
    def = ((t_new_sym)k->newf)(&s_);
    CHECK(def != NULL, "hex2dec instantiated with no creation argument");
    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(def, 3.0);
    expect_symbol(0, 0, "file.3");
    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(def, 42.0);
    expect_symbol(0, 0, "file.42");
    /* The float method formats an int: 42.9 truncates to 42. */
    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(def, 42.9);
    expect_symbol(0, 0, "file.42");

    /* An explicit creation argument is the printf format.  Each format is used
     * only with the argument type it is defined for, because upstream feeds
     * `(int)f` to the float method and `s->s_name` to the symbol one. */
    shim_new_object();
    hex = ((t_new_sym)k->newf)(gensym("hex:%x"));
    CHECK(hex != NULL, "hex2dec instantiated with the creation format 'hex:%%x'");
    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(hex, 255.0);
    expect_symbol(0, 0, "hex:ff");

    shim_new_object();
    tag = ((t_new_sym)k->newf)(gensym("tag-%s"));
    CHECK(tag != NULL, "hex2dec instantiated with the creation format 'tag-%%s'");
    g_nev = 0;
    ((void (*)(void *, t_symbol *))k->m_symbol)(tag, gensym("z"));
    expect_symbol(0, 0, "tag-z");

    free(def);
    free(hex);
    free(tag);
}

/* ---- cxc_prepend: selector-prefixed lists --------------------------- */
static void test_cxc_prepend(const char *dir)
{
    char path[4096];
    shim_class *k;
    t_method m_set;
    void *obj;
    t_atom argv[2];
    static const double nums[] = {1.0, 2.0};
    /* The "anything" body prepends the incoming selector to the atoms and sends
     * the result with the object's own prefix (x_s) as the selector; the list
     * body is the same without the leading selector atom. */
    static const char *any_default[] = {"foo", NULL, NULL};
    static const char *any_bar[] = {"foo", NULL, NULL};
    static const char *kinds_anything[] = {"s", "f", "f"};
    static const double anything_vals[] = {0.0, 1.0, 2.0};
    static const char *kinds_list[] = {"f", "f"};
    static const double list_vals[] = {1.0, 2.0};

    snprintf(path, sizeof(path), "%s/cxc_prepend.pd_linux", dir);
    k = load_and_setup(path, "cxc_prepend");
    if (!k || !k->newf || !k->m_anything || !k->m_list)
        return;
    m_set = find_selector(k, "set");
    CHECK(m_set != NULL, "cxc_prepend registers the 'set' message");
    if (!m_set)
        return;

    shim_new_object();
    obj = ((t_new_sym)k->newf)(&s_);
    CHECK(obj != NULL, "cxc_prepend instantiated with no creation argument");

    SETFLOAT(&argv[0], nums[0]);
    SETFLOAT(&argv[1], nums[1]);
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))k->m_anything)
        (obj, gensym("foo"), 2, argv);
    expect_message(0, "anything", 0, "cxc_prepend", 3, kinds_anything,
                   anything_vals, any_default);
    expect_count(0, "cxc_prepend anything", 1);

    /* The list body is the same minus the leading selector atom. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))k->m_list)(obj, &s_list, 2, argv);
    expect_message(0, "anything", 0, "cxc_prepend", 2, kinds_list,
                   list_vals, any_default);
    expect_count(0, "cxc_prepend list", 1);

    /* set: change the prefix; the next message carries it. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *))m_set)(obj, gensym("bar"));
    expect_nothing("cxc_prepend set bar");
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))k->m_anything)
        (obj, gensym("foo"), 2, argv);
    expect_message(0, "anything", 0, "bar", 3, kinds_anything,
                   anything_vals, any_bar);
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))k->m_list)(obj, &s_list, 2, argv);
    expect_message(0, "anything", 0, "bar", 2, kinds_list, list_vals, any_bar);
    free(obj);
}

/* ---- cxc_split: one-character splitter ------------------------------ */
static void test_cxc_split(const char *dir)
{
    char path[4096];
    shim_class *k;
    t_method m_set;
    void *obj, *comma;
    /* Default splitter is the symbol "cxc_split", so only its first character
     * 'c' splits (split_anything: `u[0] == x->x_splitter->s_name[0]`). */
    static const char *default_syms[] = {"ab", NULL};
    static const double default_vals[] = {0.0, 0.0};
    static const char *kinds_default[] = {"s", "f"};
    static const char *alpha_syms[] = {"ab", "cd", NULL};
    static const char *kinds_ss[] = {"s", "s"};
    static const char *kinds_ff[] = {"f", "f"};
    static const char *kinds_fff[] = {"f", "f", "f"};
    /* t_float is 32-bit (PD_FLOATSIZE=32), so upstream's (float)atof("3.4") is
     * 3.4000000953674316 -- compare against the same conversion, not 3.4. */
    static const double dot_vals[] = {12.0, (double)(t_float)3.4};
    static const double three_vals[] = {1.0, 2.0, 3.0};
    static const double comma_vals[] = {7.0, 8.0};

    snprintf(path, sizeof(path), "%s/cxc_split.pd_linux", dir);
    k = load_and_setup(path, "cxc_split");
    if (!k || !k->newf || !k->m_anything || !k->m_symbol)
        return;
    m_set = find_selector(k, "set");
    CHECK(m_set != NULL, "cxc_split registers the 'set' message");
    if (!m_set)
        return;

    shim_new_object();
    obj = ((t_new_sym)k->newf)(&s_);
    CHECK(obj != NULL, "cxc_split instantiated with no creation argument");

    /* "ab" is not numeric -> symbol; the empty tail *is* numeric
     * (split_string_isnum("") returns 1) and atof("") is 0.0. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))k->m_anything)
        (obj, gensym("abc"), 0, NULL);
    expect_message(0, "list", 0, "list", 2, kinds_default, default_vals, default_syms);
    expect_count(0, "cxc_split anything 'abc'", 1);

    /* `set` keeps only the first character of its argument as the splitter. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *))m_set)(obj, gensym("/"));
    expect_nothing("cxc_split set /");

    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))k->m_anything)
        (obj, gensym("12./3.4"), 0, NULL);
    expect_message(0, "list", 0, "list", 2, kinds_ff, dot_vals, alpha_syms);

    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))k->m_anything)
        (obj, gensym("ab/cd"), 0, NULL);
    expect_message(0, "list", 0, "list", 2, kinds_ss, default_vals, alpha_syms);

    /* The symbol method forwards to the same body; with argc 0 upstream's
     * uninitialised `t_atom *a` is never dereferenced. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *))k->m_symbol)(obj, gensym("1/2/3"));
    expect_message(0, "list", 0, "list", 3, kinds_fff, three_vals, alpha_syms);
    free(obj);

    /* A creation argument is the splitter itself, not a format. */
    shim_new_object();
    comma = ((t_new_sym)k->newf)(gensym(","));
    CHECK(comma != NULL, "cxc_split instantiated with the splitter ','");
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))k->m_anything)
        (comma, gensym("7,8"), 0, NULL);
    expect_message(0, "list", 0, "list", 2, kinds_ff, comma_vals, alpha_syms);
    free(comma);
}

/* ---- cxc_counter: the count up/down state machine ------------------- */
static void test_cxc_counter(const char *dir)
{
    char path[4096];
    shim_class *k;
    t_method m_reset, m_clear, m_fl1;
    void *obj;
    t_atom argv[1];
    int i;

    snprintf(path, sizeof(path), "%s/cxc_counter.pd_linux", dir);
    k = load_and_setup(path, "cxc_counter");
    if (!k || !k->newf || !k->m_bang)
        return;
    m_reset = find_selector(k, "reset");
    m_clear = find_selector(k, "clear");
    m_fl1 = find_selector(k, "fl1");
    CHECK(m_reset != NULL, "cxc_counter registers 'reset'");
    CHECK(m_clear != NULL, "cxc_counter registers 'clear'");
    CHECK(m_fl1 != NULL, "cxc_counter registers 'fl1' (direction)");
    if (!m_reset || !m_clear || !m_fl1)
        return;

    /* counter_new(0, 0, 0) takes the no-argument branch: c_dir = c_low = 1,
     * c_high = 10, c_current = 0. */
    shim_new_object();
    obj = ((t_new_f3)k->newf)(0.0, 0.0, 0.0);
    CHECK(obj != NULL, "cxc_counter instantiated with no arguments");

    /* Count up from 1 to 9: one float on outlet 0 per bang, no bang yet. */
    for (i = 1; i <= 9; i++) {
        g_nev = 0;
        ((void (*)(void *))k->m_bang)(obj);
        expect_float(0, 0, (double)i);
        expect_count(i, "cxc_counter bang below the high bound", 1);
    }
    /* Reaching the high bound emits the count and then a bang on outlet 1. */
    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_float(0, 0, 10.0);
    expect_bang(1, 1);
    expect_count(0, "cxc_counter bang at the high bound", 2);
    /* ... and the next bang wraps around to the low bound, silently. */
    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_float(0, 0, 1.0);
    expect_count(0, "cxc_counter wrap bang", 1);

    /* reset with no argument restarts at the low bound and reports it. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))m_reset)(obj, &s_list, 0, NULL);
    expect_float(0, 0, 1.0);
    expect_count(0, "cxc_counter reset", 1);

    /* reset <float> sets an explicit current value. */
    SETFLOAT(&argv[0], 7.0);
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))m_reset)(obj, &s_list, 1, argv);
    expect_float(0, 0, 7.0);
    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_float(0, 0, 8.0);

    /* clear is silent and primes the next bang. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))m_clear)(obj, &s_list, 0, NULL);
    expect_nothing("cxc_counter clear");
    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_float(0, 0, 1.0);

    /* fl1 2 switches to counting down; the wrap bang then marks the low bound
     * instead of the high one, and reset restarts from the high bound. */
    g_nev = 0;
    ((void (*)(void *, t_floatarg))m_fl1)(obj, 2.0);
    expect_nothing("cxc_counter fl1 2");
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))m_reset)(obj, &s_list, 0, NULL);
    expect_float(0, 0, 10.0);
    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_float(0, 0, 9.0);
    g_nev = 0;
    ((void (*)(void *, t_symbol *, int, t_atom *))m_reset)(obj, &s_list, 0, NULL);
    for (i = 9; i >= 2; i--) {
        g_nev = 0;
        ((void (*)(void *))k->m_bang)(obj);
        expect_float(0, 0, (double)i);
        expect_count(i, "cxc_counter bang while counting down", 1);
    }
    /* Landing exactly on the low bound is what raises the bang when counting
     * down (case 2 of counter_bang: `else if (c_current == c_low)`). */
    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_float(0, 0, 1.0);
    expect_bang(1, 1);
    expect_count(0, "cxc_counter bang reaching the low bound while counting down", 2);
    /* One bang further steps below the low bound, which wraps to the high
     * bound silently (the first branch of case 2, so no bang). */
    g_nev = 0;
    ((void (*)(void *))k->m_bang)(obj);
    expect_float(0, 0, 10.0);
    expect_count(0, "cxc_counter silent wrap while counting down", 1);
    free(obj);
}

/* ---- ENV: environment variables through the Pd outlet --------------- */
static void test_env(const char *dir)
{
    char path[4096];
    shim_class *k;
    t_method m_rand, m_getenv, m_setenv;
    void *obj;
    double rand_max_val[1];
    static const double unset_val[] = {-1.0};
    static const char *set_syms[] = {"cxc-value", NULL};
    static const char *kinds_f[] = {"f"};
    static const char *kinds_s[] = {"s"};

    snprintf(path, sizeof(path), "%s/ENV.pd_linux", dir);
    k = load_and_setup(path, "ENV");
    if (!k || !k->newf || !k->m_float)
        return;
    m_rand = find_selector(k, "RAND_MAX");
    m_getenv = find_selector(k, "getenv");
    m_setenv = find_selector(k, "setenv");
    CHECK(m_rand != NULL, "ENV registers 'RAND_MAX'");
    CHECK(m_getenv != NULL, "ENV registers 'getenv'");
    CHECK(m_setenv != NULL, "ENV registers 'setenv'");
    if (!m_rand || !m_getenv || !m_setenv)
        return;

    shim_new_object();
    obj = ((void *(*)(void *))k->newf)(NULL);
    CHECK(obj != NULL, "ENV instantiated");

    /* ENV_new seeds x_RM = RAND_MAX and RAND_MAX sends it out as a one-atom
     * list.  The expectation is the C library's own RAND_MAX rather than a
     * literal, because t_float is 32-bit and RAND_MAX is an int. */
    rand_max_val[0] = (double)(t_float)RAND_MAX;
    g_nev = 0;
    ((void (*)(void *))m_rand)(obj);
    expect_message(0, "list", 0, "list", 1, kinds_f, rand_max_val, set_syms);
    expect_count(0, "ENV RAND_MAX", 1);

    /* setenv then getenv round-trips through the real process environment. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *, t_symbol *))m_setenv)
        (obj, gensym("CXC_TEST_VAR"), gensym("cxc-value"));
    expect_nothing("ENV setenv (it only posts)");
    g_nev = 0;
    ((void (*)(void *, t_symbol *))m_getenv)(obj, gensym("CXC_TEST_VAR"));
    expect_message(0, "list", 0, "list", 1, kinds_s, unset_val, set_syms);
    expect_count(0, "ENV getenv of a variable it just set", 1);

    /* An unset variable is reported as the float -1. */
    g_nev = 0;
    ((void (*)(void *, t_symbol *))m_getenv)(obj, gensym("CXC_DEFINITELY_UNSET"));
    expect_message(0, "list", 0, "list", 1, kinds_f, unset_val, set_syms);
    expect_count(0, "ENV getenv of an unset variable", 1);

    /* A float into ENV only posts (ENV_float), it has no outlet. */
    g_nev = 0;
    ((void (*)(void *, t_floatarg))k->m_float)(obj, 1.5);
    expect_nothing("ENV float 1.5");
    free(obj);
}

/* ---- packaging invariants ------------------------------------------- */
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
    int count, i, loaded, help_patches;

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
    CHECK(count == CXC_EXTERNALS,
          "pd-cxc 0.5.2 packages %d externals (found %d)", CXC_EXTERNALS, count);

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

    /* Tier B: drive five externals' real code through the Pd API. */
    test_hex2dec(dir);
    test_cxc_prepend(dir);
    test_cxc_split(dir);
    test_cxc_counter(dir);
    test_env(dir);

    /* The library must ship what its -meta patch and the Pd help system need:
     * one help patch per class, plus fader.pd, cxc-meta.pd, README.txt and the
     * GPL text that the Makefile's install-doc / libdir_install rules copy. */
    help_patches = 0;
    for (i = 0; i < count; i++) {
        size_t len = strlen(names[i]);
        snprintf(cls, sizeof(cls), "%.*s", (int)(len - 9), names[i]);
        snprintf(path, sizeof(path), "%s/%s-help.pd", dir, cls);
        if (file_has(path, "#N canvas"))
            help_patches++;
        else
            CHECK(0, "help patch %s-help.pd is installed", cls);
    }
    CHECK(help_patches == count,
          "every external ships its help patch (%d of %d)", help_patches, count);

    snprintf(path, sizeof(path), "%s/fader.pd", dir);
    CHECK(file_has(path, "#N canvas"), "the fader.pd abstraction is installed");
    snprintf(path, sizeof(path), "%s/cxc-meta.pd", dir);
    CHECK(file_has(path, "NAME cxc"), "the cxc-meta.pd library marker is installed");
    CHECK(file_has(path, "VERSION 0.5.2"),
          "cxc-meta.pd declares VERSION 0.5.2, matching the package version");
    snprintf(path, sizeof(path), "%s/README.txt", dir);
    CHECK(file_has(path, "cxc pd eternals library"), "README.txt is installed");
    snprintf(path, sizeof(path), "%s/LICENSE.txt", dir);
    CHECK(file_has(path, "GNU GENERAL PUBLIC LICENSE"), "the GPL v2 text is installed");

    printf("PD_CXC_TEST post()/error() calls observed: %d\n", g_post_count);
    printf("PD_CXC_TEST sys_fopen() calls observed: %d\n", g_fopen_count);
    printf("PD_CXC_TEST interned symbols: %d\n", g_nsymbol);
    printf("PD_CXC_TEST checks: %d, failures: %d\n", g_checks, g_failures);

    /* Lower-bound guard (local AI review 2026-10-12, P2): the suite performs
     * exactly PD_CXC_TEST_MIN_CHECKS checks, so a run that reports fewer has
     * lost assertions somewhere -- by an early return, a loop that no longer
     * iterates, or somebody commenting a block out.  Without this floor such a
     * run would still exit 0 and look like a pass; the structural checks above
     * would catch most cases, but the exit code has to say it too. */
    if (g_checks < PD_CXC_TEST_MIN_CHECKS) {
        printf("FAIL: only %d check(s) ran, the suite defines %d -- "
               "assertions were lost, refusing to report success\n",
               g_checks, PD_CXC_TEST_MIN_CHECKS);
        return 1;
    }
    return g_failures == 0 ? 0 : 1;
}
