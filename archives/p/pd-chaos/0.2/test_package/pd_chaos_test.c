/*
 * test_package/pd_chaos_test.c — functional consumer test for pd-chaos 0.2.
 *
 * pd-chaos ships no linkable library API of its own: it is a set of Pure Data
 * externals that Pd dlopen()s from its search path (`<class>.pd_linux`) and
 * whose Pd symbols are resolved out of Pd's own -rdynamic executable image at
 * load time.  This test drives the packaged artifacts the same way Pd does,
 * without needing a working Pd binary:
 *
 *   1. it embeds a minimal Pure Data runtime shim providing the 14 Pd symbols
 *      the plugins import (gensym, class_new, class_addbang, class_addmethod,
 *      outlet_new/float/list/anything, pd_new, atom_getfloat,
 *      atom_getfloatarg, post and the s_float / s_list selector objects);
 *   2. it dlopen()s every one of the 28 <class>.pd_linux plugins with
 *      RTLD_NOW and calls the real <class>_setup() entry point, then checks
 *      the class got registered with a non-zero instance size, a bang and a
 *      reset method;
 *   3. it dlopen()s libchaos.so and calls the real lyapunov() /
 *      lyapunov_full() exports on two logistic maps (a=1.5 stable -> negative
 *      exponent, a=4 chaotic -> positive exponent) and checks determinism;
 *   4. it instantiates the real `logistic` and `martin` objects through
 *      pd_new(), sends them bangs through their registered bang method and
 *      compares the emitted floats with the closed-form iteration
 *      (4*x*(1-x), and y-sin(x) / a-x for the two-outlet martin map), plus a
 *      `reset` message round trip.
 *
 * Any missing plugin, unresolved symbol, failed registration or wrong number
 * makes the process exit non-zero.
 */
#include "m_pd.h"

#include <dlfcn.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ------------------------------------------------------------------ */
/* Minimal Pure Data runtime                                          */
/* ------------------------------------------------------------------ */

/* m_pd.h only forward-declares these two structures.  Nothing outside this
 * file ever dereferences them -- the plugins just hand the pointers back to
 * us -- so a faithful-enough layout is all that is needed here. */
struct _class {
    t_symbol *c_name;
    t_newmethod c_new;
    t_method c_free;
    int c_classsize;
    int c_flags;
};

struct _outlet {
    t_pd o_pd;
    struct _outlet *next;
    t_symbol *o_symbol;
    int o_type;
};

#define MAX_CLASSES 64
#define MAX_SYMBOLS 256
#define MAX_FLOATS 128

/* m_pd.h redefines class_addbang() as a casting wrapper around itself; the
 * shim below has to provide the real symbol, so drop the macro (the plain
 * prototype declared further up in m_pd.h stays in effect). */
#undef class_addbang

typedef void (*gotfn_t)(void *, double *);

static struct {
    t_symbol *name;
    struct _class *cls;
    t_method bang;
    t_method reset;
} g_classes[MAX_CLASSES];
static int g_nclasses;

static struct { char name[40]; t_symbol sym; } g_symbols[MAX_SYMBOLS];
static int g_nsymbols;

static struct { void *outlet; double value; } g_floats[MAX_FLOATS];
static int g_nfloats;

static int g_checks;
static int g_failures;

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

static void check_close(double got, double want, const char *what)
{
    g_checks++;
    if (isfinite(got) && fabs(got - want) <= 1e-9 * (1.0 + fabs(want))) {
        printf("  ok   %s (= %.10g)\n", what, got);
    } else {
        printf("  FAIL %s: got %.12g, want %.12g\n", what, got, want);
        g_failures++;
    }
}

/* The attractor maps iterate in double precision, but Pd's t_float is 32-bit
 * in the puredata build, so outlet_float() narrows every emitted value.
 * Expectations are pushed through the same narrowing (a no-op for a 64-bit
 * float build). */
static double out_value(double d)
{
    return (double)(t_float)d;
}

t_symbol s_float = { "float", 0, 0 };
t_symbol s_list = { "list", 0, 0 };

t_symbol *gensym(const char *s)
{
    int i;
    for (i = 0; i < g_nsymbols; i++)
        if (strcmp(g_symbols[i].name, s) == 0)
            return &g_symbols[i].sym;
    if (g_nsymbols >= MAX_SYMBOLS)
        return &g_symbols[0].sym;
    snprintf(g_symbols[g_nsymbols].name, sizeof(g_symbols[0].name), "%s", s);
    g_symbols[g_nsymbols].sym.s_name = g_symbols[g_nsymbols].name;
    g_symbols[g_nsymbols].sym.s_thing = 0;
    g_symbols[g_nsymbols].sym.s_next = 0;
    g_nsymbols++;
    return &g_symbols[g_nsymbols - 1].sym;
}

