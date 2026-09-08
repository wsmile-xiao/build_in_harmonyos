#include <stdio.h>
#include <stdlib.h>

#include "btor2parser/btor2parser.h"

/* Minimal consumer test: parse an in-memory BTOR2 file and check that the
 * parser returns the expected line count and max id.  Uses fmemopen instead
 * of tmpfile because /tmp may be read-only on OHOS. */
int
main (int argc, char **argv)
{
  Btor2Parser *reader;
  Btor2LineIterator it;
  Btor2Line *l;
  FILE *f;
  int64_t lines = 0;
  char input[] =
    "1 sort bitvec 1\n"
    "2 input 1 x\n"
    "3 one 1\n"
    "4 not 1 2\n"
    "5 and 1 2 4\n";

  f = fmemopen (input, sizeof (input) - 1, "r");
  if (!f)
    {
      fprintf (stderr, "test_btor2tools: fmemopen failed\n");
      return 1;
    }

  reader = btor2parser_new ();
  if (!reader)
    {
      fprintf (stderr, "test_btor2tools: btor2parser_new failed\n");
      fclose (f);
      return 1;
    }
  if (!btor2parser_read_lines (reader, f))
    {
      fprintf (stderr, "test_btor2tools: parse error: %s\n",
               btor2parser_error (reader));
      btor2parser_delete (reader);
      fclose (f);
      return 1;
    }
  if (btor2parser_max_id (reader) != 5)
    {
      fprintf (stderr, "test_btor2tools: expected max id 5\n");
      btor2parser_delete (reader);
      fclose (f);
      return 1;
    }
  it = btor2parser_iter_init (reader);
  while ((l = btor2parser_iter_next (&it)))
    lines++;
  btor2parser_delete (reader);
  fclose (f);

  if (lines != 5)
    {
      fprintf (stderr, "test_btor2tools: expected 5 lines, got %lld\n",
               (long long) lines);
      return 1;
    }
  printf ("test_btor2tools: parser OK (%lld lines)\n", (long long) lines);
  return 0;
}
