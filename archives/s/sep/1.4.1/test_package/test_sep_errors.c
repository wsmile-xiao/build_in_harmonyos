#include <stdio.h>
#include <string.h>

#include <sep.h>

int main(void) {
  float pixels[16] = {0.0f};
  sep_image image;
  sep_bkg *bkg = NULL;
  char message[64] = {0};
  int status;

  memset(&image, 0, sizeof(image));
  image.data = pixels;
  image.dtype = -1;
  image.w = 4;
  image.h = 4;
  image.noise_type = SEP_NOISE_NONE;

  status = sep_background(&image, 2, 2, 1, 1, 0.0, &bkg);
  if (status == 0 || bkg != NULL) {
    fprintf(stderr, "illegal datatype was not rejected\n");
    return 1;
  }
  sep_get_errmsg(status, message);
  if (message[0] == '\0') {
    fprintf(stderr, "error status has no public message\n");
    return 1;
  }
  if (strstr(message, "dtype") == NULL) {
    fprintf(stderr, "unexpected error message: %s\n", message);
    return 1;
  }

  printf("SEP error-path checks passed: status=%d message=%s\n", status, message);
  return 0;
}
