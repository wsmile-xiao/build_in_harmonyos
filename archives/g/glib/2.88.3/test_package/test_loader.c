#include <dlfcn.h>

#include <stdio.h>

int
main (int argc, char **argv)
{
  void *handles[6] = { NULL };
  int index;
  int result = 1;

  if (argc != 7)
    {
      fprintf (stderr, "GLIB2_LOADER_PROBE_USAGE_ERROR argc=%d\n", argc);
      return 64;
    }

  for (index = 0; index < 6; index++)
    {
      const char *error;

      dlerror ();
      handles[index] = dlopen (argv[index + 1], RTLD_NOW | RTLD_GLOBAL);
      error = dlerror ();
      if (handles[index] == NULL || error != NULL)
        {
          fprintf (stderr,
                   "GLIB2_LOADER_PROBE_FAIL index=%d path=%s error=%s\n",
                   index,
                   argv[index + 1],
                   error != NULL ? error : "unknown");
          goto cleanup;
        }
    }

  puts ("GLIB2_LOADER_PROBE_PASS=6/6");
  result = 0;

cleanup:
  while (index > 0)
    {
      index--;
      if (handles[index] != NULL)
        dlclose (handles[index]);
    }
  return result;
}
