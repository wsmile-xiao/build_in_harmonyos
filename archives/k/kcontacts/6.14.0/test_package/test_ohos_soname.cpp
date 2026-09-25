// OHOS-specific check for the kcontacts HarmonyOS PC adaptation.
//
// The recipe gives libKF6Contacts a real DT_SONAME through CMake's OHOS
// platform rules plus a CMAKE_USER_MAKE_RULES_OVERRIDE defining
// CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG ("-Wl,-soname,"): CMake ships no
// Platform/HarmonyOS module, so without that override the shared library is
// linked without a SONAME and every consumer bakes the absolute conan-cache
// path of the build machine into DT_NEEDED. musl performs no fallback lookup
// for slash-qualified NEEDED entries, so such binaries only run where the
// exact cache path exists.
//
// This test parses its own ELF dynamic section and asserts the consumer
// linkage stayed SONAME-based: DT_NEEDED must contain exactly
// "libKF6Contacts.so.6" and no slash-qualified absolute path.
#include <KContacts/Addressee>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#ifdef TP_REQUIRE_OHOS
#ifndef __OHOS__
#error "TP_REQUIRE_OHOS set but __OHOS__ is not defined: the OHOS toolchain triplet is not in effect"
#endif
#endif

namespace {

std::string selfPath(int argc, char** argv)
{
    std::ifstream probe("/proc/self/exe", std::ios::binary);
    if (probe.good()) {
        return "/proc/self/exe";
    }
    if (argc > 0 && argv[0]) {
        return argv[0];
    }
    return {};
}

bool vaddrToFileOffset(uint64_t addr,
                       const std::vector<char>& image,
                       uint64_t phoff,
                       uint16_t phnum,
                       uint64_t& fileOffset)
{
    for (uint16_t i = 0; i < phnum; ++i) {
        const uint64_t entry = phoff + static_cast<uint64_t>(i) * 56u;
        if (entry + 56u > image.size()) {
            return false;
        }
        uint32_t pType = 0;
        std::memcpy(&pType, image.data() + entry + 0, sizeof(pType));
        if (pType != 1u) { // PT_LOAD
            continue;
        }
        uint64_t pVaddr = 0;
        uint64_t pFilesz = 0;
        uint64_t pOffset = 0;
        std::memcpy(&pOffset, image.data() + entry + 8, sizeof(pOffset));
        std::memcpy(&pVaddr, image.data() + entry + 16, sizeof(pVaddr));
        std::memcpy(&pFilesz, image.data() + entry + 32, sizeof(pFilesz));
        if (addr >= pVaddr && addr - pVaddr < pFilesz) {
            fileOffset = addr - pVaddr + pOffset;
            return true;
        }
    }
    return false;
}

} // namespace

