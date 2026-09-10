/*
 * test.c — test_package consumer test for GNU libmicrohttpd 1.0.1.
 * Real API usage (R34): starts an MHD daemon, verifies bind, stops it,
 * and reports MHD_get_version(). Compiled against the installed package.
 */
#include <microhttpd.h>
#include <stdio.h>
#include <string.h>

static enum MHD_Result
dummy_cb (void *cls, struct MHD_Connection *connection,
          const char *url, const char *method, const char *version,
          const char *upload_data, size_t *upload_data_size, void **con_cls)
{
  (void) cls; (void) url; (void) method; (void) version;
  (void) upload_data; (void) upload_data_size; (void) con_cls;
  return MHD_NO;
}

int
main (void)
{
  struct MHD_Daemon *d;
  const char *ver = MHD_get_version ();
  const union MHD_DaemonInfo *di;
  unsigned short port = 0;

  printf ("libmicrohttpd version: %s\n", ver);
  if (NULL == ver || 0 == strlen (ver))
    return 1;

  d = MHD_start_daemon (MHD_USE_INTERNAL_POLLING_THREAD,
                        port, NULL, NULL, &dummy_cb, NULL, MHD_OPTION_END);
  if (NULL == d)
    {
      fprintf (stderr, "MHD_start_daemon failed\n");
      return 2;
    }
  di = MHD_get_daemon_info (d, MHD_DAEMON_INFO_BIND_PORT);
  if (NULL == di)
    {
      fprintf (stderr, "MHD_get_daemon_info failed\n");
      MHD_stop_daemon (d);
      return 3;
    }
  printf ("daemon started on port %u\n", (unsigned) di->port);
  MHD_stop_daemon (d);
  printf ("consumer test PASS\n");
  return 0;
}
