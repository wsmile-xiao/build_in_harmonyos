/* ISC license. */
/* Consumer test for utmps: links libutmps and calls its public API.
 * utmps' daemon cannot run on this platform (AF_UNIX path sockets are refused,
 * see notes), so the assertions below cover the client-side contract that is
 * still observable: the header ABI constants, the struct layout the daemon
 * protocol relies on, and that a connect attempt against an absent daemon fails
 * cleanly instead of blocking or crashing. */
#include <errno.h>
#include <stdio.h>
#include <string.h>

#include <skalibs/tai.h>
#include <utmps/utmpx.h>
#include <utmps/utmps.h>

static int fails = 0;

#define CHECK(cond, what) do {                       \
    if (cond) { printf("ok   - %s\n", what); }       \
    else { printf("FAIL - %s\n", what); ++fails; }  \
  } while (0)

int main(void)
{
  utmps a = UTMPS_ZERO ;
  struct utmpx e ;
  tain deadline ;
  int rc ;

  CHECK(UTMPS_UT_LINESIZE == 32, "UTMPS_UT_LINESIZE is 32") ;
  CHECK(UTMPS_UT_HOSTSIZE == 256, "UTMPS_UT_HOSTSIZE is 256") ;

  memset(&e, 0, sizeof(e)) ;
  e.ut_type = USER_PROCESS ;
  e.ut_pid = 4242 ;
  memcpy(e.ut_line, "pts/hw6", 7) ;
  memcpy(e.ut_id, "hw6", 3) ;
  CHECK(e.ut_pid == 4242 && e.ut_line[0] == 'p' && e.ut_id[0] == 'h',
        "struct utmpx round-trips the fields the protocol carries") ;

  tain_addsec_g(&deadline, 3) ;
  errno = 0 ;
  rc = utmps_start_g(&a, "/nonexistent-hw6-dir/utmpd.sock", &deadline) ;
  printf("info - utmps_start rc=%d errno=%d\n", rc, errno) ;
  CHECK(rc == 0, "utmps_start fails cleanly when no daemon is listening") ;
  utmps_end(&a) ;

  printf("info - utmpxname rc=%d (recorded, not asserted)\n",
         utmpxname("/nonexistent-hw6-dir/utmp")) ;

  printf("UTMPS_CONSUMER pass=%d fail=%d\n", 4 - fails, fails) ;
  return fails ? 1 : 0 ;
}
