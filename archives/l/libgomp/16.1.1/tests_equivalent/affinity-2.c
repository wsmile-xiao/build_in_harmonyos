/* affinity-2.c — 完全等价改写
 * 两个嵌套 parallel → GOMP_parallel。place 相关 API 保留原样(无 abort，仅打印)。
 */
#include <omp.h>
#include <stdlib.h>
#include <stdio.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

int *
get_buf (int nump)
{
  static int *buf;
  static size_t buf_size;
  if ((size_t) nump > buf_size)
    {
      buf_size *= 2;
      if ((size_t) nump > buf_size)
	buf_size = nump + 64;
      int *bufn = realloc (buf, buf_size * sizeof (int));
      if (bufn == NULL)
	{
	  fprintf (stderr, "memory allocation error\n");
	  exit (1);
	}
      buf = bufn;
    }
  return buf;
}

void
print_place (int count, int *ids)
{
  int i, j;
  printf ("{");
  for (i = 0; i < count; i++)
    {
      for (j = i + 1; j < count; j++)
	if (ids[j] != ids[i] + (j - i))
	  break;
      if (i)
	printf (",");
      if (j == i + 1)
	printf ("%d", ids[i]);
      else
	{
	  printf ("%d:%d", ids[i], j - i);
	  i = j - 1;
	}
    }
  printf ("}\n");
}

void
print_place_var (void)
{
  int place = omp_get_place_num ();
  int num_places = omp_get_partition_num_places ();
  int *ids = get_buf (num_places);
  omp_get_partition_place_nums (ids);
  printf ("place %d\n", place);
  if (num_places)
    printf ("partition %d-%d\n", ids[0], ids[num_places - 1]);
}

static void
p2_fn (void *d)
{
  if (omp_get_thread_num () == omp_get_num_threads () - 1)
    print_place_var ();
}

static void
p1_fn (void *d)
{
  if (omp_get_thread_num () == omp_get_num_threads () - 1)
    GOMP_parallel (p2_fn, NULL, 0, 0);
}

int
main (void)
{
  int i, num = omp_get_num_places (), nump, *ids;
  printf ("omp_get_num_places () == %d\n", num);
  for (i = 0; i < num; i++)
    {
      printf ("place %d ", i);
      nump = omp_get_place_num_procs (i);
      ids = get_buf (nump);
      omp_get_place_proc_ids (i, ids);
      print_place (nump, ids);
    }
  print_place_var ();
  omp_set_nested (1);
  GOMP_parallel (p1_fn, NULL, 0, 0);
  return 0;
}
