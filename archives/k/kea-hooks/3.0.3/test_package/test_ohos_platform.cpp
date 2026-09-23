/*
 * HarmonyOS / OHOS platform-specific test for kea-hooks.
 *
 * The upstream Meson suite (src/lib/hooks/tests, registered as
 * kea-hooks-tests) verifies the hooks framework logic on whichever
 * Linux-like target it is built for.  This test is the HarmonyOS-specific
 * one: it verifies the parts of the delivery that only exist because the
 * package is built for OHOS aarch64.
 *
 * Checks
 *   A. compile-time guard: the OHOS compiler is in use (__OHOS__)
 *   B. the OHOS escape hatch the recipe exports for consumers
 *      (boost's BOOST_SP_NO_PTHREAD_SETCANCELSTATE, set by the recipe's
 *      package_info for os=OHOS) is really in the consumer's compile line:
 *      the boost header that calls pthread_setcancelstate() is included here,
 *      so this translation unit only compiles when the define is propagated
 *   C. the packaged libkea-hooks.so is a 64-bit aarch64 ELF (OHOS PC target)
 *   D. its PT_DYNAMIC segment and dynamic string table are readable
 *   E. DT_NEEDED links the OHOS musl libc ("libc.so") and not the glibc
 *      naming ("libc.so.6")
 *   F. DT_NEEDED links the OHOS libc++ runtime ("libc++_shared.so")
 *   G. the OHOS loader can dlopen(RTLD_NOW) the library, i.e. the seven Kea
 *      runtime libraries shipped alongside it resolve from the package
 *
 * Only public headers, ELF parsing and POSIX calls are used, so the test is
 * portable but can only pass for an OHOS-built artefact.  Any failed check
 * makes main() return non-zero so CTest / the Conan test_package reports it.
 */
#include <hooks/hooks.h>

#if defined(__OHOS__)
/* This header calls pthread_setcancelstate(), which the OHOS musl pthread.h
 * does not declare; it compiles only with the define the package exports. */
#include <boost/core/detail/sp_thread_sleep.hpp>
#define KEA_HOOKS_OHOS_TU 1
#else
#define KEA_HOOKS_OHOS_TU 0
#endif

#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include <string>

namespace {

int failures = 0;

void
check(bool ok, const std::string& what) {
    printf("%s - %s\n", ok ? "ok  " : "FAIL", what.c_str());
    fflush(stdout);
    if (!ok) {
        ++failures;
    }
}

int
read_at(int fd, void* buf, size_t n, unsigned long long off) {
    unsigned char* p = static_cast<unsigned char*>(buf);
    size_t done = 0;
    while (done < n) {
        const ssize_t r = pread(fd, p + done, n - done, static_cast<off_t>(off + done));
        if (r <= 0) {
            return -1;
        }
        done += static_cast<size_t>(r);
    }
    return 0;
}

/* Map a virtual address to a file offset through the PT_LOAD headers. */
int
vaddr_to_off(const Elf64_Phdr* ph, int nph, Elf64_Addr va, unsigned long long* off) {
    for (int i = 0; i < nph; ++i) {
        if (ph[i].p_type != PT_LOAD) {
            continue;
        }
        if (va >= ph[i].p_vaddr && va < ph[i].p_vaddr + ph[i].p_memsz) {
            *off = static_cast<unsigned long long>(ph[i].p_offset + (va - ph[i].p_vaddr));
            return 0;
        }
    }
    return -1;
}

bool
has_needed(char needed[][256], int count, const char* name) {
    for (int i = 0; i < count; ++i) {
        if (strcmp(needed[i], name) == 0) {
            return true;
        }
    }
    return false;
}

} // namespace

int
main(int argc, char** argv) {
    constexpr int MAX_PHDR = 64;
    constexpr int MAX_NEEDED = 64;
    constexpr int MAX_DYNENT = 1024;
    /* Sanity bound for the dynamic string table (libkea-hooks.so needs ~1 KiB). */
    constexpr unsigned long long MAX_STRTAB = 16ull * 1024ull * 1024ull;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-libkea-hooks.so>\n", argv[0]);
        return 2;
    }

    // A) OHOS build
    check(KEA_HOOKS_OHOS_TU == 1, "built by the OHOS compiler (__OHOS__ defined)");

    // B) the packaged headers are the Kea 3.0.3 ones and the OHOS escape hatch
    // propagated through the Conan target (this TU includes the boost header
    // that needs it).
    check(KEA_HOOKS_VERSION == 30003, "packaged headers are Kea 3.0.3 (KEA_HOOKS_VERSION)");

#ifdef BOOST_SP_NO_PTHREAD_SETCANCELSTATE
    check(true, "package exports BOOST_SP_NO_PTHREAD_SETCANCELSTATE to OHOS consumers");
#else
    check(false, "package exports BOOST_SP_NO_PTHREAD_SETCANCELSTATE to OHOS consumers");
