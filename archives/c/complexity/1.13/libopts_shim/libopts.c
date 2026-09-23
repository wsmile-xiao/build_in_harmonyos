/* Minimal private libopts shim for GNU complexity 1.13.
 *
 * Why this exists: complexity's configure probes GNU autogen libopts via
 * `autoopts-config`. The HarmonyOS PC preflight machine has no system
 * libopts and the full autogen build needs guile/libxml, which is too
 * heavy and fragile for a single-library PR. The upstream tarball already
 * ships pre-generated opts.c/opts.h (AutoOpts 42:2:17 templates), so only
 * the *runtime* library is missing -- not the `autogen` generator itself.
 *
 * What it does: implements just the libopts entry points that
 * complexity's generated opts.c actually uses, on top of the *real*
 * `autoopts/options.h` struct layouts (vendored from autogen-5.18.16 and
 * aligned to AutoOpts 42:2:17 as required by complexity's generated
 * opts.h AO_TEMPLATE_VERSION=172034, so the positional
 * `tOptions`/`tOptDesc` initializers in opts.c stay ABI-correct):
 *   optionProcess, optionUsage, optionPagedUsage, optionPrintVersion,
 *   optionNumericVal, optionStackArg, optionLoadOpt
 * plus harmless stubs for the other declared but unused callbacks.
 * Parsing is done with POSIX getopt_long over the live descriptor table,
 * so option semantics (short/long/negation/stacked/numeric/config-file)
 * follow the upstream descriptors instead of a hardcoded copy.
 *
 * Scope: intentionally minimal -- no NLS, no env/RC auto-loading, no
 * save-opts/vendor/nested/time support. optionLoadOpt handles the config
 * file form used by the upstream test (`hist`, `score`, `thresh 0`, one
 * per line, unambiguous prefix match allowed, `#` comments skipped).
 *
 * License: written from scratch for this recipe; same terms as complexity
 * (GPL-3.0-or-later).
 */
#include <stdint.h>
#include <limits.h>
#ifdef __linux__
#define HAVE_STDINT_H 1
#define HAVE_LIMITS_H 1
#define HAVE_STDBOOL_H 1
#define HAVE_INTTYPES_H 1
#else
#define HAVE_STDINT_H 1
#define HAVE_LIMITS_H 1
#define HAVE_STDBOOL_H 1
#define HAVE_INTTYPES_H 1
#endif
#include <autoopts/options.h>

#include <ctype.h>
#include <errno.h>
#include <getopt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

FILE *option_usage_fp = NULL;

/* ---- small helpers ---- */

static tOptDesc *find_by_value(tOptions *opts, int val)
{
    int i;
    for (i = 0; i < opts->optCt; i++) {
        if (opts->pOptDesc[i].optValue == (uint16_t)val)
            return &opts->pOptDesc[i];
    }
    return NULL;
}

static tOptDesc *find_by_long(tOptions *opts, const char *name)
{
    int i;
    for (i = 0; i < opts->optCt; i++) {
        tOptDesc *od = &opts->pOptDesc[i];
        if (od->pz_Name && strcmp(od->pz_Name, name) == 0)
            return od;
        if (od->pz_DisableName && strcmp(od->pz_DisableName, name) == 0)
            return od;
    }
    return NULL;
}

/* Unambiguous prefix match used for config-file names (e.g. "hist" for
 * "histogram", "thresh" for "threshold"). Returns NULL when ambiguous. */
static tOptDesc *find_by_prefix(tOptions *opts, const char *name)
{
    size_t len = strlen(name);
    tOptDesc *hit = NULL;
    int i;
    if (len == 0)
        return NULL;
    for (i = 0; i < opts->optCt; i++) {
        tOptDesc *od = &opts->pOptDesc[i];
        if (od->pz_Name && strncasecmp(od->pz_Name, name, len) == 0) {
            if (strlen(od->pz_Name) == len)
                return od; /* exact wins immediately */
            if (hit != NULL && hit != od)
                return NULL; /* ambiguous */
            hit = od;
        }
        if (od->pz_DisableName && strncasecmp(od->pz_DisableName, name, len) == 0) {
            if (strlen(od->pz_DisableName) == len)
                return od;
            if (hit != NULL && hit != od)
                return NULL;
            hit = od;
        }
    }
    return hit;
}

