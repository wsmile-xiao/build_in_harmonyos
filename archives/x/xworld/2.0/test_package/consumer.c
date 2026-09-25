/* consumer.c — HarmonyOS consumer case for xworld/2.0
 *
 * xworld's core design: append raw pixel data (world.o) to the ELF binary,
 * then mmap the data segment at runtime for zero-copy pixel access.
 * This consumer verifies that the mmap self-loading mechanism works
 * correctly on OHOS (musl aarch64) — the key feature a downstream
 * consumer relies on when reusing xworld as a data app.
 *
 * Build:  cc -Wall -O2 -o consumer consumer.c
 * Run:    ./consumer <path-to-xworld-binary>
 */

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include <elf.h>

/* Minimum valid ELF file size: header + one program header */
#define ELF_MIN_SIZE ((off_t)(sizeof(Elf64_Ehdr) + sizeof(Elf64_Phdr)))

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <xworld-binary>\n", argv[0]);
        return 2;
    }

    const char *path = argv[1];
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    struct stat st;
    if (fstat(fd, &st) < 0) {
        perror("fstat");
        close(fd);
        return 1;
    }

    /* P3 fix 1: Reject files too small to contain ELF + program headers */
    if (st.st_size < ELF_MIN_SIZE) {
        fprintf(stderr, "FAIL: file too small for valid ELF (%ld bytes, min %ld)\n",
                (long)st.st_size, (long)ELF_MIN_SIZE);
        close(fd);
        return 1;
    }

    /* Map the entire binary read-only — same mechanism xworld uses at runtime */
    unsigned char *map = mmap(NULL, (size_t)st.st_size, PROT_READ,
                              MAP_FILE | MAP_PRIVATE, fd, 0);
    if (map == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 1;
    }

    /* Verify ELF magic */
    if (memcmp(map, "\x7f"
               "ELF", 4) != 0) {
        fprintf(stderr, "FAIL: not a valid ELF\n");
        munmap(map, (size_t)st.st_size);
        close(fd);
        return 1;
    }

    /* Must be 64-bit ELF for aarch64 */
    if (map[4] != ELFCLASS64) {
        fprintf(stderr, "FAIL: not a 64-bit ELF (class=%d)\n", map[4]);
        munmap(map, (size_t)st.st_size);
        close(fd);
        return 1;
    }

    /* Parse program headers to find the end of the last LOAD segment */
    Elf64_Ehdr *ehdr = (Elf64_Ehdr *)map;

    /* Sanity check: program header table must fit within file */
    off_t phdr_end = (off_t)ehdr->e_phoff +
                     (off_t)ehdr->e_phentsize * ehdr->e_phnum;
    if (phdr_end > st.st_size) {
        fprintf(stderr, "FAIL: program header table extends beyond file\n");
        munmap(map, (size_t)st.st_size);
        close(fd);
        return 1;
    }

    Elf64_Phdr *phdr_tbl = (Elf64_Phdr *)(map + ehdr->e_phoff);
    off_t last_load_end = 0;

    for (int i = 0; i < ehdr->e_phnum; i++) {
        if (phdr_tbl[i].p_type == PT_LOAD) {
            off_t seg_end = phdr_tbl[i].p_offset + phdr_tbl[i].p_filesz;
            if (seg_end > last_load_end)
                last_load_end = seg_end;
        }
    }

    if (last_load_end <= 0) {
        fprintf(stderr, "FAIL: no LOAD segments found\n");
        munmap(map, (size_t)st.st_size);
        close(fd);
        return 1;
    }

    /* Last LOAD segment must end after program headers */
    if (last_load_end < phdr_end) {
        fprintf(stderr, "FAIL: last LOAD segment ends before program headers\n");
        munmap(map, (size_t)st.st_size);
        close(fd);
        return 1;
    }

    size_t appended = (size_t)(st.st_size - last_load_end);

    printf("  ELF total size:  %ld bytes\n", (long)st.st_size);
    printf("  Last LOAD end:   %ld (0x%lx)\n",
           (long)last_load_end, (unsigned long)last_load_end);
    printf("  Appended data:   %zu bytes\n", appended);

    /* Verify the appended region is readable through the mmap */
    if (appended > 0) {
        volatile unsigned char *data = map + last_load_end;
        unsigned char first = data[0];  /* touch — SIGSEGV if mapping incomplete */
        unsigned char last  = data[appended - 1];
        (void)first;
        (void)last;
        printf("  Data readable:   first byte=0x%02x, last byte=0x%02x\n",
               first, last);
    }

    /* P3 fix 2: Verify appended data is NOT an ELF (raw pixel data, not another ELF) */
    int appended_is_elf = 0;
    if (appended >= 4 && memcmp(map + last_load_end, "\x7f""ELF", 4) == 0) {
        appended_is_elf = 1;
    }

    munmap(map, (size_t)st.st_size);
    close(fd);

    if (appended_is_elf) {
        fprintf(stderr, "FAIL: appended data appears to be an ELF (expected raw pixel data)\n");
        return 1;
    }

    if (appended == 0) {
        fprintf(stderr, "FAIL: no appended data segment — world.o not linked\n");
        return 1;
    }

    printf("\nPASS: OHOS mmap self-loading consumer verified (%zu bytes appended data)\n",
           appended);
    return 0;
}
