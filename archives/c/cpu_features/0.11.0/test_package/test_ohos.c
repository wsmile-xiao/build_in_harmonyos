/*
 * OHOS 专项测试 — cpu_features 0.11.0
 *
 * 真实校验库在 OHOS 运行时平台上的行为：
 *   1. GetAarch64Info() 读取的 implementer/part 必须与 /proc/cpuinfo 一致；
 *   2. 双向交叉核对：库报告的基础特性（fp/asimd）与 /proc/cpuinfo 的
 *      Features 字段（空格分隔的 token 列表，词级精确匹配）互相印证——
 *      库报出则 cpuinfo 必含，cpuinfo 含则库必报出（证明库真正读取了
 *      本机硬件而非返回空壳/默认值）。
 * 若 /proc/cpuinfo 不可读（容器/沙箱），则退化为校验库能检测到非空
 * 特性集（库内部实现路径为 getauxval(AT_HWCAP)，此处不做直接交叉核对）。
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cpu_features/cpu_features_macros.h"
#include "cpu_features/cpuinfo_aarch64.h"

/* 解析 /proc/cpuinfo：Features 行、CPU implementer、CPU part。
 * 数值字段经 endptr 校验，解析失败不写入（保持 -1 哨兵值）。 */
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
        /* 去掉行尾换行 */
        snprintf(features, features_sz, "%s", val);
        features[strcspn(features, "\r\n")] = '\0';
      }
    } else if (strncmp(line, "CPU implementer", 15) == 0) {
      const char* val = strchr(line, ':');
      if (val && implementer) {
        char* end = NULL;
        long v = strtol(val + 1, &end, 0);
        if (end != val + 1) *implementer = (int)v;
      }
    } else if (strncmp(line, "CPU part", 8) == 0) {
      const char* val = strchr(line, ':');
      if (val && part) {
        char* end = NULL;
        long v = strtol(val + 1, &end, 0);
        if (end != val + 1) *part = (int)v;
      }
    }
  }
  fclose(f);
  return 1;
}

/* Features 是空格分隔的 token 列表（如 "fp asimd evtstrm aes ..."）。
 * 词级精确匹配：完整 token 相等才命中，避免 "fp" 误中 "fphp" 等子串假阳性。 */
static int features_has_token(const char* features, const char* name) {
  if (features == NULL || name == NULL) return 0;
  const char* p = features;
  const size_t n = strlen(name);
  while (*p != '\0') {
    while (*p == ' ' || *p == '\t') p++;
    if (*p == '\0') break;
    const char* tok = p;
    while (*p != '\0' && *p != ' ' && *p != '\t') p++;
    if ((size_t)(p - tok) == n && strncmp(tok, name, n) == 0) return 1;
  }
  return 0;
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

  if (have_cpuinfo && features[0] != '\0') {
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
    /* 2. 库报出的基础特性必须真实存在于 /proc/cpuinfo Features（词级匹配） */
    if (info.features.fp && !features_has_token(features, "fp")) {
      fprintf(stderr, "FAIL: lib reports fp=%d but /proc/cpuinfo lacks it\n",
              info.features.fp);
      failures++;
    }
    if (info.features.asimd && !features_has_token(features, "asimd")) {
      fprintf(stderr,
              "FAIL: lib reports asimd=%d but /proc/cpuinfo lacks it\n",
              info.features.asimd);
      failures++;
    }
    /* 3. 反向核对：cpuinfo 中存在的基础特性，库必须报出 */
    if (features_has_token(features, "fp") && !info.features.fp) {
      fprintf(stderr, "FAIL: /proc/cpuinfo has fp but lib reports fp=0\n");
      failures++;
    }
    if (features_has_token(features, "asimd") && !info.features.asimd) {
      fprintf(stderr, "FAIL: /proc/cpuinfo has asimd but lib reports asimd=0\n");
      failures++;
    }
  } else {
    fprintf(stderr,
            "INFO: /proc/cpuinfo unreadable/empty, fallback check only\n");
    /* 无 /proc/cpuinfo 时退化为非空特性集校验（库内部走 getauxval 路径），
       此处不与 auxv 做直接交叉核对。 */
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
