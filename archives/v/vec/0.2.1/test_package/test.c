#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "vec.h"

/* test_package: consumer view — actually exercise the vec API (R34).
 * Mirrors the upstream test/test_vec.c assertions against the packaged
 * vec.h + libvec.a so `conan create` proves the library links and works.
 */

static int pass_count = 0;
static int fail_count = 0;

#define test_assert(cond) \
  do { \
    int pass__ = cond; \
    printf("[%s] %s:%d: %s\n", pass__ ? "PASS" : "FAIL", __FILE__, __LINE__, #cond); \
    if (pass__) pass_count++; else fail_count++; \
  } while (0)

static int intptrcmp(const void *a_, const void *b_) {
  const int *a = a_, *b = b_;
  return *a < *b ? -1 : *a > *b;
}

int main(void) {
  /* vec_push / vec_pop (exercises vec_expand_, libvec.a symbol) */
  vec_int_t v;
  vec_init(&v);
  int i;
  for (i = 0; i < 1000; i++) vec_push(&v, i * 2);
  test_assert(v.data[1] == 2);
  test_assert(v.data[999] == 999 * 2);
  test_assert(vec_push(&v, 10) == 0);
  /* pop 从末尾弹出一个元素；1000 个元素之上 push 的 10 位于末尾 */
  test_assert(vec_pop(&v) == 10);
  test_assert(v.length == 1000);
  vec_deinit(&v);

  /* vec_insert / vec_remove / vec_find */
  vec_init(&v);
  for (i = 0; i < 26; i++) vec_push(&v, 'a' + i);
  vec_find(&v, 'z', i);
  test_assert(i == 25);
  vec_remove(&v, 'c');
  test_assert(v.data[0] == 'a' && v.data[1] == 'b' && v.data[2] == 'd');
  test_assert(v.length == 25);
  vec_insert(&v, 0, 'A');
  test_assert(v.data[0] == 'A' && v.length == 26);
  vec_deinit(&v);

  /* vec_sort (exercises callback ordering) */
  vec_init(&v);
  vec_push(&v, 3);
  vec_push(&v, -1);
  vec_push(&v, 0);
  vec_sort(&v, intptrcmp);
  test_assert(v.data[0] == -1 && v.data[1] == 0 && v.data[2] == 3);
  vec_deinit(&v);

  /* vec_foreach / vec_reverse / vec_compact */
  vec_init(&v);
  vec_push(&v, 'a');
  vec_push(&v, 'b');
  vec_push(&v, 'c');
  vec_reverse(&v);
  test_assert(v.data[0] == 'c' && v.data[2] == 'a');
  vec_truncate(&v, 1);
  vec_compact(&v);
  test_assert(v.length == v.capacity);
  test_assert(v.data[0] == 'c');
  vec_deinit(&v);

  /* vec_extend */
  vec_int_t v2;
  vec_init(&v2);
  vec_init(&v);
  vec_push(&v, 12);
  vec_push(&v, 34);
  vec_push(&v2, 56);
  vec_extend(&v, &v2);
  test_assert(v.length == 3 && v.data[2] == 56);
  vec_deinit(&v);
  vec_deinit(&v2);

  printf("vec test_package results: %d total, %d passed, %d failed\n",
         pass_count + fail_count, pass_count, fail_count);
  return fail_count == 0 ? 0 : 1;
}