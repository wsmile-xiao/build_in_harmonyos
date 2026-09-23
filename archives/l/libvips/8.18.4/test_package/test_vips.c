/* libvips consumer test.
 *
 * Six checks over the packaged runtime surface: version reporting, image
 * creation, statistics (vips_avg), arithmetic (vips_add), and a PNG
 * encode/decode round-trip through memory buffers (libpng load + save).
 *
 * Also supports "--gen-image <path>" to materialise a black PNG through the
 * vips pipeline; the vendored upstream C tests consume it.  It must be at
 * least 64x64: test_descriptors.c reads 10-row crops at y=0 and y=20 with
 * VIPS_ACCESS_RANDOM, so the source needs a Ysize >= 30.
 */

#include <vips/vips.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks = 0;
static int failures = 0;

static void check(int ok, const char *name)
{
	checks++;
	if (ok) {
		printf("PASS: %s\n", name);
	} else {
		failures++;
		printf("FAIL: %s\n", name);
	}
}

static int gen_image(const char *path)
{
	VipsImage *image = NULL;

	if (vips_black(&image, 64, 64, NULL)) {
		fprintf(stderr, "gen_image: vips_black failed: %s\n",
			vips_error_buffer());
		return 1;
	}
	if (vips_pngsave(image, path, NULL)) {
		fprintf(stderr, "gen_image: vips_pngsave failed: %s\n",
			vips_error_buffer());
		g_object_unref(image);
		return 1;
	}
	g_object_unref(image);
	return 0;
}

int main(int argc, char **argv)
{
	VipsImage *image;
	VipsImage *a;
	VipsImage *b;
	VipsImage *sum;
	VipsImage *decoded;
	void *buf;
	size_t len;
	double average;

	if (VIPS_INIT(argv[0]))
		vips_error_exit("unable to start: %s", vips_error_buffer());

	if (argc == 3 && strcmp(argv[1], "--gen-image") == 0)
		return gen_image(argv[2]);

	check(vips_version(0) == 8 && vips_version(1) == 18,
		"libvips runtime version 8.18");

	if (vips_black(&image, 64, 64, NULL))
		vips_error_exit("vips_black failed: %s", vips_error_buffer());
	check(image->Xsize == 64 && image->Ysize == 64,
		"vips_black produces a 64x64 image");

	if (vips_avg(image, &average, NULL))
		vips_error_exit("vips_avg failed: %s", vips_error_buffer());
	check(fabs(average) < 1e-6, "vips_avg(black) is zero");

	if (vips_black(&a, 32, 32, NULL) || vips_black(&b, 32, 32, NULL))
		vips_error_exit("vips_black failed: %s", vips_error_buffer());
	if (vips_add(a, b, &sum, NULL))
		vips_error_exit("vips_add failed: %s", vips_error_buffer());
	if (vips_avg(sum, &average, NULL))
		vips_error_exit("vips_avg failed: %s", vips_error_buffer());
	check(fabs(average) < 1e-6, "vips_add(black, black) is zero");

	if (vips_black(&image, 8, 8, NULL))
		vips_error_exit("vips_black failed: %s", vips_error_buffer());
	if (vips_pngsave_buffer(image, &buf, &len, NULL))
		vips_error_exit("vips_pngsave_buffer failed: %s",
			vips_error_buffer());
	check(len > 0, "vips_pngsave_buffer produces data");

	if (vips_pngload_buffer(buf, len, &decoded, NULL))
		vips_error_exit("vips_pngload_buffer failed: %s",
			vips_error_buffer());
	check(decoded->Xsize == 8 && decoded->Ysize == 8,
		"PNG decode round-trip is 8x8");

	g_object_unref(decoded);
	g_free(buf);
	g_object_unref(image);

	vips_shutdown();

	printf("checks=%d failures=%d\n", checks, failures);
	return failures ? 1 : 0;
}
