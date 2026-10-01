/*
 * Consumer test for the macutils command-line tools (HarmonyOS PC / OHOS).
 *
 * The program is compiled against the target toolchain and drives the tools
 * shipped in the macutils package (found on PATH via the Conan run env):
 *
 *   1. macunpack: extract a PackIt archive that this program synthesises
 *      (MacBinary II wrapper, per-entry header CRC, fork CRC); Mac Roman file
 *      names go through util/transname.c (patched: musl has neither MAXNAMLEN
 *      nor DIRSIZ, FNAMELEN now falls back to NAME_MAX); a corrupted archive
 *      must be rejected by the fork CRC check.
 *   2. binhex: encode a data file to BinHex 4.0; the result is decoded here by
 *      an independent decoder (6-bit alphabet, 0x90 RLE, header/data/rsrc CRC).
 *   3. hexbin: decode the .hqx back to fork files (byte-identical); a tampered
 *      .hqx must not reproduce the original data fork.
 *   4. macstream + macsave: re-pack the fork files from step 1 into a MacBinary
 *      stream (header CRC checked here) and unpack it again (byte-identical).
 *
 * Usage: test_macutils <empty-or-new work directory>
 */
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int failures;

static int fail(const char *fmt, ...)
{
    va_list ap;
    fprintf(stderr, "FAIL: ");
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
    failures++;
    return -1;
}

#define CHECK(cond, ...) do { if (!(cond)) return fail(__VA_ARGS__); } while (0)

/* CRC-16/CCITT (poly 0x1021, init 0) as used by BinHex 4.0, MacBinary II
 * and PackIt. */
