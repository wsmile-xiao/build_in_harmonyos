/*
 * test.c — hash 0.0.1 test_package consumer
 *
 * Links against the installed libhash.a and public headers (hash.h/khash.h),
 * exercising the real public API: hash_new/hash_set/hash_get/hash_has/
 * hash_size/hash_del/hash_each. Uses the library's public API only.
 */
#include <stdio.h>
#include <string.h>
#include "hash.h"

int
main(void) {
  hash_t *hash = hash_new();
  if (!hash) {
    fprintf(stderr, "FAIL: hash_new returned NULL\n");
    return 1;
  }
  if (0 != hash_size(hash)) {
    fprintf(stderr, "FAIL: fresh hash size != 0\n");
    hash_free(hash);
    return 1;
  }

  hash_set(hash, "name", "tobi");
  hash_set(hash, "species", "ferret");
  hash_set(hash, "age", "2");

  if (3 != hash_size(hash)) {
    fprintf(stderr, "FAIL: hash_size expected 3\n");
    hash_free(hash);
    return 1;
  }
  char *name = (char *) hash_get(hash, "name");
  if (!name) {
    fprintf(stderr, "FAIL: hash_get(name) returned NULL\n");
    hash_free(hash);
    return 1;
  }
  if (0 != strcmp("tobi", name)) {
    fprintf(stderr, "FAIL: hash_get(name) value mismatch\n");
    hash_free(hash);
    return 1;
  }
  char *species = (char *) hash_get(hash, "species");
  if (!species) {
    fprintf(stderr, "FAIL: hash_get(species) returned NULL\n");
    hash_free(hash);
    return 1;
  }
  if (0 != strcmp("ferret", species)) {
    fprintf(stderr, "FAIL: hash_get(species) value mismatch\n");
    hash_free(hash);
    return 1;
  }
  if (1 != hash_has(hash, "age") || 0 != hash_has(hash, "missing")) {
    fprintf(stderr, "FAIL: hash_has\n");
    hash_free(hash);
    return 1;
  }

  unsigned int n = 0;
  hash_each(hash, { n++; });
  if (3 != n) {
    fprintf(stderr, "FAIL: hash_each saw %u entries\n", n);
    hash_free(hash);
    return 1;
  }

  hash_del(hash, "age");
  if (2 != hash_size(hash) || 0 != hash_has(hash, "age")) {
    fprintf(stderr, "FAIL: hash_del\n");
    hash_free(hash);
    return 1;
  }

  hash_clear(hash);
  if (0 != hash_size(hash)) {
    fprintf(stderr, "FAIL: hash_clear\n");
    hash_free(hash);
    return 1;
  }

  hash_free(hash);
  printf("test_hash_consumer: OK (public API exercised)\n");
  return 0;
}
