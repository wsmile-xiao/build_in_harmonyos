/* Consumer-side smoke test for riemann-c-client (L1 test_package).
 *
 * Verifies, from a pure consumer's point of view on the target device:
 *   1. <riemann/riemann-client.h> is discoverable via the package,
 *   2. libriemann-client links (static archive + transitive protobuf-c),
 *   3. the public event/message API works end to end: build a message and
 *      serialize it to the wire format protobuf-c produces.
 * No network access is required (upstream's network tests need a live
 * Riemann server; see MANIFEST.yml).
 */
#include <riemann/riemann-client.h>

#include <stdio.h>
#include <stdlib.h>

int
main (void)
{
  riemann_client_t *client;
  riemann_message_t *message;
  uint8_t *buffer;
  size_t len = 0;

  client = riemann_client_new ();
  if (!client)
    {
      fprintf (stderr, "FAIL: riemann_client_new returned NULL\n");
      return 1;
    }

  message = riemann_message_create_with_events
    (riemann_event_create (RIEMANN_EVENT_FIELD_HOST, "localhost",
                           RIEMANN_EVENT_FIELD_SERVICE, "test_package",
                           RIEMANN_EVENT_FIELD_STATE, "ok",
                           RIEMANN_EVENT_FIELD_NONE),
     NULL);
  if (!message)
    {
      fprintf (stderr, "FAIL: riemann_message_create_with_events returned NULL\n");
      riemann_client_free (client);
      return 2;
    }

  buffer = riemann_message_to_buffer (message, &len);
  if (!buffer || len == 0)
    {
      fprintf (stderr, "FAIL: riemann_message_to_buffer produced no payload\n");
      riemann_message_free (message);
      riemann_client_free (client);
      return 3;
    }

  printf ("riemann-c-client test_package: OK, packed message = %zu bytes\n", len);

  free (buffer);
  riemann_message_free (message);
  riemann_client_free (client);
  return 0;
}
