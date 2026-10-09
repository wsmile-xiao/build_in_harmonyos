/* test_hivex.c — end-to-end consumer test for hivex 1.3.24 on OHOS.
 *
 * Upstream ships one C test (lib/test-just-header.c, run by `make check`)
 * which only asserts that images/minimal opens.  This test_package drives
 * the library the way a real consumer does, in two phases:
 *
 *   phase 1 (producer): open the upstream registry image in WRITE mode,
 *            grow a small registry tree under the root key, set values of
 *            five different registry types and commit the result to a new
 *            hive file;
 *   phase 2 (consumer): reopen the committed hive read-only, navigate it by
 *            key/value name, read every value back through the typed
 *            accessors, verify the structure (child/value counts, parent
 *            links, full tree walk) and check the error paths.
 *
 * The hive image is a fixture because upstream cannot create a hive from
 * scratch (lib/hivex.pod: "Creating a new hive file from scratch.  This is
 * impossible at present"), and hivex_open() rejects files below 0x2000
 * bytes.  The fixture is the byte-identical upstream images/minimal image.
 *
 * The fixture is shipped as a base64 TEXT file (minimal.b64) rather than a
 * binary, because the CI applies each PR as a text .diff and cannot carry
 * binary patch data ("missing binary patch data" on git apply).  When the
 * fixture argument ends in ".b64", it is decoded to a real hive image at
 * runtime (see decode_b64_fixture) before being opened.  This matches the
 * repo-wide convention for binary test fixtures (e.g. blur/test_in.png.b64).
 *
 * Usage: test_hivex [<fixture-hive|fixture.b64> <committed-hive>]
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <hivex.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond, what)                                               \
  do {                                                                  \
    checks++;                                                           \
    if (cond) {                                                         \
      printf ("ok   - %s\n", what);                                     \
    } else {                                                            \
      failures++;                                                       \
      printf ("FAIL - %s\n", what);                                     \
    }                                                                   \
  } while (0)

/* Value payloads, kept as NUL-carrying byte arrays: sizeof - 1 is the exact
 * registry data length handed to hivex_node_set_value(). */
static const char sz_path[] = "C\0:\0\\\0O\0H\0O\0S\0\0\0";
static const char dword_value[] = "\x78\x56\x34\x12";
static const char qword_value[] = "\x88\x77\x66\x55\x44\x33\x22\x11";
static const char multi_value[] =
  "a\0l\0p\0h\0a\0\0\0" "b\0e\0t\0a\0\0\0" "\0\0";
static const char binary_value[] = "\xde\xad\xbe\xef";

/* Recursively count keys and values, the way a consumer walks a hive. */
static void
count_tree (hive_h *h, hive_node_h node, size_t *nr_nodes, size_t *nr_values)
{
  hive_node_h *children;
  hive_value_h *values;

  (*nr_nodes)++;

  values = hivex_node_values (h, node);
  if (values) {
    for (size_t i = 0; values[i] != 0; ++i)
      (*nr_values)++;
    free (values);
  }

  children = hivex_node_children (h, node);
  if (children) {
    for (size_t i = 0; children[i] != 0; ++i)
      count_tree (h, children[i], nr_nodes, nr_values);
    free (children);
  }
}

static size_t
count_children (hive_h *h, hive_node_h node)
{
  hive_node_h *children = hivex_node_children (h, node);
  size_t n = 0;

  if (children) {
    while (children[n] != 0)
      n++;
    free (children);
  }
  return n;
}

/* Base64 decoder for the text-shipped fixture.  Returns the value of a
 * base64 character, or -1 for padding/whitespace/non-base64 bytes. */
static int
b64_val (int c)
{
  if (c >= 'A' && c <= 'Z')
    return c - 'A';
  if (c >= 'a' && c <= 'z')
    return c - 'a' + 26;
  if (c >= '0' && c <= '9')
    return c - '0' + 52;
  if (c == '+')
    return 62;
  if (c == '/')
    return 63;
  return -1;
}

/* Read a base64 TEXT fixture, decode it to a real hive image written next to
 * it (the ".b64" suffix stripped), and return the decoded file path.  The
 * caller owns the returned string and should remove the decoded file.  On
 * failure returns NULL. */
static char *
decode_b64_fixture (const char *b64path)
{
  FILE *in = fopen (b64path, "rb");
  long n;
  char *buf;
  size_t rd, plen, i;
  int v;
  unsigned acc = 0;
  int bits = 0;
  char *outpath;
  FILE *out;

  if (in == NULL)
    return NULL;
  if (fseek (in, 0, SEEK_END) != 0 || (n = ftell (in)) < 0 ||
      fseek (in, 0, SEEK_SET) != 0)
    {
      fclose (in);
      return NULL;
    }
  buf = malloc ((size_t) n + 1);
  if (buf == NULL)
    {
      fclose (in);
      return NULL;
    }
  rd = fread (buf, 1, (size_t) n, in);
  buf[rd] = '\0';
  fclose (in);

  plen = strlen (b64path);
  if (plen < 5)
    {
      free (buf);
      return NULL;
    }
  outpath = malloc (plen + 1);
  if (outpath == NULL)
    {
      free (buf);
      return NULL;
    }
  memcpy (outpath, b64path, plen - 4);
  outpath[plen - 4] = '\0';

  out = fopen (outpath, "wb");
  if (out == NULL)
    {
      free (buf);
      free (outpath);
      return NULL;
    }
  for (i = 0; i < rd; i++)
    {
      v = b64_val ((unsigned char) buf[i]);
      if (v < 0)
        continue;               /* skip '=', whitespace, newlines */
      acc = (acc << 6) | (unsigned) v;
      bits += 6;
      while (bits >= 8)
        {
          bits -= 8;
          if (fputc ((int) ((acc >> bits) & 0xFF), out) == EOF)
            {
              fclose (out);
              free (buf);
              free (outpath);
              return NULL;
            }
        }
    }
  fclose (out);
  free (buf);
  return outpath;
}