t_class *class_new(t_symbol *name, t_newmethod newmethod, t_method freemethod,
                   size_t size, int flags, t_atomtype arg1, ...)
{
    struct _class *c;
    (void)arg1;
    if (g_nclasses >= MAX_CLASSES)
        return NULL;
    c = (struct _class *)calloc(1, sizeof(*c));
    c->c_name = name;
    c->c_new = newmethod;
    c->c_free = freemethod;
    c->c_classsize = (int)size;
    c->c_flags = flags;
    g_classes[g_nclasses].name = name;
    g_classes[g_nclasses].cls = c;
    g_classes[g_nclasses].bang = NULL;
    g_classes[g_nclasses].reset = NULL;
    g_nclasses++;
    return c;
}

void class_addmethod(t_class *c, t_method fn, t_symbol *sel, t_atomtype arg1, ...)
{
    (void)arg1;
    if (c == NULL || sel == NULL || sel->s_name == NULL)
        return;
    if (strcmp(sel->s_name, "reset") == 0)
        g_classes[g_nclasses - 1].reset = fn;
}

void class_addbang(t_class *c, t_method fn)
{
    (void)c;
    g_classes[g_nclasses - 1].bang = fn;
}
t_outlet *outlet_new(t_object *owner, t_symbol *s)
{
    t_outlet *o = (t_outlet *)calloc(1, sizeof(*o));
    o->o_symbol = s;
    if (owner->te_outlet == NULL) {
        owner->te_outlet = o;
    } else {
        t_outlet *last = owner->te_outlet;
        while (last->next)
            last = last->next;
        last->next = o;
    }
    return o;
}

void outlet_float(t_outlet *x, t_float f)
{
    if (g_nfloats < MAX_FLOATS) {
        g_floats[g_nfloats].outlet = x;
        g_floats[g_nfloats].value = f;
        g_nfloats++;
    }
}

void outlet_list(t_outlet *x, t_symbol *s, int argc, t_atom *argv)
{
    int i;
    (void)x;
    (void)s;
    for (i = 0; i < argc; i++)
        if (argv[i].a_type == A_FLOAT)
            printf("  info outlet_list float %.10g\n", argv[i].a_w.w_float);
}

void outlet_anything(t_outlet *x, t_symbol *s, int argc, t_atom *argv)
{
    (void)x;
    (void)s;
    (void)argc;
    (void)argv;
}

t_pd *pd_new(t_class *cls)
{
    t_object *obj;
    if (cls == NULL || cls->c_classsize <= 0)
        return NULL;
    obj = (t_object *)calloc(1, (size_t)cls->c_classsize);
    obj->te_g.g_pd = cls;
    return (t_pd *)obj;
}

t_float atom_getfloat(const t_atom *a)
{
    return (a != NULL && a->a_type == A_FLOAT) ? a->a_w.w_float : 0;
}

t_float atom_getfloatarg(int which, int argc, const t_atom *argv)
{
    return (which >= 0 && which < argc) ? atom_getfloat(&argv[which]) : 0;
}

void post(const char *fmt, ...)
{
    va_list ap;
    printf("  info post: ");
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
}

/* ------------------------------------------------------------------ */
/* Test body                                                          */
/* ------------------------------------------------------------------ */

static const char *const CLASSES[] = {
    "attract1", "base", "base3", "dejong", "gingerbreadman", "henon",
    "hopalong", "ikeda", "latoocarfian", "latoomutalpha", "latoomutbeta",
    "latoomutgamma", "logistic", "lorenz", "lotkavolterra", "martin",
    "mlogistic", "pickover", "popcorn", "quadruptwo", "rossler",
    "standardmap", "strange1", "tent", "three_d", "threeply", "tinkerbell",
    "unity"
};
#define NCLASSES ((int)(sizeof(CLASSES) / sizeof(CLASSES[0])))

static int class_slot(const char *name)
{
    int i;
    for (i = 0; i < g_nclasses; i++)
        if (strcmp(g_classes[i].name->s_name, name) == 0)
            return i;
    return -1;
}

