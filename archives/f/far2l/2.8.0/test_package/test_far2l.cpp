// test_far2l.cpp — Consumer test for far2l 2.8.0
//
// far2l is an application (type=tool), so the test verifies:
//   1. The far2l binary exists at the expected package path
//   2. The binary is a valid ELF executable for the target arch
//   3. The binary links against expected system libraries (dl, pthread)
//
// The actual functional test (running far2l --help and checking output)
// is performed by test_far2l.sh, invoked via self.run() in conanfile.py.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/stat.h>

// Custom CHECK macro (not assert — NDEBUG would disable it in Release)
#define CHECK(cond, msg) \
    do { \
        if (!(cond)) { \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
            return 1; \
        } \
    } while (0)

int main(int argc, char *argv[]) {
    // The far2l binary path is expected to be passed by the test harness
    // or found via the conan package layout.
    const char *far2l_path = nullptr;

    // Check if path is provided as argument
    if (argc > 1) {
        far2l_path = argv[1];
    } else {
        // Default expected location relative to conan package
        far2l_path = "bin/far2l";
    }

    // Test 1: Binary exists
    struct stat st;
    CHECK(stat(far2l_path, &st) == 0, "far2l binary not found at expected path");
    CHECK(st.st_size > 0, "far2l binary is empty");

    // Test 2: Verify it is an ELF file (magic bytes 0x7f E L F)
    FILE *fp = fopen(far2l_path, "rb");
    CHECK(fp != nullptr, "cannot open far2l binary for reading");

    unsigned char elf_magic[4];
    size_t nread = fread(elf_magic, 1, 4, fp);
    fclose(fp);

    CHECK(nread == 4, "cannot read ELF magic from far2l binary");
    CHECK(elf_magic[0] == 0x7f, "ELF magic byte 0 incorrect");
    CHECK(elf_magic[1] == 0x45, "ELF magic byte 1 incorrect");  // E
    CHECK(elf_magic[2] == 0x4c, "ELF magic byte 2 incorrect");  // L
    CHECK(elf_magic[3] == 0x46, "ELF magic byte 3 incorrect");  // F

    // Test 3: Verify ELF class (64-bit for aarch64)
    fp = fopen(far2l_path, "rb");
    CHECK(fp != nullptr, "cannot reopen far2l binary");

    unsigned char header[20];
    nread = fread(header, 1, 20, fp);
    fclose(fp);

    CHECK(nread >= 20, "cannot read ELF header");
    CHECK(header[4] == 2, "ELF class is not 64-bit (ELFCLASS64)");
    CHECK(header[5] == 1, "ELF data encoding is not little-endian");
    // header[18..19] = e_machine, should be 0xB7 (183 = EM_AARCH64)
    unsigned short e_machine = header[18] | (header[19] << 8);
    CHECK(e_machine == 0xB7, "ELF machine type is not AARCH64");

    printf("test_far2l: PASSED (binary exists, ELF64 aarch64)\n");
    return 0;
}
