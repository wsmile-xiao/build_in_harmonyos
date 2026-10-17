/* aegisub 3.4.2 test_package — 产物验证（R34 非空壳补充）。
 *
 * 校验打包产物 libaegisub.a 真实存在且为合法 ar 归档（静态库），并进一步
 * 检查包含 ELF 对象成员（libaegisub 由 clang/llvm-ar 生成，成员为 ELF
 * relocatable 对象，magic 为 0x7f 'E' 'L' 'F'）。
 *
 * 用法：./elf_check <libaegisub.a 路径>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ar 成员头（60 字节固定）：name[16] mtime[12] uid[6] gid[6] mode[8] size[10] 0x60 0x0a */
typedef struct {
    char name[16];
    char mtime[12];
    char uid[6];
    char gid[6];
    char mode[8];
    char size[10];
    char end[2];
} ArHdr;

static long ar_size(const ArHdr *h) {
    char buf[11] = {0};
    memcpy(buf, h->size, 10);
    /* ar size 字段为 10 字节右对齐（数字后带空格填充）：strtol 解析后 end 指向
     * 空格是正常的。校验 end==buf（未解析到数字 = 全空格/非法）与负值即可。 */
    char *end = NULL;
    long v = strtol(buf, &end, 10);
    if (end == buf || v < 0)
        return -1;
    return v;
}

/* 检查归档是否含至少一个 ELF 对象成员 */
static int check_elf_member(FILE *f) {
    unsigned char hdr[60];
    while (1) {
        if (fread(hdr, 1, 60, f) != 60)
            break; /* 成员头读不完整 = 归档结束 */
        ArHdr *ah = (ArHdr *)hdr;
        long sz = ar_size(ah);
        if (sz < 0)
            break;
        /* 仅当成员至少 4 字节时才读取 ELF magic（size<4 时跳过，避免越界） */
        unsigned char elfmagic[4] = {0};
        size_t got = 0;
        if (sz >= 4) {
            got = fread(elfmagic, 1, 4, f);
            if (got == 4 && elfmagic[0] == 0x7f && elfmagic[1] == 'E' &&
                elfmagic[2] == 'L' && elfmagic[3] == 'F') {
                fclose(f);
                return 1;
            }
        }
        /* 跳到下一成员：内容剩余 + 可选对齐到 2 字节的 '\n' */
        long skip = sz - (long)got;
        if (skip > 0 && fseek(f, skip, SEEK_CUR) != 0)
            break;
        /* 奇数长度成员后有一个补齐 '\n' */
        if (sz % 2 == 1) {
            int c = fgetc(f);
            if (c == EOF)
                break;
        }
        if (sz == 0)
            break; /* 空成员 */
    }
    fclose(f);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <libaegisub.a>\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", argv[1]);
        return 1;
    }
    unsigned char magic[8] = {0};
    size_t n = fread(magic, 1, 8, f);
    if (n != 8 || magic[0] != '!' || magic[1] != '<' ||
        magic[2] != 'a' || magic[3] != 'r' || magic[4] != 'c' ||
        magic[5] != 'h' || magic[6] != '>' || magic[7] != '\n') {
        fprintf(stderr, "FAIL: %s is not a valid ar archive (magic=%.8s)\n",
                argv[1], magic);
        fclose(f);
        return 1;
    }
    if (!check_elf_member(f)) {
        fprintf(stderr, "FAIL: %s has no ELF object member\n", argv[1]);
        return 1;
    }
    printf("OK: %s is a valid ar archive with ELF object member "
           "(libaegisub static library)\n", argv[1]);
    return 0;
}
