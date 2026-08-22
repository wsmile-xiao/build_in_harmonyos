/*
 * Test: Verify the timezonedb.so PHP extension shared library.
 *
 * Reads the .so file directly and checks:
 * 1. ELF magic number (valid shared object)
 * 2. Dynamic symbol table contains get_module (PHP extension entry point)
 *
 * This test substantively depends on the built package by reading
 * and verifying its contents.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <elf.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>

int main(void) {
#ifdef SO_PATH
    const char *path = SO_PATH;
#else
    const char *path = getenv("TIMEZONEDB_SO");
    if (!path) {
        fprintf(stderr, "TIMEZONEDB_SO not set\n");
        return 1;
    }
#endif

    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "Cannot open %s\n", path);
        return 1;
    }

    struct stat st;
    if (fstat(fd, &st) < 0) {
        fprintf(stderr, "fstat failed\n");
        close(fd);
        return 1;
    }

    void *map = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (map == MAP_FAILED) {
        fprintf(stderr, "mmap failed\n");
        close(fd);
        return 1;
    }
    close(fd);

    /* Check ELF magic */
    unsigned char *ident = (unsigned char *)map;
    if (ident[EI_MAG0] != ELFMAG0 ||
        ident[EI_MAG1] != ELFMAG1 ||
        ident[EI_MAG2] != ELFMAG2 ||
        ident[EI_MAG3] != ELFMAG3) {
        fprintf(stderr, "Not a valid ELF file\n");
        munmap(map, st.st_size);
        return 1;
    }

    /* Check ELF type is shared object (ET_DYN = 3) */
    Elf64_Ehdr *ehdr = (Elf64_Ehdr *)map;
    if (ehdr->e_type != ET_DYN) {
        fprintf(stderr, "Not a shared object (e_type=%d)\n", ehdr->e_type);
        munmap(map, st.st_size);
        return 1;
    }

    /* Find dynamic symbol table and search for get_module */
    Elf64_Shdr *shdr = (Elf64_Shdr *)((char *)map + ehdr->e_shoff);
    Elf64_Shdr *strtab = NULL;
    int found = 0;

    for (int i = 0; i < ehdr->e_shnum; i++) {
        if (shdr[i].sh_type == SHT_DYNSYM) {
            /* Found dynamic symbol table */
            Elf64_Sym *syms = (Elf64_Sym *)((char *)map + shdr[i].sh_offset);
            int nsyms = shdr[i].sh_size / sizeof(Elf64_Sym);
            /* Get string table */
            if (shdr[i].sh_link < ehdr->e_shnum) {
                strtab = &shdr[shdr[i].sh_link];
                char *strs = (char *)map + strtab->sh_offset;
                for (int j = 0; j < nsyms; j++) {
                    char *name = strs + syms[j].st_name;
                    if (strcmp(name, "get_module") == 0) {
                        found = 1;
                        break;
                    }
                }
            }
            break;
        }
    }

    munmap(map, st.st_size);

    if (!found) {
        fprintf(stderr, "get_module symbol not found in dynamic symbol table\n");
        return 1;
    }

    printf("timezonedb.so verified: valid ELF shared object with get_module symbol\n");
    return 0;
}