static void bang(const char *name, void *obj)
{
    int slot = class_slot(name);
    if (slot < 0 || g_classes[slot].bang == NULL || obj == NULL)
        return;
    ((void (*)(void *))g_classes[slot].bang)(obj);
}

/* Mirror of Pd's newobject(): allocate through the plugin's own pd_new() and
 * hand the creation arguments to the class constructor. */
static void *newobject(const char *name, int argc, t_atom *argv)
{
    int slot = class_slot(name);
    if (slot < 0 || g_classes[slot].cls->c_new == NULL)
        return NULL;
    return (void *)(*(void *(*)(t_symbol *, int, t_atom *))
                       g_classes[slot].cls->c_new)(gensym(name), argc, argv);
}

static void send_reset(const char *name, void *obj, int argc, t_atom *argv)
{
    int slot = class_slot(name);
    if (slot < 0 || g_classes[slot].reset == NULL || obj == NULL)
        return;
    ((void (*)(void *, t_symbol *, int, t_atom *))g_classes[slot].reset)(
        obj, gensym("reset"), argc, argv);
}

/* logistic map iteration used as the lyapunov() callback */
struct map1 { double a; };

static void map1_calc(void *fractal, double *vars)
{
    struct map1 *m = (struct map1 *)fractal;
    vars[0] = m->a * vars[0] * (1.0 - vars[0]);
}

