#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include <libcork/core/hash.h>
#include <libcork/ds/buffer.h>

int main(void) {
    /* 真实调用 libcork 公开 API (R34): 哈希计算 + 动态缓冲区 */
    cork_hash seed = 0;
    const char *msg = "libcork harmonyos test";
    cork_hash h = cork_hash_buffer(seed, msg, strlen(msg));

    struct cork_buffer buf;
    cork_buffer_init(&buf);
    cork_buffer_set(&buf, msg, strlen(msg));
    cork_buffer_append(&buf, "|hash", 5);
    /* 0.9.0 中 cork_buffer 内容通过 buf.buf / buf.size 访问 */
    const char *data = (const char *) buf.buf;
    int ok = data[0] == 'l' && buf.size > 0;
    cork_buffer_done(&buf);

    printf("libcork 0.9.0 consumer test: hash=0x%08x ok=%d\n", h, ok);
    return ok ? 0 : 1;
}