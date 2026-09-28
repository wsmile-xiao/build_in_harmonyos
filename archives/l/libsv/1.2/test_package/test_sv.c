/*
 * libsv 1.2 消费者测试：验证安装后的包可被真实链接与调用。
 * 所有断言的期望值均取自上游 test/ 目录中已验证的用例
 * （test/version.c、comp.c、range.c、match.c、semvers.c、usage.c）。
 */
#include <sv/semver.h>

#include <stdio.h>
#include <string.h>

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond, msg)                          \
  do {                                            \
    g_checks++;                                   \
    if (cond) {                                   \
      printf("ok   - %s\n", msg);                 \
    } else {                                      \
      fprintf(stderr, "FAIL - %s\n", msg);        \
      g_failures++;                               \
    }                                             \
  } while (0)

/* 解析 input 后写回，与 expected 逐字节比较（对应上游 test_read） */
static int check_roundtrip(const char *input, const char *expected) {
  char buffer[1024];
  semver_t semver = {0};
  size_t elen = strlen(expected);
  int slen;

  if (semver(&semver, input)) {
    return 0;
  }
  slen = semver_write(semver, buffer, sizeof(buffer));
  if (slen <= 0 || (size_t) slen != elen || memcmp(buffer, expected, elen) != 0) {
    semver_dtor(&semver);
    return 0;
  }
  semver_dtor(&semver);
  return 1;
}

int main(void) {
  char buffer[1024];
  semver_t v = {0}, a = {0}, b = {0};
  semver_range_t range = {0};
  semver_comp_t comp = {0};
  semvers_t list = {0};

  /* --- 解析与字段（usage.c 的已验证场景） --- */
  CHECK(semver(&v, "v1.2.3-alpha.1+build.7") == 0,
        "parse v1.2.3-alpha.1+build.7");
  CHECK(v.major == 1 && v.minor == 2 && v.patch == 3,
        "major/minor/patch == 1.2.3");
  CHECK(v.prerelease.raw != NULL
          && strncmp(v.prerelease.raw, "alpha", 5) == 0,
        "prerelease[0] raw == alpha");
  CHECK(v.prerelease.next != NULL && v.prerelease.next->num == 1,
        "prerelease[1] numeric == 1");

  /* --- 写回往返（version.c: test_read 已验证样例） --- */
  CHECK(check_roundtrip("v1.2.3-alpha.1+build.7", "1.2.3-alpha.1+build.7"),
        "write round-trip strips leading v");
  CHECK(check_roundtrip("1.2.3-alpha.2+77.2", "1.2.3-alpha.2+77.2"),
        "write round-trip keeps prerelease+build");

  /* --- 比较语义（由 match.c 的比较器用例反推的严格序） --- */
  semver(&a, "1.2.3");
  semver(&b, "1.2.3");
  CHECK(semver_cmp(a, b) == 0, "cmp 1.2.3 == 1.2.3");
  semver(&a, "0.0.1-98");
  semver(&b, "0.0.1-99");
  CHECK(semver_cmp(a, b) < 0, "cmp 0.0.1-98 < 0.0.1-99");
  semver(&a, "0.0.1-alpha.98");
  semver(&b, "0.0.1-alpha.98.1");
  CHECK(semver_cmp(a, b) < 0, "cmp alpha.98 < alpha.98.1");
  semver(&a, "0.0.1-alpha.98.1.3");
  semver(&b, "0.0.1-alpha.98.1");
  CHECK(semver_cmp(a, b) > 0, "cmp alpha.98.1.3 > alpha.98.1");

  /* --- 比较器匹配（match.c 逐条对应） --- */
  CHECK(semver_match(v, ">=1.0.0") == true, "match 1.2.3-alpha.1 ^ >=1.0.0");
  CHECK(semver_match(a, ">2") == false, "no-match 1.2.3 ^ >2");
  semver(&a, "0.0.1-98");
  CHECK(semver_match(a, "=0.0.1-98") == true, "match 0.0.1-98 ^ =0.0.1-98");

  /* --- 范围解析、写回与匹配（range.c / usage.c 已验证样例） --- */
  CHECK(semver_range(&range, "1.2.3 - 2.3.4 || >=5") == 0,
        "parse range 1.2.3 - 2.3.4 || >=5");
  buffer[0] = '\0';
  semver_range_write(range, buffer, sizeof(buffer));
  CHECK(strcmp(buffer, ">=1.2.3 <=2.3.4 || >=5.0.0") == 0,
        "range write-back expands hyphen/x forms");
  semver_range_dtor(&range);
  range = (semver_range_t) {0};

  semver(&a, "1.2.3");
  CHECK(semver_rmatch(a, "9.x || 1.2.x") == true, "rmatch 1.2.3 ^ 9.x || 1.2.x");
  CHECK(semver_rmatch(a, "9.x || >2") == false, "no-rmatch 1.2.3 ^ 9.x || >2");
  CHECK(semver_rmatch(v, "1.2.1 || >=1.2.3-alpha <1.2.5") == true,
        "rmatch 1.2.3-alpha.1 ^ 1.2.1 || >=1.2.3-alpha <1.2.5");

  /* --- 比较器对象 API（comp.c 失败样例 + match 语义） --- */
  CHECK(semver_comp(&comp, "abc") != 0, "reject comparator abc");
  comp = (semver_comp_t) {0};
  CHECK(semver_comp(&comp, "1.2.x") == 0, "parse comparator 1.2.x");
  CHECK(semver_comp_match(a, comp) == true, "comp-match 1.2.3 ^ 1.2.x");
  semver_comp_dtor(&comp);

  /* --- 非法输入（version.c / range.c 失败样例） --- */
  semver_t bad = {0};
  CHECK(semver(&bad, "1.2") != 0, "reject incomplete 1.2");
  CHECK(semver(&bad, "") != 0, "reject empty string");
  range = (semver_range_t) {0};
  CHECK(semver_range(&range, "* |") != 0, "reject truncated range '* |'");

  /* --- semvers 向量（semvers.c 场景：push + sort） --- */
  semver(&a, "2.0.3");
  semver(&b, "2.0.0");
  semver_t c = {0};
  semver(&c, "2.0.2");
  semvers_push(list, a);
  semvers_push(list, b);
  semvers_push(list, c);
  CHECK(list.length == 3, "semvers length == 3");
  semvers_sort(list);
  CHECK(list.data[0].patch == 0 && list.data[2].patch == 3,
        "semvers sort orders 2.0.0 < 2.0.2 < 2.0.3");
  semvers_dtor(list);

  printf("\ntest_sv: %d checks, %d failures\n", g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
