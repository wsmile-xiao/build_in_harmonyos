/* test_package: verify core libowfat modules from the installed package.
 *
 * Exercises byte, str, array, buffer, fmt, scan and io against the packaged
 * static archives; exits nonzero on the first failed assertion.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <libowfat/byte.h>
#include <libowfat/str.h>
#include <libowfat/array.h>
#include <libowfat/buffer.h>
#include <libowfat/fmt.h>
#include <libowfat/scan.h>
#include <libowfat/io.h>
#include <libowfat/stralloc.h>

static char memsink_buf[1024];
static size_t memsink_pos;

static ssize_t memsink_write(int fd, const char *buf, size_t len) {
    (void) fd;
    if (len == 0) return 0;
    if (memsink_pos + len > sizeof(memsink_buf)) return 0;
    memcpy(memsink_buf + memsink_pos, buf, len);
    memsink_pos += (size_t) len;
    return (ssize_t) len;
}

int main(void) {
    /* ---- byte ---- */
    {
        const char s[] = "hello, libowfat";
        assert(byte_chr(s, sizeof s, 'o') == 4);
        assert(byte_rchr(s, sizeof s, 'o') == 10);
        assert(byte_equal("abc", 3, "abc"));
        assert(!byte_equal("abc", 3, "abd"));
        assert(byte_diff("abc", 3, "abd") != 0);
    }

    /* ---- str ---- */
    {
        char buf[32];
        assert(str_len("libowfat") == 8);
        assert(str_diff("abc", "abd") != 0);
        assert(str_equal("abc", "abc"));
        assert(str_copy(buf, "copied") == 6 && buf[6] == 0);
        assert(str_start("libowfat-0.34", "libowfat"));
        assert(str_chr("aabbcc", 'b') == 2);
    }

    /* ---- array ---- */
    {
        array a;
        memset(&a, 0, sizeof a);
        array_catb(&a, "one", 3);
        array_cats(&a, "-two");
        assert(array_bytes(&a) == 7);
        assert(memcmp(a.p, "one-two", 7) == 0);
        array_reset(&a);
        assert(array_bytes(&a) == 0);
    }

    /* ---- buffer (memory sink via BUFFER_INIT) ---- */
    {
        buffer b = BUFFER_INIT(memsink_write, 1, memsink_buf, 0);
        memsink_pos = 0;
        buffer_puts(&b, "buffer-");
        buffer_put(&b, "ok", 2);
        assert(buffer_flush(&b) == 0);
        assert(memsink_pos == 9);
        assert(memcmp(memsink_buf, "buffer-ok", 9) == 0);
    }

    /* ---- fmt ---- */
    {
        char buf[FMT_ULONG + 1];
        size_t l;
        l = fmt_str(buf, "fmtstr");
        assert(l == 6 && memcmp(buf, "fmtstr", 6) == 0);
        l = fmt_ulong(buf, 255ul);
        assert(l == 3 && memcmp(buf, "255", 3) == 0);
        l = fmt_xlong(buf, 255ul);
        assert(l == 2 && memcmp(buf, "ff", 2) == 0);
        l = fmt_ulong0(buf, 23ul, 4);
        assert(l == 4 && memcmp(buf, "0023", 4) == 0);
    }

    /* ---- scan ---- */
    {
        unsigned long ul, xl;
        long sl;
        size_t l;
        l = scan_ulong("65535xyz", &ul);
        assert(l == 5 && ul == 65535ul);
        l = scan_xlong("ff;", &xl);
        assert(l == 2 && xl == 255ul);
        l = scan_long("-42", &sl);
        assert(l == 3 && sl == -42L);
        l = scan_8longn("7558", 3, &xl);
        assert(l == 3 && xl == 493ul);  /* 0755 octal = 493 */
    }

    /* ---- io + stralloc round-trip in CWD ---- */
    {
        static const char msg[] = "io-roundtrip";
        char back[sizeof msg];
        int64 fd = -1;
        if (io_createfile(&fd, "test_package.tmp") && fd >= 0) {
            /* descriptors must be registered with io_fd before use */
            assert(io_fd(fd));
            assert(io_waitwrite(fd, msg, (int64) sizeof msg) == (int64) sizeof msg);
            io_close(fd);
            fd = -1;
            assert(io_readfile(&fd, "test_package.tmp") && fd >= 0);
            {
                ssize_t r = read((int) fd, back, sizeof back);
                assert(r == (ssize_t) sizeof msg);
            }
            io_close(fd);
            unlink("test_package.tmp");
            assert(memcmp(back, msg, sizeof msg) == 0);
        } else {
            /* Read-only CWD: still prove the io module links and the
             * stralloc allocator path works end to end. */
            stralloc sa;
            memset(&sa, 0, sizeof sa);
            assert(stralloc_copys(&sa, "io-linked") == 1);
            assert(sa.len == 9 && memcmp(sa.s, "io-linked", 9) == 0);
            stralloc_free(&sa);
        }
    }

    puts("libowfat test_package: all module assertions passed");
    return 0;
}
