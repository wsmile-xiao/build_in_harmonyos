#include <pixman.h>
#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libpixman-1.so"
#endif

typedef const char *(*version_fn)(void);
typedef void (*region_init_fn)(pixman_region32_t *);
typedef void (*region_init_rect_fn)(pixman_region32_t *, int, int, unsigned int, unsigned int);
typedef pixman_bool_t (*region_union_rect_fn)(pixman_region32_t *, const pixman_region32_t *, int, int, unsigned int, unsigned int);
typedef pixman_bool_t (*region_contains_point_fn)(const pixman_region32_t *, int, int, pixman_box32_t *);
typedef pixman_region_overlap_t (*region_contains_rectangle_fn)(const pixman_region32_t *, const pixman_box32_t *);
typedef void (*region_fini_fn)(pixman_region32_t *);

static void *load_symbol(void *handle, const char *name)
{
    void *sym = dlsym(handle, name);
    if (!sym) {
        fprintf(stderr, "dlsym %s failed: %s\n", name, dlerror());
    }
    return sym;
}

#define LOAD_SYM(handle, name, type) ((type)load_symbol((handle), (name)))

static int box_equals(const pixman_box32_t *a, const pixman_box32_t *b)
{
    return a->x1 == b->x1 && a->y1 == b->y1 && a->x2 == b->x2 && a->y2 == b->y2;
}

static int expect_point_case(const char *case_name,
                             region_contains_point_fn contains_point,
                             const pixman_region32_t *region,
                             int x,
                             int y,
                             const pixman_box32_t *expected_box,
                             pixman_bool_t expected_inside,
                             const char *label)
{
    pixman_box32_t actual_box = { 0, 0, 0, 0 };
    pixman_bool_t actual_inside = contains_point(region, x, y, &actual_box);
    if (!!actual_inside != !!expected_inside) {
        fprintf(stderr, "%s: %s expected %s but got %s\n",
                case_name, label, expected_inside ? "inside" : "outside", actual_inside ? "inside" : "outside");
        return 0;
    }
    if (expected_inside && !box_equals(&actual_box, expected_box)) {
        fprintf(stderr, "%s: %s box mismatch: got %d %d %d %d, expect %d %d %d %d\n",
                case_name,
                label,
                actual_box.x1, actual_box.y1, actual_box.x2, actual_box.y2,
                expected_box->x1, expected_box->y1, expected_box->x2, expected_box->y2);
        return 0;
    }
    return 1;
}

static int expect_rectangle_case(const char *case_name,
                                 region_contains_rectangle_fn contains_rectangle,
                                 const pixman_region32_t *region,
                                 const pixman_box32_t *rect,
                                 pixman_region_overlap_t expected,
                                 const char *label)
{
    pixman_region_overlap_t actual = contains_rectangle(region, rect);
    if (actual != expected) {
        fprintf(stderr, "%s: %s expected %d but got %d\n", case_name, label, expected, actual);
        return 0;
    }
    return 1;
}

static int run_simple_rect_case(region_contains_point_fn contains_point,
                                region_init_rect_fn init_rect,
                                region_contains_rectangle_fn contains_rectangle,
                                region_fini_fn fini_region)
{
    const char *case_name = "simple-rect";
    pixman_region32_t region;
    pixman_box32_t inside_box = { 1, 2, 11, 22 };
    pixman_box32_t inner_rect = { 2, 3, 5, 6 };
    pixman_box32_t outer_rect = { 50, 50, 60, 60 };
    pixman_box32_t partial_rect = { 0, 0, 3, 3 };
    int ok = 1;

    init_rect(&region, 1, 2, 10, 20);
    ok &= expect_point_case(case_name, contains_point, &region, 5, 5, &inside_box, 1, "inside");
    ok &= expect_point_case(case_name, contains_point, &region, 50, 50, NULL, 0, "outside");
    ok &= expect_point_case(case_name, contains_point, &region, 11, 22, NULL, 0, "edge-outside");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &inner_rect, PIXMAN_REGION_IN, "inner");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &outer_rect, PIXMAN_REGION_OUT, "outer");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &partial_rect, PIXMAN_REGION_PART, "partial");
    fini_region(&region);
    return ok;
}

