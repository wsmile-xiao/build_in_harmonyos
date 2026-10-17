/* Consumer tests for libmustach-core (merged single binary).
 *
 * suite 1 (rend_, ex test_core_render.c): low-level mustach render API —
 * variable interpolation, HTML escaping, truthy/falsy sections, inverted
 * sections and list iteration via hand-written struct mustach_itf, plus
 * error paths.
 * suite 2 (wrap_, ex test_core_wrap.c): mustach_wrap render API — field
 * selection via sel/subsel, scalar retrieval, default HTML escaping and
 * triple-mustache raw output.
 *
 * Each numbered check returns a distinct exit code so failures are
 * diagnosable from the exit status; both suites run inside one main and each
 * prints its own sentinel line.
 *
 * NOTE (OHOS readonly /tmp): mustach_mem()/mustach_wrap_mem() render via
 * open_memstream(), which traps at startup (SIGTRAP, rc=-5, no output) on
 * the HarmonyOS preflight device while a plain hello binary runs fine. The
 * rendering engines under test are identical for mustach_file() and
 * mustach_wrap_file(), so both suites drive the *_file() variant with an
 * explicitly fopen()'d file inside the HMBS-writable TMPDIR (never /tmp)
 * and read the result back.
 */
#include <mustach/mustach.h>
#include <mustach/mustach-wrap.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ===================== suite 1: mustach render API ===================== */
static const char *rend_g_name = "R&D";
static const char *rend_g_items[] = {"alpha", "beta"};
static const int rend_g_nitems = 2;
static int rend_g_idx = -1;
static int rend_g_in_items = 0;
static int rend_g_tmpseq = 0;

static int rend_cb_enter(void *closure, const char *name)
{
    (void)closure;
    if (strcmp(name, "items") == 0) {
        rend_g_in_items = 1;
        rend_g_idx = 0;
        return 1;
    }
    if (strcmp(name, "show") == 0)
        return 1;
    return 0;
}

static int rend_cb_next(void *closure)
{
    (void)closure;
    if (!rend_g_in_items)
        return 0;
    rend_g_idx++;
    return rend_g_idx < rend_g_nitems;
}

static int rend_cb_leave(void *closure)
{
    (void)closure;
    rend_g_in_items = 0;
    rend_g_idx = -1;
    return 0;
}

static int rend_cb_get(void *closure, const char *name, struct mustach_sbuf *sbuf)
{
    (void)closure;
    sbuf->value = NULL;
    sbuf->freecb = NULL;
    sbuf->closure = NULL;
    sbuf->length = 0;
    if (strcmp(name, "name") == 0) {
        sbuf->value = rend_g_name;
        return MUSTACH_OK;
    }
    if (strcmp(name, "item") == 0 && rend_g_in_items
        && rend_g_idx >= 0 && rend_g_idx < rend_g_nitems) {
        sbuf->value = rend_g_items[rend_g_idx];
        return MUSTACH_OK;
    }
    return MUSTACH_ERROR_ITEM_NOT_FOUND;
}

static const struct mustach_itf rend_g_itf = {
    .start = NULL,
    .put = NULL,
    .enter = rend_cb_enter,
    .next = rend_cb_next,
    .leave = rend_cb_leave,
    .partial = NULL,
    .emit = NULL,
    .get = rend_cb_get,
    .stop = NULL
};

static const char *rend_writable_dir(void)
{
    static const char *keys[] = {"TMPDIR", "TMP", "TEMP", NULL};
    int i;
    for (i = 0; keys[i] != NULL; i++) {
        const char *v = getenv(keys[i]);
        if (v != NULL && v[0] != '\0' && strcmp(v, "/tmp") != 0)
            return v;
    }
    return ".";
}

/* Render via mustach_file() into a writable tmp file; read bytes back.
 * Returns the mustach status code; on success *out/*len hold malloc'd data.
 */
