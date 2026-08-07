/* nghttp2 1.70.0 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 编解码得对。这里真的跑一轮 **HPACK 头部
 * 压缩/解压往返**，再断言解出来的头部与压进去的**逐字节相同**。
 *
 * 选 HPACK 而不是「建个 session 看没崩」，是因为 HPACK 有确定的输入输出：
 * 压完再解，得到的必须是原文。这条链一旦有问题（霍夫曼表、动态表索引、
 * 整数编码），立刻对不上，不会「看起来跑通了」。
 *
 * 另外验一条真实场景：**同一组头部压第二遍应该更短** —— 那是动态表在起作用。
 * 只压一遍看不出动态表有没有工作。
 */
#include <nghttp2/nghttp2.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUFSZ 4096

static nghttp2_nv mknv(const char *name, const char *value)
{
    nghttp2_nv nv;
    nv.name = (uint8_t *)name;
    nv.namelen = strlen(name);
    nv.value = (uint8_t *)value;
    nv.valuelen = strlen(value);
    nv.flags = NGHTTP2_NV_FLAG_NONE;
    return nv;
}

int main(void)
{
    nghttp2_hd_deflater *def = NULL;
    nghttp2_hd_inflater *inf = NULL;
    uint8_t buf[BUFSZ], buf2[BUFSZ];
    nghttp2_nv nva[3];
    ssize_t len1, len2;
    int rv;

    nva[0] = mknv(":method", "GET");
    nva[1] = mknv(":path", "/batch36/fftw");
    nva[2] = mknv("user-agent", "harmony-pc-conan-check");

    if ((rv = nghttp2_hd_deflate_new(&def, 4096)) != 0) {
        printf("FAIL deflate_new: %s\n", nghttp2_strerror(rv));
        return 1;
    }
    if ((rv = nghttp2_hd_inflate_new(&inf)) != 0) {
        printf("FAIL inflate_new: %s\n", nghttp2_strerror(rv));
        return 1;
    }

    /* ① 压缩一次 */
    len1 = nghttp2_hd_deflate_hd(def, buf, sizeof(buf), nva, 3);
    if (len1 <= 0) {
        printf("FAIL deflate_hd 返回 %zd\n", len1);
        return 1;
    }

    /* ② 解压并与原头部逐字段对账 */
    {
        const uint8_t *p = buf;
        size_t left = (size_t)len1;
        int got = 0;
        for (;;) {
            nghttp2_nv out;
            int flags = 0;
            ssize_t n = nghttp2_hd_inflate_hd2(inf, &out, &flags, p, left, 1);
            if (n < 0) {
                printf("FAIL inflate_hd2: %s\n", nghttp2_strerror((int)n));
                return 1;
            }
            p += n; left -= (size_t)n;
            if (flags & NGHTTP2_HD_INFLATE_EMIT) {
                if (got >= 3) { printf("FAIL 解出的头部多于 3 条\n"); return 1; }
                if (out.namelen != nva[got].namelen ||
                    memcmp(out.name, nva[got].name, out.namelen) != 0 ||
                    out.valuelen != nva[got].valuelen ||
                    memcmp(out.value, nva[got].value, out.valuelen) != 0) {
                    printf("FAIL 第 %d 条头部往返不一致：得到 [%.*s: %.*s]\n",
                           got, (int)out.namelen, out.name,
                           (int)out.valuelen, out.value);
                    return 1;
                }
                ++got;
            }
            if (flags & NGHTTP2_HD_INFLATE_FINAL) {
                nghttp2_hd_inflate_end_headers(inf);
                break;
            }
            if (left == 0) break;
        }
        if (got != 3) {
            printf("FAIL 只解出 %d 条头部，期望 3 条\n", got);
            return 1;
        }
    }

    /* ③ 同一组头部压第二遍必须更短 —— 动态表真的在起作用。
     *    只压一遍看不出这一点。 */
    len2 = nghttp2_hd_deflate_hd(def, buf2, sizeof(buf2), nva, 3);
    if (len2 <= 0) {
        printf("FAIL 第二次 deflate_hd 返回 %zd\n", len2);
        return 1;
    }
    if (len2 >= len1) {
        printf("FAIL 第二次压缩 %zd 字节未小于第一次 %zd —— 动态表没生效\n",
               len2, len1);
        return 1;
    }

    nghttp2_hd_inflate_del(inf);
    nghttp2_hd_deflate_del(def);

    printf("libnghttp2 OK: HPACK 往返 3 条头部逐字节一致 + 动态表生效"
           "(%zd → %zd 字节)；库版本 %s\n",
           len1, len2, nghttp2_version(0)->version_str);
    return 0;
}
