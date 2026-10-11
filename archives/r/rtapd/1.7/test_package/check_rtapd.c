/* check_rtapd.c — consumer-side client for rtapd's external TNPP queue socket.
 *
 * Plays the role of rtnppd: it connects to the AF_UNIX datagram socket that
 * rtapd binds for "ExtSocketIn" and delivers one TNPP packet carrying a CAP
 * page block, byte-for-byte in the wire format rtapd itself emits (see
 * send_tnpp_packet() in rtapd.c):
 *
 *   SOH | tnpp_to(4 hex) | blk(2 hex) | tnpp_from(4 hex) | serial(2 hex) | STX
 *   | block... | ETX | crc16 lo | crc16 hi
 *
 * Block type 'A' (CAP page):
 *   'A' | 4 bytes | funct(1) | pager-id(8 hex) | page body...
 *
 * CRC-16 is the TNPP/ARC variant, identical to upstream crc.c.
 *
 * usage: check_rtapd <socket-path> <to-hex> <from-hex> <pager-id-hex> <body>
 *        check_rtapd --pick-sockdir      # print a dir where AF_UNIX bind() works
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

static const unsigned short crc16tab[256] = {
    0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
    0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
    0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
    0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
    0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
    0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
    0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
    0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
    0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
    0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
    0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
    0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
    0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
    0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
    0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
    0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
    0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
    0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
    0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
    0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
    0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
    0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
    0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
    0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
    0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
    0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
    0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
    0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
    0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
    0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
    0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
    0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040
};

static unsigned short crc16(const unsigned char *s, int len)
{
    unsigned short crc = 0;

    for (; len--; s++)
        crc = crc16tab[(crc & 0xff) ^ *s] ^ ((crc >> 8) & 0xff);
    return crc;
}

/* ---- OHOS sandbox quirk: not every directory permits AF_UNIX bind() -------
 * Observed on OHOS PC hosts (and on the CI workers): /tmp is read-only, and
 * user-data directories — e.g. $HOME and the CI worker's TMPDIR
 * ($HOME/.cache/tmp) — are writable yet reject bind() with EPERM
 * ("Operation not permitted"), while the app sandbox dirs
 * (/data/storage/el2/base/temp, /data/storage/el2/base/cache, ...) allow it.
 *
 * A writable-directory test is therefore NOT sufficient: probe each candidate
 * with a real bind(), using the exact socket type and addrlen that rtapd
 * itself uses (SOCK_DGRAM, strlen(sun_path) + 2), and report the first dir
 * that works.  Same approach as the merged
 * archives/l/libmilter/8.18.2/test_package/test_milter.c precedent.
 */
static const char *pick_sockdir(void)
{
    static const char *cand[] = {
        NULL, NULL, NULL,               /* $TMPDIR, $TMP, $TEMP */
        "/data/storage/el2/base/temp",
        "/data/storage/el2/base/cache",
        "/data/storage/el1/base",
        "/dev/shm",
        "/tmp",
    };
    char tmpl[512], path[512];
    struct sockaddr_un sun;
    size_t i;

    cand[0] = getenv("TMPDIR");
    cand[1] = getenv("TMP");
    cand[2] = getenv("TEMP");

    for (i = 0; i < sizeof(cand) / sizeof(cand[0]); i++) {
        const char *dir = cand[i];
        char *sub;
        int fd, ok;

        if (dir == NULL || dir[0] == '\0')
            continue;
        if (snprintf(tmpl, sizeof tmpl, "%s/tmpl.XXXXXX", dir) >= (int)sizeof tmpl)
            continue;
        sub = mkdtemp(tmpl);
        if (sub == NULL)
            continue;                       /* missing / not writable */
        if (snprintf(path, sizeof path, "%s/queue.out", sub) >= (int)sizeof path) {
            rmdir(sub);
            continue;
        }
        /* sun_path holds at most sizeof(sun_path) bytes; rtapd passes
         * strlen(sun_path) + 2 as addrlen (offsetof(sun_path) == 2). */
        if (strlen(path) + 2 > sizeof sun.sun_path) {
            rmdir(sub);
            continue;
        }
        memset(&sun, 0, sizeof sun);
        sun.sun_family = AF_UNIX;
        strncpy(sun.sun_path, path, sizeof(sun.sun_path) - 1);

        fd = socket(AF_UNIX, SOCK_DGRAM, 0);
        if (fd < 0) {
            rmdir(sub);
            continue;
        }
        ok = bind(fd, (struct sockaddr *)&sun,
                  (socklen_t)(strlen(sun.sun_path) + 2)) == 0;
        close(fd);
        unlink(path);
        rmdir(sub);
        if (ok)
            return dir;
    }
    return NULL;
}

