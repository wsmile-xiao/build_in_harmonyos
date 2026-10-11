/* test_libpuzzle.c — libpuzzle 0.11 consumer test (R34: real API calls).
 *
 * Generates its own PNG fixtures at runtime with GD (no binary fixtures
 * that could silently go missing), then exercises the public API the way
 * upstream regress_1/2/3 do: fill cvecs from files, normalized distance,
 * compress/uncompress roundtrip checksum, dvec path, and the error path.
 *
 * Usage: test_libpuzzle <workdir>
 * Exit code: number of failed cases (0 = all 6 pass).
 */
#include <stdio.h>
#include <string.h>

#include <gd.h>
#include <puzzle.h>

#define IMG_W 96
#define IMG_H 96

static int g_failures;

#define CHECK(cond, ...) do { \
    if (!(cond)) { \
        printf("[fail] " __VA_ARGS__); \
        printf("\n"); \
        return 1; \
    } \
} while (0)

static int make_image(const char *path, int perturb) {
    gdImagePtr im = gdImageCreateTrueColor(IMG_W, IMG_H);
    FILE *out;
    int red, green, blue, black;
    if (im == NULL) {
        return 1;
    }
    red = gdImageColorAllocate(im, 200, 30, 30);
    green = gdImageColorAllocate(im, 30, 200, 30);
    blue = gdImageColorAllocate(im, 30, 30, 200);
    black = gdImageColorAllocate(im, 0, 0, 0);
    gdImageFilledRectangle(im, 0, 0, IMG_W - 1, IMG_H - 1, red);
    gdImageLine(im, 0, 0, IMG_W - 1, IMG_H - 1, green);
    gdImageLine(im, 0, IMG_H - 1, IMG_W - 1, 0, blue);
    gdImageFilledRectangle(im, 10, 10, 40, 40, green);
    if (perturb) {
        /* Tiny local change: the pair must still read as similar. */
        gdImageFilledRectangle(im, 60, 60, 63, 63, black);
    }
    out = fopen(path, "wb");
    if (out == NULL) {
        gdImageDestroy(im);
        return 1;
    }
    gdImagePng(im, out);
    fclose(out);
    gdImageDestroy(im);
    return 0;
}

/* Case 1: context tunables accept sane values. */
static int test_context_tunables(void) {
    PuzzleContext context;
    puzzle_init_context(&context);
    CHECK(puzzle_set_lambdas(&context, 9) == 0, "set_lambdas");
    CHECK(puzzle_set_max_width(&context, 1024) == 0, "set_max_width");
    CHECK(puzzle_set_max_height(&context, 1024) == 0, "set_max_height");
    CHECK(puzzle_set_autocrop(&context, 1) == 0, "set_autocrop");
    CHECK(puzzle_set_noise_cutoff(&context, 2.0) == 0, "set_noise_cutoff");
    CHECK(puzzle_set_p_ratio(&context, 4.0) == 0, "set_p_ratio");
    CHECK(puzzle_set_contrast_barrier_for_cropping(&context, 0.05) == 0,
          "set_contrast_barrier");
    CHECK(puzzle_set_max_cropping_ratio(&context, 0.25) == 0,
          "set_max_cropping_ratio");
    puzzle_free_context(&context);
    return 0;
}

/* Case 2: near-identical images read as similar (both text modes). */
static int test_fill_and_similar(const char *t1, const char *t2) {
    PuzzleContext context;
    PuzzleCvec cvec1, cvec2;
    double d_fix1, d_fix0;
    int rc = 0;
    puzzle_init_context(&context);
    puzzle_init_cvec(&context, &cvec1);
    puzzle_init_cvec(&context, &cvec2);
    if (puzzle_fill_cvec_from_file(&context, &cvec1, t1) != 0) {
        printf("[fail] fill t1\n");
        rc = 1;
        goto out;
    }
    if (puzzle_fill_cvec_from_file(&context, &cvec2, t2) != 0) {
        printf("[fail] fill t2\n");
        rc = 1;
        goto out;
    }
    d_fix1 = puzzle_vector_normalized_distance(&context, &cvec1, &cvec2, 1);
    d_fix0 = puzzle_vector_normalized_distance(&context, &cvec1, &cvec2, 0);
    printf("[info] similar-pair distances: fix1=%g fix0=%g\n", d_fix1, d_fix0);
    if (!(d_fix1 < PUZZLE_CVEC_SIMILARITY_THRESHOLD)) {
        printf("[fail] fix1 distance %g >= 0.6\n", d_fix1);
        rc = 1;
    }
    if (!(d_fix0 < PUZZLE_CVEC_SIMILARITY_THRESHOLD)) {
        printf("[fail] fix0 distance %g >= 0.6\n", d_fix0);
        rc = 1;
    }
out:
    puzzle_free_cvec(&context, &cvec1);
    puzzle_free_cvec(&context, &cvec2);
    puzzle_free_context(&context);
    return rc;
}

