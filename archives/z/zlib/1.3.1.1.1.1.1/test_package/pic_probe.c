#include <zlib.h>

int zlib_pic_probe(const unsigned char *src, unsigned long src_len) {
    unsigned long dst_len = compressBound(src_len);
    unsigned char dst[128];

    if (dst_len > sizeof(dst)) {
        return Z_BUF_ERROR;
    }

    return compress(dst, &dst_len, src, src_len);
}