static void mark_defined(tOptDesc *od)
{
    od->fOptState &= (opt_state_mask_t)~OPTST_DISABLED;
    od->fOptState |= (OPTST_DEFINED | OPTST_SET);
    od->optOccCt++;
}

static void mark_negated(tOptDesc *od)
{
    od->fOptState |= (opt_state_mask_t)(OPTST_DEFINED | OPTST_SET | OPTST_DISABLED);
    od->optOccCt++;
}

static char *dup_str(const char *s)
{
    char *r;
    size_t n;
    if (s == NULL)
        return NULL;
    n = strlen(s) + 1;
    r = (char *)malloc(n);
    if (r == NULL) {
        fprintf(stderr, "complexity libopts shim: out of memory\n");
        exit(3);
    }
    memcpy(r, s, n);
    return r;
}

/* ---- callbacks referenced by complexity's generated opts.c ---- */

void optionNumericVal(tOptions *pOpts, tOptDesc *pOD)
{
    const char *s = pOD->optArg.argString;
    char *end = NULL;
    long v;
    (void)pOpts;
    /* Called via SET_OPT_xxx(a) macros with argInt pre-set and no string;
     * leave the value alone in that case. */
    if (s == NULL || (uintptr_t)s < (uintptr_t)4096)
        return;
    errno = 0;
    v = strtol(s, &end, 0);
    if (errno == 0 && end != NULL && *end == '\0')
        pOD->optArg.argInt = v;
    /* On parse failure keep the previous (default) value; the real
     * libopts would emit a usage error, but complexity only feeds it
     * plain integers ("-t0", "thresh 0"). */
}

void optionStackArg(tOptions *pOpts, tOptDesc *pOD)
{
    tArgList *lst = (tArgList *)pOD->optCookie;
    const char *s = pOD->optArg.argString;
    (void)pOpts;
    if (lst == NULL) {
        lst = (tArgList *)malloc(sizeof(*lst));
        if (lst == NULL) {
            fprintf(stderr, "complexity libopts shim: out of memory\n");
            exit(3);
        }
        lst->useCt = 0;
        lst->allocCt = MIN_ARG_ALLOC_CT;
        pOD->optCookie = (void *)lst;
    }
    if (lst->useCt >= lst->allocCt) {
        int nalloc = lst->allocCt + INCR_ARG_ALLOC_CT;
        /* tArgList has a fixed 6-slot array; grow via whole-struct realloc
         * only when the header layout allows -- instead spill into a larger
         * malloc and copy. Simplest correct approach: realloc with extra. */
        size_t need = sizeof(*lst) + (size_t)(nalloc - MIN_ARG_ALLOC_CT) * sizeof(char const *);
        tArgList *nl = (tArgList *)realloc(lst, need);
        if (nl == NULL) {
            fprintf(stderr, "complexity libopts shim: out of memory\n");
            exit(3);
        }
        lst = nl;
        lst->allocCt = nalloc;
        pOD->optCookie = (void *)lst;
    }
    /* store at index useCt; the fixed array covers the first 6, the
     * over-allocated tail covers the rest (same address arithmetic). */
    {
        char const **slot;
        if (lst->useCt < MIN_ARG_ALLOC_CT)
            slot = &lst->apzArgs[lst->useCt];
        else
            slot = (char const **)((char *)lst->apzArgs + (size_t)lst->useCt * sizeof(char const *));
        *slot = dup_str(s ? s : "");
        lst->useCt++;
    }
}

static void load_config_file(tOptions *opts, const char *path);

void optionLoadOpt(tOptions *pOpts, tOptDesc *pOD)
{
    const char *path = pOD->optArg.argString;
    if (path == NULL || *path == '\0')
        return;
    load_config_file(pOpts, path);
}

void optionPrintVersion(tOptions *pOpts, tOptDesc *pOD)
{
    (void)pOD;
    if (pOpts && pOpts->pzFullVersion)
        puts(pOpts->pzFullVersion);
    else
        puts("complexity (GNU Complexity) 1.13");
    exit(0);
}

void optionPrintVersionAndReturn(tOptions *pOpts, tOptDesc *pOD)
{
    (void)pOD;
    if (pOpts && pOpts->pzFullVersion)
        puts(pOpts->pzFullVersion);
    else
        puts("complexity (GNU Complexity) 1.13");
}

