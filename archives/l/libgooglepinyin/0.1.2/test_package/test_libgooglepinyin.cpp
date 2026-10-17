#include <cstdio>
#include <cstring>
#include "pinyinime.h"

using ime_pinyin::char16;

/* Consumer test: open the packaged system dictionary plus a fresh user
 * dictionary, search "nihao" and require that the top candidates contain
 * U+4F60 U+597D ("ni hao"). */
int main(int argc, char **argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage: %s <sys_dict.dat> <user_dict>\n", argv[0]);
        return 2;
    }
    if (!ime_pinyin::im_open_decoder(argv[1], argv[2])) {
        std::fprintf(stderr, "FAIL: im_open_decoder\n");
        return 1;
    }
    ime_pinyin::im_reset_search();
    size_t n = ime_pinyin::im_search("nihao", 5);
    if (n == 0) {
        std::fprintf(stderr, "FAIL: im_search returned 0 candidates\n");
        return 1;
    }
    char16 cand[64];
    if (ime_pinyin::im_get_candidate(0, cand, 63) == NULL) {
        std::fprintf(stderr, "FAIL: im_get_candidate returned NULL\n");
        return 1;
    }
    bool found = false;
    const size_t look = n < 10 ? n : 10;
    for (size_t i = 0; i < look; i++) {
        char16 c[64];
        if (ime_pinyin::im_get_candidate(i, c, 63) == NULL) continue;
        if (c[0] == 0x4F60 && c[1] == 0x597D) { found = true; break; }
    }
    if (!found) {
        std::fprintf(stderr, "FAIL: 'nihao' -> U+4F60 U+597D not in top %zu candidates\n",
                     look);
        return 1;
    }
    char16 c0[64];
    ime_pinyin::im_get_candidate(0, c0, 63);
    char out[192];
    size_t oi = 0;
    for (size_t i = 0; c0[i] != 0 && oi + 4 <= sizeof(out); i++) {
        unsigned int ch = (unsigned int)c0[i];
        if (ch < 0x80) out[oi++] = (char)ch;
        else if (ch < 0x800) {
            out[oi++] = (char)(0xC0 | (ch >> 6));
            out[oi++] = (char)(0x80 | (ch & 0x3F));
        } else {
            out[oi++] = (char)(0xE0 | (ch >> 12));
            out[oi++] = (char)(0x80 | ((ch >> 6) & 0x3F));
            out[oi++] = (char)(0x80 | (ch & 0x3F));
        }
    }
    out[oi] = 0;
    std::printf("PASS: candidates=%zu top=%s ('nihao' decoded through packaged library)\n",
                n, out);
    ime_pinyin::im_close_decoder();
    return 0;
}
