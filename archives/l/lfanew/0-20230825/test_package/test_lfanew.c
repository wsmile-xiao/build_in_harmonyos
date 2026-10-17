/*
 * HarmonyOS PC consumer test for lfanew.
 *
 * Links the packaged libfanew.a and headers, builds MZ executables in memory
 * with <nexgen/mzhdr.h> + <nexgen/mzendian.h>, writes them with _binmode()
 * from <lfanew/io.h>, drives the packaged `lfanew` CLI (default / -S / -U
 * modes and two refusal paths), parses its output files back and finally
 * lists the work directory with scandir() + _direntdup() from
 * <lfanew/dirent.h> (the code path touched by patches/0001).
 *
 * usage: test_lfanew LFANEW-TOOL WORK-DIR [LAUNCHER]
 */
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <lfanew/dirent.h>
#include <lfanew/io.h>
#include <nexgen/mzhdr.h>

static int checks, failures;
static const char *tool, *workdir, *launcher;

#define CHECK(cond, what)                                              \
  do                                                                   \
    {                                                                  \
      checks++;                                                        \
      if (cond)                                                        \
        printf ("  ok   %s\n", what);                                  \
      else                                                             \
        {                                                              \
          failures++;                                                  \
          printf ("  FAIL %s (%s:%d)\n", what, __FILE__, __LINE__);    \
        }                                                              \
    }                                                                  \
  while (0)

static char *
wpath (const char *name)
{
  static char buf[8][4096];
  static int slot;
  char *p = buf[slot++ % 8];
  snprintf (p, sizeof buf[0], "%s/%s", workdir, name);
  return p;
}

