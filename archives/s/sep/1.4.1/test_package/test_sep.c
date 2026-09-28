#include <math.h>
#include <stdio.h>
#include <string.h>

#include <sep.h>

static int checks;

#define CHECK(condition, message)                                                \
  do {                                                                           \
    ++checks;                                                                     \
    if (!(condition)) {                                                           \
      fprintf(stderr, "check %d failed: %s\n", checks, message);                 \
      return 1;                                                                   \
    }                                                                             \
  } while (0)

int main(void) {
  enum { width = 16, height = 16, pixels = width * height };
  float image[pixels];
  float background[pixels];
  unsigned char ellipse_mask[pixels];
  sep_bkg *bkg = NULL;
  sep_catalog *catalog = NULL;
  sep_image descriptor;
  double sum = 0.0;
  double sum_error = 0.0;
  double area = 0.0;
  double a = 0.0;
  double b = 0.0;
  double theta = 0.0;
  double cxx = 0.0;
  double cyy = 0.0;
  double cxy = 0.0;
  short flag = 0;
  size_t old_stack;
  int old_limit;
  int status;
  int x;
  int y;
  int marked = 0;

  for (y = 0; y < height; ++y) {
    for (x = 0; x < width; ++x) {
      image[y * width + x] = 2.0f;
    }
  }
  for (y = 6; y <= 9; ++y) {
    for (x = 6; x <= 9; ++x) {
      image[y * width + x] = 22.0f;
    }
  }

  memset(&descriptor, 0, sizeof(descriptor));
  descriptor.data = image;
  descriptor.dtype = SEP_TFLOAT;
  descriptor.w = width;
  descriptor.h = height;
  descriptor.noise_type = SEP_NOISE_NONE;
  descriptor.noiseval = 1.0;
  descriptor.gain = 0.0;

  CHECK(strcmp(sep_version_string, "1.4.1") == 0, "version string");
  status = sep_background(&descriptor, 4, 4, 3, 3, 0.0, &bkg);
  CHECK(status == 0, "background calculation status");
  CHECK(bkg != NULL, "background allocation");
  CHECK(fabs(sep_bkg_global(bkg) - 2.0) < 0.05, "global background");
  CHECK(sep_bkg_globalrms(bkg) >= 0.0, "global background rms");
  CHECK(fabs(sep_bkg_pix(bkg, 0, 0) - 2.0) < 0.1, "background pixel");
  status = sep_bkg_array(bkg, background, SEP_TFLOAT);
  CHECK(status == 0, "background array status");
  CHECK(fabs(background[0] - 2.0f) < 0.1, "background array value");

  status = sep_sum_circle(
      &descriptor, 7.5, 7.5, 2.0, 0, 5, 0, &sum, &sum_error, &area, &flag);
  CHECK(status == 0, "circle aperture status");
  CHECK(sum > 200.0, "circle aperture flux");
  CHECK(area > 11.0 && area < 14.0, "circle aperture area");
  CHECK(flag == 0, "circle aperture flags");

  status = sep_extract(
      &descriptor, 10.0f, SEP_THRESH_ABS, 4, NULL, 0, 0, SEP_FILTER_CONV,
      16, 0.005, 1, 1.0, &catalog);
  CHECK(status == 0, "source extraction status");
  CHECK(catalog != NULL, "catalog allocation");
  CHECK(catalog->nobj == 1, "single source extracted");
  CHECK(catalog->npix[0] >= 16, "source pixel count");
  CHECK(fabs(catalog->x[0] - 7.5) < 0.2, "source x centroid");
  CHECK(fabs(catalog->y[0] - 7.5) < 0.2, "source y centroid");
  CHECK(catalog->flux[0] > 300.0f, "source flux");

  sep_ellipse_coeffs(3.0, 2.0, 0.25, &cxx, &cyy, &cxy);
  CHECK(cxx > 0.0 && cyy > 0.0, "ellipse coefficients");
  status = sep_ellipse_axes(cxx, cyy, cxy, &a, &b, &theta);
  CHECK(status == 0, "ellipse axes status");
  CHECK(fabs(a - 3.0) < 1.0e-10, "ellipse major axis");
  CHECK(fabs(b - 2.0) < 1.0e-10, "ellipse minor axis");
  CHECK(fabs(theta - 0.25) < 1.0e-10, "ellipse angle");

  memset(ellipse_mask, 0, sizeof(ellipse_mask));
  sep_set_ellipse(ellipse_mask, width, height, 7.5, 7.5, cxx, cyy, cxy, 1.0, 7);
  for (x = 0; x < pixels; ++x) {
    if (ellipse_mask[x] == 7) {
      ++marked;
    }
  }
  CHECK(marked > 0, "ellipse mask populated");
  CHECK(ellipse_mask[7 * width + 7] == 7, "ellipse center populated");

  old_stack = sep_get_extract_pixstack();
  sep_set_extract_pixstack(old_stack + 128);
  CHECK(sep_get_extract_pixstack() == old_stack + 128, "pixel stack setter");
  sep_set_extract_pixstack(old_stack);
  CHECK(sep_get_extract_pixstack() == old_stack, "pixel stack restore");
  old_limit = sep_get_sub_object_limit();
  sep_set_sub_object_limit(old_limit + 1);
  CHECK(sep_get_sub_object_limit() == old_limit + 1, "sub-object limit setter");
  sep_set_sub_object_limit(old_limit);
  CHECK(sep_get_sub_object_limit() == old_limit, "sub-object limit restore");

  sep_catalog_free(catalog);
  sep_bkg_free(bkg);
  if (checks != 30) {
    fprintf(stderr, "unexpected consumer check count: %d\n", checks);
    return 1;
  }
  printf("SEP consumer API checks passed: %d\n", checks);
  return 0;
}
