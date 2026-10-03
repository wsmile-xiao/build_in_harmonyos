#ifndef DICTIONARY_FIXTURE_H
#define DICTIONARY_FIXTURE_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static const char *fixture_words[] = { "computer", "shield", "s\xb3owo" };
static const char *fixture_defs[] = { "komputer", "tarcza rycerza\xb3", "definicja s\xb3owa" };

static int write_le(FILE *file, uint32_t value, unsigned int bytes)
{
    unsigned char data[4];
    unsigned int i;
    for (i = 0; i < bytes; ++i)
        data[i] = (unsigned char)(value >> (8 * i));
    return fwrite(data, 1, bytes, file) == bytes ? 0 : -1;
}

/* Explicit little endian layout from the upstream misc/mkdict.py. */
static int make_dict(const char *dat_path, const char *idx_path)
{
    FILE *dat = fopen(dat_path, "wb");
    FILE *idx = fopen(idx_path, "wb");
    unsigned char header[256] = { 0xd5, 0x11, 0x4e, 0x8d };
    uint32_t offset = 0;
    int error = 0, i;
    header[8] = 3;
    header[17] = 1;
    if (!dat || !idx) {
        if (dat) fclose(dat);
        if (idx) fclose(idx);
        return -1;
    }
    if (fwrite(header, 1, sizeof(header), idx) != sizeof(header))
        error = 1;
    for (i = 0; i < 3; ++i) {
        size_t wlen = strlen(fixture_words[i]), dlen = strlen(fixture_defs[i]);
        unsigned char record[2] = { (unsigned char)(wlen + 1), 2 };
        if (fwrite(record, 1, 2, idx) != 2 || write_le(idx, i + 1, 2) ||
            write_le(idx, offset, 4) || fwrite(fixture_words[i], 1, wlen + 1, idx) != wlen + 1 ||
            write_le(dat, (uint32_t)dlen, 4) || fwrite(fixture_defs[i], 1, dlen, dat) != dlen)
            error = 1;
        offset += 4 + (uint32_t)dlen;
    }
    if (fclose(dat)) error = 1;
    if (fclose(idx)) error = 1;
    return error ? -1 : 0;
}
#endif
