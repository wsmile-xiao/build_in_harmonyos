#include <lfp/lfp.h>
#include <lfp/memfile.h>
#include <stdio.h>
#include <string.h>

/* 真实计算：建一个内存协议、真读真 seek 真 tell，断言字节与偏移。
 * 只验「能编能链」验不出 lfp 最容易坏的那部分——分层协议的偏移语义。 */
int main(void) {
    int bad = 0;
    const unsigned char payload[] = "0123456789ABCDEF";
    const int64_t n = (int64_t)sizeof(payload) - 1;   /* 16 字节，不含结尾 NUL */

    lfp_protocol* f = lfp_memfile_openwith(payload, n);
    if (!f) { printf("FAIL lfp_memfile_openwith 返回 NULL\n"); return 1; }

    /* ① 读前 8 字节，断言内容与读到的长度 */
    char buf[9] = {0};
    int64_t nread = 0;
    if (lfp_readinto(f, buf, 8, &nread) != LFP_OK) { printf("FAIL readinto 状态\n"); bad++; }
    if (nread != 8) { printf("FAIL readinto 长度=%lld\n", (long long)nread); bad++; }
    if (strncmp(buf, "01234567", 8) != 0) { printf("FAIL readinto 内容=%s\n", buf); bad++; }

    /* ② tell 必须等于已读字节数 */
    int64_t pos = -1;
    if (lfp_tell(f, &pos) != LFP_OK || pos != 8) { printf("FAIL tell=%lld\n", (long long)pos); bad++; }

    /* ③ seek 回 4 再读 4，断言拿到的是 4567 —— 验偏移语义而不只是能调用 */
    if (lfp_seek(f, 4) != LFP_OK) { printf("FAIL seek 状态\n"); bad++; }
    memset(buf, 0, sizeof buf);
    if (lfp_readinto(f, buf, 4, &nread) != LFP_OK || nread != 4) { printf("FAIL seek 后 readinto\n"); bad++; }
    if (strncmp(buf, "4567", 4) != 0) { printf("FAIL seek 后内容=%s\n", buf); bad++; }

    /* ④ seek 到正好 size 也算越界 —— 上游 test/memfile.cpp「Seeking past EOF
     *    returns invalid args error」对 (== size) 与 (> size) 都断言 LFP_INVALID_ARGS。 */
    if (lfp_seek(f, n) != LFP_INVALID_ARGS) { printf("FAIL seek(size) 该报越界\n"); bad++; }

    /* ⑤ eof 是**读完**才置位，不是 seek 出来的：从头读满 n 字节后才为真。 */
    if (lfp_seek(f, 0) != LFP_OK) { printf("FAIL seek 回 0\n"); bad++; }
    {
        char all[32] = {0};
        int64_t got = 0;
        if (lfp_readinto(f, all, n, &got) != LFP_OK || got != n) {
            printf("FAIL 读满: got=%lld\n", (long long)got); bad++;
        }
        if (memcmp(all, payload, (size_t)n) != 0) { printf("FAIL 全量内容不符\n"); bad++; }
    }
    if (!lfp_eof(f)) { printf("FAIL 读完后 eof 未置位\n"); bad++; }

    lfp_close(f);
    if (bad == 0) printf("lfp: 11 项断言全过（读/偏移/越界/eof 语义）\n");
    return bad ? 1 : 0;
}