static void print_usage(tOptions *opts, int code)
{
    FILE *fp = option_usage_fp;
    int i;
    if (fp == NULL)
        fp = (code == 0) ? stdout : stderr;
    if (opts) {
        if (opts->pzUsageTitle)
            fprintf(fp, "%s\n", opts->pzUsageTitle);
        if (opts->pzExplain)
            fprintf(fp, "%s\n", opts->pzExplain);
        for (i = 0; i < opts->optCt; i++) {
            tOptDesc *od = &opts->pOptDesc[i];
            if (od->pz_Name == NULL)
                continue;
            /* Skip pure helper entries with no user text (save/load/help
             * still shown; internal aliases have NULL pzText). */
            if (od->pzText)
                fprintf(fp, "  --%-18s %s\n", od->pz_Name, od->pzText);
            else
                fprintf(fp, "  --%s\n", od->pz_Name);
        }
        if (opts->pzDetail)
            fprintf(fp, "%s\n", opts->pzDetail);
    } else {
        fputs("complexity: option usage\n", fp);
    }
    exit(code);
}

void optionUsage(tOptions *pOpts, int exitCode)
{
    print_usage(pOpts, exitCode);
}

void optionOnlyUsage(tOptions *pOpts, int exitCode)
{
    print_usage(pOpts, exitCode);
}

void optionPagedUsage(tOptions *pOpts, tOptDesc *pOD)
{
    (void)pOD;
    print_usage(pOpts, 0);
}

/* Unused-but-declared callbacks: harmless no-ops so the link succeeds. */
void optionBooleanVal(tOptions *pOpts, tOptDesc *pOD) { (void)pOpts; (void)pOD; }
void optionNestedVal(tOptions *pOpts, tOptDesc *pOD) { (void)pOpts; (void)pOD; }
void optionResetOpt(tOptions *pOpts, tOptDesc *pOD) { (void)pOpts; (void)pOD; }
void optionTimeDate(tOptions *pOpts, tOptDesc *pOD) { (void)pOpts; (void)pOD; }
void optionTimeVal(tOptions *pOpts, tOptDesc *pOD) { (void)pOpts; (void)pOD; }
void optionUnstackArg(tOptions *pOpts, tOptDesc *pOD) { (void)pOpts; (void)pOD; }
void optionVendorOption(tOptions *pOpts, tOptDesc *pOD) { (void)pOpts; (void)pOD; }

/* ---- config file loading ---- */

static void apply_config_option(tOptions *opts, tOptDesc *od, const char *value, int is_disable)
{
    if (is_disable) {
        mark_negated(od);
        if (od->pOptProc != NULL)
            od->pOptProc(opts, od);
        return;
    }
    {
        unsigned argtype = (unsigned)((od->fOptState & OPTST_ARG_TYPE_MASK) >> OPTST_ARG_TYPE_SHIFT);
        if (argtype == OPARG_TYPE_NONE) {
            mark_defined(od);
            if (od->pOptProc != NULL)
                od->pOptProc(opts, od);
            return;
        }
        if (value == NULL)
            value = "";
        od->optArg.argString = dup_str(value);
        mark_defined(od);
        if (od->pOptProc != NULL)
            od->pOptProc(opts, od);
    }
}

