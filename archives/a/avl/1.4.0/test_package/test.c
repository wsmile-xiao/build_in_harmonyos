/* test_package for GNU libavl 1.4.0 — real consumer test (R34).
 *
 * Exercises the public avl.h API: create / insert / count / find /
 * delete / destroy, with assertions on the resulting tree state.
 */
#include <stdio.h>
#include <stdlib.h>
#include "avl.h"

static int
compare_ints (const void *a, const void *b, void *param)
{
  int x = *(const int *) a;
  int y = *(const int *) b;
  (void) param;
  return (x > y) - (x < y);
}

int
main (void)
{
  avl_tree *tree;
  int values[] = { 30, 10, 50, 20, 40 };
  int i, failures = 0;

  tree = avl_create (compare_ints, NULL);
  if (tree == NULL)
    {
      fprintf (stderr, "avl_create failed\n");
      return 1;
    }

  for (i = 0; i < 5; i++)
    {
      void *dup = avl_insert (tree, &values[i]);
      if (dup != NULL)
        {
          fprintf (stderr, "unexpected duplicate at insert %d\n", i);
          failures++;
        }
    }

  if (avl_count (tree) != 5)
    {
      fprintf (stderr, "avl_count expected 5, got %d\n", avl_count (tree));
      failures++;
    }

  for (i = 0; i < 5; i++)
    {
      int *found = (int *) avl_find (tree, &values[i]);
      if (found == NULL || *found != values[i])
        {
          fprintf (stderr, "avl_find missed %d\n", values[i]);
          failures++;
        }
    }

  /* Deleting a key must return the stored item and shrink the tree. */
  {
    int key = 20;
    int *removed = (int *) avl_delete (tree, &key);
    if (removed == NULL || *removed != 20)
      {
        fprintf (stderr, "avl_delete failed for 20\n");
        failures++;
      }
    if (avl_count (tree) != 4)
      {
        fprintf (stderr, "avl_count after delete expected 4, got %d\n",
                 avl_count (tree));
        failures++;
      }
    if (avl_find (tree, &key) != NULL)
      {
        fprintf (stderr, "avl_find still finds deleted key 20\n");
        failures++;
      }
  }

  avl_destroy (tree, NULL);

  if (failures != 0)
    {
      fprintf (stderr, "avl test_package FAILED: %d failure(s)\n", failures);
      return 1;
    }

  printf ("test avl 1.4.0: OK\n");
  return 0;
}
