#ifndef __OHOS__
#error "test_cubature_ohos.c must be compiled for HarmonyOS"
#endif

#include <cubature.h>

#include <dlfcn.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>

static int square(unsigned ndim, const double *x, void *data, unsigned fdim,
                  double *fval) {
  (void)data;
  if (ndim != 1 || fdim != 1) {
    return 1;
  }
  fval[0] = x[0] * x[0];
  return 0;
}

static int require_symbol(void *handle, const char *name) {
  const char *error;

  dlerror();
  if (dlsym(handle, name) == NULL) {
    error = dlerror();
    fprintf(stderr, "missing symbol %s: %s\n", name,
            error == NULL ? "unknown error" : error);
    return 1;
  }
  return 0;
}

int main(void) {
  static const char *const symbols[] = {
      "hcubature", "hcubature_v", "pcubature", "pcubature_v", "pcubature_v_buf",
  };
  const double lower[1] = {0.0};
  const double upper[1] = {1.0};
  const size_t symbol_count = sizeof(symbols) / sizeof(symbols[0]);
  double value = 0.0;
  double error = 0.0;
  void *handle;
  size_t index;
  int status;

  handle = dlopen("libcubature.so", RTLD_NOW | RTLD_LOCAL);
  if (handle == NULL) {
    fprintf(stderr, "HarmonyOS dlopen failed: %s\n", dlerror());
    return 1;
  }

  for (index = 0; index < symbol_count; ++index) {
    if (require_symbol(handle, symbols[index]) != 0) {
      dlclose(handle);
      return 1;
    }
  }

  status = hcubature(1, square, NULL, 1, lower, upper, 0, 0.0, 1e-10,
                     ERROR_INDIVIDUAL, &value, &error);
  if (status != 0) {
    fprintf(stderr, "HarmonyOS hcubature returned status %d\n", status);
    dlclose(handle);
    return 1;
  }
  if (fabs(value - (1.0 / 3.0)) > 1e-9) {
    fprintf(stderr, "HarmonyOS integral %.17g is outside tolerance\n", value);
    dlclose(handle);
    return 1;
  }
  if (dlclose(handle) != 0) {
    fprintf(stderr, "HarmonyOS dlclose failed: %s\n", dlerror());
    return 1;
  }

  puts("HarmonyOS cubature checks passed: 9 assertions");
  return 0;
}