int main(int argc, char** argv)
{
    const std::string path = selfPath(argc, argv);
    if (path.empty()) {
        std::printf("FAIL: cannot determine self executable path\n");
        return 1;
    }

    std::ifstream input(path, std::ios::binary);
    if (!input) {
        std::printf("FAIL: cannot open %s\n", path.c_str());
        return 1;
    }
    const std::vector<char> image((std::istreambuf_iterator<char>(input)),
                                  std::istreambuf_iterator<char>());
    if (image.size() < 64 || std::memcmp(image.data(), "\x7f" "ELF", 4) != 0) {
        std::printf("FAIL: %s is not an ELF image\n", path.c_str());
        return 1;
    }
    const unsigned char eiClass = static_cast<unsigned char>(image[4]);
    const unsigned char eiData = static_cast<unsigned char>(image[5]);
    if (eiClass != 2u || eiData != 1u) {
        std::printf("FAIL: expected ELF64 little-endian image, class=%u data=%u\n",
                    eiClass, eiData);
        return 1;
    }

    uint64_t phoff = 0;
    uint16_t phentsize = 0;
    uint16_t phnum = 0;
    std::memcpy(&phoff, image.data() + 32, sizeof(phoff));
    std::memcpy(&phentsize, image.data() + 54, sizeof(phentsize));
    std::memcpy(&phnum, image.data() + 56, sizeof(phnum));
    if (phentsize != 56u) {
        std::printf("FAIL: unexpected program header entry size %llu\n",
                    static_cast<unsigned long long>(phentsize));
        return 1;
    }

    uint64_t dynamicOffset = 0;
    uint64_t dynamicSize = 0;
    for (uint16_t i = 0; i < phnum; ++i) {
        const uint64_t entry = phoff + static_cast<uint64_t>(i) * phentsize;
        if (entry + 56u > image.size()) {
            std::printf("FAIL: program header table truncated\n");
            return 1;
        }
        uint32_t pType = 0;
        std::memcpy(&pType, image.data() + entry + 0, sizeof(pType));
        if (pType != 2u) { // PT_DYNAMIC
            continue;
        }
        std::memcpy(&dynamicOffset, image.data() + entry + 8, sizeof(dynamicOffset));
        std::memcpy(&dynamicSize, image.data() + entry + 32, sizeof(dynamicSize));
    }
    if (dynamicOffset == 0 || dynamicSize == 0) {
        std::printf("FAIL: no PT_DYNAMIC segment found\n");
        return 1;
    }

    uint64_t strtabAddr = 0;
    bool strtabFound = false;
    std::vector<uint64_t> neededOffsets;
    for (uint64_t pos = 0; pos + 16u <= dynamicSize; pos += 16u) {
        int64_t tag = 0;
        uint64_t value = 0;
        std::memcpy(&tag, image.data() + dynamicOffset + pos, sizeof(tag));
        std::memcpy(&value, image.data() + dynamicOffset + pos + 8, sizeof(value));
        if (tag == 0) { // DT_NULL
            break;
        }
        if (tag == 5) { // DT_STRTAB
            strtabAddr = value;
            strtabFound = true;
        } else if (tag == 1) { // DT_NEEDED
            neededOffsets.push_back(value);
        }
    }
    if (!strtabFound) {
        std::printf("FAIL: DT_STRTAB not found in dynamic section\n");
        return 1;
    }
    uint64_t strtabFileOffset = 0;
    if (!vaddrToFileOffset(strtabAddr, image, phoff, phnum, strtabFileOffset)) {
        std::printf("FAIL: cannot map DT_STRTAB address to a file offset\n");
        return 1;
    }

    auto neededString = [&](uint64_t offset) -> std::string {
        const uint64_t at = strtabFileOffset + offset;
        if (at >= image.size()) {
            return {};
        }
        const char* begin = image.data() + at;
        const uint64_t limit = image.size() - at;
        const char* end = static_cast<const char*>(std::memchr(begin, '\0', limit));
        if (!end) {
            return {};
        }
        return std::string(begin, end);
    };

    bool contactsFound = false;
    for (uint64_t offset : neededOffsets) {
        const std::string name = neededString(offset);
        if (name.empty()) {
            std::printf("FAIL: unreadable DT_NEEDED entry\n");
            return 1;
        }
        if (!name.empty() && name.front() == '/') {
            std::printf("FAIL: slash-qualified absolute DT_NEEDED entry baked in: %s\n",
                        name.c_str());
            return 1;
        }
        if (name == "libKF6Contacts.so.6") {
            contactsFound = true;
        }
    }
    if (!contactsFound) {
        std::printf("FAIL: DT_NEEDED does not reference libKF6Contacts.so.6 by SONAME\n");
        return 1;
    }

    // Real API touch: guarantees the linkage is live (not dropped by
    // --as-needed) and that the shared library loads and runs under musl.
    KContacts::Addressee contact;
    contact.setGivenName(QStringLiteral("Grace"));
    contact.setFamilyName(QStringLiteral("Hopper"));
    if (contact.realName() != QStringLiteral("Grace Hopper")) {
        std::printf("FAIL: KContacts API round-trip mismatch\n");
        return 1;
    }

    std::printf(
        "PASS: SONAME-based DT_NEEDED (libKF6Contacts.so.6, %zu NEEDED entries, none absolute)\n",
        neededOffsets.size());
    return 0;
}
