/* sort-1.c — 完全等价改写
 * sort1: parallel firstprivate → GOMP_parallel + 共享锁/栈/busy/num_threads。
 * sort2: parallel single nowait / atomic / 嵌套 parallel num_threads(2) → GOMP ABI。
 * sort3: parallel single + task → GOMP_parallel + GOMP_single_start + GOMP_task。
 * 去掉 _OPENMP 守卫，sort3 恒编译。
 */
#include <limits.h>
#include <omp.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);
extern void GOMP_barrier (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);

int failures;

#define THRESHOLD 100

static void
verify (const char *name, double stime, int *array, int count)
{
  int i;
  double etime = omp_get_wtime ();

  printf ("%s: %g\n", name, etime - stime);
  for (i = 1; i < count; i++)
    if (array[i] < array[i - 1])
      {
	printf ("%s: incorrectly sorted\n", name);
	failures = 1;
      }
}

static void
insertsort (int *array, int s, int e)
{
  int i, j, val;
  for (i = s + 1; i <= e; i++)
    {
      val = array[i];
      j = i;
      while (j-- > s && val < array[j])
	array[j + 1] = array[j];
      array[j + 1] = val;
    }
}

struct int_pair
{
  int lo;
  int hi;
};

struct int_pair_stack
{
  struct int_pair *top;
#define STACK_SIZE 4 * CHAR_BIT * sizeof (int)
  struct int_pair arr[STACK_SIZE];
};

static inline void
init_int_pair_stack (struct int_pair_stack *stack)
{
  stack->top = &stack->arr[0];
}

static inline void
push_int_pair_stack (struct int_pair_stack *stack, int lo, int hi)
{
  stack->top->lo = lo;
  stack->top->hi = hi;
  stack->top++;
}

static inline void
pop_int_pair_stack (struct int_pair_stack *stack, int *lo, int *hi)
{
  stack->top--;
  *lo = stack->top->lo;
  *hi = stack->top->hi;
}

static inline int
size_int_pair_stack (struct int_pair_stack *stack)
{
  return stack->top - &stack->arr[0];
}

static inline void
busy_wait (void)
{
#if defined __i386__ || defined __x86_64__
  __builtin_ia32_pause ();
#elif defined __ia64__
  __asm volatile ("hint @pause" : : : "memory");
#elif defined __sparc__ && (defined __arch64__ || defined __sparc_v9__)
  __asm volatile ("membar #LoadLoad" : : : "memory");
#else
  __asm volatile ("" : : : "memory");
#endif
}

static inline void
swap (int *array, int a, int b)
{
  int val = array[a];
  array[a] = array[b];
  array[b] = val;
}

static inline int
choose_pivot (int *array, int lo, int hi)
{
  int mid = (lo + hi) / 2;

  if (array[mid] < array[lo])
    swap (array, lo, mid);
  if (array[hi] < array[mid])
    {
      swap (array, mid, hi);
      if (array[mid] < array[lo])
	swap (array, lo, mid);
    }
  return array[mid];
}

static inline int
partition (int *array, int lo, int hi)
{
  int pivot = choose_pivot (array, lo, hi);
  int left = lo;
  int right = hi;

  for (;;)
    {
      while (array[++left] < pivot);
      while (array[--right] > pivot);
      if (left >= right)
	break;
      swap (array, left, right);
    }
  return left;
}

/* ---------------- sort1 ---------------- */
struct sort1d
{
  int *array;
  int count;
  omp_lock_t *lock;
  struct int_pair_stack *global_stack;
  int *busy;
  int *num_threads;
};

static void
sort1_fn (void *arg)
{
  struct sort1d *d = (struct sort1d *) arg;
  int *array = d->array;	/* firstprivate */
  int count = d->count;		/* firstprivate */
  int lo = 0, hi = 0, mid, next_lo, next_hi;
  bool idle = true;
  struct int_pair_stack local_stack;

  init_int_pair_stack (&local_stack);
  if (omp_get_thread_num () == 0)
    {
      *d->num_threads = omp_get_num_threads ();
      hi = count - 1;
      idle = false;
    }

  for (;;)
    {
      if (hi - lo < THRESHOLD)
	{
	  insertsort (array, lo, hi);
	  lo = hi;
	}
      if (lo >= hi)
	{
	  if (size_int_pair_stack (&local_stack) == 0)
	    {
	    again:
	      omp_set_lock (d->lock);
	      if (size_int_pair_stack (d->global_stack) == 0)
		{
		  if (!idle)
		    (*d->busy)--;
		  if (*d->busy == 0)
		    {
		      omp_unset_lock (d->lock);
		      break;
		    }
		  omp_unset_lock (d->lock);
		  idle = true;
		  while (size_int_pair_stack (d->global_stack) == 0
			 && *d->busy)
		    busy_wait ();
		  goto again;
		}
	      if (idle)
		(*d->busy)++;
	      pop_int_pair_stack (d->global_stack, &lo, &hi);
	      omp_unset_lock (d->lock);
	      idle = false;
	    }
	  else
	    pop_int_pair_stack (&local_stack, &lo, &hi);
	}

      mid = partition (array, lo, hi);
      if (mid - lo < hi - mid)
	{
	  next_lo = mid;
	  next_hi = hi;
	  hi = mid - 1;
	}
      else
	{
	  next_lo = lo;
	  next_hi = mid - 1;
	  lo = mid;
	}

      if (next_hi - next_lo < THRESHOLD)
	insertsort (array, next_lo, next_hi);
      else
	{
	  if (size_int_pair_stack (d->global_stack) < *d->num_threads - 1)
	    {
	      int size;

	      omp_set_lock (d->lock);
	      size = size_int_pair_stack (d->global_stack);
	      if (size < *d->num_threads - 1 && size < STACK_SIZE)
		push_int_pair_stack (d->global_stack, next_lo, next_hi);
	      else
		push_int_pair_stack (&local_stack, next_lo, next_hi);
	      omp_unset_lock (d->lock);
	    }
	  else
	    push_int_pair_stack (&local_stack, next_lo, next_hi);
	}
    }
}

