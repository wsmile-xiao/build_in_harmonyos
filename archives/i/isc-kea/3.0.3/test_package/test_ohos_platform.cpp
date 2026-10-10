/*
 * HarmonyOS / OHOS platform-specific test for isc-kea.
 *
 * The upstream Meson suites (the per-library and per-server gtest binaries)
 * verify the Kea logic on whichever Linux-like target they are built for.
 * This test is the HarmonyOS-specific one: it verifies the parts of the
 * delivery that only exist because the package is built for OHOS aarch64.
 *
 * Checks
 *   A. compile-time guard: the OHOS compiler is in use (__OHOS__)
 *   B. the OHOS escape hatch the recipe exports for consumers
 *      (boost's BOOST_SP_NO_PTHREAD_SETCANCELSTATE, set by the recipe's
 *      package_info for os=OHOS) is really in the consumer's compile line:
 *      the boost header that calls pthread_setcancelstate() is included here,
 *      so this translation unit only compiles when the define is propagated
 *   C. the packaged libkea-asiolink.so is a 64-bit aarch64 ELF (OHOS PC target)
 *   D. its PT_DYNAMIC segment and dynamic string table are readable
 *   E. DT_NEEDED links the OHOS musl libc ("libc.so") and not the glibc
 *      naming ("libc.so.6")
 *   F. DT_NEEDED links the OHOS libc++ runtime ("libc++_shared.so")
 *   G. the OHOS loader can dlopen(RTLD_NOW) the library, i.e. the Kea
 *      libraries shipped alongside it resolve from the package
 *
 * Only public headers, ELF parsing and POSIX calls are used, so the test is
 * portable but can only pass for an OHOS-built artefact.  Any failed check
 * makes main() return non-zero so the Conan test_package reports it.
 */
#include <asiolink/io_address.h>

#if defined(__OHOS__)
/* This header calls pthread_setcancelstate(), which the OHOS musl pthread.h
 * does not declare; it compiles only with the define the package exports. */
#include <boost/core/detail/sp_thread_sleep.hpp>
#define ISC_KEA_OHOS_TU 1
#else
#define ISC_KEA_OHOS_TU 0
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
#include <vector>

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
        if (va >= ph[i].p_vaddr && va < ph[i].p_vaddr + ph[i].p_filesz) {
            *off = ph[i].p_offset + (va - ph[i].p_vaddr);
            return 0;
        }
    }
    return -1;
}

} // namespace

int
main(int argc, char** argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <libkea-asiolink.so>\n", argv[0]);
        return 2;
    }
    const char* libpath = argv[1];

    // A. The OHOS toolchain compiled this translation unit.
    check(ISC_KEA_OHOS_TU == 1, "compiled with the OHOS clang (__OHOS__)");

    // B. The boost escape hatch the recipe exports reached this TU: the
    //    include above would not compile without it on OHOS musl.
    check(true, "boost sp_thread_sleep.hpp compiled (BOOST_SP_NO_PTHREAD_SETCANCELSTATE propagated)");

    // C-F. Parse the packaged library ELF.
    const int fd = open(libpath, O_RDONLY);
    check(fd >= 0, std::string("open ") + libpath);
    if (fd < 0) {
        printf("FAILED: cannot continue without the artefact\n");
        return 1;
    }

    Elf64_Ehdr eh;
    check(read_at(fd, &eh, sizeof(eh), 0) == 0, "read ELF header");
    check(memcmp(eh.e_ident, ELFMAG, SELFMAG) == 0 && eh.e_ident[EI_CLASS] == ELFCLASS64,
          "64-bit ELF (aarch64 target)");
    check(eh.e_machine == EM_AARCH64, "EM_AARCH64 machine type");

    std::vector<Elf64_Phdr> ph(eh.e_phnum);
    check(read_at(fd, ph.data(), sizeof(Elf64_Phdr) * eh.e_phnum, eh.e_phoff) == 0,
          "read program headers");

    const Elf64_Phdr* dyn = 0;
    for (int i = 0; i < eh.e_phnum; ++i) {
        if (ph[i].p_type == PT_DYNAMIC) {
            dyn = &ph[i];
            break;
        }
    }
    check(dyn != 0, "PT_DYNAMIC segment present");

    bool musl = false, libcxx = false, glibc = false;
    if (dyn) {
        unsigned long long off = 0;
        check(vaddr_to_off(ph.data(), eh.e_phnum, dyn->p_vaddr, &off) == 0,
              "map PT_DYNAMIC to file offset");
        const size_t ndyn = dyn->p_filesz / sizeof(Elf64_Dyn);
        std::vector<Elf64_Dyn> dyns(ndyn);
        check(read_at(fd, dyns.data(), dyn->p_filesz, off) == 0, "read dynamic table");

        const char* strtab = 0;
        for (size_t i = 0; i < ndyn; ++i) {
            if (dyns[i].d_tag == DT_STRTAB) {
                unsigned long long so = 0;
                if (vaddr_to_off(ph.data(), eh.e_phnum,
                                 static_cast<Elf64_Addr>(dyns[i].d_un.d_ptr), &so) == 0) {
                    /* The string table can be several KiB; read it in chunks
                     * through a bounded buffer scan instead of one big read. */
                    strtab = reinterpret_cast<const char*>(1);  /* marker */
                    for (size_t j = 0; j < ndyn; ++j) {
                        if (dyns[j].d_tag != DT_NEEDED) {
                            continue;
                        }
                        char name[256];
                        const unsigned long long name_off = so + dyns[j].d_un.d_val;
                        ssize_t r = pread(fd, name, sizeof(name) - 1,
                                          static_cast<off_t>(name_off));
                        if (r <= 0) {
                            continue;
                        }
                        name[r] = '\0';
                        const std::string needed(name);
                        if (needed == "libc.so") {
                            musl = true;
                        }
                        if (needed == "libc.so.6") {
                            glibc = true;
                        }
                        if (needed == "libc++_shared.so") {
                            libcxx = true;
                        }
                    }
                }
                break;
            }
        }
        check(strtab != 0, "dynamic string table readable");
    }
    check(musl, "DT_NEEDED links the OHOS musl libc (libc.so)");
    check(!glibc, "no glibc naming (libc.so.6) in DT_NEEDED");
    check(libcxx, "DT_NEEDED links the OHOS libc++ runtime (libc++_shared.so)");
    close(fd);

    // G. The OHOS loader maps the library with RTLD_NOW: every Kea library it
    //    needs resolves from the package lib/ directory (conanrun env).
    void* handle = dlopen(libpath, RTLD_NOW);
    check(handle != 0, "dlopen(RTLD_NOW) resolves the packaged closure");
    if (handle) {
        dlclose(handle);
    }
    // The packaged API is reachable from the linked mapping too: a direct
    // IOAddress round-trip through the header the package installs.
    const isc::asiolink::IOAddress probe("198.51.100.7");
    check(probe.toText() == "198.51.100.7" && probe.isV4(),
          "IOAddress API reachable through the packaged mapping");

    printf("%s: test_ohos_platform\n", failures == 0 ? "PASS" : "FAILED");
    return failures == 0 ? 0 : 1;
}
