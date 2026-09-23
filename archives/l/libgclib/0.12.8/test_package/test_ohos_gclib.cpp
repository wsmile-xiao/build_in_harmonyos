/*
 * HarmonyOS / OHOS 专有测试 —— libgclib 0.12.8（OpenHarmony PC / aarch64）
 *
 * 上游 gclib 仓库没有任何测试目录、没有 CI、也没有发行版测试脚本
 * （见 notes.md 第 1 节），所以「在目标平台上真的能加载并正确工作」
 * 这件事必须由本文件承担。两个鸿蒙特有场景：
 *
 *   场景 #1 平台 ABI 契约
 *     - ELF64 / EM_AARCH64；
 *     - DT_NEEDED 链的是 OHOS 的 musl libc（"libc.so"），不是 glibc 的
 *       "libc.so.6"；
 *     - DT_NEEDED 链的是 OHOS 的 C++ 运行时 "libc++_shared.so"，且没有
 *       任何 glibc 世界的 "libstdc++.so.6"；
 *     - 动态串表里确实导出了 gclib 的 C++ 入口（ntComplement /
 *       translateCodon / get_mem_usage）；
 *     - OHOS 加载器能 dlopen(RTLD_NOW|RTLD_LOCAL) 完成符号解析。
 *
 *   场景 #2 运行时契约（/proc + 命名空间级静态初始化）
 *     - gdna.cpp 的 `static bool gdna_Ready=gDnaInit();` 与 codons.cpp 的
 *       `static bool isCodonTableReady=codonTableInit();` 都是命名空间级
 *       静态初始化：本测试**从不显式调用** gDnaInit()/codonTableInit()，
 *       只在 dlopen 之后直接调 ntComplement()/translateCodon()。若 OHOS
 *       加载器没有在映射阶段执行 .init_array，这两组断言立刻失败。
 *     - proc_mem.cpp 在非 __APPLE__ / 非 _WIN32 时走 `#else //assume Linux`
 *       分支读 /proc/self/stat。断言 /proc 挂载存在且 get_mem_usage()
 *       返回非零的虚拟内存/常驻内存，即证明 OHOS 走的是 Linux 分支、
 *       musl 的 sysconf(_SC_PAGE_SIZE) 也可用。
 *
 * 本文件**不链接** libgclib：所有入口都经 dlopen + dlsym 取得，因此
 * 「符号被导出」「加载器能解析」「静态初始化已执行」三件事都是真的被测到，
 * 而不是被链接期悄悄满足。链接期契约由 test_libgclib.cpp 覆盖。
 *
 * 断言 21 条，全部无条件执行；任何一条失败返回非 0。
 */
#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* 只为取得函数指针的精确类型，不调用任何被声明的函数 */
#include "codons.h"
#include "gdna.h"
#include "proc_mem.h"

#define MAX_PHDR 64
#define MAX_DYN 512
#define STRMAX 65536

static int g_checks = 0;
static int g_fails = 0;

static void chk(int cond, const char* what) {
    ++g_checks;
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        printf("FAIL - %s\n", what);
        ++g_fails;
    }
    fflush(stdout);
}

#define CHECKF(cond, msg) chk((cond) ? 1 : 0, msg)

/* 读满 n 字节；返回实际读到的字节数（可能少于 n，例如越过文件尾） */
static size_t read_some(int fd, void* buf, size_t n, unsigned long long off) {
    unsigned char* p = (unsigned char*)buf;
    size_t done = 0;
    while (done < n) {
        ssize_t r = pread(fd, p + done, n - done, (off_t)(off + done));
        if (r <= 0) break;
        done += (size_t)r;
    }
    return done;
}

static int read_at(int fd, void* buf, size_t n, unsigned long long off) {
    return read_some(fd, buf, n, off) == n ? 0 : -1;
}

/* 虚地址 -> 文件偏移，经 PT_LOAD 段换算 */
static int vaddr_to_off(const Elf64_Phdr* ph, int nph, Elf64_Addr va,
                        unsigned long long* off) {
    int i;
    for (i = 0; i < nph; ++i) {
        if (ph[i].p_type != PT_LOAD) continue;
        if (va >= ph[i].p_vaddr && va < ph[i].p_vaddr + ph[i].p_memsz) {
            *off = (unsigned long long)(ph[i].p_offset + (va - ph[i].p_vaddr));
            return 0;
        }
    }
    return -1;
}

static int has_needed(char needed[][256], int count, const char* name) {
    int i;
    for (i = 0; i < count; ++i) {
        if (strcmp(needed[i], name) == 0) return 1;
    }
    return 0;
}

