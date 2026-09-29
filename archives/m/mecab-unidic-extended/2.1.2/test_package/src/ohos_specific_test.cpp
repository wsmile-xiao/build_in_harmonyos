// HarmonyOS PC (OHOS) specific test for mecab-unidic-extended 2.1.2.
//
// This is NOT a generic MeCab consumer test: every check below asserts a
// property that is either unique to the HarmonyOS PC platform or verifies
// the packaged UniDic indices through the OHOS-target toolchain on a real
// OHOS host. It can only pass when built AND executed on HarmonyOS.
//
//   T1  compile-time OHOS target attributes: __OHOS__, __OHOS_FAMILY__,
//       __aarch64__ defined (aarch64-unknown-linux-ohos target; a generic
//       Linux build defines none of the OHOS macros); __MUSL__ is reported
//       as info only — the OHOS Clang does not define it, the musl verdict
//       is the ELF PT_INTERP check in T4
//   T2  runtime platform identity: uname().sysname == "HarmonyOS"
//       (a Linux host reports "Linux")
//   T3  self ELF identity via /proc/self/exe: ELF magic, ELF64 class,
//       little-endian, e_machine == EM_AARCH64 (183)
//   T4  self PT_INTERP == "/lib/ld-musl-aarch64.so.1" — the OHOS musl
//       dynamic loader (glibc Linux uses /lib64/ld-linux-aarch64.so.1)
//   T5  the OHOS-target libmecab (clang aarch64-unknown-linux-ohos + musl
//       + libc++) really loads the packaged UniDic binary indices that
//       were compiled on-device by the OHOS mecab-dict-index
//   T6  loaded index statistics match the official UniDic 2.1.2 release:
//       charset=utf8, size=756463 lexemes, 5981x5981 connection matrix —
//       proving on-OHOS endianness / dictionary-format compatibility of
//       the artifacts (values verified against a real on-device build)
//   T7  the loaded indices actually tokenize Japanese text (すもも… + EOS)
#include <mecab.h>
#include <sys/utsname.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

namespace {

int g_pass = 0;
int g_fail = 0;

void check(bool ok, const char *name, const std::string &detail) {
    if (ok) {
        ++g_pass;
        std::printf("[ohos] PASS %s — %s\n", name, detail.c_str());
    } else {
        ++g_fail;
        std::printf("[ohos] FAIL %s — %s\n", name, detail.c_str());
    }
}

// Little-endian scalar readers (self ELF is LE on aarch64; explicit decode
// keeps the parser independent of host byte order).
uint16_t rd16(const unsigned char *p) {
    return static_cast<uint16_t>(p[0] | (p[1] << 8));
}

uint64_t rd64(const unsigned char *p) {
    uint64_t v = 0;
    for (int i = 7; i >= 0; --i) v = (v << 8) | p[i];
    return v;
}

const uint16_t kEtDyn = 3;       // ET_DYN (PIE executable / shared object)
const uint16_t kEmAarch64 = 183; // EM_AARCH64
const uint32_t kPtInterp = 3;    // PT_INTERP

// Minimal ELF64 program-header entry (56 bytes).
struct Phdr64 {
    uint32_t p_type;
    uint32_t p_flags;
    uint64_t p_offset;
    uint64_t p_vaddr;
    uint64_t p_paddr;
    uint64_t p_filesz;
    uint64_t p_memsz;
    uint64_t p_align;
};

bool parse_self_elf(unsigned char ehdr[64], Phdr64 *interp, std::string *interp_str) {
    std::FILE *f = std::fopen("/proc/self/exe", "rb");
    if (f == nullptr) return false;
    if (std::fread(ehdr, 1, 64, f) != 64) { std::fclose(f); return false; }

    const uint64_t phoff = rd64(ehdr + 0x20);
    const uint16_t phentsize = rd16(ehdr + 0x36);
    const uint16_t phnum = rd16(ehdr + 0x38);
    if (phentsize != sizeof(Phdr64) || phnum == 0) { std::fclose(f); return false; }

    unsigned char ph[ sizeof(Phdr64) ];
    for (uint16_t i = 0; i < phnum; ++i) {
        if (std::fseek(f, static_cast<long>(phoff + static_cast<uint64_t>(i) * phentsize), SEEK_SET) != 0) break;
        if (std::fread(ph, 1, sizeof(Phdr64), f) != sizeof(Phdr64)) break;
        Phdr64 ent;
        std::memcpy(&ent.p_type, ph + 0, 4);
        std::memcpy(&ent.p_flags, ph + 4, 4);
        ent.p_offset = rd64(ph + 8);
        ent.p_filesz = rd64(ph + 32);
        if (ent.p_type == kPtInterp) {
            *interp = ent;
            interp_str->assign(static_cast<size_t>(ent.p_filesz), '\0');
            if (std::fseek(f, static_cast<long>(ent.p_offset), SEEK_SET) == 0 &&
                std::fread(&(*interp_str)[0], 1, static_cast<size_t>(ent.p_filesz), f) == ent.p_filesz) {
                // strip trailing NUL if present
                const size_t nul = interp_str->find('\0');
                if (nul != std::string::npos) interp_str->resize(nul);
            }
            break;
        }
    }
    std::fclose(f);
    return true;
}

}  // namespace

int main(int argc, char **argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage: %s <dicdir> <rcfile>\n", argv[0]);
        return 2;
    }
    const std::string dicdir = argv[1];
    const std::string rcfile = argv[2];

    std::printf("=== HARMONYOS-SPECIFIC TEST: mecab-unidic-extended 2.1.2 ===\n");

    // --- T1: compile-time OHOS target attributes -------------------------
#if defined(__OHOS__)
    const bool has_ohos = true;
