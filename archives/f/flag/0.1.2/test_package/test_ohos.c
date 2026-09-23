/*
 * test_ohos.c — HarmonyOS 专项测试 — flag 0.1.2
 *
 * 在 OHOS PC (aarch64) 工具链与运行时下，覆盖 flag 公开 API 的完整调用面：
 *   - flagset_write_usage() 输出到 FILE*（OHOS 上常见于 --help）
 *   - flag_str 别名 / flag_string 单例
 *   - 错误联合体 error.flag / error.arg 的字段可读
 *   - 布尔取反（--no-*）、整型/字符串/布尔混合解析、argc/argv 保留
 *   - FLAGS_MAX 边界（大量 flag 定义不越界）
 * 全部通过公开头文件 flag.h 与 libflag.a 链接调用，可观察输出与退出码。
 */
#include <stdio.h>
#include <string.h>
#include "flag.h"

static int failures = 0;

#define CHECK(cond, msg) \
  do { \
    if (!(cond)) { \
      printf("OHOS FAIL: %s\n", msg); \
      failures++; \
    } else { \
      printf("OHOS OK:   %s\n", msg); \
    } \
  } while (0)

int main(void) {
  /* 1. flagset_write_usage() 输出到 stdout（模拟 --help） */
  {
    flagset_t *set = flagset_new();
    set->usage = "test_ohos [options]";
    flagset_int(set, &(int){0}, "port", "Listen port");
    flagset_bool(set, &(bool){false}, "verbose", "Verbose output");
    flagset_write_usage(set, stdout, "test_ohos");
    fflush(stdout);
    CHECK(set->nflags == 2, "write_usage reflects nflags=2");
    flagset_free(set);
  }

  /* 2. 混合类型解析 + 布尔取反 + 位置参数保留 */
  {
    int port = 0;
    bool verbose = true;
    const char *host = NULL;
    const char *args[] = {"server", "--port", "8080", "--no-verbose", "--host", "0.0.0.0", "extra1", "extra2"};

    flagset_t *set = flagset_new();
    flagset_int(set, &port, "port", "");
    flagset_bool(set, &verbose, "verbose", "");
    flagset_string(set, &host, "host", "");
    flag_error err = flagset_parse(set, 8, args);

    CHECK(err == FLAG_OK, "mixed parse returns FLAG_OK");
    CHECK(port == 8080, "int flag --port 8080 parsed");
    CHECK(verbose == false, "bool negation --no-verbose parsed");
    CHECK(host != NULL && strcmp(host, "0.0.0.0") == 0, "string flag --host parsed");
    CHECK(set->argc == 3, "3 positional args preserved");
    CHECK(strcmp(set->argv[0], "server") == 0 && strcmp(set->argv[2], "extra2") == 0,
          "positional args content preserved");
    flagset_free(set);
  }

  /* 3. 错误联合体字段可读：未定义 flag → error.arg；缺参数 → error.flag */
  {
    const char *args[] = {"--bogus"};
    flagset_t *set = flagset_new();
    flag_error err = flagset_parse(set, 1, args);
    CHECK(err == FLAG_ERROR_UNDEFINED_FLAG, "undefined flag error code");
    CHECK(set->error.arg != NULL && strcmp(set->error.arg, "--bogus") == 0,
          "error.arg names the undefined flag");

    int n = 0;
    const char *args2[] = {"--num"};
    flagset_t *set2 = flagset_new();
    flagset_int(set2, &n, "num", "");
    err = flagset_parse(set2, 1, args2);
    CHECK(err == FLAG_ERROR_ARG_MISSING, "missing arg error code");
    CHECK(set2->error.flag != NULL && strcmp(set2->error.flag->name, "num") == 0,
          "error.flag names the flag missing its argument");
    flagset_free(set);
    flagset_free(set2);
  }

  /* 4. flag_str 别名与单例 flag_string */
  {
    const char *val = NULL;
    const char *args[] = {"app", "--out", "/data/tmp/out.log"};
    flag_str(&val, "out", "Output path");
    flag_parse(3, args, "0.1.2");
    CHECK(val != NULL && strcmp(val, "/data/tmp/out.log") == 0,
          "flag_str alias parses --out path");
  }

  /* 5. FLAGS_MAX 边界：定义接近上限的 flag 不越界 */
  {
    flagset_t *set = flagset_new();
    int vals[FLAGS_MAX];
    for (int i = 0; i < FLAGS_MAX; i++) {
      vals[i] = i;
      char name[16];
      snprintf(name, sizeof(name), "f%d", i);
      flagset_int(set, &vals[i], name, "");
    }
    CHECK(set->nflags == FLAGS_MAX, "FLAGS_MAX flags accepted without overflow");
    flagset_free(set);
  }

  if (failures == 0) {
    printf("test_ohos: ALL PASS (%d checks)\n", 13);
    return 0;
  }
  printf("test_ohos: %d CHECK(S) FAILED\n", failures);
  return 1;
}