static unsigned crc16(const unsigned char *p, size_t n, unsigned crc)
{
    size_t i;
    int b;
    for (i = 0; i < n; i++) {
        crc ^= (unsigned)p[i] << 8;
        for (b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
        crc &= 0xffff;
    }
    return crc;
}

static void put2(unsigned char *p, unsigned v) { p[0] = v >> 8; p[1] = v; }
static void put4(unsigned char *p, unsigned long v)
{
    p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v;
}
static unsigned get2(const unsigned char *p) { return (p[0] << 8) | p[1]; }
static unsigned long get4(const unsigned char *p)
{
    return ((unsigned long)p[0] << 24) | ((unsigned long)p[1] << 16) |
           ((unsigned long)p[2] << 8) | p[3];
}

/* ---- file helpers ------------------------------------------------------ */

static unsigned char *read_file(const char *path, size_t *len)
{
    FILE *f = fopen(path, "rb");
    unsigned char *buf;
    long n;
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    buf = malloc(n > 0 ? (size_t)n : 1);
    if (buf && n > 0 && fread(buf, 1, (size_t)n, f) != (size_t)n) {
        free(buf);
        buf = NULL;
    }
    fclose(f);
    *len = (size_t)(n > 0 ? n : 0);
    return buf;
}

static int write_file(const char *path, const unsigned char *buf, size_t len)
{
    FILE *f = fopen(path, "wb");
    if (!f)
        return -1;
    if (len && fwrite(buf, 1, len, f) != len) {
        fclose(f);
        return -1;
    }
    return fclose(f);
}

/* Compare a file with an expected buffer. */
static int same_file(const char *path, const unsigned char *want, size_t len)
{
    size_t got_len;
    unsigned char *got = read_file(path, &got_len);
    int ok = got && got_len == len && (len == 0 || memcmp(got, want, len) == 0);
    free(got);
    return ok;
}

/* Run a tool from PATH inside `dir`, optional stdin/stdout redirection.
 * Returns the exit status (128+signal when killed, 127 exec failure). */
static int run_tool(const char *dir, const char *in, const char *out,
                    char *const argv[])
{
    pid_t pid;
    int status;
    fflush(NULL);
    pid = fork();
    if (pid < 0)
        return -1;
    if (pid == 0) {
        int fd;
        if (chdir(dir) != 0)
            _exit(126);
        if (in) {
            fd = open(in, O_RDONLY);
            if (fd < 0 || dup2(fd, 0) < 0)
                _exit(126);
            close(fd);
        }
        if (out) {
            fd = open(out, O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if (fd < 0 || dup2(fd, 1) < 0)
                _exit(126);
            close(fd);
        }
        execvp(argv[0], argv);
        _exit(127);
    }
    if (waitpid(pid, &status, 0) < 0)
        return -1;
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    return WIFSIGNALED(status) ? 128 + WTERMSIG(status) : -1;
}

static char *path_join(char *buf, const char *a, const char *b)
{
    if (snprintf(buf, 4096, "%s/%s", a, b) >= 4096)
        buf[0] = '\0';
    return buf;
}

static int make_dir(const char *root, const char *name, char *out)
{
    path_join(out, root, name);
    if (mkdir(out, 0755) != 0 && errno != EEXIST)
        return fail("mkdir %s: %s", out, strerror(errno));
    return 0;
}

/* ---- test data ----------------------------------------------------------- */

/* Mac Roman name: 0x8E = e-acute, 0x9F = u-diaeresis; the space and the two
 * high characters are mapped by transname() -> "Cafe_Menu". */
static const unsigned char MAC_NAME[] = "Caf\x8e Men\x9f";
#define MAC_NAME_LEN 9
#define UNIX_NAME "Cafe_Menu"

static unsigned char data_fork[3000], rsrc_fork[777];

static void fill_payloads(void)
{
    unsigned long seed = 20260926UL;
    size_t i;
    for (i = 0; i < sizeof(data_fork); i++) {
        seed = seed * 1103515245UL + 12345UL;
        data_fork[i] = (unsigned char)(seed >> 16);
    }
    /* runs for the BinHex RLE path, including the RLE marker byte 0x90 */
    memset(data_fork + 100, 'A', 300);
    memset(data_fork + 600, 0x90, 40);
    memset(data_fork + 1200, 0x00, 260);
    for (i = 0; i < sizeof(rsrc_fork); i++)
        rsrc_fork[i] = (unsigned char)(i * 7 + 3);
}

/* MacBinary II header (128 bytes) with CRC over bytes 0..123. */
static void macbinary_header(unsigned char *h, const unsigned char *name,
                             int nlen, const char *type, const char *creator,
                             unsigned long dlen, unsigned long rlen)
{
    memset(h, 0, 128);
    h[1] = (unsigned char)nlen;
    memcpy(h + 2, name, nlen);
    memcpy(h + 65, type, 4);
    memcpy(h + 69, creator, 4);
    put4(h + 83, dlen);
    put4(h + 87, rlen);
    put4(h + 91, 0xA5B6C7D8UL);   /* creation time (Mac epoch) */
    put4(h + 95, 0xA5B6C7D9UL);   /* modification time */
    h[122] = 129;
    h[123] = 129;
    put2(h + 124, crc16(h, 124, 0));
}

/* One uncompressed PackIt entry: "PMag", 94-byte header, forks, fork CRC. */
static size_t pit_entry(unsigned char *p, const unsigned char *name, int nlen,
                        const unsigned char *d, size_t dlen,
                        const unsigned char *r, size_t rlen)
{
    unsigned char *h = p + 4;
    size_t off;
    unsigned crc;
    memcpy(p, "PMag", 4);
    memset(h, 0, 94);
    h[0] = (unsigned char)nlen;
    memcpy(h + 1, name, nlen);
    memcpy(h + 64, "TEXT", 4);
    memcpy(h + 68, "OHOS", 4);
    put4(h + 76, dlen);
    put4(h + 80, rlen);
    put4(h + 84, 0xA5B6C7D8UL);
    put4(h + 88, 0xA5B6C7D9UL);
    put2(h + 92, crc16(h, 92, 0));
    off = 4 + 94;
    memcpy(p + off, d, dlen);
    off += dlen;
    memcpy(p + off, r, rlen);
    off += rlen;
    crc = crc16(r, rlen, crc16(d, dlen, 0));
    put2(p + off, crc);
    return off + 2;
}

/* ---- test 1: macunpack on a PackIt archive -------------------------------- */

static size_t build_pit_macbinary(unsigned char *out)
{
    static unsigned char pit[8192];
    static const unsigned char second[] = "notes";
    static const unsigned char notes[] = "PackIt entry without resource fork\n";
    size_t n = 0, total;

    n += pit_entry(pit + n, MAC_NAME, MAC_NAME_LEN, data_fork,
                   sizeof(data_fork), rsrc_fork, sizeof(rsrc_fork));
    n += pit_entry(pit + n, second, 5, notes, sizeof(notes) - 1, NULL, 0);
    memcpy(pit + n, "PEnd", 4);
    n += 4;

    macbinary_header(out, (const unsigned char *)"Archive.pit", 11,
                     "PIT ", "PIT ", n, 0);
    memcpy(out + 128, pit, n);
    total = 128 + ((n + 127) / 128) * 128;
    memset(out + 128 + n, 0, total - 128 - n);
    return total;
}

static int test_macunpack(const char *root)
{
    static unsigned char archive[16384];
    char dir[4096], p[4096], bad[4096];
    unsigned char *info;
    size_t len, ilen;
    int rc;
    char *argv_ok[] = { "macunpack", "-3", "../archive.bin", NULL };
    char *argv_bad[] = { "macunpack", "-3", "../corrupt.bin", NULL };

    len = build_pit_macbinary(archive);
    CHECK(write_file(path_join(p, root, "archive.bin"), archive, len) == 0,
          "cannot write archive.bin");
    if (make_dir(root, "unpack", dir) != 0)
        return -1;
    rc = run_tool(dir, NULL, NULL, argv_ok);
    CHECK(rc == 0, "macunpack exited with %d", rc);

    CHECK(same_file(path_join(p, dir, UNIX_NAME ".data"), data_fork,
                    sizeof(data_fork)),
          "macunpack: %s.data differs from the packed data fork", UNIX_NAME);
    CHECK(same_file(path_join(p, dir, UNIX_NAME ".rsrc"), rsrc_fork,
                    sizeof(rsrc_fork)),
          "macunpack: %s.rsrc differs from the packed resource fork", UNIX_NAME);
    info = read_file(path_join(p, dir, UNIX_NAME ".info"), &ilen);
    CHECK(info && ilen == 128, "macunpack: %s.info missing or not 128 bytes",
          UNIX_NAME);
    CHECK(info[1] == MAC_NAME_LEN && memcmp(info + 2, MAC_NAME, MAC_NAME_LEN) == 0,
          "macunpack: original Mac Roman name not kept in .info");
    CHECK(memcmp(info + 65, "TEXTOHOS", 8) == 0,
          "macunpack: type/creator not kept in .info");
    CHECK(get4(info + 83) == sizeof(data_fork) &&
          get4(info + 87) == sizeof(rsrc_fork),
          "macunpack: fork lengths in .info are wrong");
    free(info);
    CHECK(same_file(path_join(p, dir, "notes.data"),
                    (const unsigned char *)"PackIt entry without resource fork\n",
                    35),
          "macunpack: second archive entry not extracted");
    printf("OK: macunpack extracted 2 PackIt entries, Mac Roman name -> %s\n",
           UNIX_NAME);

    /* corrupt one data byte of the first entry: fork CRC must reject it */
    archive[128 + 4 + 94 + 1500] ^= 0x5a;
    CHECK(write_file(path_join(p, root, "corrupt.bin"), archive, len) == 0,
          "cannot write corrupt.bin");
    if (make_dir(root, "unpack-bad", bad) != 0)
        return -1;
    rc = run_tool(bad, NULL, NULL, argv_bad);
    CHECK(rc != 0, "macunpack accepted an archive with a broken fork CRC");
    printf("OK: macunpack rejected corrupted archive (exit %d)\n", rc);
    return 0;
}

/* ---- test 2: binhex + independent BinHex 4.0 decoder ---------------------- */

static const char HQX_ALPHABET[] =
    "!\"#$%&'()*+,-012345689@ABCDEFGHIJKLMNPQRSTUVXYZ[`abcdefhijklmpqr";

/* Decode the BinHex 4.0 body of `text` into `out` (RLE expanded). */
static long hqx_decode(const unsigned char *text, size_t tlen,
                       unsigned char *out, size_t cap)
{
    const char *hdr = "(This file must be converted";
    const unsigned char *s, *end = text + tlen;
    unsigned long acc = 0;
    int bits = 0, have_last = 0, rle = 0;
    unsigned char last = 0;
    size_t n = 0;

    s = (const unsigned char *)strstr((const char *)text, hdr);
    if (!s)
        return -1;
    while (s < end && *s != '\n')
        s++;
    while (s < end && *s != ':')
        s++;
    if (s >= end)
        return -2;
    for (s++; s < end && *s != ':'; s++) {
        const char *q;
        unsigned char b;
        if (*s == '\n' || *s == '\r')
            continue;
        q = strchr(HQX_ALPHABET, *s);
        if (!q || !*s)
            return -3;
        acc = (acc << 6) | (unsigned long)(q - HQX_ALPHABET);
        bits += 6;
        if (bits < 8)
            continue;
        bits -= 8;
        b = (unsigned char)(acc >> bits);
        if (rle) {
            rle = 0;
            if (b == 0) {
                if (n >= cap) return -4;
                out[n++] = last = 0x90;
            } else {
                int k;
                if (!have_last) return -5;
                for (k = 1; k < b; k++) {
                    if (n >= cap) return -4;
                    out[n++] = last;
                }
            }
        } else if (b == 0x90) {
            rle = 1;
        } else {
            if (n >= cap) return -4;
            out[n++] = last = b;
            have_last = 1;
        }
    }
    return s < end ? (long)n : -6;
}

static int test_binhex(const char *root, char *hqx_name)
{
    static unsigned char dec[16384];
    char p[4096];
    unsigned char *text, *h;
    size_t tlen, off;
    long n;
    int rc, nlen;
    unsigned long dlen, rlen;
    char *argv[] = { "binhex", "-d", "-c", "OHOS", "-t", "TEST",
                     "payload.dat", NULL };

    CHECK(write_file(path_join(p, root, "payload.dat"), data_fork,
                     sizeof(data_fork)) == 0, "cannot write payload.dat");
    strcpy(hqx_name, "payload.hqx");
    rc = run_tool(root, NULL, hqx_name, argv);
    CHECK(rc == 0, "binhex exited with %d", rc);

    text = read_file(path_join(p, root, hqx_name), &tlen);
    CHECK(text && tlen > 0, "binhex produced no output");
    text = realloc(text, tlen + 1);
    text[tlen] = '\0';
    n = hqx_decode(text, tlen, dec, sizeof(dec));
    free(text);
    CHECK(n > 0, "BinHex 4.0 stream not decodable (code %ld)", n);

    h = dec;
    nlen = h[0];
    CHECK(nlen == 11 && memcmp(h + 1, "payload.dat", 11) == 0,
          "BinHex header: unexpected file name");
    off = 1 + nlen + 1;                               /* name + version byte */
    CHECK(memcmp(dec + off, "TESTOHOS", 8) == 0,
          "BinHex header: type/creator not TEST/OHOS");
    dlen = get4(dec + off + 10);
    rlen = get4(dec + off + 14);
    CHECK(dlen == sizeof(data_fork) && rlen == 0,
          "BinHex header: fork lengths %lu/%lu", dlen, rlen);
    CHECK(get2(dec + off + 18) == crc16(dec, off + 18, 0),
          "BinHex header CRC mismatch");
    off += 20;
    CHECK((size_t)n >= off + dlen + 2 + rlen + 2, "BinHex stream truncated");
    CHECK(memcmp(dec + off, data_fork, dlen) == 0,
          "BinHex data fork differs from input");
    CHECK(get2(dec + off + dlen) == crc16(dec + off, dlen, 0),
          "BinHex data fork CRC mismatch");
    off += dlen + 2;
    CHECK(get2(dec + off + rlen) == crc16(dec + off, rlen, 0),
          "BinHex resource fork CRC mismatch");
    printf("OK: binhex output decoded independently (%ld bytes, 3 CRCs valid)\n",
           n);
    return 0;
}

/* ---- test 3: hexbin decode + tamper detection ----------------------------- */

static int test_hexbin(const char *root, const char *hqx_name)
{
    char dir[4096], bad[4096], p[4096], src[4096];
    unsigned char *text;
    size_t tlen, i;
    int rc, changed = 0;
    char *argv_ok[] = { "hexbin", "-3", "../payload.hqx", NULL };
    char *argv_bad[] = { "hexbin", "-3", "../tampered.hqx", NULL };

    if (make_dir(root, "hexbin", dir) != 0)
        return -1;
    rc = run_tool(dir, NULL, NULL, argv_ok);
    CHECK(rc == 0, "hexbin exited with %d", rc);
    CHECK(same_file(path_join(p, dir, "payload.dat.data"), data_fork,
                    sizeof(data_fork)),
          "hexbin: payload.dat.data differs from the original");
    CHECK(same_file(path_join(p, dir, "payload.dat.rsrc"), NULL, 0),
          "hexbin: payload.dat.rsrc should be empty");
    printf("OK: hexbin restored the data fork byte-for-byte\n");

    /* flip one encoded character in the middle of the body */
    text = read_file(path_join(src, root, hqx_name), &tlen);
    CHECK(text != NULL, "cannot read %s", hqx_name);
    for (i = tlen / 2; i < tlen; i++) {
        const char *q = strchr(HQX_ALPHABET, text[i]);
        if (text[i] && q && text[i] != ':') {
            text[i] = (text[i] == 'a') ? 'b' : 'a';
            changed = 1;
            break;
        }
    }
    CHECK(changed, "no character to tamper with");
    CHECK(write_file(path_join(p, root, "tampered.hqx"), text, tlen) == 0,
          "cannot write tampered.hqx");
    free(text);
    if (make_dir(root, "hexbin-bad", bad) != 0)
        return -1;
    rc = run_tool(bad, NULL, NULL, argv_bad);
    CHECK(rc != 0 || !same_file(path_join(p, bad, "payload.dat.data"),
                                data_fork, sizeof(data_fork)),
          "hexbin silently accepted a tampered .hqx");
    printf("OK: hexbin detected the tampered .hqx (exit %d)\n", rc);
    return 0;
}

/* ---- test 4: macstream -> macsave round trip ------------------------------- */

static int test_macstream_macsave(const char *root)
{
    char unpack[4096], dir[4096], p[4096];
    unsigned char *s;
    size_t slen, off;
    int rc;
    char *argv_stream[] = { "macstream", UNIX_NAME ".info", NULL };
    char *argv_save[] = { "macsave", "-3", NULL };

    path_join(unpack, root, "unpack");
    rc = run_tool(unpack, NULL, "../stream.bin", argv_stream);
    CHECK(rc == 0, "macstream exited with %d", rc);
    s = read_file(path_join(p, root, "stream.bin"), &slen);
    CHECK(s && slen >= 128, "macstream produced no MacBinary stream");
    CHECK(s[1] == MAC_NAME_LEN && memcmp(s + 2, MAC_NAME, MAC_NAME_LEN) == 0 &&
          memcmp(s + 65, "TEXTOHOS", 8) == 0,
          "macstream: MacBinary header lost name/type/creator");
    CHECK(get4(s + 83) == sizeof(data_fork) && get4(s + 87) == sizeof(rsrc_fork),
          "macstream: MacBinary fork lengths are wrong");
    CHECK(s[122] < 129 || get2(s + 124) == crc16(s, 124, 0),
          "macstream: MacBinary II header CRC mismatch");
    off = 128;
    CHECK(slen >= off + sizeof(data_fork) &&
          memcmp(s + off, data_fork, sizeof(data_fork)) == 0,
          "macstream: data fork not at offset 128");
    off += ((sizeof(data_fork) + 127) / 128) * 128;
    CHECK(slen >= off + sizeof(rsrc_fork) &&
          memcmp(s + off, rsrc_fork, sizeof(rsrc_fork)) == 0,
          "macstream: resource fork not after the padded data fork");
    free(s);

    if (make_dir(root, "macsave", dir) != 0)
        return -1;
    rc = run_tool(dir, "../stream.bin", NULL, argv_save);
    CHECK(rc == 0, "macsave exited with %d", rc);
    CHECK(same_file(path_join(p, dir, UNIX_NAME ".data"), data_fork,
                    sizeof(data_fork)) &&
          same_file(path_join(p, dir, UNIX_NAME ".rsrc"), rsrc_fork,
                    sizeof(rsrc_fork)),
          "macsave: forks differ after the macstream round trip");
    printf("OK: macstream -> macsave round trip is byte-identical\n");
    return 0;
}

int main(int argc, char **argv)
{
    char hqx_name[64];
    const char *root;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <work directory>\n", argv[0]);
        return 2;
    }
    root = argv[1];
    if (mkdir(root, 0755) != 0 && errno != EEXIST) {
        fprintf(stderr, "cannot create %s: %s\n", root, strerror(errno));
        return 2;
    }
    fill_payloads();

    test_macunpack(root);
    if (test_binhex(root, hqx_name) == 0)
        test_hexbin(root, hqx_name);
    test_macstream_macsave(root);

    if (failures) {
        fprintf(stderr, "%d macutils consumer check(s) failed\n", failures);
        return 1;
    }
    printf("ALL MACUTILS CONSUMER TESTS PASSED\n");
    return 0;
}
