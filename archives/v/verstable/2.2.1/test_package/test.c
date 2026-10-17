#include <stdio.h>
#include <stdlib.h>

/* Consumer test for verstable 2.2.1 (Conan test_package, R34).
   Uses ONLY the installed public header `verstable.h` and its public
   C11 generic macro API — no private headers, no internal symbols. */

#define NAME int_set
#define KEY_TY int
#include "verstable.h"   /* installed header from package include/ */

int main(void)
{
  int_set our_set;
  vt_init(&our_set);

  /* Insert 10 keys via public API. */
  for (int i = 0; i < 10; ++i)
  {
    int_set_itr itr = vt_insert(&our_set, i);
    if (vt_is_end(itr))   /* OOM path */
    {
      vt_cleanup(&our_set);
      fprintf(stderr, "insert failed at %d\n", i);
      return 1;
    }
  }

  /* Erase some keys. */
  for (int i = 0; i < 10; i += 3)
    vt_erase(&our_set, i);

  /* Verify observable results: size + retrieval. */
  int expect[] = {1, 2, 4, 5, 7, 8};
  int found[6];
  int n = 0;
  for (int i = 0; i < 10; ++i)
  {
    int_set_itr itr = vt_get(&our_set, i);
    if (!vt_is_end(itr))
      found[n++] = itr.data->key;
  }

  if (n != 6)
  {
    fprintf(stderr, "FAIL: expected 6 remaining keys, got %d\n", n);
    vt_cleanup(&our_set);
    return 1;
  }
  for (int i = 0; i < 6; ++i)
  {
    if (found[i] != expect[i])
    {
      fprintf(stderr, "FAIL: found[%d]=%d expected %d\n", i, found[i], expect[i]);
      vt_cleanup(&our_set);
      return 1;
    }
  }

  /* Iteration via public API. */
  int count = 0;
  for (int_set_itr itr = vt_first(&our_set); !vt_is_end(itr); itr = vt_next(itr))
    ++count;
  if (count != 6)
  {
    fprintf(stderr, "FAIL: iteration count %d, expected 6\n", count);
    vt_cleanup(&our_set);
    return 1;
  }

  vt_cleanup(&our_set);
  printf("verstable consumer test: OK (6 keys, iteration verified)\n");
  return 0;
}