#endif

    const char* path = argv[1];
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return 2;
    }

    Elf64_Ehdr eh;
    if (read_at(fd, &eh, sizeof(eh), 0) != 0) {
        fprintf(stderr, "cannot read ELF header of %s\n", path);
        close(fd);
        return 2;
    }
    unsigned long long fsize = 0;
    struct stat st;
    if (fstat(fd, &st) == 0) {
        fsize = static_cast<unsigned long long>(st.st_size);
    }

    // C) ELF class / machine
    check(memcmp(eh.e_ident, ELFMAG, SELFMAG) == 0, "packaged library is an ELF object");
    check(eh.e_ident[EI_CLASS] == ELFCLASS64, "ELFCLASS64 (64-bit OHOS PC target)");
    check(eh.e_machine == EM_AARCH64, "e_machine == EM_AARCH64 (OHOS aarch64)");

    // D) program headers / dynamic section
    const int nph = eh.e_phnum < MAX_PHDR ? eh.e_phnum : MAX_PHDR;
    Elf64_Phdr ph[MAX_PHDR];
    Elf64_Addr dyn_off = 0;
    Elf64_Xword dyn_size = 0;
    for (int i = 0; i < nph; ++i) {
        if (read_at(fd, &ph[i], sizeof(Elf64_Phdr),
                    static_cast<unsigned long long>(eh.e_phoff)
                        + static_cast<unsigned long long>(i) * eh.e_phentsize) != 0) {
            fprintf(stderr, "cannot read program header %d\n", i);
            close(fd);
            return 2;
        }
        if (ph[i].p_type == PT_DYNAMIC) {
            dyn_off = ph[i].p_offset;
            dyn_size = ph[i].p_filesz;
        }
    }
    check(dyn_off != 0, "PT_DYNAMIC segment present (shared library)");

    Elf64_Dyn dyn[MAX_DYNENT];
    int ndyn = 0;
    unsigned long long strtab_off = 0;
    unsigned long long strsz = 0;
    if (dyn_off != 0) {
        size_t n = static_cast<size_t>(dyn_size / sizeof(Elf64_Dyn));
        if (n > MAX_DYNENT) {
            n = MAX_DYNENT;
        }
        if (read_at(fd, dyn, n * sizeof(Elf64_Dyn), dyn_off) != 0) {
            fprintf(stderr, "cannot read dynamic section\n");
            close(fd);
            return 2;
        }
        ndyn = static_cast<int>(n);
        for (int i = 0; i < ndyn; ++i) {
            if (dyn[i].d_tag == DT_STRTAB) {
                (void)vaddr_to_off(ph, nph, dyn[i].d_un.d_ptr, &strtab_off);
            } else if (dyn[i].d_tag == DT_STRSZ) {
                strsz = dyn[i].d_un.d_val;
            }
        }
    }

    char* strtab = nullptr;
    bool strtab_ok = false;
    if (strtab_off != 0 && strsz != 0 && strsz <= MAX_STRTAB && strtab_off + strsz <= fsize) {
        strtab = static_cast<char*>(malloc(static_cast<size_t>(strsz)));
        if (strtab != nullptr && read_at(fd, strtab, static_cast<size_t>(strsz), strtab_off) == 0) {
            strtab_ok = true;
        }
    }
    check(strtab_ok, "dynamic string table (DT_STRTAB/DT_STRSZ) read from the file");

    char needed[MAX_NEEDED][256];
    int nneeded = 0;
    memset(needed, 0, sizeof(needed));
    if (strtab_ok) {
        for (int i = 0; i < ndyn && nneeded < MAX_NEEDED; ++i) {
            if (dyn[i].d_tag != DT_NEEDED) {
                continue;
            }
            const unsigned long long off = dyn[i].d_un.d_val;
            if (off >= strsz) {
                continue;
            }
            const char* s = strtab + off;
            const size_t len = strnlen(s, static_cast<size_t>(strsz - off));
            if (len > 0 && len < sizeof(needed[0])) {
                memcpy(needed[nneeded], s, len);
                needed[nneeded][len] = '\0';
                ++nneeded;
            }
        }
    }
    free(strtab);
    close(fd);

    printf("info - DT_NEEDED closure (%d entries)\n", nneeded);
    for (int i = 0; i < nneeded; ++i) {
        printf("info -   %s\n", needed[i]);
    }

    // E) OHOS musl libc naming, not glibc
    check(has_needed(needed, nneeded, "libc.so"),
          "DT_NEEDED links the OHOS musl libc (\"libc.so\")");
    check(!has_needed(needed, nneeded, "libc.so.6"),
          "DT_NEEDED does not use the glibc naming (\"libc.so.6\")");

    // F) OHOS libc++ runtime
    check(has_needed(needed, nneeded, "libc++_shared.so"),
          "DT_NEEDED links the OHOS libc++ runtime (\"libc++_shared.so\")");

    // G) the OHOS loader resolves the whole Kea runtime closure of the package
    void* handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    check(handle != nullptr, "OHOS loader dlopen(RTLD_NOW) resolves libkea-hooks.so");
    if (handle != nullptr) {
        dlclose(handle);
    } else {
        fprintf(stderr, "dlopen(%s) failed: %s\n", path, dlerror());
    }

    if (failures == 0) {
        printf("kea-hooks/3.0.3 OHOS platform check OK\n");
        return 0;
    }
    printf("kea-hooks/3.0.3 OHOS platform check FAILED (%d check(s))\n", failures);
    return 1;
}