/* Case 3: distance is symmetric (upstream regress_2 principle). */
static int test_symmetry(const char *t1, const char *t2) {
    PuzzleContext context;
    PuzzleCvec cvec1, cvec2;
    double d12, d21;
    int rc = 0;
    puzzle_init_context(&context);
    puzzle_init_cvec(&context, &cvec1);
    puzzle_init_cvec(&context, &cvec2);
    if (puzzle_fill_cvec_from_file(&context, &cvec1, t1) != 0 ||
        puzzle_fill_cvec_from_file(&context, &cvec2, t2) != 0) {
        printf("[fail] symmetry fill\n");
        rc = 1;
        goto out;
    }
    d12 = puzzle_vector_normalized_distance(&context, &cvec1, &cvec2, 1);
    d21 = puzzle_vector_normalized_distance(&context, &cvec2, &cvec1, 1);
    if ((int)(d12 * 100.0) != (int)(d21 * 100.0)) {
        printf("[fail] asymmetric: %g vs %g\n", d12, d21);
        rc = 1;
    }
out:
    puzzle_free_cvec(&context, &cvec1);
    puzzle_free_cvec(&context, &cvec2);
    puzzle_free_context(&context);
    return rc;
}

/* Case 4: compress/uncompress roundtrip preserves the checksum. */
static int test_compress_roundtrip(const char *t1) {
    PuzzleContext context;
    PuzzleCvec cvec;
    PuzzleCompressedCvec compressed;
    unsigned int sum_before = 0, sum_after = 0;
    int rc = 0;
    puzzle_init_context(&context);
    puzzle_init_cvec(&context, &cvec);
    puzzle_init_compressed_cvec(&context, &compressed);
    if (puzzle_fill_cvec_from_file(&context, &cvec, t1) != 0) {
        printf("[fail] roundtrip fill\n");
        rc = 1;
        goto out;
    }
    CHECK(puzzle_compress_cvec(&context, &compressed, &cvec) == 0, "compress");
    puzzle_cvec_cksum(&context, &cvec, &sum_before);
    puzzle_free_cvec(&context, &cvec);
    puzzle_init_cvec(&context, &cvec);
    CHECK(puzzle_uncompress_cvec(&context, &compressed, &cvec) == 0, "uncompress");
    puzzle_cvec_cksum(&context, &cvec, &sum_after);
    printf("[info] roundtrip cksum: %u -> %u\n", sum_before, sum_after);
    CHECK(sum_before == sum_after, "cksum mismatch %u vs %u", sum_before, sum_after);
out:
    puzzle_free_cvec(&context, &cvec);
    puzzle_free_compressed_cvec(&context, &compressed);
    puzzle_free_context(&context);
    return rc;
}

/* Case 5: dvec path agrees with itself (self distance is zero). */
static int test_dvec_path(const char *t1) {
    PuzzleContext context;
    PuzzleDvec dvec;
    PuzzleCvec cvec;
    double d;
    int rc = 0;
    puzzle_init_context(&context);
    puzzle_init_dvec(&context, &dvec);
    puzzle_init_cvec(&context, &cvec);
    if (puzzle_fill_dvec_from_file(&context, &dvec, t1) != 0) {
        printf("[fail] fill_dvec\n");
        rc = 1;
        goto out;
    }
    CHECK(puzzle_fill_cvec_from_dvec(&context, &cvec, &dvec) == 0,
          "fill_cvec_from_dvec");
    d = puzzle_vector_normalized_distance(&context, &cvec, &cvec, 1);
    CHECK(d == 0.0, "self distance %g != 0", d);
out:
    puzzle_free_dvec(&context, &dvec);
    puzzle_free_cvec(&context, &cvec);
    puzzle_free_context(&context);
    return rc;
}

/* Case 6: missing file is reported (error path, deterministic). */
static int test_missing_file(void) {
    PuzzleContext context;
    PuzzleCvec cvec;
    int rc;
    puzzle_init_context(&context);
    puzzle_init_cvec(&context, &cvec);
    rc = puzzle_fill_cvec_from_file(&context, &cvec, "no-such-file.png");
    puzzle_free_cvec(&context, &cvec);
    puzzle_free_context(&context);
    CHECK(rc != 0, "missing file must fail");
    return 0;
}

int main(int argc, char **argv) {
    const char *workdir = argc > 1 ? argv[1] : ".";
    char t1[1024], t2[1024];
    int failed = 0;
    snprintf(t1, sizeof(t1), "%s/t1.png", workdir);
    snprintf(t2, sizeof(t2), "%s/t2.png", workdir);

    printf("=== libpuzzle 0.11 consumer test (OpenHarmony/aarch64) ===\n");
    if (make_image(t1, 0) != 0 || make_image(t2, 1) != 0) {
        printf("[fail] fixture generation\n");
        return 6;
    }
    printf("[info] fixtures: %s %s\n", t1, t2);

    if (test_context_tunables() != 0) { printf("case 1 tunables FAILED\n"); failed++; }
    else { printf("case 1 tunables ok\n"); }
    if (test_fill_and_similar(t1, t2) != 0) { printf("case 2 similar FAILED\n"); failed++; }
    else { printf("case 2 similar ok\n"); }
    if (test_symmetry(t1, t2) != 0) { printf("case 3 symmetry FAILED\n"); failed++; }
    else { printf("case 3 symmetry ok\n"); }
    if (test_compress_roundtrip(t1) != 0) { printf("case 4 roundtrip FAILED\n"); failed++; }
    else { printf("case 4 roundtrip ok\n"); }
    if (test_dvec_path(t1) != 0) { printf("case 5 dvec FAILED\n"); failed++; }
    else { printf("case 5 dvec ok\n"); }
    if (test_missing_file() != 0) { printf("case 6 missing-file FAILED\n"); failed++; }
    else { printf("case 6 missing-file ok\n"); }

    printf("=== C API: %d/6 cases passed ===\n", 6 - failed);
    return failed;
}
