/* abi_probe.c — check which library actually answers the caller's time APIs.
 *
 * The port replaces glibc version-node bindings with plain aliases, so two
 * things must hold on OHOS: the public names are exported *unversioned* from
 * libfaketime, and the _22/_225/_232/_233 implementation names stay hidden by
 * the version script. A regression in either half is invisible to the timing
 * checks (libc would quietly answer the call instead), hence this probe.
 *
 * It must run *preloaded* (`LD_PRELOAD=...libfaketime.so.1 ./abi_probe
 * libfaketime.so.1`): libfaketime is an LD_PRELOAD payload and dlopen()ing it
 * aborts with SIGSEGV on this platform, so the library is inspected through the
 * global symbol namespace plus dladdr() attribution instead of a private handle.
 */
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

static const char *const exported[] = {
  "time", "clock_gettime", "gettimeofday",
  "timer_settime", "timer_gettime",
  "pthread_cond_timedwait", "pthread_cond_init", "pthread_cond_destroy",
  "getpid", "getrandom", "getentropy",
};

static const char *const hidden[] = {
  "timer_settime_22", "timer_settime_233", "timer_gettime_22", "timer_gettime_233",
  "pthread_cond_timedwait_225", "pthread_cond_timedwait_232",
  "pthread_cond_init_232", "pthread_cond_destroy_232",
};

/* The same names, called the way a real consumer calls them: the addresses the
 * dynamic linker bound in *this* process must land in libfaketime. */
static struct { const char *name; void *addr; } called[] = {
  { "time", (void *)time },
  { "clock_gettime", (void *)clock_gettime },
  { "gettimeofday", (void *)gettimeofday },
  { "getpid", (void *)getpid },
  { "pthread_cond_timedwait", (void *)pthread_cond_timedwait },
};

static const char *soname;

static int attributed(void *p)
{
  Dl_info info;
  return p != NULL && dladdr(p, &info) && info.dli_fname != NULL &&
         strstr(info.dli_fname, soname) != NULL;
}

int main(int argc, char **argv)
{
  if (argc < 2)
  {
    fprintf(stderr, "abi_probe: usage: abi_probe <libfaketime-soname>\n");
    return 2;
  }
  soname = argv[1];

  int bad = 0;
  for (unsigned i = 0; i < sizeof(exported) / sizeof(*exported); i++)
  {
    /* dlsym(RTLD_DEFAULT) also walks the dependencies, so the hit has to be
     * attributed: an answer coming from libc would make this test meaningless. */
    if (attributed(dlsym(RTLD_DEFAULT, exported[i])))
      printf("in libfaketime  : %s\n", exported[i]);
    else
    {
      printf("NOT in libfaketime: %s\n", exported[i]);
      bad++;
    }
  }
  for (unsigned i = 0; i < sizeof(hidden) / sizeof(*hidden); i++)
  {
    if (dlsym(RTLD_DEFAULT, hidden[i]) != NULL)
    {
      printf("LEAKED internal : %s\n", hidden[i]);
      bad++;
    }
    else
      printf("hidden          : %s\n", hidden[i]);
  }
  for (unsigned i = 0; i < sizeof(called) / sizeof(*called); i++)
  {
    if (attributed(called[i].addr))
      printf("caller bound to : %s\n", called[i].name);
    else
    {
      printf("caller NOT served by libfaketime: %s\n", called[i].name);
      bad++;
    }
  }

  if (bad) { fprintf(stderr, "abi_probe: %d symbol(s) wrong\n", bad); return 1; }
  printf("abi_probe: OK\n");
  return 0;
}
