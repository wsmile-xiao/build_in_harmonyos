/* Consumer test for libbacktrace on HarmonyOS (R34: real API usage).
 * Captures a backtrace through the installed library and verifies that
 * frames are collected, the bottom frame resolves to main(), and the
 * symbol table resolves the address of main().
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <backtrace.h>

int main (void);

static struct backtrace_state *g_state;
static int g_frames;
static int g_error;
static int g_found_main;
static int g_sym_fail;

static void
error_cb (void *data, const char *msg, int errnum)
{
  (void) data;
  fprintf (stderr, "backtrace error callback: %s (%d)\n", msg, errnum);
  g_error++;
}

static int
full_cb (void *data, uintptr_t pc, const char *filename, int lineno,
	 const char *function)
{
  (void) data;
  (void) pc;
  g_frames++;
  if (function != NULL && strcmp (function, "main") == 0)
    g_found_main = 1;
  if (filename != NULL && lineno <= 0)
    {
      fprintf (stderr, "frame with file but non-positive line\n");
      g_error++;
    }
  return 0;
}

static void
sym_cb (void *data, uintptr_t pc, const char *symname, uintptr_t symval,
	uintptr_t symsize)
{
  (void) data;
  (void) pc;
  if (symname == NULL)
    {
      fprintf (stderr, "syminfo: no symbol name\n");
      g_sym_fail++;
      return;
    }
  /* The address of main must lie inside the reported symbol range. */
  if (symsize == 0 || (uintptr_t) (void *) &main < symval
      || (uintptr_t) (void *) &main >= symval + symsize)
    {
      fprintf (stderr, "syminfo: main outside symbol range\n");
      g_sym_fail++;
    }
}

int
main (void)
{
  int failures = 0;

  g_state = backtrace_create_state ("test_libbacktrace", 0, error_cb, NULL);
  if (g_state == NULL)
    {
      fprintf (stderr, "FAIL: backtrace_create_state returned NULL\n");
      return 1;
    }

  /* 1) backtrace_full: collect frames of the current call stack */
  backtrace_full (g_state, 0, full_cb, error_cb, NULL);
  if (g_frames < 2)
    {
      fprintf (stderr, "FAIL: backtrace_full collected %d frames, want >= 2\n",
	       g_frames);
      failures++;
    }
  if (g_error != 0)
    {
      fprintf (stderr, "FAIL: error callback invoked during backtrace_full\n");
      failures++;
    }
  if (!g_found_main)
    {
      fprintf (stderr, "FAIL: main not resolved in backtrace_full\n");
      failures++;
    }

  /* 2) backtrace_syminfo: symbol table lookup for the address of main */
  backtrace_syminfo (g_state, (uintptr_t) (void *) &main, sym_cb, error_cb,
		     NULL);
  if (g_sym_fail != 0)
    {
      fprintf (stderr, "FAIL: backtrace_syminfo mismatches: %d\n", g_sym_fail);
      failures++;
    }

  if (failures != 0)
    {
      fprintf (stderr, "consumer test: %d failure(s)\n", failures);
      return 1;
    }
  printf ("test libbacktrace 20240505: OK (full=%d frames, main resolved)\n",
	  g_frames);
  return 0;
}
