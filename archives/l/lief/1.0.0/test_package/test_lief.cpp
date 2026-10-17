#include <stdio.h>
#include <string.h>
#include <LIEF/LIEF.hpp>

int main(void) {
    // 构造一个最小的 ELF 头并让 LIEF 解析，验证公开 API 可用
    // ELF header: e_ident(16) + e_type + e_machine + ... (52 bytes for 64-bit)
    static const uint8_t elf_data[] = {
        0x7f, 'E', 'L', 'F', /* ELF magic */
        2,                   /* ELFCLASS64 */
        1,                   /* ELFDATA2LSB */
        1,                   /* EV_CURRENT */
        0, 0,                /* OSABI + abi version */
        0, 0, 0, 0, 0, 0, 0, /* padding */
        3, 0,                /* e_type = ET_DYN */
        0x3e, 0,             /* e_machine = EM_X86_64 */
        1, 0, 0, 0,          /* e_version */
        0, 0, 0, 0, 0, 0, 0, 0, /* e_entry */
    };
    std::vector<uint8_t> content(elf_data, elf_data + sizeof(elf_data));
    content.resize(64, 0);

    auto binary = LIEF::ELF::Parser::parse(content);
    if (binary == nullptr) {
        fprintf(stderr, "FAIL: LIEF::ELF::Parser::parse returned nullptr\n");
        return 1;
    }
    LIEF::ELF::Header::CLASS elf_class = binary->header().identity_class();
    if (elf_class != LIEF::ELF::Header::CLASS::ELF64) {
        fprintf(stderr, "FAIL: unexpected ELF class\n");
        return 1;
    }
    printf("test lief 1.0.0: OK (parsed ELF64, header.entrypoint=0x%llx)\n",
           (unsigned long long)binary->header().entrypoint());
    return 0;
}
