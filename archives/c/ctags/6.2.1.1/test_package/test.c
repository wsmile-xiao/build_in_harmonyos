/* test.c — L1 test for the ctags binary (Universal Ctags 6.2.1)
 *
 * Verifies that the packaged ctags executable is installed and usable:
 *
 *   1. `ctags --version` exits 0 and reports a Universal Ctags banner
 *   2. `ctags --list-languages` lists the C parser
 *   3. [OpenHarmony] the ctags executable is statically linked
 *      (no PT_INTERP program header).  OHOS ships a minimal /lib, so a
 *      terminal tool must not depend on shared objects being present at
 *      runtime.
 *   4. [OpenHarmony] end-to-end tag generation works on the running
 *      system: a probe source file is indexed with `ctags -o` and the
 *      generated tags file must contain the expected symbols.
 *
 * Usage: test_ctags <path-to-ctags-binary>
 * The ctags path is passed as argv[1] so that the test does not depend on
 * PATH lookup.
 */

#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define PROBE_SOURCE "ctags_l1_probe.c"
#define PROBE_TAGS "ctags_l1_probe.tags"

/* PT_INTERP == 3 (from <elf.h>); defined locally to avoid the header. */
#define PT_INTERP_TYPE 3

/* Return 1 when the ELF at `path` has no interpreter (static), 0 when it
 * is dynamically linked, -1 when it cannot be inspected. */
static int elf_is_static(const char *path)
{
    int fd = open(path, O_RDONLY);
    unsigned char eh[64];
    unsigned long phoff;
    unsigned int phentsize, phnum, i;
    unsigned char ph[64];

    if (fd < 0)
        return -1;
    if (read(fd, eh, sizeof(eh)) != (ssize_t)sizeof(eh) ||
        memcmp(eh, "\177ELF", 4) != 0) {
        close(fd);
        return -1;
    }

    if (eh[4] == 2) { /* ELF64 */
        memcpy(&phoff, eh + 0x20, 8);
        memcpy(&phentsize, eh + 0x36, 2);
        memcpy(&phnum, eh + 0x38, 2);
    } else { /* ELF32 */
        uint32_t off32;
        uint16_t entsz16, num16;
        memcpy(&off32, eh + 0x1C, 4);
        memcpy(&entsz16, eh + 0x2A, 2);
        memcpy(&num16, eh + 0x2C, 2);
        phoff = off32;
        phentsize = entsz16;
        phnum = num16;
    }

    if (phoff == 0 || phentsize == 0)
        return 1; /* no program headers at all: treat as static */

    for (i = 0; i < phnum; i++) {
        uint32_t p_type;
        if (lseek(fd, (off_t)(phoff + (unsigned long)i * phentsize), SEEK_SET) < 0)
            break;
        if (read(fd, ph, sizeof(ph)) != (ssize_t)sizeof(ph))
            break;
        memcpy(&p_type, ph, 4);
        if (p_type == PT_INTERP_TYPE) {
            close(fd);
            return 0;
        }
    }
    close(fd);
    return 1;
}

/* Run `cmd`, return the exit status of the shell and optionally copy the
 * first `n` bytes of output into `buf`. */
static int run_capture(const char *cmd, char *buf, size_t n, int *exit_code)
{
    FILE *fp = popen(cmd, "r");
    size_t used = 0;

    if (fp == NULL)
        return -1;
    if (buf != NULL && n > 0) {
        size_t got;
        while (used + 1 < n && (got = fread(buf + used, 1, n - 1 - used, fp)) > 0)
            used += got;
        buf[used] = '\0';
    } else {
        char sink[256];
        while (fread(sink, 1, sizeof(sink), fp) > 0)
            ;
    }
    *exit_code = pclose(fp);
    return 0;
}