static int rend_render_file(const char *tmpl, const struct mustach_itf *itf,
                            int flags, char **out, size_t *len)
{
    char path[1024];
    FILE *f = NULL;
    char *buf = NULL;
    size_t n = 0;
    long pos = 0;
    int rc;

    *out = NULL;
    if (len != NULL)
        *len = 0;
    snprintf(path, sizeof path, "%s/mustach_render_%d.tmp",
             rend_writable_dir(), rend_g_tmpseq++);
    f = fopen(path, "w+");
    if (f == NULL)
        return MUSTACH_ERROR_SYSTEM;
    rc = mustach_file(tmpl, 0, itf, NULL, flags, f);
    if (rc != MUSTACH_OK) {
        fclose(f);
        remove(path);
        return rc;
    }
    fflush(f);
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    pos = ftell(f);
    if (pos < 0) {
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    n = (size_t)pos;
    if (fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    buf = (char *)malloc(n + 1);
    if (buf == NULL && n > 0) {
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    if (n > 0 && fread(buf, n, 1, f) != 1) {
        free(buf);
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    fclose(f);
    remove(path);
    buf[n] = '\0';
    *out = buf;
    if (len != NULL)
        *len = n;
    return MUSTACH_OK;
}

static int run_render_suite(void)
{
    static const char template_text[] =
        "Hello {{name}}!"
        "{{#show}} shown{{/show}}"
        "{{^hide}} visible{{/hide}}"
        "{{#items}}[{{item}}]{{/items}}";
    static const char expected[] =
        "Hello R&amp;D! shown visible[alpha][beta]";
    char *result = NULL;
    size_t size = 0;
    int rc;

    /* 1: header version sanity. */
    if (MUSTACH_VERSION_MAJOR != 1 || MUSTACH_VERSION_MINOR != 2)
        return 1;

    /* 2-4: full render path (variable + escape + sections + iteration). */
    rc = rend_render_file(template_text, &rend_g_itf,
                          Mustach_With_NoExtensions, &result, &size);
    if (rc != MUSTACH_OK)
        return 2;
    if (size != strlen(expected)) {
        free(result);
        return 3;
    }
    if (memcmp(result, expected, size) != 0) {
        fprintf(stderr, "render mismatch: got '%.*s'\n", (int)size, result);
        free(result);
        return 4;
    }
    free(result);

    /* 5: missing mandatory callbacks must report INVALID_ITF. */
    {
        static const struct mustach_itf empty_itf = {0};
        char *r2 = NULL;
        size_t s2 = 0;
        rc = rend_render_file("x", &empty_itf,
                              Mustach_With_NoExtensions, &r2, &s2);
        free(r2);
        if (rc != MUSTACH_ERROR_INVALID_ITF)
            return 5;
    }

    /* 6: unclosed section must fail. */
    {
        char *r3 = NULL;
        size_t s3 = 0;
        rc = rend_render_file("{{#show}} truncated", &rend_g_itf,
                              Mustach_With_NoExtensions, &r3, &s3);
        free(r3);
        if (rc >= 0)
            return 6;
    }

    /* 7: empty tag must fail without the EmptyTag extension. */
    {
        char *r4 = NULL;
        size_t s4 = 0;
        rc = rend_render_file("a{{}}b", &rend_g_itf,
                              Mustach_With_NoExtensions, &r4, &s4);
        free(r4);
        if (rc >= 0)
            return 7;
    }

    printf("test_core_render: all 7 checks passed\n");
    return 0;
}

/* ===================== suite 2: mustach_wrap render API ===================== */
static const char *wrap_g_title = "Hi & Bye";
static int wrap_g_selected = 0; /* 0 = none, 1 = title */
static int wrap_g_tmpseq = 0;

static int wrap_cb_sel(void *closure, const char *name)
{
    (void)closure;
    if (name == NULL)
        return wrap_g_selected != 0;
    if (strcmp(name, "title") == 0) {
        wrap_g_selected = 1;
        return 1;
    }
    wrap_g_selected = 0;
    return 0;
}

static int wrap_cb_subsel(void *closure, const char *name)
{
    return wrap_cb_sel(closure, name);
}

static int wrap_cb_enter(void *closure, int objiter)
{
    (void)closure;
    (void)objiter;
    return 0;
}

static int wrap_cb_next(void *closure)
{
    (void)closure;
    return 0;
}

static int wrap_cb_leave(void *closure)
{
    (void)closure;
    return 0;
}

static int wrap_cb_get(void *closure, struct mustach_sbuf *sbuf, int key)
{
    (void)closure;
    sbuf->value = NULL;
    sbuf->freecb = NULL;
    sbuf->closure = NULL;
    sbuf->length = 0;
    if (key != 0)
        return 0;
    if (wrap_g_selected == 1) {
        sbuf->value = wrap_g_title;
        return 1;
    }
    return 0;
}

static const struct mustach_wrap_itf wrap_g_itf = {
    .start = NULL,
    .stop = NULL,
    .compare = NULL,
    .sel = wrap_cb_sel,
    .subsel = wrap_cb_subsel,
    .enter = wrap_cb_enter,
    .next = wrap_cb_next,
    .leave = wrap_cb_leave,
    .get = wrap_cb_get
};

static const char *wrap_writable_dir(void)
{
    static const char *keys[] = {"TMPDIR", "TMP", "TEMP", NULL};
    int i;
    for (i = 0; keys[i] != NULL; i++) {
        const char *v = getenv(keys[i]);
        if (v != NULL && v[0] != '\0' && strcmp(v, "/tmp") != 0)
            return v;
    }
    return ".";
}

/* Render via mustach_wrap_file() into a writable tmp file; read bytes back. */
static int wrap_render_file(const char *tmpl, char **out, size_t *len)
{
    char path[1024];
    FILE *f = NULL;
    char *buf = NULL;
    size_t n = 0;
    long pos = 0;
    int rc;

    *out = NULL;
    if (len != NULL)
        *len = 0;
    snprintf(path, sizeof path, "%s/mustach_wrap_%d.tmp",
             wrap_writable_dir(), wrap_g_tmpseq++);
    f = fopen(path, "w+");
    if (f == NULL)
        return MUSTACH_ERROR_SYSTEM;
    rc = mustach_wrap_file(tmpl, 0, &wrap_g_itf, NULL,
                           Mustach_With_AllExtensions, f);
    if (rc != MUSTACH_OK) {
        fclose(f);
        remove(path);
        return rc;
    }
    fflush(f);
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    pos = ftell(f);
    if (pos < 0) {
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    n = (size_t)pos;
    if (fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    buf = (char *)malloc(n + 1);
    if (buf == NULL && n > 0) {
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    if (n > 0 && fread(buf, n, 1, f) != 1) {
        free(buf);
        fclose(f);
        remove(path);
        return MUSTACH_ERROR_SYSTEM;
    }
    fclose(f);
    remove(path);
    buf[n] = '\0';
    *out = buf;
    if (len != NULL)
        *len = n;
    return MUSTACH_OK;
}

static int wrap_check_render(const char *tmpl, const char *expected, int retcode)
{
    char *result = NULL;
    size_t size = 0;
    int rc = wrap_render_file(tmpl, &result, &size);
    if (rc != MUSTACH_OK)
        return retcode;
    if (size != strlen(expected) || memcmp(result, expected, size) != 0) {
        fprintf(stderr, "wrap mismatch for '%s': got '%.*s'\n",
                tmpl, (int)size, result ? result : "");
        free(result);
        return retcode + 1;
    }
    free(result);
    return 0;
}

static int run_wrap_suite(void)
{
    int fail;

    /* 1: header version sanity. */
    if (MUSTACH_VERSION != 102)
        return 1;

    /* 2-3: escaped interpolation through the wrapper. */
    fail = wrap_check_render("Title: {{title}}!", "Title: Hi &amp; Bye!", 2);
    if (fail)
        return fail;

    /* 4-5: triple-mustache raw output through the wrapper. */
    fail = wrap_check_render("Raw: {{{title}}}", "Raw: Hi & Bye", 4);
    if (fail)
        return fail;

    printf("test_core_wrap: all 5 checks passed\n");
    return 0;
}

int main(void)
{
    int rc = run_render_suite();
    if (rc != 0)
        return rc;
    return run_wrap_suite();
}