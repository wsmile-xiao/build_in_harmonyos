/* test_consumer.c — consumer assertions against libsmputils1 (smp-utils 0.99).
 *
 * Expected values are taken from the upstream sources:
 *   - lib/smp_lib.c: smp_def_rrlen_arr[]  (SAS-1.1 request/response lengths)
 *   - lib/smp_lib.c: smp_get_num()/smp_get_llnum() suffix parsing
 *   - lib/smp_lib.c: smp_get_page_size() == sysconf(_SC_PAGESIZE)
 * Plus OHOS-specific checks on the binary itself (ELF64 aarch64, static).
 */
#include <elf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>

#include "smp_lib.h"

static int g_pass = 0;
static int g_fail = 0;

static void check(const char *name, int ok)
{
    if (ok) {
        g_pass++;
        printf("ok  %s\n", name);
    } else {
        g_fail++;
        printf("FAIL %s\n", name);
    }
}

int main(void)
{
    /* 1-4: SMP function length table (lib/smp_lib.c smp_def_rrlen_arr) */
    check("REPORT_GENERAL req_len == 0",
          smp_get_func_def_req_len(SMP_FN_REPORT_GENERAL) == 0);
    check("REPORT_GENERAL resp_len == 6",
          smp_get_func_def_resp_len(SMP_FN_REPORT_GENERAL) == 6);
    check("DISCOVER req_len == 2",
          smp_get_func_def_req_len(SMP_FN_DISCOVER) == 2);
    check("DISCOVER resp_len == 12",
          smp_get_func_def_resp_len(SMP_FN_DISCOVER) == 12);

    /* 5-8: numeric suffix parser (lib/smp_lib.c smp_get_num/llnum) */
    check("smp_get_num(\"2k\") == 2048", smp_get_num("2k") == 2048);
    check("smp_get_num(\"2KB\") == 2000", smp_get_num("2KB") == 2000);
    check("smp_get_num(\"0x10\") == 16", smp_get_num("0x10") == 16);
    check("smp_get_llnum(\"1m\") == 1048576",
          smp_get_llnum("1m") == 1048576);

    /* 9: page size */
    check("smp_get_page_size() == 4096", smp_get_page_size() == 4096);

    /* 10: target machine. On a real OHOS device uname().machine is
     * "aarch64"; under qemu-user on the build host the uname syscall
     * passes through the host kernel and reports the host machine
     * (typically "x86_64"), so both are accepted here. */
    struct utsname uts;
    if (uname(&uts) == 0) {
        check("uname().machine is aarch64 (or qemu-host x86_64)",
              strcmp(uts.machine, "aarch64") == 0 ||
              strcmp(uts.machine, "x86_64") == 0);
    } else {
        check("uname() succeeded", 0);
    }

    /* 11-12: OHOS binary identity — parse our own ELF header:
     * ELFCLASS64 + EM_AARCH64, and no PT_INTERP (static, self-contained). */
    FILE *f = fopen("/proc/self/exe", "rb");
    const unsigned int ehdr_size = (unsigned int)sizeof(Elf64_Ehdr);
    if (!f) {
        check("open /proc/self/exe", 0);
    } else {
        unsigned char ehdr[ehdr_size];
        if (fread(ehdr, 1, sizeof(ehdr), f) != sizeof(ehdr)) {
            check("read ELF header", 0);
        } else {
            unsigned char ei_class = ehdr[EI_CLASS];
            unsigned int e_type = ehdr[16] | (ehdr[17] << 8);
            unsigned int e_machine = ehdr[18] | (ehdr[19] << 8);
            check("ELF is ELFCLASS64", ei_class == ELFCLASS64);
            check("ELF e_machine == EM_AARCH64 (0xb7)",
                  e_machine == EM_AARCH64);
            (void)e_type;

            /* Walk program headers looking for PT_INTERP. */
            fseek(f, 0, SEEK_SET);
            unsigned char full[ehdr_size];
            if (fread(full, 1, sizeof(full), f) == sizeof(full)) {
                /* Field widths are matched to the ELF64 layout so no read
                 * overruns its destination: e_phoff is Elf64_Off (8 bytes at
                 * offset 32), e_phentsize / e_phnum are Elf64_Half (2 bytes). */
                Elf64_Off e_phoff = 0;
                Elf64_Half e_phentsize = 0;
                Elf64_Half e_phnum = 0;
                memcpy(&e_phoff, full + 32, sizeof(e_phoff));
                memcpy(&e_phentsize, full + 54, sizeof(e_phentsize));
                memcpy(&e_phnum, full + 56, sizeof(e_phnum));
                int has_interp = 0;
                for (Elf64_Half i = 0; i < e_phnum; i++) {
                    unsigned char ph[64];
                    if (e_phentsize > sizeof(ph))
                        break;
                    fseek(f, (long)e_phoff + (long)i * e_phentsize, SEEK_SET);
                    if (fread(ph, 1, e_phentsize, f) != e_phentsize)
                        break;
                    unsigned int p_type = ph[0] | (ph[1] << 8);
                    if (p_type == PT_INTERP) {
                        has_interp = 1;
                        break;
                    }
                }
                check("no PT_INTERP (static, self-contained)", !has_interp);
            } else {
                check("re-read ELF header", 0);
            }
        }
        fclose(f);
    }

    printf("smp-utils consumer: pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