int main(int argc, char *argv[])
{
    char cmd[1024];
    char out[8192];
    int exit_code = 0;
    int failures = 0;

    if (argc < 2) {
        fprintf(stderr, "FAIL: usage: test_ctags <path-to-ctags>\n");
        return 1;
    }

    /* --- Case 1: ctags --version ------------------------------------- */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", argv[1]);
    if (run_capture(cmd, out, sizeof(out), &exit_code) != 0) {
        fprintf(stderr, "FAIL: cannot execute ctags --version\n");
        return 1;
    }
    if (exit_code != 0 || strstr(out, "Universal Ctags") == NULL) {
        fprintf(stderr, "FAIL: ctags --version unexpected output (exit=%d)\n", exit_code);
        failures++;
    } else {
        printf("[test] ctags --version contains 'Universal Ctags': PASS\n");
    }

    /* --- Case 2: ctags --list-languages ------------------------------ */
    snprintf(cmd, sizeof(cmd), "\"%s\" --list-languages 2>&1", argv[1]);
    if (run_capture(cmd, out, sizeof(out), &exit_code) != 0) {
        fprintf(stderr, "FAIL: cannot execute ctags --list-languages\n");
        return 1;
    }
    if (exit_code != 0 || strstr(out, "\nC\n") == NULL) {
        fprintf(stderr, "FAIL: ctags --list-languages did not list C (exit=%d)\n", exit_code);
        failures++;
    } else {
        printf("[test] ctags --list-languages lists C: PASS\n");
    }

    /* --- Case 3: [OpenHarmony] statically linked executable ---------- */
    {
        int st = elf_is_static(argv[1]);
        if (st < 0) {
            fprintf(stderr, "FAIL: [OHOS] cannot inspect '%s' as ELF\n", argv[1]);
            failures++;
        } else if (st == 0) {
            fprintf(stderr, "FAIL: [OHOS] ctags is dynamically linked (PT_INTERP found)\n");
            failures++;
        } else {
            printf("[test] [OHOS] ctags is statically linked: PASS\n");
        }
    }

    /* --- Case 4: [OpenHarmony] end-to-end tag generation -------------- */
    {
        FILE *sf = fopen(PROBE_SOURCE, "w");
        int generated = 0;

        if (sf == NULL) {
            fprintf(stderr, "FAIL: [OHOS] cannot create probe source file\n");
            failures++;
        } else {
            fputs("int ctags_probe_function(int x) { return x + 1; }\n"
                  "struct ctags_probe_struct { int ctags_probe_field; };\n",
                  sf);
            fclose(sf);
        }

        snprintf(cmd, sizeof(cmd), "\"%s\" -o %s %s 2>&1", argv[1], PROBE_TAGS, PROBE_SOURCE);
        if (run_capture(cmd, out, sizeof(out), &exit_code) != 0 || exit_code != 0) {
            fprintf(stderr, "FAIL: [OHOS] ctags -o failed (exit=%d): %s\n", exit_code, out);
            failures++;
        } else {
            FILE *tf = fopen(PROBE_TAGS, "r");
            char tbuf[8192];
            size_t got = 0;

            if (tf != NULL) {
                got = fread(tbuf, 1, sizeof(tbuf) - 1, tf);
                tbuf[got] = '\0';
                fclose(tf);
            }
            if (tf == NULL ||
                strstr(tbuf, "ctags_probe_function") == NULL ||
                strstr(tbuf, "ctags_probe_struct") == NULL) {
                fprintf(stderr, "FAIL: [OHOS] generated tags file lacks expected symbols\n");
                failures++;
            } else {
                printf("[test] [OHOS] end-to-end tag generation: PASS\n");
                generated = 1;
            }
        }
        if (generated)
            remove(PROBE_TAGS);
        remove(PROBE_SOURCE);
    }

    if (failures != 0) {
        fprintf(stderr, "ctags L1 test: %d case(s) FAILED\n", failures);
        return 1;
    }
    printf("ctags L1 test: ALL PASS\n");
    return 0;
}
