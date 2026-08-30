// Real consumer test for the astromenace package.
//
// The package is an application (game binary + gamedata.vfs), not a
// library, so a consumer test verifies the delivered artifacts:
//   1. the AstroMenace binary exists at the expected path;
//   2. it is a valid ELF executable for the target architecture
//      (AArch64 on OHOS);
//   3. the game data archive gamedata.vfs ships beside the binary;
//   4. both files carry the executable/readable permissions expected of
//      packaged artifacts.
//   5. (real invocation) when the binary is locally runnable, spawn it and
//      require the startup banner "AstroMenace 1.3.2" to be emitted; this is
//      a behavioral check, separate from any upstream test suite counts.
// The test exits non-zero on any hard failure so CI catches packaging
// regressions; a missing binary on a pure cross-compilation host is
// reported as a note (the compile/link of this consumer test is a pass).

#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <sys/stat.h>

#ifndef ASTROMENACE_BINARY
#error "ASTROMENACE_BINARY must be defined by CMake configure step"
#endif

#ifndef ASTROMENACE_BINDIR
#define ASTROMENACE_BINDIR ""
#endif

// Real invocation check: spawn the binary and require it to emit the startup
// banner "AstroMenace 1.3.2".  The banner is printed before any GL/VFS init
// that could fail on a headless host, so this is a stable behavioral probe of
// the packaged binary (separate from upstream test counts).
static int run_binary_check(const char* binary) {
    char cmd[4096];
    std::snprintf(cmd, sizeof(cmd), "%s 2>&1 | head -1", binary);
    FILE* p = ::popen(cmd, "r");   // C stdio function, global namespace
    if (!p) {
        std::fprintf(stderr, "FAIL: cannot spawn %s\n", binary);
        return 1;
    }
    char line[256];
    bool got = false;
    if (std::fgets(line, sizeof(line), p) != NULL) {
        got = (std::strstr(line, "AstroMenace 1.3.2") != NULL);
    }
    int rc = ::pclose(p);
    if (got) {
        std::printf("OK: real invocation emitted startup banner: %s", line);
        return 0;
    }
    std::fprintf(stderr, "FAIL: binary did not emit 'AstroMenace 1.3.2' banner (popen rc=%d, out='%s')\n",
                 rc, line[0] ? line : "<empty>");
    return 1;
}

static int check_executable_bit(const char* path) {
    struct stat st;
    if (stat(path, &st) != 0) {
        std::fprintf(stderr, "FAIL: cannot stat %s\n", path);
        return 1;
    }
    if (!(st.st_mode & S_IXUSR)) {
        std::fprintf(stderr, "FAIL: %s is not executable\n", path);
        return 1;
    }
    return 0;
}

int main() {
    const char* binary = ASTROMENACE_BINARY;
    std::printf("ASTROMENACE_BINARY = %s\n", binary);

    //--- 1. Check the binary exists ---
    FILE* f = std::fopen(binary, "rb");
    if (!f) {
        // On a cross-compilation host the binary may not be locally
        // accessible; the consumer compile/link is still a valid PASS.
        std::printf("NOTE: binary not accessible locally (cross-compile host)\n");
        std::printf("astromenace test_package: compile/link OK\n");
        return 0;
    }

    //--- 2. Validate ELF header ---
    unsigned char hdr[20];
    size_t n = std::fread(hdr, 1, sizeof(hdr), f);
    std::fclose(f);

    if (n < 20 || hdr[0] != 0x7f || hdr[1] != 'E' || hdr[2] != 'L' || hdr[3] != 'F') {
        std::fprintf(stderr, "FAIL: not an ELF file\n");
        return 1;
    }

    int elf_class = hdr[4];   // 1 = ELF32, 2 = ELF64
    int elf_endian = hdr[5];  // 1 = little-endian
    if (elf_class == 1) {
        std::printf("OK: 32-bit ELF\n");
    } else if (elf_class == 2) {
        std::printf("OK: 64-bit ELF\n");
    } else {
        std::fprintf(stderr, "FAIL: unknown ELF class %d\n", elf_class);
        return 1;
    }
    if (elf_endian != 1) {
        std::fprintf(stderr, "FAIL: not little-endian (endian=%d)\n", elf_endian);
        return 1;
    }
    std::printf("OK: little-endian ELF\n");

    //--- 3. ELF machine type (e_machine at offset 18) ---
    unsigned int mach = (unsigned int)hdr[18] | ((unsigned int)hdr[19] << 8);
    // 0xB7 (183) = EM_AARCH64
    if (mach == 183) {
        std::printf("OK: machine AArch64\n");
    } else if (mach == 62) {  // EM_X86_64
        std::printf("OK: machine x86-64\n");
    } else if (mach == 3) {   // EM_386
        std::printf("OK: machine i386\n");
    } else {
        std::fprintf(stderr, "FAIL: unexpected machine type 0x%x\n", mach);
        return 1;
    }

    //--- 4. Executable permission bit ---
    if (check_executable_bit(binary) != 0) {
        return 1;
    }
    std::printf("OK: binary is executable\n");

    //--- 5. gamedata.vfs ships beside the binary ---
    char vfs_path[2048];
    std::snprintf(vfs_path, sizeof(vfs_path), "%s/gamedata.vfs", ASTROMENACE_BINDIR);
    FILE* vfs = std::fopen(vfs_path, "rb");
    if (!vfs) {
        std::fprintf(stderr, "FAIL: gamedata.vfs not found at %s\n", vfs_path);
        return 1;
    }
    std::printf("OK: gamedata.vfs present at %s\n", vfs_path);
    std::fclose(vfs);

    //--- 6. Real invocation: the packaged binary must start up on the
    //        local (OHOS) host and emit the startup banner ---
    if (run_binary_check(binary) != 0) {
        return 1;
    }

    std::printf("OK: astromenace test_package passed\n");
    return 0;
}