static int
write_bytes (const char *path, const unsigned char *data, size_t n)
{
  int fd = open (path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (fd == -1)
    return -1;
  if (_binmode (fd) == -1)
    {
      close (fd);
      return -1;
    }
  while (n)
    {
      ssize_t r = write (fd, data, n);
      if (r <= 0)
        {
          close (fd);
          return -1;
        }
      data += r;
      n -= (size_t) r;
    }
  return close (fd);
}

static unsigned char *
read_bytes (const char *path, size_t *n)
{
  unsigned char *buf = NULL;
  size_t cap = 0, len = 0;
  int fd = open (path, O_RDONLY);
  if (fd == -1)
    return NULL;
  _binmode (fd);
  for (;;)
    {
      ssize_t r;
      if (len == cap)
        {
          cap = cap ? cap * 2 : 512;
          buf = realloc (buf, cap);
          if (! buf)
            abort ();
        }
      r = read (fd, buf + len, cap - len);
      if (r < 0)
        {
          free (buf);
          close (fd);
          return NULL;
        }
      if (r == 0)
        break;
      len += (size_t) r;
    }
  close (fd);
  *n = len;
  return buf;
}

static int
exists (const char *path)
{
  return access (path, F_OK) == 0;
}

/* Run the packaged lfanew with ARGS (NULL-terminated); return exit status. */
static int
run_tool (const char *const *args)
{
  const char *argv[16];
  int i = 0, status;
  pid_t pid;

  if (launcher)
    argv[i++] = launcher;
  argv[i++] = tool;
  while (*args)
    argv[i++] = *args++;
  argv[i] = NULL;

  fflush (stdout);
  pid = fork ();
  if (pid == -1)
    return -1;
  if (pid == 0)
    {
      execv (argv[0], (char *const *) argv);
      _exit (127);
    }
  if (waitpid (pid, &status, 0) != pid || ! WIFEXITED (status))
    return -1;
  return WEXITSTATUS (status);
}

static void
test_endian (void)
{
  uint_le16_t v16 = hle16 (0xa1b2);
  uint_le32_t v32 = hle32 (0x11223344UL);
  uint_le64_t v64 = hle64 (0x0102030405060708ULL);
  const unsigned char *p16 = (const unsigned char *) &v16;
  const unsigned char *p32 = (const unsigned char *) &v32;
  const unsigned char *p64 = (const unsigned char *) &v64;
  unsigned char raw[9] = { 0xee, 0x78, 0x56, 0x34, 0x12, 0, 0, 0, 0 };
  uint_le32_t odd;

  puts ("[1] <nexgen/mzendian.h> little-endian accessors");
  CHECK (sizeof v16 == 2 && sizeof v32 == 4 && sizeof v64 == 8,
         "uint_le16/32/64_t are 2/4/8 bytes");
  CHECK (p16[0] == 0xb2 && p16[1] == 0xa1, "hle16 stores LE bytes");
  CHECK (p32[0] == 0x44 && p32[3] == 0x11, "hle32 stores LE bytes");
  CHECK (p64[0] == 0x08 && p64[7] == 0x01, "hle64 stores LE bytes");
  CHECK (leh16 (v16) == 0xa1b2 && leh32 (v32) == 0x11223344UL
         && leh64 (v64) == 0x0102030405060708ULL, "leh16/32/64 round trip");
  CHECK (leh32hi (v32) == 0x1122 && leh32lo (v32) == 0x3344,
         "leh32hi/leh32lo halves");
  CHECK (leh64hi (v64) == 0x01020304UL && leh64lo (v64) == 0x05060708UL,
         "leh64hi/leh64lo halves");
  memcpy (&odd, raw + 1, sizeof odd);
  CHECK (leh32 (odd) == 0x12345678UL, "leh32 on bytes from odd offset");
  CHECK (sizeof (mz_hdr_t) == 0x40 && MZ_LFARLC_NEW == 0x40
         && offsetof (mz_hdr_t, e_lfanew) == 0x3c,
         "mz_hdr_t layout: 0x40 bytes, e_lfanew at 0x3c");
}

/* Old-style MZ: 0x1c-byte header, 2 relocations, 3-paragraph header,
   0x33-byte load image (total 0x63, deliberately not paragraph aligned). */
#define OLD_SZ      0x63
#define OLD_HDR_END 0x30
static unsigned char old_mz[OLD_SZ];

static void
build_old_mz (void)
{
  static const char msg[] = "world, hello\r\n$";
  mz_hdr_t h;
  size_t i;

  memset (&h, 0, sizeof h);
  h.e_magic = hle16 (MZ_MAGIC);
  h.e_cblp = hle16 (OLD_SZ);
  h.e_cp = hle16 (1);
  h.e_crlc = hle16 (2);
  h.e_cparhdr = hle16 (OLD_HDR_END / MZ_PARA_SZ);
  h.e_maxalloc = hle16 (0xffff);
  h.e_ss = hle16 (0xfff0);
  h.e_sp = hle16 (0x0100);
  h.e_ip = hle16 (0x0010);
  h.e_lfarlc = hle16 (0x1c);
  memset (old_mz, 0, sizeof old_mz);
  memcpy (old_mz, &h, 0x1c);
  old_mz[0x1c] = 0x01;          /* relocation 1: 0000:0001 */
  old_mz[0x20] = 0x05;          /* relocation 2: 0000:0005 */
  memcpy (old_mz + OLD_HDR_END, msg, sizeof msg - 1);
  for (i = OLD_HDR_END + sizeof msg - 1; i < OLD_SZ; i++)
    old_mz[i] = (unsigned char) (i * 7 + 3);
}

static int
all_zero (const unsigned char *p, size_t n)
{
  while (n--)
    if (*p++)
      return 0;
  return 1;
}

static void
test_add_lfanew (void)
{
  static const char *const args[] = { "-o", NULL, NULL, NULL };
  const char *a[4];
  unsigned char *out;
  size_t n = 0;
  mz_hdr_t h;

  puts ("[2] lfanew (default mode): old MZ stub -> MZ with .e_lfanew");
  build_old_mz ();
  CHECK (write_bytes (wpath ("old.exe"), old_mz, sizeof old_mz) == 0,
         "consumer wrote old.exe via _binmode()");
  memcpy (a, args, sizeof a);
  a[1] = wpath ("new.exe");
  a[2] = wpath ("old.exe");
  CHECK (run_tool (a) == 0, "`lfanew -o new.exe old.exe` exits 0");
  out = read_bytes (wpath ("new.exe"), &n);
  CHECK (out && n == 0x90, "new.exe is 0x90 bytes (0x40 hdr + relocs + image)");
  if (! out || n != 0x90)
    {
      free (out);
      return;
    }
  memcpy (&h, out, sizeof h);
  CHECK (leh16 (h.e_magic) == MZ_MAGIC, "e_magic is MZ");
  CHECK (leh16 (h.e_lfarlc) == MZ_LFARLC_NEW, "e_lfarlc moved to 0x40");
  CHECK (leh16 (h.e_cparhdr) == 5, "e_cparhdr grown 3 -> 5 paragraphs");
  CHECK (leh16 (h.e_cblp) == 0x90 && leh16 (h.e_cp) == 1,
         "e_cblp/e_cp describe the 0x90-byte stub");
  CHECK (leh32 (h.e_lfanew) == 0x90, "e_lfanew points to end of stub");
  CHECK (leh16 (h.e_crlc) == 2 && leh16 (h.e_ss) == 0xfff0
         && leh16 (h.e_sp) == 0x0100 && leh16 (h.e_ip) == 0x0010
         && leh16 (h.e_maxalloc) == 0xffff,
         "e_crlc/e_ss/e_sp/e_ip/e_maxalloc preserved");
  CHECK (memcmp (out + 0x40, old_mz + 0x1c, 8) == 0,
         "relocation table copied to 0x40");
  CHECK (all_zero (out + 0x48, 8), "header padded with zeros to 0x50");
  CHECK (memcmp (out + 0x50, old_mz + OLD_HDR_END, OLD_SZ - OLD_HDR_END) == 0,
         "load image copied byte-for-byte");
  CHECK (all_zero (out + 0x50 + OLD_SZ - OLD_HDR_END,
                   0x90 - 0x50 - (OLD_SZ - OLD_HDR_END)),
         "image tail zero-padded to paragraph boundary");
  free (out);

  a[1] = wpath ("again.exe");
  a[2] = wpath ("new.exe");
  CHECK (run_tool (a) == 2, "rewriting an MZ that already has e_lfanew fails (2)");
  CHECK (! exists (wpath ("again.exe")), "failed run leaves no again.exe");
}

#define PAYLOAD_SZ 0x80
static unsigned char payload[PAYLOAD_SZ];

static void
test_stubify_roundtrip (void)
{
  unsigned char *stub, *fat, *back;
  size_t stub_n = 0, fat_n = 0, back_n = 0, i;
  const char *a[6];
  mz_hdr_t h;

  puts ("[3] lfanew -S / -U: stubify then unstubify a payload");
  payload[0] = 'N';
  payload[1] = 'E';
  for (i = 2; i < PAYLOAD_SZ; i++)
    payload[i] = (unsigned char) (0xa5 ^ (i * 13));
  CHECK (write_bytes (wpath ("payload.bin"), payload, sizeof payload) == 0,
         "consumer wrote payload.bin");

  a[0] = "-S";
  a[1] = "-o";
  a[2] = wpath ("fat.exe");
  a[3] = wpath ("payload.bin");
  a[4] = wpath ("new.exe");
  a[5] = NULL;
  CHECK (run_tool (a) == 0, "`lfanew -S -o fat.exe payload.bin new.exe` exits 0");
  stub = read_bytes (wpath ("new.exe"), &stub_n);
  fat = read_bytes (wpath ("fat.exe"), &fat_n);
  CHECK (stub && fat && fat_n == stub_n + PAYLOAD_SZ,
         "fat.exe = stub + payload in size");
  if (stub && fat && fat_n == stub_n + PAYLOAD_SZ)
    {
      memcpy (&h, fat, sizeof h);
      CHECK (memcmp (fat, stub, stub_n) == 0, "fat.exe starts with the MZ stub");
      CHECK (memcmp (fat + stub_n, payload, PAYLOAD_SZ) == 0,
             "payload appended verbatim");
      CHECK (leh32 (h.e_lfanew) == stub_n
             && fat[leh32 (h.e_lfanew)] == 'N',
             "e_lfanew locates the payload magic");
    }
  free (stub);
  free (fat);

  a[0] = "-U";
  a[1] = "-o";
  a[2] = wpath ("back.bin");
  a[3] = wpath ("fat.exe");
  a[4] = NULL;
  CHECK (run_tool (a) == 0, "`lfanew -U -o back.bin fat.exe` exits 0");
  back = read_bytes (wpath ("back.bin"), &back_n);
  CHECK (back && back_n == PAYLOAD_SZ
         && memcmp (back, payload, PAYLOAD_SZ) == 0,
         "unstubify returns the original payload byte-for-byte");
  free (back);
}

static void
test_refusals (void)
{
  unsigned char le[16] = { 'L', 'E', 0, 0 };
  const char *a[6];

  puts ("[4] refusal paths clean up their output");
  CHECK (write_bytes (wpath ("le.bin"), le, sizeof le) == 0,
         "consumer wrote LE-magic payload");
  a[0] = "-S";
  a[1] = "-o";
  a[2] = wpath ("bad.exe");
  a[3] = wpath ("le.bin");
  a[4] = wpath ("new.exe");
  a[5] = NULL;
  CHECK (run_tool (a) == 2, "stubifying an LE program is refused (2)");
  CHECK (! exists (wpath ("bad.exe")), "no bad.exe left behind");

  a[0] = "-o";
  a[1] = wpath ("x.exe");
  a[2] = wpath ("payload.bin");
  a[3] = NULL;
  CHECK (run_tool (a) == 2, "non-MZ input is rejected (2)");
  CHECK (! exists (wpath ("x.exe")), "no x.exe left behind");
}

static int
is_exe (const struct dirent *ent)
{
  size_t n = strlen (ent->d_name);
  return n > 4 && strcmp (ent->d_name + n - 4, ".exe") == 0;
}

static int
by_name (const struct dirent **x, const struct dirent **y)
{
  return strcmp ((*x)->d_name, (*y)->d_name);
}

static void
test_scandir (void)
{
  static const char *const want[] = { "fat.exe", "new.exe", "old.exe" };
  struct dirent **names = NULL;
  int n, i, ok = 1;

  puts ("[5] <lfanew/dirent.h>: scandir + _direntdup on the work directory");
  n = scandir (workdir, &names, is_exe, by_name);
  CHECK (n == 3, "exactly fat.exe, new.exe, old.exe survive");
  for (i = 0; i < n; i++)
    {
      struct dirent *dup = _direntdup (names[i]);
      if (! dup || strcmp (dup->d_name, names[i]->d_name) != 0
          || (n == 3 && strcmp (dup->d_name, want[i]) != 0))
        ok = 0;
      free (dup);
      free (names[i]);
    }
  free (names);
  CHECK (n == 3 && ok, "_direntdup copies every entry name intact");
}

int
main (int argc, char **argv)
{
  if (argc < 3 || argc > 4)
    {
      fprintf (stderr, "usage: %s LFANEW-TOOL WORK-DIR [LAUNCHER]\n", argv[0]);
      return 2;
    }
  tool = argv[1];
  workdir = argv[2];
  launcher = argc == 4 && argv[3][0] ? argv[3] : NULL;

  test_endian ();
  test_add_lfanew ();
  test_stubify_roundtrip ();
  test_refusals ();
  test_scandir ();

  printf ("lfanew consumer test: %d/%d checks passed\n",
          checks - failures, checks);
  return failures ? 1 : 0;
}