static void
sort1 (int *array, int count)
{
  omp_lock_t lock;
  struct int_pair_stack global_stack;
  int busy = 1;
  int num_threads;
  struct sort1d d;

  omp_init_lock (&lock);
  init_int_pair_stack (&global_stack);
  d.array = array;
  d.count = count;
  d.lock = &lock;
  d.global_stack = &global_stack;
  d.busy = &busy;
  d.num_threads = &num_threads;
  GOMP_parallel (sort1_fn, &d, 0, 0);
  omp_destroy_lock (&lock);
}

/* ---------------- sort2 ---------------- */
struct nt_arg
{
  int *num_threads;
};

static void
nt_fn (void *arg)
{
  struct nt_arg *a = (struct nt_arg *) arg;
  if (GOMP_single_start ())
    *a->num_threads = omp_get_num_threads ();
}

struct sort2d
{
  int *array;
  int lo;
  int hi;
  int mid;
  int num_threads;
  int *busy;
};

static void sort2_1 (int *array, int lo, int hi, int num_threads, int *busy);

static void
sort2_par_fn (void *arg)
{
  struct sort2d *d = (struct sort2d *) arg;
  if (omp_get_thread_num () == 0)
    sort2_1 (d->array, d->lo, d->mid - 1, d->num_threads, d->busy);
  else
    {
      sort2_1 (d->array, d->mid, d->hi, d->num_threads, d->busy);
      GOMP_atomic_start ();
      *d->busy -= 1;
      GOMP_atomic_end ();
    }
}

static void
sort2_1 (int *array, int lo, int hi, int num_threads, int *busy)
{
  int mid;

  if (hi - lo < THRESHOLD)
    {
      insertsort (array, lo, hi);
      return;
    }

  mid = partition (array, lo, hi);

  if (*busy >= num_threads)
    {
      sort2_1 (array, lo, mid - 1, num_threads, busy);
      sort2_1 (array, mid, hi, num_threads, busy);
      return;
    }

  GOMP_atomic_start ();
  *busy += 1;
  GOMP_atomic_end ();

  struct sort2d d = { array, lo, hi, mid, num_threads, busy };
  GOMP_parallel (sort2_par_fn, &d, 2, 0);
}

static void
sort2 (int *array, int count)
{
  int num_threads;
  int busy = 1;
  struct nt_arg a = { &num_threads };

  GOMP_parallel (nt_fn, &a, 0, 0);

  sort2_1 (array, 0, count - 1, num_threads, &busy);
}

/* ---------------- sort3 ---------------- */
struct sort3_task
{
  int *array;
  int lo;
  int hi;
};

static void sort3_1 (int *array, int lo, int hi);

static void
sort3_task_fn (void *arg)
{
  struct sort3_task *t = (struct sort3_task *) arg;
  sort3_1 (t->array, t->lo, t->hi);
}

static void
sort3_1 (int *array, int lo, int hi)
{
  int mid;

  if (hi - lo < THRESHOLD)
    {
      insertsort (array, lo, hi);
      return;
    }

  mid = partition (array, lo, hi);
  struct sort3_task t = { array, lo, mid - 1 };
  GOMP_task (sort3_task_fn, &t, NULL, sizeof (t), __alignof__ (struct sort3_task),
	     1, 0, NULL, 0, NULL);
  sort3_1 (array, mid, hi);
}

struct sort3_arg
{
  int *array;
  int lo;
  int hi;
};

static void
sort3_par_fn (void *arg)
{
  struct sort3_arg *a = (struct sort3_arg *) arg;
  if (GOMP_single_start ())
    sort3_1 (a->array, a->lo, a->hi);
  GOMP_barrier ();
}

static void
sort3 (int *array, int count)
{
  struct sort3_arg a = { array, 0, count - 1 };
  GOMP_parallel (sort3_par_fn, &a, 0, 0);
}

/* ---------------- main ---------------- */
int
main (int argc, char **argv)
{
  int i, count = 1000000;
  double stime;
  int *unsorted, *sorted, num_threads;
  struct nt_arg a;

  if (argc >= 2)
    count = strtoul (argv[1], NULL, 0);

  unsorted = malloc (count * sizeof (int));
  sorted = malloc (count * sizeof (int));
  if (unsorted == NULL || sorted == NULL)
    {
      puts ("allocation failure");
      exit (1);
    }

  srand (0xdeadbeef);
  for (i = 0; i < count; i++)
    unsorted[i] = rand ();

  omp_set_nested (1);
  omp_set_dynamic (0);
  a.num_threads = &num_threads;
  GOMP_parallel (nt_fn, &a, 0, 0);
  printf ("Threads: %d\n", num_threads);

  memcpy (sorted, unsorted, count * sizeof (int));
  stime = omp_get_wtime ();
  sort1 (sorted, count);
  verify ("sort1", stime, sorted, count);

  memcpy (sorted, unsorted, count * sizeof (int));
  stime = omp_get_wtime ();
  sort2 (sorted, count);
  verify ("sort2", stime, sorted, count);

  memcpy (sorted, unsorted, count * sizeof (int));
  stime = omp_get_wtime ();
  sort3 (sorted, count);
  verify ("sort3", stime, sorted, count);

  return 0;
}
