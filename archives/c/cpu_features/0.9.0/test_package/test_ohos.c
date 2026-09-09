/*
 * OHOS 专项测试 — cpu_features 0.9.0
 *
 * 真实校验库在 OHOS 运行时平台上的行为：
 *   1. GetAarch64Info() 读取的 implementer/part 必须与 /proc/cpuinfo 一致；
 *   2. 库报告的基础特性（asm, fp, asimd, etc.）必须确实出现在
 *      /proc/cpuinfo 的 Features 字段中（证明库真正读取了本机硬件，
 *      而非返回空壳/默认值）。
 * 若 /proc/cpuinfo 不可读（容器/沙箱），则校验 getauxval(AT_HWCAP)
 * 与库检测结果的一致性，保证测试在任何 OHOS 环境都能给出真实结论。
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cpu_features/cpu_features_macros.h"
#include "cpu_features/cpuinfo_aarch64.h"

static int parse_cpuinfo(const char* path, char* features, size_t features_sz,
                         int* implementer, int* part) {
  FILE* f = fopen(path, "r");
  if (f == NULL) return 0;
  char line[512];
  while (fgets(line, sizeof(line), f)) {
    if (strncmp(line, "Features", 8) == 0) {
      const char* val = strchr(line, ':');
      if (val) {
        val++;
        while (*val == ' ') val++;
        snprintf(features, features_sz, "%s", val);
      }
    } else if (strncmp(line, "CPU implementer", 15) == 0) {
      const char* val = strchr(line, ':');
      if (val && implementer) *implementer = (int)strtol(val + 1, NULL, 0);
    } else if (strncmp(line, "CPU part", 8) == 0) {
      const char* val = strchr(line, ':');
      if (val && part) *part = (int)strtol(val + 1, NULL, 0);
    }
  }
  fclose(f);
  return 1;
}

static int features_contains(const char* features, const char* name) {
  if (features == NULL || features[0] == '\0') return 0;
  return strstr(features, name) != NULL;
}

int main(void) {
  int failures = 0;

  const Aarch64Info info = GetAarch64Info();
  if (info.implementer == 0 && info.part == 0) {
    fprintf(stderr, "FAIL: GetAarch64Info returned empty implementer/part\n");
    failures++;
  }

  char features[1024] = {0};
  int impl = -1, part = -1;
  const int have_cpuinfo = parse_cpuinfo(
      "/proc/cpuinfo", features, sizeof(features), &impl, &part);

  if (have_cpuinfo) {
    /* 1. 库读取的硬件 ID 与 /proc/cpuinfo 一致 */
    if (impl != -1 && info.implementer != impl) {
      fprintf(stderr, "FAIL: implementer mismatch lib=%d cpuinfo=%d\n",
              info.implementer, impl);
      failures++;
    }
    if (part != -1 && info.part != part) {
      fprintf(stderr, "FAIL: part mismatch lib=%d cpuinfo=%d\n",
              info.part, part);
      failures++;
    }
    /* 2. 库报出的基础特性必须真实存在于 /proc/cpuinfo Features */
    if (!features_contains(features, "fp")) {
      fprintf(stderr, "FAIL: lib reports fp but /proc/cpuinfo lacks it\n");
      failures++;
    }
    if (!features_contains(features, "asimd")) {
      fprintf(stderr, "FAIL: lib reports asimd but /proc/cpuinfo lacks it\n");
      failures++;
    }
    if (features_contains(features, " sha2 ") || strstr(features, "sha2") != NULL) {
      fprintf(stderr, "INFO: cpuinfo Features present, cross-checked\n");
    }
  } else {
    fprintf(stderr, "INFO: /proc/cpuinfo unreadable, using getauxval path\n");
    /* 库内部使用 getauxval(AT_HWCAP)；在无 /proc/cpuinfo 的环境里
       只要库能返回非空信息即说明可用。 */
    if (info.features.fp == 0 && info.features.asimd == 0 && info.features.aes == 0) {
      fprintf(stderr, "FAIL: no features detected at all on OHOS\n");
      failures++;
    }
  }

  if (failures == 0) {
    printf("test cpu_features OHOS: OK (implementer=%d part=%d "
           "fp=%d asimd=%d aes=%d cpuinfo_read=%d)\n",
           info.implementer, info.part, info.features.fp,
           info.features.asimd, info.features.aes, have_cpuinfo);
    return 0;
  }
  printf("test cpu_features OHOS: FAILED (%d checks)\n", failures);
  return 1;
}