/* 在动态串表里找第一个包含 needle 的 NUL 结尾名字 */
static int strtab_find(const char* tab, size_t sz, const char* needle,
                       char* out, size_t outsz) {
    size_t i = 0;
    while (i < sz) {
        const char* s = tab + i;
        size_t len = strnlen(s, sz - i);
        if (strstr(s, needle) != NULL) {
            size_t n = len < outsz - 1 ? len : outsz - 1;
            memcpy(out, s, n);
            out[n] = '\0';
            return 1;
        }
        i += len + 1;
    }
    return 0;
}

int main(int argc, char** argv) {
    const char* path;
    int fd, nph, ndyn = 0, nneeded = 0, i;
    Elf64_Ehdr eh;
    Elf64_Phdr ph[MAX_PHDR];
    Elf64_Dyn dyn[MAX_DYN];
    Elf64_Addr dyn_off = 0;
    Elf64_Xword dyn_size = 0;
    unsigned long long strtab_off = 0, strsz = 0;
    static char strtab[STRMAX];
    int have_strtab = 0;
    char needed[64][256];
    char nc_name[256], tc_name[256], mu_name[256];
    void* handle = NULL;
    void* nc_sym = NULL;
    void* tc_sym = NULL;
    void* mu_sym = NULL;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <package>/lib/libgclib.so\n", argv[0]);
        return 2;
    }
    path = argv[1];

    fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return 2;
    }
    if (read_at(fd, &eh, sizeof(eh), 0) != 0) {
        fprintf(stderr, "cannot read ELF header of %s\n", path);
        close(fd);
        return 2;
    }

    /* ---------------- 场景 #1：平台 ABI ---------------- */
    printf("=== OHOS specific #1: platform ABI of %s ===\n", path);

    CHECKF(memcmp(eh.e_ident, ELFMAG, SELFMAG) == 0, "ELF magic present");
    CHECKF(eh.e_ident[EI_CLASS] == ELFCLASS64,
           "ELFCLASS64 (64-bit OHOS PC target)");
    CHECKF(eh.e_machine == EM_AARCH64,
           "e_machine == EM_AARCH64 (OHOS aarch64)");

    nph = eh.e_phnum < MAX_PHDR ? eh.e_phnum : MAX_PHDR;
    for (i = 0; i < nph; ++i) {
        if (read_at(fd, &ph[i], sizeof(Elf64_Phdr),
                    (unsigned long long)eh.e_phoff +
                        (unsigned long long)i * eh.e_phentsize) != 0) {
            fprintf(stderr, "cannot read program header %d\n", i);
            close(fd);
            return 2;
        }
        if (ph[i].p_type == PT_DYNAMIC) {
            dyn_off = ph[i].p_offset;
            dyn_size = ph[i].p_filesz;
        }
    }
    CHECKF(dyn_off != 0, "PT_DYNAMIC segment present");

    if (dyn_off != 0) {
        size_t n = (size_t)(dyn_size / sizeof(Elf64_Dyn));
        if (n > MAX_DYN) n = MAX_DYN;
        if (read_at(fd, dyn, n * sizeof(Elf64_Dyn), dyn_off) != 0) {
            fprintf(stderr, "cannot read dynamic section\n");
            close(fd);
            return 2;
        }
        ndyn = (int)n;
        for (i = 0; i < ndyn; ++i) {
            if (dyn[i].d_tag == DT_STRTAB) {
                (void)vaddr_to_off(ph, nph, dyn[i].d_un.d_ptr, &strtab_off);
            } else if (dyn[i].d_tag == DT_STRSZ) {
                strsz = dyn[i].d_un.d_val;
            }
        }
        if (strsz > STRMAX) strsz = STRMAX;
        if (strtab_off != 0 && strsz != 0 &&
            read_at(fd, strtab, (size_t)strsz, strtab_off) == 0) {
            have_strtab = 1;
            for (i = 0; i < ndyn && nneeded < 64; ++i) {
                if (dyn[i].d_tag != DT_NEEDED) continue;
                if (dyn[i].d_un.d_val >= strsz) continue;
                {
                    const char* s = strtab + dyn[i].d_un.d_val;
                    size_t len = strnlen(s, (size_t)(strsz - dyn[i].d_un.d_val));
                    if (len < sizeof(needed[0])) {
                        memcpy(needed[nneeded], s, len);
                        needed[nneeded][len] = '\0';
                        nneeded++;
                    }
                }
            }
        }
        printf("info - DT_NEEDED closure (%d entries)\n", nneeded);
        for (i = 0; i < nneeded; ++i) printf("info -   %s\n", needed[i]);
    }
    close(fd);

    CHECKF(has_needed(needed, nneeded, "libc.so"),
           "DT_NEEDED links the OHOS musl libc (\"libc.so\")");
    CHECKF(!has_needed(needed, nneeded, "libc.so.6"),
           "DT_NEEDED does not use the glibc naming (\"libc.so.6\")");
    CHECKF(has_needed(needed, nneeded, "libc++_shared.so"),
           "DT_NEEDED links the OHOS libc++ runtime (\"libc++_shared.so\")");
    CHECKF(!has_needed(needed, nneeded, "libstdc++.so.6"),
           "DT_NEEDED does not pull any glibc libstdc++ (\"libstdc++.so.6\")");

    /* 动态串表里必须能找到 gclib 的 C++ 入口（名字含 Itanium 修饰前缀） */
    nc_name[0] = tc_name[0] = mu_name[0] = '\0';
    if (have_strtab) {
        (void)strtab_find(strtab, (size_t)strsz, "ntComplement",
                          nc_name, sizeof(nc_name));
        (void)strtab_find(strtab, (size_t)strsz, "translateCodon",
                          tc_name, sizeof(tc_name));
        (void)strtab_find(strtab, (size_t)strsz, "get_mem_usage",
                          mu_name, sizeof(mu_name));
    }
    printf("info - exported: %s | %s | %s\n",
           nc_name[0] ? nc_name : "(missing)",
           tc_name[0] ? tc_name : "(missing)",
           mu_name[0] ? mu_name : "(missing)");
    CHECKF(nc_name[0] != '\0',
           "dynamic string table exports ntComplement (gdna.h API)");
    CHECKF(tc_name[0] != '\0',
           "dynamic string table exports translateCodon (codons.h API)");

    /* 场景 #1 收尾：OHOS 加载器必须能按 RTLD_NOW 把它整个解析进来 */
    handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    CHECKF(handle != NULL, "OHOS loader dlopen(RTLD_NOW|RTLD_LOCAL) succeeds");
    if (handle == NULL) fprintf(stderr, "dlopen(%s): %s\n", path, dlerror());

    if (handle != NULL) {
        if (nc_name[0]) nc_sym = dlsym(handle, nc_name);
        if (tc_name[0]) tc_sym = dlsym(handle, tc_name);
        if (mu_name[0]) mu_sym = dlsym(handle, mu_name);
    }
    CHECKF(nc_sym != NULL, "dlsym resolves ntComplement");
    CHECKF(tc_sym != NULL, "dlsym resolves translateCodon");
    CHECKF(mu_sym != NULL, "dlsym resolves get_mem_usage");

    /* ---------------- 场景 #2：运行时契约 ---------------- */
    printf("\n=== OHOS specific #2: runtime contract ===\n");
    {
        char (*nc)(char) = (char (*)(char))nc_sym;
        char (*tc)(const char*) = (char (*)(const char*))tc_sym;
        void (*mu)(double&, double&) = (void (*)(double&, double&))mu_sym;

        /* 全库零显式初始化：两张碱基表 / 32K 密码子表都靠 .init_array 里的
         * 命名空间级静态初始化，在 dlopen 映射阶段就绪。 */
        CHECKF(nc != NULL && nc('A') == 'T',
               "ntComplement('A')=='T' with NO explicit gDnaInit()");
        CHECKF(nc != NULL && nc('a') == 't',
               "ntComplement('a')=='t' (256-entry table fully built)");
        CHECKF(tc != NULL && tc("ATG") == 'M',
               "translateCodon(\"ATG\")=='M' with NO explicit codonTableInit()");
        CHECKF(tc != NULL && tc("TAA") == '.',
               "translateCodon(\"TAA\")=='.' (gclib stop codon)");

        /* proc_mem.cpp 在 OHOS 上走 `#else //assume Linux`：读 /proc/self/stat */
        CHECKF(access("/proc/self/stat", F_OK) == 0,
               "/proc/self/stat is readable (OHOS mounts procfs)");

        double vs = 0.0, rs = 0.0;
        CHECKF(mu != NULL && (mu(vs, rs), vs > 0.0),
               "get_mem_usage() reports non-zero virtual memory (Linux branch)");
        vs = 0.0;
        rs = 0.0;
        CHECKF(mu != NULL && (mu(vs, rs), rs > 0.0),
               "get_mem_usage() reports non-zero resident set (musl sysconf OK)");
    }

    if (handle != NULL) dlclose(handle);

    printf("\nchecks=%d failures=%d\n", g_checks, g_fails);
    if (g_fails == 0) {
        printf("libgclib/0.12.8 OHOS-specific checks OK\n");
        return 0;
    }
    printf("libgclib/0.12.8 OHOS-specific checks FAILED\n");
    return 1;
}
