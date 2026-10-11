/* Consumer test for paflib 0.3.0 on OHOS/aarch64.
 *
 * Exercises the installed public headers and both static libraries against the
 * aarch64 port: the software DSCR model, the portable Time Base and the
 * emulated EBB event source (interval timer driving the registered callback).
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>

#include <paf/dsc.h>
#include <paf/ebb.h>
#include <paf/ppr.h>
#include <paf/tb.h>

static int checks = 0;
static int fails = 0;
static volatile int ebb_fired = 0;

static void
ebb_cb (void *ctx)
{
  int *p = (int *) ctx;
  (*p)++;
}

static void
check (const char *name, int ok)
{
  checks++;
  if (ok)
    printf ("PASS: %s\n", name);
  else
    {
      fails++;
      printf ("FAIL: %s\n", name);
    }
}

int
main (void)
{
  uint64_t mask;
  uint64_t dscr = 0;
  uint64_t got = 0;
  timing t0, t1, sum;
  ebbhandler_t handler;
  int ebbfd;
  int i;

  /* ---- DSCR: software model, full API state machine ------------------- */
  errno = 0;
  mask = paf_dsc_check_support ();
  check ("paf_dsc_check_support reports a non-empty mask", mask != 0);
  check ("DSCR mask includes DPFD",
         (mask & DSCR_DPFD_MASK) == DSCR_DPFD_MASK);
  check ("DSCR mask is the full ISA 2.07 mask", mask == DSCR_ISA_2_07_MASK);

  errno = 0;
  check ("paf_dsc_get succeeds", paf_dsc_get (&dscr) == 0 && errno != ENOSYS);

  check ("paf_dsc_set accepts DPFD field",
         paf_dsc_set (DSCR_DPFD_SET (dscr, DSCR_DPFD_MAX)) == 0);
  check ("paf_dsc_get reflects DPFD field",
         paf_dsc_get (&got) == 0 && DSCR_DPFD_GET (got) == DSCR_DPFD_MAX);
  check ("paf_dsc_set(0) then get == 0",
         paf_dsc_set (0) == 0 && paf_dsc_get (&got) == 0 && got == 0);
  errno = 0;
  check ("paf_dsc_set rejects out-of-mask bits with EINVAL",
         paf_dsc_set (~(uint64_t) 0) == -1 && errno == EINVAL);

  /* ---- Time Base: portable monotonic analogue ------------------------- */
  t0 = paf_timing_now ();
  t1 = paf_timing_now ();
  check ("paf_timing_now is monotonic", t1 >= t0);
  sum = 0;
  paf_timing_accum (&sum, paf_timing_diff (t0, t1));
  check ("paf_timing_accum accumulates", sum == paf_timing_diff (t0, t1));

  /* ---- EBB: emulated event source drives the registered callback ------ */
  errno = 0;
  check ("paf_ebb_register_handler(NULL) -> EBB_REG_ERR",
         paf_ebb_register_handler (NULL, NULL, PAF_EBB_CALLBACK_GPR_SAVE, 0)
         == EBB_REG_ERR);

  handler = paf_ebb_register_handler (ebb_cb, (void *) &ebb_fired,
                                      PAF_EBB_CALLBACK_GPR_SAVE, 0);
  check ("paf_ebb_register_handler returns the handler",
         handler == ebb_cb);
  check ("paf_ebb_handler returns the registered handler",
         paf_ebb_handler () == ebb_cb);

  ebbfd = paf_ebb_pmu_init (0x400FA, -1);
  check ("paf_ebb_pmu_init returns a descriptor", ebbfd >= 0);

  check ("paf_ebb_enable_branches succeeds",
         paf_ebb_enable_branches () == 0);
  for (i = 0; i < 300 && ebb_fired < 2; i++)
    usleep (1000);
  check ("emulated EBB callback fired at least twice", ebb_fired >= 2);
  check ("paf_ebb_disable_branches succeeds",
         paf_ebb_disable_branches () == 0);
  check ("paf_ebb_event_close succeeds",
         paf_ebb_event_close (ebbfd) == 0);

  /* ---- PPR / lock hints: callable no-ops ------------------------------ */
  paf_ppr_very_low ();
  paf_ppr_low ();
  paf_ppr_med_low ();
  paf_ppr_med ();
  paf_ppr_med_high ();
  paf_yield ();
  paf_mdoio ();
  paf_mdoom ();
  check ("PPR/lock-hint helpers are callable no-ops", 1);

  printf ("PAFLIB_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
  return fails == 0 ? 0 : 1;
}
