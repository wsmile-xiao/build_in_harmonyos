#include <nice/agent.h>
#include <stdio.h>

int
main (void)
{
  GMainContext *context = g_main_context_new ();
  NiceAgent *agent;
  guint stream_id;

  if (context == NULL) {
    fprintf (stderr, "could not create GLib main context\n");
    return 1;
  }

  agent = nice_agent_new (context, NICE_COMPATIBILITY_RFC5245);
  if (agent == NULL) {
    fprintf (stderr, "nice_agent_new() returned NULL\n");
    g_main_context_unref (context);
    return 1;
  }

  stream_id = nice_agent_add_stream (agent, 1);
  if (stream_id == 0) {
    fprintf (stderr, "nice_agent_add_stream() returned stream id 0\n");
    g_object_unref (agent);
    g_main_context_unref (context);
    return 1;
  }

  printf ("libnice consumer created NiceAgent stream %u\n", stream_id);
  g_object_unref (agent);
  g_main_context_unref (context);
  return 0;
}
