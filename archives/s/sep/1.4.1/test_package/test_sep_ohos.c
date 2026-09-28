#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <sep.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#if !defined(__aarch64__)
#error "HarmonyOS PC package must target AArch64"
#endif

int main(void) {
  double pixels[64];
  sep_image image;
  sep_bkg *bkg = NULL;
  int index;
  int status;

  for (index = 0; index < 64; ++index) {
    pixels[index] = 5.0;
  }
  memset(&image, 0, sizeof(image));
  image.data = pixels;
  image.dtype = SEP_TDOUBLE;
  image.w = 8;
  image.h = 8;
  image.noise_type = SEP_NOISE_NONE;

  if (sizeof(void *) != 8 || sizeof(int64_t) != 8) {
    fprintf(stderr, "unexpected HarmonyOS AArch64 ABI widths\n");
    return 1;
  }
  if (strcmp(sep_version_string, "1.4.1") != 0) {
    fprintf(stderr, "unexpected library version: %s\n", sep_version_string);
    return 1;
  }
  status = sep_background(&image, 4, 4, 1, 1, 0.0, &bkg);
  if (status != 0 || bkg == NULL) {
    fprintf(stderr, "double-image background failed on HarmonyOS: %d\n", status);
    return 1;
  }
  if (sep_bkg_global(bkg) < 4.99f || sep_bkg_global(bkg) > 5.01f) {
    fprintf(stderr, "unexpected HarmonyOS background value\n");
    sep_bkg_free(bkg);
    return 1;
  }
  sep_bkg_free(bkg);
  puts("SEP HarmonyOS AArch64 ABI and runtime checks passed");
  return 0;
}