static void load_config_file(tOptions *opts, const char *path)
{
    FILE *fp = fopen(path, "r");
    char line[4096];
    if (fp == NULL) {
        fprintf(stderr, "complexity: cannot open option file %s: %s\n", path, strerror(errno));
        exit(66);
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        char *p = line;
        char *name, *value = NULL;
        tOptDesc *od;
        int is_disable = 0;
        while (*p && isspace((unsigned char)*p))
            p++;
        if (*p == '\0' || *p == '\n' || *p == '#')
            continue;
        /* strip trailing newline */
        {
            size_t n = strlen(p);
            while (n > 0 && (p[n - 1] == '\n' || p[n - 1] == '\r'))
                p[--n] = '\0';
            while (n > 0 && isspace((unsigned char)p[n - 1]))
                p[--n] = '\0';
        }
        if (*p == '\0' || *p == '#')
            continue;
        /* split name/value on '=' or whitespace */
        {
            char *sep = strchr(p, '=');
            if (sep != NULL) {
                *sep = '\0';
                value = sep + 1;
            } else {
                char *sp = p;
                while (*sp && !isspace((unsigned char)*sp))
                    sp++;
                if (*sp) {
                    *sp = '\0';
                    value = sp + 1;
                }
            }
        }
        name = p;
        while (*name && isspace((unsigned char)*name))
            name++;
        /* strip leading dashes (config files use bare names) */
        while (*name == '-')
            name++;
        if (value) {
            while (*value && isspace((unsigned char)*value))
                value++;
            if (*value == '\0')
                value = NULL;
        }
        if (*name == '\0')
            continue;
        od = find_by_long(opts, name);
        if (od == NULL)
            od = find_by_prefix(opts, name);
        if (od == NULL) {
            fprintf(stderr, "complexity: unknown option in %s: %s\n", path, name);
            fclose(fp);
            exit(64);
        }
        if (od->pz_DisableName && strcasecmp(name, od->pz_DisableName) == 0)
            is_disable = 1;
        else if (od->pz_Name && strcasecmp(name, od->pz_Name) != 0) {
            /* prefix hit on the disable name? re-check */
            if (od->pz_DisableName && strncasecmp(od->pz_DisableName, name, strlen(name)) == 0)
                is_disable = 1;
        }
        apply_config_option(opts, od, value, is_disable);
    }
    fclose(fp);
}

/* ---- main entry point ---- */