int main(int argc, char **argv)
{
    char path[1024];
    void *helper;
    double (*lyapunov)(void *, t_gotfn, int, double *);
    double *(*lyapunov_full)(void *, t_gotfn, int, double *, double *);
    struct map1 stable = { 1.5 };
    struct map1 chaotic = { 4.0 };
    double vars[1];
    double results[1];
    double e1, e2;
    void *obj;
    int i;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <externals-dir>\n", argv[0]);
        return 2;
    }
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("pd-chaos 0.2 consumer test (externals dir: %s)\n", argv[1]);

    /* 1. every plugin must dlopen, expose <class>_setup and register itself */
    for (i = 0; i < NCLASSES; i++) {
        void *lib;
        void (*setup)(void);
        int before, slot;
        char what[128];
        snprintf(path, sizeof(path), "%s/%s.pd_linux", argv[1], CLASSES[i]);
        lib = dlopen(path, RTLD_NOW | RTLD_LOCAL);
        if (lib == NULL) {
            printf("  FAIL dlopen %s.pd_linux: %s\n", CLASSES[i], dlerror());
            g_checks++;
            g_failures++;
            continue;
        }
        snprintf(path, sizeof(path), "%s_setup", CLASSES[i]);
        setup = (void (*)(void))dlsym(lib, path);
        if (setup == NULL) {
            printf("  FAIL dlsym %s_setup in %s.pd_linux\n", CLASSES[i],
                   CLASSES[i]);
            g_checks++;
            g_failures++;
            continue;
        }
        before = g_nclasses;
        setup();
        slot = class_slot(CLASSES[i]);
        snprintf(what, sizeof(what), "[%s] plugin loads and registers its class",
                 CLASSES[i]);
        check(slot >= 0 && g_nclasses == before + 1, what);
        snprintf(what, sizeof(what), "[%s] class name / instance size / bang / reset",
                 CLASSES[i]);
        check(slot >= 0
                  && strcmp(g_classes[slot].name->s_name, CLASSES[i]) == 0
                  && g_classes[slot].cls->c_classsize > 0
                  && g_classes[slot].bang != NULL
                  && g_classes[slot].reset != NULL, what);
        /* No dlclose(): the registered method pointers point into the plugin. */
    }
    check(g_nclasses == NCLASSES,
          "all 28 chaos externals registered exactly one class each");

    /* 2. the shared lyapunov helper library */
    snprintf(path, sizeof(path), "%s/libchaos.so", argv[1]);
    helper = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    check(helper != NULL, "libchaos.so dlopen");
    if (helper == NULL) {
        printf("  info dlerror: %s\n", dlerror());
    } else {
        lyapunov = (double (*)(void *, t_gotfn, int, double *))
            dlsym(helper, "lyapunov");
        lyapunov_full = (double *(*)(void *, t_gotfn, int, double *, double *))
            dlsym(helper, "lyapunov_full");
        check(lyapunov != NULL, "libchaos.so exports lyapunov()");
        check(lyapunov_full != NULL, "libchaos.so exports lyapunov_full()");

        if (lyapunov != NULL) {
            /* a=4 logistic map: perturbation grows -> positive exponent */
            vars[0] = 0.1;
            e1 = lyapunov(&chaotic, (t_gotfn)map1_calc, 1, vars);
            check(isfinite(e1), "lyapunov() finite for the chaotic map (a=4)");
            check(e1 > 0.0, "chaotic logistic map (a=4) -> positive exponent");
            vars[0] = 0.1;
            e2 = lyapunov(&chaotic, (t_gotfn)map1_calc, 1, vars);
            check(e1 == e2, "lyapunov() deterministic for identical input");
            /* a=1.5 logistic map: the fixed point attracts -> negative */
            vars[0] = 0.1;
            e1 = lyapunov(&stable, (t_gotfn)map1_calc, 1, vars);
            check(isfinite(e1), "lyapunov() finite for the stable map (a=1.5)");
            check(e1 < 0.0, "stable logistic map (a=1.5) -> negative exponent");
        }
        if (lyapunov_full != NULL) {
            vars[0] = 0.1;
            results[0] = -12345.0;
            check(lyapunov_full(&chaotic, (t_gotfn)map1_calc, 1, vars,
                                results) == results,
                  "lyapunov_full() returns the caller buffer it filled");
            check(isfinite(results[0]),
                  "lyapunov_full() wrote a finite exponent");
        }
    }

    /* 3. drive the real `logistic` object: x = a*x*(1-x) with creation args
     *    [logistic 0.1 4], then a `reset` message round trip */
    g_nfloats = 0;
    {
        t_atom args[2];
        SETFLOAT(&args[0], 0.1);
        SETFLOAT(&args[1], 4);
        obj = newobject("logistic", 2, args);
    }
    check(obj != NULL, "logistic[0.1 4] created through its real constructor");
    if (obj != NULL) {
        void *out0 = ((t_object *)obj)->te_outlet;
        double x = 0.1;
        bang("logistic", obj);
        check(g_nfloats == 1, "logistic emitted one float per bang");
        if (g_nfloats == 1) {
            x = 4.0 * x * (1.0 - x);
            check_close(g_floats[0].value, out_value(x), "logistic bang #1 = 4*x*(1-x)");
            check(g_floats[0].outlet == out0, "logistic emits on its first outlet");
        }
        bang("logistic", obj);
        check(g_nfloats == 2, "logistic answered the second bang");
        if (g_nfloats == 2) {
            x = 4.0 * x * (1.0 - x);
            check_close(g_floats[1].value, out_value(x), "logistic bang #2 = 4*x*(1-x)");
        }
        {
            t_atom one[1];
            SETFLOAT(&one[0], 0.25);
            send_reset("logistic", obj, 1, one);
        }
        bang("logistic", obj);
        check(g_nfloats == 3, "logistic answered the bang after `reset 0.25`");
        if (g_nfloats == 3)
            check_close(g_floats[2].value, out_value(4.0 * 0.25 * 0.75),
                        "logistic after `reset 0.25` = 4*0.25*(1-0.25)");
    }

    /* 4. drive the real `martin` object: [martin 0.01 0 3.14] iterates
     *    x = y-sin(x) and y = a-x and emits on two distinct outlets */
    g_nfloats = 0;
    {
        t_atom args[3];
        SETFLOAT(&args[0], 0.01);
        SETFLOAT(&args[1], 0);
        SETFLOAT(&args[2], 3.14);
        obj = newobject("martin", 3, args);
    }
    check(obj != NULL, "martin[0.01 0 3.14] created through its real constructor");
    if (obj != NULL) {
        bang("martin", obj);
        check(g_nfloats == 2, "martin emitted two floats per bang");
        if (g_nfloats == 2) {
            check_close(g_floats[0].value, out_value(3.14 - 0.01), "martin y outlet = a - x");
            check_close(g_floats[1].value, out_value(0.0 - sin(0.01)),
                        "martin x outlet = y - sin(x)");
            check(g_floats[0].outlet != g_floats[1].outlet,
                  "martin's two values come from two distinct outlets");
        }
    }

    printf("PD_CHAOS_CHECK_SUMMARY checks=%d failures=%d\n", g_checks,
           g_failures);
    fflush(stdout);
    /* When a summary path is given (argv[2]) also write it there so the
     * conan test_package can read the counts back from the program itself
     * instead of restating a constant. */
    if (argc >= 3) {
        FILE *fh = fopen(argv[2], "w");
        if (fh != NULL) {
            fprintf(fh, "checks=%d failures=%d\n", g_checks, g_failures);
            fclose(fh);
        }
    }
    return g_failures == 0 ? 0 : 1;
}