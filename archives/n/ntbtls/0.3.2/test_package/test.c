/* Consumer smoke test for the ntbtls HarmonyOS build.
 *
 * Exercises the public API of the installed library only:
 *   - version query and version-comparison semantics
 *   - TLS context lifecycle for the client role
 *   - hostname (SNI) accessors
 *   - failure paths: invalid constructor flags, invalid transport, and a
 *     handshake attempted without any peer must return an error code
 *     instead of crashing.
 */

#include <stdio.h>
#include <string.h>

#include <gpg-error.h>
#include <ntbtls.h>

static int checks;
static int failures;

static void
check (int condition, const char *what)
{
  checks++;
  if (!condition)
    {
      failures++;
      fprintf (stderr, "FAIL: %s\n", what);
    }
}


int
main (void)
{
  const char *version;
  ntbtls_t tls = NULL;
  ntbtls_t bad = NULL;
  gpg_error_t err;

  /* 1. Version query returns the installed library version.  */
  version = ntbtls_check_version (NULL);
  check (version != NULL && strcmp (version, NTBTLS_VERSION) == 0,
         "ntbtls_check_version(NULL)");
  printf ("ntbtls version: %s\n", version ? version : "()");

  /* 2. A satisfied version requirement returns the version.  */
  check (ntbtls_check_version ("0.3.2") != NULL,
         "ntbtls_check_version(\"0.3.2\")");

  /* 3. An unsatisfied version requirement reports failure.  */
  check (ntbtls_check_version ("0.4.0") == NULL,
         "ntbtls_check_version(\"0.4.0\")");

  /* 4. Client context can be created.  */
  err = ntbtls_new (&tls, NTBTLS_CLIENT);
  check (err == 0 && tls != NULL, "ntbtls_new(NTBTLS_CLIENT)");

  /* 5. Unknown constructor flags are rejected without leaking a context.  */
  err = ntbtls_new (&bad, 0x40);
  check (err != 0 && bad == NULL, "ntbtls_new(invalid flags) rejected");

  /* 6. Hostname setter/getter round trip (SNI input path).  */
  check (ntbtls_set_hostname (tls, "example.invalid") == 0,
         "ntbtls_set_hostname");
  check (ntbtls_get_hostname (tls) != NULL
         && strcmp (ntbtls_get_hostname (tls), "example.invalid") == 0,
         "ntbtls_get_hostname");

  /* 7. A NULL transport must be refused.  */
  check (ntbtls_set_transport (tls, NULL, NULL) != 0,
         "ntbtls_set_transport(NULL) rejected");

  /* 8. Handshake without a peer returns an error code, not a crash.  */
  err = ntbtls_handshake (tls);
  check (err != 0, "ntbtls_handshake without peer fails cleanly");
  printf ("handshake without peer: %s\n", gpg_strerror (err));

  /* 9. Alert diagnostics stay usable on a failed context.  */
  check (ntbtls_get_last_alert (tls, NULL, NULL) == NULL,
         "ntbtls_get_last_alert on idle context");

  /* 10. Release is idempotent w.r.t. NULL input.  */
  ntbtls_release (tls);
  ntbtls_release (NULL);
  check (1, "ntbtls_release(NULL) safe");

  printf ("ntbtls consumer test: %d/%d checks passed\n",
          checks - failures, checks);
  return failures == 0 ? 0 : 1;
}