int main(int argc, char **argv)
{
    unsigned char buf[2048];
    struct sockaddr_un sun;
    unsigned long long pager;
    unsigned short crc;
    size_t bodylen;
    int fd, n = 0;

    if (argc == 2 && strcmp(argv[1], "--pick-sockdir") == 0) {
        const char *dir = pick_sockdir();
        if (dir == NULL) {
            fprintf(stderr,
                    "no candidate directory permits AF_UNIX bind()\n"
                    "  probed: $TMPDIR, $TMP, $TEMP, /data/storage/el2/base/temp,\n"
                    "          /data/storage/el2/base/cache, /data/storage/el1/base,\n"
                    "          /dev/shm, /tmp\n");
            return 3;
        }
        printf("%s\n", dir);
        return 0;
    }

    if (argc != 6) {
        fprintf(stderr, "usage: %s <socket> <to-hex> <from-hex> <pager-hex> <body>\n",
                argv[0]);
        return 2;
    }
    pager = strtoull(argv[4], NULL, 16);
    bodylen = strlen(argv[5]);
    if (bodylen > sizeof(buf) - 32) {
        fprintf(stderr, "body too long\n");
        return 2;
    }

    /* ---- TNPP header: byte-identical to rtapd send_tnpp_packet() ---- */
    buf[n++] = '\01';                                          /* SOH */
    n += sprintf((char *)buf + n, "%04lX", strtoul(argv[2], NULL, 16));
    n += sprintf((char *)buf + n, "%02X", 20);                 /* as upstream */
    n += sprintf((char *)buf + n, "%04lX", strtoul(argv[3], NULL, 16));
    n += sprintf((char *)buf + n, "%02X", 1);                  /* serial */
    buf[n++] = '\02';                                          /* STX */

    /* ---- block 'A': CAP page ---- */
    buf[n++] = 'A';
    buf[n++] = '0'; buf[n++] = '0'; buf[n++] = '0'; buf[n++] = '0';
    buf[n++] = '1';                                            /* funct */
    n += sprintf((char *)buf + n, "%08llX", pager);             /* 8 hex pager id */
    memcpy(buf + n, argv[5], bodylen);                         /* page body */
    n += (int)bodylen;
    buf[n++] = '\03';                                          /* ETX */

    crc = crc16(buf, n);                                       /* SOH..ETX, as upstream */
    buf[n++] = (unsigned char)(crc & 0xff);
    buf[n++] = (unsigned char)((crc >> 8) & 0xff);

    memset(&sun, 0, sizeof sun);
    sun.sun_family = AF_UNIX;
    strncpy(sun.sun_path, argv[1], sizeof(sun.sun_path) - 1);

    fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (fd < 0) {
        fprintf(stderr, "socket(): %s\n", strerror(errno));
        return 1;
    }
    if (sendto(fd, buf, n, 0, (struct sockaddr *)&sun,
               (socklen_t)(sizeof(sun.sun_family) + strlen(sun.sun_path) + 1)) < 0) {
        fprintf(stderr, "sendto(%s): %s\n", sun.sun_path, strerror(errno));
        close(fd);
        return 1;
    }
    close(fd);
    printf("check_rtapd: sent %d-byte TNPP CAP page for pager %08llX\n", n, pager);
    return 0;
}
