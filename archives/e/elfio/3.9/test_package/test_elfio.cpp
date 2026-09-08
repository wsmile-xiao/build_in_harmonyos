#include <elfio/elfio.hpp>
#include <iostream>
#include <cstdlib>

using namespace ELFIO;

int main(void) {
    // Test 1: Create a new ELF file in memory (header-only API)
    elfio writer;
    writer.create(ELFCLASS64, ELFDATA2LSB);
    writer.set_os_abi(ELFOSABI_LINUX);
    writer.set_type(ET_EXEC);
    writer.set_machine(EM_X86_64);

    // Test 2: Add a section
    section* text_sec = writer.sections.add(".text");
    if (!text_sec) {
        std::cerr << "FAIL: Failed to add .text section" << std::endl;
        return 1;
    }
    text_sec->set_type(SHT_PROGBITS);
    text_sec->set_flags(SHF_ALLOC | SHF_EXECINSTR);
    text_sec->set_addr_align(0x10);

    // Add code bytes (x86-64 ret instruction)
    char code[] = {(char)0xC3};
    text_sec->set_data(code, sizeof(code));

    // Test 3: Save to file (check return value)
    const char* filename = "test_output.elf";
    if (!writer.save(filename)) {
        std::cerr << "FAIL: Failed to save ELF file" << std::endl;
        return 1;
    }

    // Test 4: Read back the ELF file we just created
    elfio reader;
    if (!reader.load(filename)) {
        std::cerr << "FAIL: Failed to load the ELF file we just created" << std::endl;
        return 1;
    }

    // Test 5: Verify the ELF properties
    if (reader.get_class() != ELFCLASS64) {
        std::cerr << "FAIL: Expected ELFCLASS64" << std::endl;
        return 1;
    }
    if (reader.get_encoding() != ELFDATA2LSB) {
        std::cerr << "FAIL: Expected ELFDATA2LSB" << std::endl;
        return 1;
    }
    if (reader.get_machine() != EM_X86_64) {
        std::cerr << "FAIL: Expected EM_X86_64" << std::endl;
        return 1;
    }

    // Test 6: Verify section count matches
    if (reader.sections.size() != writer.sections.size()) {
        std::cerr << "FAIL: Section count mismatch" << std::endl;
        return 1;
    }

    // Test 7: Find .text section and verify content
    section* read_text = reader.sections[".text"];
    if (read_text == nullptr) {
        std::cerr << "FAIL: .text section not found in reader" << std::endl;
        return 1;
    }
    if (read_text->get_type() != SHT_PROGBITS) {
        std::cerr << "FAIL: .text section type mismatch" << std::endl;
        return 1;
    }

    // Test 8: Check ELFIO version
    std::string version = ELFIO_VERSION;
    if (version != "3.9") {
        std::cerr << "FAIL: Expected version 3.9, got " << version << std::endl;
        return 1;
    }

    std::cout << "ELFIO version: " << ELFIO_VERSION << std::endl;
    std::cout << "All ELFIO API tests passed!" << std::endl;
    return 0;
}