int
main (int argc, char *argv[])
{
  const char *fixture_arg = argc > 1 ? argv[1] : "minimal";
  const char *outfile = argc > 2 ? argv[2] : "hivex-test-out.hive";
  const char *fixture = fixture_arg;
  char *decoded_fixture = NULL;
  hive_h *h;
  hive_node_h root, software, vendor, product;
  hive_value_h val;
  hive_set_value setval;
  char *str;
  char **multi;
  char *raw;
  size_t len, nr_nodes, nr_values, nr_multi, i;
  hive_type type;
  size_t falen = strlen (fixture_arg);

  /* Binary fixtures are shipped base64-encoded to survive PR .diff application;
   * decode to a real hive image before opening. */
  if (falen > 4 && strcmp (fixture_arg + falen - 4, ".b64") == 0)
    {
      decoded_fixture = decode_b64_fixture (fixture_arg);
      if (decoded_fixture == NULL)
        {
          printf ("FAIL - could not decode base64 fixture %s\n", fixture_arg);
          failures++;
          return 1;
        }
      fixture = decoded_fixture;
    }

  printf ("hivex consumer test — fixture: %s\n", fixture);

  /* ── phase 1: producer — grow the upstream image and commit it ── */
  h = hivex_open (fixture, HIVEX_OPEN_WRITE);
  CHECK (h != NULL, "producer: hivex_open(fixture, HIVEX_OPEN_WRITE)");
  if (h == NULL)
    goto out;

  root = hivex_root (h);
  CHECK (root != 0, "producer: hivex_root() returns the root key");

  software = hivex_node_add_child (h, root, "Software");
  CHECK (software != 0, "producer: hivex_node_add_child(root, Software)");

  vendor = software ? hivex_node_add_child (h, software, "OHOSVendor") : 0;
  CHECK (vendor != 0,
         "producer: hivex_node_add_child(Software, OHOSVendor)");

  product = vendor ? hivex_node_add_child (h, vendor, "hivex") : 0;
  CHECK (product != 0, "producer: hivex_node_add_child(OHOSVendor, hivex)");
  if (product == 0) {
    hivex_close (h);
    h = NULL;
    goto out;
  }

  setval.key = (char *) "Path";
  setval.t = hive_t_REG_SZ;
  setval.len = sizeof (sz_path) - 1;
  setval.value = (char *) sz_path;
  CHECK (hivex_node_set_value (h, product, &setval, 0) == 0,
         "producer: hivex_node_set_value(REG_SZ)");

  setval.key = (char *) "Build";
  setval.t = hive_t_REG_DWORD;
  setval.len = sizeof (dword_value) - 1;
  setval.value = (char *) dword_value;
  CHECK (hivex_node_set_value (h, product, &setval, 0) == 0,
         "producer: hivex_node_set_value(REG_DWORD)");

  setval.key = (char *) "Stamp";
  setval.t = hive_t_REG_QWORD;
  setval.len = sizeof (qword_value) - 1;
  setval.value = (char *) qword_value;
  CHECK (hivex_node_set_value (h, product, &setval, 0) == 0,
         "producer: hivex_node_set_value(REG_QWORD)");

  setval.key = (char *) "Roles";
  setval.t = hive_t_REG_MULTI_SZ;
  setval.len = sizeof (multi_value) - 1;
  setval.value = (char *) multi_value;
  CHECK (hivex_node_set_value (h, product, &setval, 0) == 0,
         "producer: hivex_node_set_value(REG_MULTI_SZ)");

  setval.key = (char *) "Blob";
  setval.t = hive_t_REG_BINARY;
  setval.len = sizeof (binary_value) - 1;
  setval.value = (char *) binary_value;
  CHECK (hivex_node_set_value (h, product, &setval, 0) == 0,
         "producer: hivex_node_set_value(REG_BINARY)");

  CHECK (hivex_commit (h, outfile, 0) == 0,
         "producer: hivex_commit() writes the new hive");
  CHECK (hivex_close (h) == 0, "producer: hivex_close()");
  h = NULL;

  /* ── phase 2: consumer — reopen what was just written ── */
  h = hivex_open (outfile, 0);
  CHECK (h != NULL, "consumer: hivex_open(committed hive)");
  if (h == NULL)
    goto out;

  root = hivex_root (h);
  CHECK (root != 0, "consumer: hivex_root()");
  CHECK (root != 0 && hivex_node_parent (h, root) == 0,
         "consumer: the root key has no parent");

  str = root ? hivex_node_name (h, root) : NULL;
  CHECK (str != NULL && strlen (str) > 0, "consumer: root key has a name");
  free (str);

  software = hivex_node_get_child (h, root, "Software");
  CHECK (software != 0, "consumer: root/Software found by name");
  vendor = software ? hivex_node_get_child (h, software, "OHOSVendor") : 0;
  CHECK (vendor != 0, "consumer: root/Software/OHOSVendor found by name");
  product = vendor ? hivex_node_get_child (h, vendor, "hivex") : 0;
  CHECK (product != 0, "consumer: root/Software/OHOSVendor/hivex found");
  CHECK (product != 0 && hivex_node_parent (h, product) == vendor,
         "consumer: parent link of the leaf key round-trips");
  CHECK (hivex_node_get_child (h, root, "no-such-key") == 0,
         "consumer: unknown key name returns 0");

  /* Structure of the tree we just wrote. */
  CHECK (count_children (h, root) == 1, "consumer: root has exactly 1 child");
  CHECK (hivex_node_nr_children (h, root) == 1,
         "consumer: hivex_node_nr_children(root) agrees");
  CHECK (product != 0 && count_children (h, product) == 0,
         "consumer: leaf key has no children");
  CHECK (product != 0 && hivex_node_nr_values (h, product) == 5,
         "consumer: leaf key holds 5 values");

  /* Typed value accessors. */
  val = product ? hivex_node_get_value (h, product, "Path") : 0;
  CHECK (val != 0, "consumer: value Path found by key name");
  str = val ? hivex_value_string (h, val) : NULL;
  CHECK (str != NULL && strcmp (str, "C:\\OHOS") == 0,
         "consumer: REG_SZ Path reads back as C:\\OHOS");
  free (str);
  CHECK (val != 0 && hivex_value_type (h, val, &type, &len) == 0 &&
         type == hive_t_string && len == sizeof (sz_path) - 1,
         "consumer: REG_SZ type and length via hivex_value_type");

  val = product ? hivex_node_get_value (h, product, "Build") : 0;
  CHECK (val != 0 && hivex_value_dword (h, val) == 0x12345678,
         "consumer: REG_DWORD Build reads back as 0x12345678");

  val = product ? hivex_node_get_value (h, product, "Stamp") : 0;
  CHECK (val != 0 && hivex_value_qword (h, val) ==
         (int64_t) 0x1122334455667788LL,
         "consumer: REG_QWORD Stamp reads back as 0x1122334455667788");

  val = product ? hivex_node_get_value (h, product, "Roles") : 0;
  multi = val ? hivex_value_multiple_strings (h, val) : NULL;
  /* The returned array is NULL-terminated.  hivex counts the empty string
   * that terminates the on-disk MULTI_SZ as a further element (see
   * hivex_value_multiple_strings() in lib/value.c), so only the leading
   * non-empty entries are asserted here. */
  nr_multi = 0;
  if (multi)
    while (multi[nr_multi] != NULL)
      nr_multi++;
  CHECK (multi != NULL && nr_multi >= 2 &&
         strcmp (multi[0], "alpha") == 0 && strcmp (multi[1], "beta") == 0,
         "consumer: REG_MULTI_SZ Roles reads back as {alpha, beta}");
  if (multi)
    for (i = 0; multi[i] != NULL; i++)
      free (multi[i]);
  free (multi);

  val = product ? hivex_node_get_value (h, product, "Blob") : 0;
  raw = val ? hivex_value_value (h, val, &type, &len) : NULL;
  CHECK (raw != NULL && type == hive_t_binary && len == 4 &&
         memcmp (raw, "\xde\xad\xbe\xef", 4) == 0,
         "consumer: REG_BINARY Blob reads back byte-exact");
  free (raw);

  CHECK (product != 0 &&
         hivex_node_get_value (h, product, "no-such-value") == 0,
         "consumer: unknown value name returns 0");

  /* Walk the whole tree — the consumer's usual entry point. */
  nr_nodes = 0;
  nr_values = 0;
  count_tree (h, root, &nr_nodes, &nr_values);
  CHECK (nr_nodes == 4, "consumer: tree walk finds 4 keys");
  CHECK (nr_values == 5, "consumer: tree walk finds 5 values");

  CHECK (hivex_close (h) == 0, "consumer: hivex_close()");
  h = NULL;

  /* Error path: a missing file must be reported, not crash. */
  h = hivex_open ("/nonexistent/hivex-no-such-file", 0);
  CHECK (h == NULL, "error path: hivex_open(missing file) returns NULL");
  if (h != NULL)
    hivex_close (h);

  /* Drop the committed hive; the fixture itself is never modified. */
  remove (outfile);
  if (decoded_fixture != NULL)
    {
      remove (decoded_fixture);
      free (decoded_fixture);
    }

out:
  printf ("\n%d checks, %d failures\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
