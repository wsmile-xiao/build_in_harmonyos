/* libxdmcp 1.1.5 consumer link + API smoke test.
 *
 * Exercises the XdmcpBuffer CARD8/16/32 round-trip path:
 *   XdmcpWriteCARD8/16/32(buf, value) -> XdmcpReadCARD8/16/32(buf, &out)
 * This is the smallest API surface that proves the library is linkable
 * and that its public type definitions (XdmcpBuffer) work as documented.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <X11/Xdmcp.h>

int main(void) {
    /* 1. Allocate a stack-resident XdmcpBuffer with a heap-backed data array.
     *    XdmcpBuffer.count = upper read bound (readable bytes);
     *    XdmcpBuffer.pointer = current read/write index into data (int);
     *    XdmcpBuffer.size = total writable capacity. */
    enum { BUFSIZE = 128 };
    unsigned char storage[BUFSIZE];
    XdmcpBuffer buf;
    memset(&buf, 0, sizeof(buf));
    buf.data = storage;
    buf.size = BUFSIZE;
    buf.count = BUFSIZE;

    /* 2. Write three CARD8 values. */
    if (XdmcpWriteCARD8(&buf, 0xA5) != 1) {
        fprintf(stderr, "XdmcpWriteCARD8 returned non-1 for first byte\n");
        return 1;
    }
    if (XdmcpWriteCARD8(&buf, 0x5A) != 1) {
        fprintf(stderr, "XdmcpWriteCARD8 returned non-1 for second byte\n");
        return 2;
    }
    if (XdmcpWriteCARD8(&buf, 0x00) != 1) {
        fprintf(stderr, "XdmcpWriteCARD8 returned non-1 for third byte\n");
        return 3;
    }
    if (buf.pointer != 3) {
        fprintf(stderr, "buf.pointer != 3 (got %d)\n", buf.pointer);
        return 4;
    }

    /* 3. Write a CARD16 and a CARD32. */
    if (XdmcpWriteCARD16(&buf, 0xBEEF) != 1) {
        fprintf(stderr, "XdmcpWriteCARD16 returned non-1\n");
        return 5;
    }
    if (XdmcpWriteCARD32(&buf, 0xDEADBEEFu) != 1) {
        fprintf(stderr, "XdmcpWriteCARD32 returned non-1\n");
        return 6;
    }
    /* 1 (CARD8) + 1 (CARD8) + 1 (CARD8) + 2 (CARD16) + 4 (CARD32) = 9 */
    if (buf.pointer != 9) {
        fprintf(stderr, "buf.pointer != 9 (got %d)\n", buf.pointer);
        return 7;
    }

    /* 4. Snapshot the written length, then reset pointer and narrow count
     *    so the read path sees only the bytes we wrote. */
    int written = buf.pointer;
    buf.pointer = 0;
    buf.count = written;

    CARD8 v8 = 0;
    if (XdmcpReadCARD8(&buf, &v8) != 1 || v8 != 0xA5) {
        fprintf(stderr, "first CARD8 round-trip failed (got 0x%02x)\n", v8);
        return 8;
    }
    if (XdmcpReadCARD8(&buf, &v8) != 1 || v8 != 0x5A) {
        fprintf(stderr, "second CARD8 round-trip failed (got 0x%02x)\n", v8);
        return 9;
    }
    if (XdmcpReadCARD8(&buf, &v8) != 1 || v8 != 0x00) {
        fprintf(stderr, "third CARD8 round-trip failed (got 0x%02x)\n", v8);
        return 10;
    }

    CARD16 v16 = 0;
    if (XdmcpReadCARD16(&buf, &v16) != 1 || v16 != 0xBEEF) {
        fprintf(stderr, "CARD16 round-trip failed (got 0x%04x)\n", v16);
        return 11;
    }
    CARD32 v32 = 0;
    if (XdmcpReadCARD32(&buf, &v32) != 1 || v32 != 0xDEADBEEFu) {
        fprintf(stderr, "CARD32 round-trip failed (got 0x%08x)\n", (unsigned)v32);
        return 12;
    }

    /* 5. XdmcpReadRemaining returns count - pointer. With count narrowed to
     *    the written length, this must be 0 at EOF. */
    if (XdmcpReadRemaining(&buf) != 0) {
        fprintf(stderr, "XdmcpReadRemaining != 0 at EOF (got %d)\n",
                XdmcpReadRemaining(&buf));
        return 13;
    }

    if (printf("libxdmcp api smoke ok\n") < 0) {
        return 14;
    }
    return 0;
}
