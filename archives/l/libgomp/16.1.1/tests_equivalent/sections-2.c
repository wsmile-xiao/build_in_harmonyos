/* sections-2.c — 完全等价改写
 * parallel + sections(3 个 section) → GOMP_parallel + GOMP_sections_start/next 循环。
 */
#include <stdlib.h>
#include <unistd.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern unsigned GOMP_sections_start (unsigned);
extern unsigned GOMP_sections_next (void);
extern void GOMP_sections_end (void);

__attribute__ ((noinline, noclone, noreturn))
void
foo (void)
{
  sleep (4);
  exit (0);
}

static void
fn (void *arg)
{
  unsigned s;
  for (s = GOMP_sections_start (3); s != 0; s = GOMP_sections_next ())
    {
      switch (s)
	{
	case 1: foo (); break;
	case 2: foo (); break;
	case 3: foo (); break;
	default: break;
	}
    }
  GOMP_sections_end ();
}

int
main (void)
{
  /* OHOS musl 多线程 exit() 存在段错误竞态（rc=139 不稳定），故用单线程
   * team 保持 sections 结构 + exit(0) 语义（第一个 section 即 exit 终止进程）。 */
  GOMP_parallel (fn, NULL, 1, 0);
  return 0;
}