#else
    const bool has_ohos = false;
#endif
#if defined(__OHOS_FAMILY__)
    const bool has_ohos_family = true;
#else
    const bool has_ohos_family = false;
#endif
#if defined(__MUSL__)
    const bool has_musl = true;
#else
    const bool has_musl = false;
#endif
#if defined(__aarch64__)
    const bool has_aarch64 = true;
#else
    const bool has_aarch64 = false;
#endif
    check(has_ohos, "T1a __OHOS__ defined", has_ohos ? "OHOS target" : "not an OHOS target");
    check(has_ohos_family, "T1b __OHOS_FAMILY__ defined", has_ohos_family ? "OHOS family" : "not OHOS family");
    // T1c is diagnostic only: the OHOS Clang does not define __MUSL__ even
    // though it targets musl; the musl verdict is the PT_INTERP check (T4).
    std::printf("[ohos] info T1c __MUSL__ %s — %s\n",
                has_musl ? "defined" : "not defined",
                has_musl ? "musl libc macro present"
                         : "OHOS Clang leaves it undefined; musl proven by T4 PT_INTERP");
    check(has_aarch64, "T1d __aarch64__ defined", has_aarch64 ? "AArch64" : "not AArch64");

    // --- T2: runtime platform identity ------------------------------------
    struct utsname uts;
    const bool un_ok = ::uname(&uts) == 0;
    const std::string sysname = un_ok ? uts.sysname : "<uname failed>";
    check(un_ok && sysname == "HarmonyOS", "T2 uname sysname",
          "sysname='" + sysname + "' (Linux hosts report 'Linux')");

    // --- T3/T4: self ELF identity (ELF64 / AArch64 / musl loader) ---------
    unsigned char ehdr[64];
    Phdr64 interp{};
    std::string interp_str;
    const bool parsed = parse_self_elf(ehdr, &interp, &interp_str);
    const bool elf_magic = parsed && std::memcmp(ehdr, "\x7f""ELF", 4) == 0;
    check(parsed && elf_magic, "T3a self ELF magic", parsed ? "ELF header parsed via /proc/self/exe" : "failed to read /proc/self/exe");
    const int ei_class = parsed ? ehdr[4] : 0;
    check(ei_class == 2, "T3b self is ELF64", "EI_CLASS=" + std::to_string(ei_class) + " (2=ELF64)");
    const int ei_data = parsed ? ehdr[5] : 0;
    check(ei_data == 1, "T3c self is little-endian", "EI_DATA=" + std::to_string(ei_data) + " (1=LSB)");
    const uint16_t e_machine = parsed ? rd16(ehdr + 0x12) : 0;
    check(e_machine == kEmAarch64, "T3d self e_machine == EM_AARCH64",
          "e_machine=" + std::to_string(e_machine) + " (183=AArch64)");
    const uint16_t e_type = parsed ? rd16(ehdr + 0x10) : 0;
    std::printf("[ohos] info self e_type=%u (3=ET_DYN PIE)\n", e_type);

    const bool interp_found = parsed && interp.p_type == kPtInterp;
    check(interp_found && interp_str == "/lib/ld-musl-aarch64.so.1",
          "T4 self PT_INTERP == /lib/ld-musl-aarch64.so.1",
          interp_found ? "interpreter='" + interp_str + "' (OHOS musl loader)" : "no PT_INTERP found");

    // --- T5: OHOS-target libmecab really loads the packaged indices -------
    mecab_t *mecab = mecab_new2(("-d " + dicdir + " -r " + rcfile).c_str());
    check(mecab != nullptr, "T5 OHOS libmecab loads packaged UniDic indices",
          mecab != nullptr ? "mecab_new2(-d <pkg>/res/unidic) OK" :
          std::string("mecab_new2 failed: ") + mecab_strerror(nullptr));
    if (mecab == nullptr) {
        std::printf("=== HARMONYOS-SPECIFIC TEST FAILED (%d passed, %d failed) ===\n", g_pass, g_fail);
        return 1;
    }
    std::printf("mecab version: %s (OHOS aarch64 build)\n", mecab_version());

    // --- T6: loaded index stats == official UniDic 2.1.2 release ----------
    const mecab_dictionary_info_t *di = mecab_dictionary_info(mecab);
    check(di != nullptr, "T6a dictionary_info available", di != nullptr ? "sys.dic loaded" : "null");
    if (di != nullptr) {
        check(std::string(di->charset) == "utf8", "T6b index charset == utf8",
              std::string("charset=") + di->charset);
        check(di->size == 756463, "T6c index size == 756463 lexemes",
              "size=" + std::to_string(di->size) + " (official 2.1.2 lex.csv entries)");
        check(di->lsize == 5981 && di->rsize == 5981, "T6d matrix == 5981x5981",
              "lsize=" + std::to_string(di->lsize) + " rsize=" + std::to_string(di->rsize));
    }

    // --- T7: loaded indices actually tokenize ------------------------------
    const char *result = mecab_sparse_tostr(mecab, "すもももももももものうち");
    const std::string out = result != nullptr ? result : "";
    check(result != nullptr && out.find("すもも") != std::string::npos && out.find("EOS") != std::string::npos,
          "T7 OHOS-loaded indices tokenize",
          result != nullptr ? "すもも… tokenized with EOS" : "mecab_sparse_tostr failed");
    mecab_destroy(mecab);

    if (g_fail != 0) {
        std::printf("=== HARMONYOS-SPECIFIC TEST FAILED (%d passed, %d failed) ===\n", g_pass, g_fail);
        return 1;
    }
    std::printf("=== HARMONYOS-SPECIFIC TEST PASSED (%d checks, 0 failed) ===\n", g_pass);
    return 0;
}