int optionProcess(tOptions *opts, int argc, char **argv)
{
    struct option *longopts;
    char *optstring;
    int i, nlong;
    int c;

    if (opts == NULL || argv == NULL) {
        fputs("optionProcess() was called with invalid data\n", stderr);
        exit(70);
    }
    opts->origArgCt = (unsigned)argc;
    opts->origArgVect = argv;

    nlong = opts->optCt * 2 + 1;
    longopts = (struct option *)calloc((size_t)nlong, sizeof(*longopts));
    optstring = (char *)malloc((size_t)opts->optCt * 4 + 8);
    if (!longopts || !optstring) {
        fputs("complexity libopts shim: out of memory\n", stderr);
        exit(3);
    }

    {
        int li = 0;
        size_t si = 0;
        /* NOTE: no '+' prefix here. getopt runs over the full range in
         * permutation mode instead: some libcs do not honour '+' in the
         * optstring, which would break or mis-parse the whole command
         * line. All real complexity invocations put options before
         * operands, where permutation agrees with stop-at-first-operand. */
        for (i = 0; i < opts->optCt; i++) {
            tOptDesc *od = &opts->pOptDesc[i];
            unsigned argtype = (unsigned)((od->fOptState & OPTST_ARG_TYPE_MASK) >> OPTST_ARG_TYPE_SHIFT);
            int has_arg = (argtype != OPARG_TYPE_NONE);
            int opt = (int)od->optValue;
            /* Immediate no-arg options (AutoOpts VER/HELP/MORE_HELP carry
             * OPTST_ARG_OPTIONAL in VER_FLAGS, but real libopts treats a
             * bare `--version`/`-v` as valid with no argument). Building
             * them as required_argument makes getopt_long return '?'
             * (missing arg) for a bare `--version`, surfacing as
             * "unknown option '-v'" rc=64 in preflight. Force no_arg. */
            if (opt == 'v' || opt == '?' || opt == '!')
                has_arg = 0;
            /* Long entries: primary name + disable name (if any). Disable
             * entries reuse the same short value; the handler distinguishes
             * via optarg/longindex. Encode disable as value | 0x8000. */
            if (od->pz_Name && od->pz_Name[0]) {
                longopts[li].name = od->pz_Name;
                longopts[li].has_arg = has_arg ? required_argument : no_argument;
                longopts[li].flag = NULL;
                longopts[li].val = opt;
                li++;
            }
            if (od->pz_DisableName && od->pz_DisableName[0]) {
                longopts[li].name = od->pz_DisableName;
                longopts[li].has_arg = no_argument;
                longopts[li].flag = NULL;
                longopts[li].val = opt | 0x8000;
                li++;
            }
            if (opt > 0 && opt < 256) {
                optstring[si++] = (char)opt;
                if (has_arg) {
                    /*required; optional only for save-opts (OPTST_ARG_OPTIONAL
                     * is compiled out to 0 in this header, so treat '>' as
                     * optional explicitly). */
                    if (opt == '>')
                        optstring[si++] = ':',
                        optstring[si++] = ':';
                    else
                        optstring[si++] = ':';
                }
            }
        }
        longopts[li].name = NULL;
        optstring[si] = '\0';
    }

    opterr = 0;
    optind = 1;
    /* No '+' prefix and no manual pre-scan: run getopt over the full range
     * in permutation mode. Real libopts stops at the first operand, but
     * every real complexity invocation (usage: "[ <file-name> ... ]",
     * options always precede operands, as in tests/complexity.test) puts
     * options first, where permutation and stop-at-first-operand agree
     * exactly. This avoids any dependence on '+' support in the libc. */
    while ((c = getopt_long(argc, argv, optstring, longopts, NULL)) != -1) {
        int is_disable = (c & 0x8000) ? 1 : 0;
        int base = c & ~0x8000;
        tOptDesc *od = NULL;

        if (c == '?') {
            /* getopt reuses '?' for unknowns and for the real '-?' / '--help'
             * flag (both have value '?'). Disambiguate via the raw token. */
            const char *tok = (optind > 0 && optind <= argc) ? argv[optind - 1] : "";
            if (strcmp(tok, "-?") == 0) {
                od = find_by_value(opts, '?');
                if (od != NULL) {
                    od->optArg.argString = NULL;
                    mark_defined(od);
                    if (od->pOptProc)
                        od->pOptProc(opts, od);
                    else
                        print_usage(opts, 0);
                    continue;
                }
            }
            if (tok[0] == '-' && tok[1] == '-') {
                char tmp[256];
                size_t k = 0;
                const char *nm = tok + 2;
                while (*nm && *nm != '=' && k + 1 < sizeof(tmp))
                    tmp[k++] = *nm++;
                tmp[k] = '\0';
                od = find_by_long(opts, tmp);
                if (od != NULL && od->optValue == (uint16_t)'?') {
                    od->optArg.argString = NULL;
                    mark_defined(od);
                    if (od->pOptProc)
                        od->pOptProc(opts, od);
                    else
                        print_usage(opts, 0);
                    continue;
                }
            }
            if (optopt)
                fprintf(stderr, "complexity: unknown option '-%c'\n", optopt);
            else if (optind > 0 && optind <= argc)
                fprintf(stderr, "complexity: unknown option: %s\n", argv[optind - 1]);
            else
                fputs("complexity: unknown option\n", stderr);
            free(longopts);
            free(optstring);
            exit(64);
        }

        od = find_by_value(opts, base);
        if (od == NULL) {
            fprintf(stderr, "complexity: unknown option code %d\n", base);
            free(longopts);
            free(optstring);
            exit(64);
        }
        if (is_disable) {
            mark_negated(od);
            if (od->pOptProc != NULL && od->optValue != (uint16_t)'h' && od->optValue != (uint16_t)'c')
                od->pOptProc(opts, od);
            continue;
        }
        {
            unsigned argtype = (unsigned)((od->fOptState & OPTST_ARG_TYPE_MASK) >> OPTST_ARG_TYPE_SHIFT);
            if (argtype == OPARG_TYPE_NONE) {
                od->optArg.argString = NULL;
                mark_defined(od);
                if (od->pOptProc != NULL)
                    od->pOptProc(opts, od);
            } else {
                const char *a = optarg ? optarg : "";
                /* Short-option immediate version/help take no arg. */
                if (base == 'v') {
                    mark_defined(od);
                    optionPrintVersion(opts, od);
                    continue;
                }
                if (base == '?') {
                    mark_defined(od);
                    if (od->pOptProc)
                        od->pOptProc(opts, od);
                    else
                        print_usage(opts, 0);
                    continue;
                }
                if (base == '!') {
                    mark_defined(od);
                    if (od->pOptProc)
                        od->pOptProc(opts, od);
                    else
                        print_usage(opts, 0);
                    continue;
                }
                od->optArg.argString = dup_str(a);
                mark_defined(od);
                if (od->pOptProc != NULL)
                    od->pOptProc(opts, od);
            }
        }
    }

    free(longopts);
    free(optstring);
    return optind;
}