static int run_union_case(region_contains_point_fn contains_point,
                          region_init_rect_fn init_rect,
                          region_union_rect_fn union_rect,
                          region_contains_rectangle_fn contains_rectangle,
                          region_fini_fn fini_region)
{
    const char *case_name = "union-rects";
    pixman_region32_t region;
    pixman_box32_t inside_box = { 10, 10, 14, 14 };
    pixman_box32_t inner_rect = { 1, 1, 2, 2 };
    pixman_box32_t outer_rect = { 20, 20, 22, 22 };
    pixman_box32_t partial_rect = { 3, 3, 11, 11 };
    int ok = 1;

    init_rect(&region, 0, 0, 4, 4);
    union_rect(&region, &region, 10, 10, 4, 4);
    ok &= expect_point_case(case_name, contains_point, &region, 11, 11, &inside_box, 1, "inside-second-rect");
    ok &= expect_point_case(case_name, contains_point, &region, 7, 7, NULL, 0, "gap-outside");
    ok &= expect_point_case(case_name, contains_point, &region, 14, 14, NULL, 0, "boundary-outside");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &inner_rect, PIXMAN_REGION_IN, "inner");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &outer_rect, PIXMAN_REGION_OUT, "outer");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &partial_rect, PIXMAN_REGION_PART, "partial");
    fini_region(&region);
    return ok;
}

static int run_empty_case(region_contains_point_fn contains_point,
                          region_init_fn init_region,
                          region_contains_rectangle_fn contains_rectangle,
                          region_fini_fn fini_region)
{
    const char *case_name = "empty-region";
    pixman_region32_t region;
    pixman_box32_t any_rect = { 0, 0, 1, 1 };
    pixman_box32_t any_other_rect = { 10, 10, 12, 12 };
    pixman_box32_t negative_rect = { -5, -5, -1, -1 };
    int ok = 1;

    init_region(&region);
    ok &= expect_point_case(case_name, contains_point, &region, 0, 0, NULL, 0, "origin");
    ok &= expect_point_case(case_name, contains_point, &region, 5, 5, NULL, 0, "positive");
    ok &= expect_point_case(case_name, contains_point, &region, -1, -1, NULL, 0, "negative");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &any_rect, PIXMAN_REGION_OUT, "any-rect");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &any_other_rect, PIXMAN_REGION_OUT, "any-other-rect");
    ok &= expect_rectangle_case(case_name, contains_rectangle, &region, &negative_rect, PIXMAN_REGION_OUT, "negative-rect");
    fini_region(&region);
    return ok;
}

int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    version_fn pixman_version = LOAD_SYM(h, "pixman_version_string", version_fn);
    region_init_fn init_region = LOAD_SYM(h, "pixman_region32_init", region_init_fn);
    region_init_rect_fn init_rect = LOAD_SYM(h, "pixman_region32_init_rect", region_init_rect_fn);
    region_union_rect_fn union_rect = LOAD_SYM(h, "pixman_region32_union_rect", region_union_rect_fn);
    region_contains_point_fn contains_point = LOAD_SYM(h, "pixman_region32_contains_point", region_contains_point_fn);
    region_contains_rectangle_fn contains_rectangle =
        LOAD_SYM(h, "pixman_region32_contains_rectangle", region_contains_rectangle_fn);
    region_fini_fn fini_region = LOAD_SYM(h, "pixman_region32_fini", region_fini_fn);
    if (!pixman_version || !init_region || !init_rect || !union_rect || !contains_point || !contains_rectangle || !fini_region) {
        dlclose(h);
        return 2;
    }

    const char *version = pixman_version();
    if (!version || !*version) { fprintf(stderr, "pixman_version_string returned empty\n"); dlclose(h); return 3; }

    if (!run_simple_rect_case(contains_point, init_rect, contains_rectangle, fini_region) ||
        !run_union_case(contains_point, init_rect, union_rect, contains_rectangle, fini_region) ||
        !run_empty_case(contains_point, init_region, contains_rectangle, fini_region)) {
        dlclose(h);
        return 4;
    }

    printf("pixman %s: adapted upstream region-contains cases + dlopen ok\n", version);
    dlclose(h);
    return 0;
}
