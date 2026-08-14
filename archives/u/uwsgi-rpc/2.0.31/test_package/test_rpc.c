#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int contains_bytes(const unsigned char *data, size_t size, const char *needle) {
    size_t needle_len = strlen(needle);
    if (needle_len == 0 || size < needle_len) {
        return 0;
    }
    for (size_t i = 0; i <= size - needle_len; ++i) {
        if (memcmp(data + i, needle, needle_len) == 0) {
            return 1;
        }
    }
    return 0;
}

static uint16_t read_le16(const unsigned char *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <rpc_plugin.so>\n", argv[0]);
        return 2;
    }

    FILE *fp = fopen(argv[1], "rb");
    if (fp == NULL) {
        perror("fopen");
        return 1;
    }
    if (fseek(fp, 0, SEEK_END) != 0) {
        perror("fseek");
        fclose(fp);
        return 1;
    }
    long file_size = ftell(fp);
    if (file_size < 1024) {
        fprintf(stderr, "plugin is too small: %ld bytes\n", file_size);
        fclose(fp);
        return 1;
    }
    if (fseek(fp, 0, SEEK_SET) != 0) {
        perror("fseek");
        fclose(fp);
        return 1;
    }

    unsigned char *data = (unsigned char *)malloc((size_t)file_size);
    if (data == NULL) {
        fprintf(stderr, "malloc failed for %ld bytes\n", file_size);
        fclose(fp);
        return 1;
    }
    size_t got = fread(data, 1, (size_t)file_size, fp);
    fclose(fp);
    if (got != (size_t)file_size) {
        fprintf(stderr, "short read: got %zu expected %ld\n", got, file_size);
        free(data);
        return 1;
    }

    if (got < 20 || memcmp(data, "\177"
                                 "ELF",
                          4) != 0) {
        fprintf(stderr, "not an ELF file\n");
        free(data);
        return 1;
    }
    if (data[4] != 2 || data[5] != 1) {
        fprintf(stderr, "unexpected ELF class/data: class=%u data=%u\n", data[4], data[5]);
        free(data);
        return 1;
    }
    uint16_t elf_type = read_le16(data + 16);
    uint16_t machine = read_le16(data + 18);
    if (elf_type != 3) {
        fprintf(stderr, "expected ET_DYN shared object, got type %u\n", elf_type);
        free(data);
        return 1;
    }
    if (!(machine == 183 || machine == 62)) {
        fprintf(stderr, "unexpected ELF machine %u\n", machine);
        free(data);
        return 1;
    }

    const char *needles[] = {
        "rpc_plugin",
        "uwsgi_rpc",
        "Empty RPC request. skip.",
        "Invalid RPC request. skip.",
        "application/binary",
        "CONTENT_LENGTH",
    };
    for (size_t i = 0; i < sizeof(needles) / sizeof(needles[0]); ++i) {
        if (!contains_bytes(data, got, needles[i])) {
            fprintf(stderr, "missing expected plugin string: %s\n", needles[i]);
            free(data);
            return 1;
        }
    }

    free(data);
    printf("uwsgi-rpc plugin probe OK: %ld bytes\n", file_size);
    return 0;
}
