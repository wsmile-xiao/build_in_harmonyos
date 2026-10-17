// libelfin consumer test.
//
// Parses its own on-disk image through the installed headers and asserts real
// structural facts: the elf++ side walks the ELF header, section table and
// symbol table, while the dwarf++ side resolves the DWARF sections of the same
// image through its ELF-backed section loader.
//
// Full DWARFv4 *parsing* (dump-tree / dump-lines over the upstream golden
// fixtures) is covered by the upstream test suite, which the recipe runs
// during build(); this consumer test covers the installed headers and both
// installed libraries.

#include <elf++.hh>
#include <dwarf++.hh>

#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <memory>
#include <string>
#include <unistd.h>

#ifndef EXPECT_MACHINE
#define EXPECT_MACHINE 0
#endif

static int checks_passed = 0;
static int checks_failed = 0;

#define CHECK(cond, what)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            ++checks_passed;                                                   \
        } else {                                                               \
            ++checks_failed;                                                   \
            std::fprintf(stderr, "FAIL: %s\n", what);                          \
        }                                                                      \
    } while (0)

int main(int argc, char **argv) {
    const char *path = (argc > 1) ? argv[1] : "/proc/self/exe";

    int fd = ::open(path, O_RDONLY);
    if (fd < 0) {
        std::fprintf(stderr, "cannot open %s: %s\n", path, std::strerror(errno));
        return 2;
    }

    elf::elf ef(elf::create_mmap_loader(fd));
    const auto &ehdr = ef.get_hdr();

    CHECK(ehdr.type == elf::et::dyn || ehdr.type == elf::et::exec,
          "ELF header type is ET_DYN or ET_EXEC");
#if EXPECT_MACHINE
    CHECK(ehdr.machine == EXPECT_MACHINE,
          "ELF header machine matches the build target");
#endif

    std::size_t section_count = 0;
    bool have_text = false;
    std::uint64_t text_size = 0;
    for (auto &sec : ef.sections()) {
        ++section_count;
        if (sec.get_name() == ".text") {
            have_text = true;
            text_size = sec.size();
        }
    }
    CHECK(section_count > 10, "ELF section count is plausible (> 10)");
    CHECK(have_text && text_size > 0, ".text section exists and is non-empty");

    bool have_symtab = false;
    bool main_symbol = false;
    bool main_is_function = false;
    bool main_is_global = false;
    for (auto &sec : ef.sections()) {
        if (sec.get_hdr().type != elf::sht::symtab)
            continue;
        have_symtab = true;
        for (auto sym : sec.as_symtab()) {
            if (sym.get_name() != "main")
                continue;
            main_symbol = true;
            main_is_function = sym.get_data().type() == elf::stt::func;
            main_is_global = sym.get_data().binding() == elf::stb::global;
        }
    }
    CHECK(have_symtab, "ELF symbol table is present");
    CHECK(main_symbol, "symbol table contains main");
    CHECK(main_is_function, "main is a FUNC symbol");
    CHECK(main_is_global, "main is a global symbol");

    std::shared_ptr<dwarf::loader> dloader = dwarf::elf::create_loader(ef);
    CHECK(std::string(dwarf::elf::section_type_to_name(dwarf::section_type::info)) ==
              std::string(".debug_info"),
          "dwarf++ maps section_type::info to .debug_info");

    const struct {
        dwarf::section_type type;
        const char *name;
    } dwarf_sections[] = {
        {dwarf::section_type::info, ".debug_info"},
        {dwarf::section_type::abbrev, ".debug_abbrev"},
        {dwarf::section_type::line, ".debug_line"},
        {dwarf::section_type::str, ".debug_str"},
    };
    for (const auto &want : dwarf_sections) {
        std::size_t size = 0;
        const void *data = dloader->load(want.type, &size);
        if (data == nullptr || size == 0) {
            std::fprintf(stderr, "FAIL: dwarf++ loader cannot resolve %s\n",
                         want.name);
            ++checks_failed;
        } else {
            ++checks_passed;
        }
    }

    if (checks_failed != 0) {
        std::fprintf(stderr, "libelfin consumer test: %d/%d checks failed\n",
                     checks_failed, checks_passed + checks_failed);
        return 1;
    }
    std::printf("libelfin consumer test: %d/%d checks passed\n", checks_passed,
                checks_passed + checks_failed);
    return 0;
}
