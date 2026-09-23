// HarmonyOS 专项测试：ELFIO 在 OHOS aarch64 平台上的真实可执行验证
// 1) 解析本机真实 OHOS aarch64 ELF 可执行文件（默认取 OHOS SDK clang），
//    验证 ELFCLASS64/ELFDATA2LSB/EM_AARCH64 及 section/segment 结构可读；
// 2) 创建 aarch64 ELF 并回写/读回（round-trip），验证写路径。
#include <elfio/elfio.hpp>
#include <iostream>
#include <cstdlib>
#include <cstring>

using namespace ELFIO;

// ELFIO 3.9 的 elf_types.hpp 未定义 EM_AARCH64（0xB7 = 183）
#ifndef EM_AARCH64
#define EM_AARCH64 183
#endif

int main(int argc, char* argv[]) {
    // 默认解析本进程自身（/proc/self/exe 恒为真实 OHOS aarch64 ELF；
    // 注意 /data/service/hnp/bin/clang 是 shell 包装脚本而非 ELF）
    const char* target = (argc > 1) ? argv[1] : "/proc/self/exe";
    int failed = 0;

    // ── 1. 解析真实 OHOS aarch64 ELF 可执行文件 ──
    elfio reader;
    if (!reader.load(target)) {
        std::cerr << "FAIL: cannot load real OHOS ELF: " << target << std::endl;
        return 1;
    }
    std::cout << "Loaded real OHOS ELF: " << target << std::endl;
    std::cout << "  class=" << (int)reader.get_class()
              << " encoding=" << (int)reader.get_encoding()
              << " machine=0x" << std::hex << reader.get_machine() << std::dec
              << " type=" << reader.get_type() << std::endl;

    if (reader.get_class() != ELFCLASS64) {
        std::cerr << "FAIL: expected ELFCLASS64 on OHOS aarch64" << std::endl;
        failed = 1;
    }
    if (reader.get_encoding() != ELFDATA2LSB) {
        std::cerr << "FAIL: expected ELFDATA2LSB" << std::endl;
        failed = 1;
    }
    if (reader.get_machine() != EM_AARCH64) {
        std::cerr << "FAIL: expected EM_AARCH64 on OHOS aarch64, got 0x"
                  << std::hex << reader.get_machine() << std::dec << std::endl;
        failed = 1;
    }
    if (reader.sections.size() == 0 || reader.segments.size() == 0) {
        std::cerr << "FAIL: real OHOS ELF has no sections/segments" << std::endl;
        failed = 1;
    } else {
        std::cout << "  sections=" << reader.sections.size()
                  << " segments=" << reader.segments.size() << std::endl;
        // 至少一个具名 section（.text/.data 等）
        bool named = false;
        for (int i = 0; i < (int)reader.sections.size(); ++i) {
            if (reader.sections[i]->get_name().size() > 0) { named = true; break; }
        }
        if (!named) {
            std::cerr << "FAIL: no named sections found" << std::endl;
            failed = 1;
        }
    }

    // ── 2. 创建 aarch64 ELF 并回写/读回 ──
    elfio writer;
    writer.create(ELFCLASS64, ELFDATA2LSB);
    writer.set_os_abi(ELFOSABI_LINUX);
    writer.set_type(ET_EXEC);
    writer.set_machine(EM_AARCH64);

    section* text_sec = writer.sections.add(".text");
    if (!text_sec) {
        std::cerr << "FAIL: cannot add .text section" << std::endl;
        return 1;
    }
    text_sec->set_type(SHT_PROGBITS);
    text_sec->set_flags(SHF_ALLOC | SHF_EXECINSTR);
    text_sec->set_addr_align(0x10);
    // AArch64 `ret` (0xD65F03C0)
    char code[] = {(char)0xC0, (char)0x03, (char)0x5F, (char)0xD6};
    text_sec->set_data(code, sizeof(code));

    const char* outfile = "test_harmonyos_aarch64.elf";
    if (!writer.save(outfile)) {
        std::cerr << "FAIL: cannot save aarch64 ELF" << std::endl;
        return 1;
    }
    elfio back;
    if (!back.load(outfile)) {
        std::cerr << "FAIL: cannot re-load saved aarch64 ELF" << std::endl;
        return 1;
    }
    if (back.get_class() != ELFCLASS64 || back.get_machine() != EM_AARCH64 ||
        back.sections.size() != writer.sections.size()) {
        std::cerr << "FAIL: round-trip mismatch" << std::endl;
        return 1;
    }
    section* rt = back.sections[".text"];
    if (rt == nullptr || rt->get_type() != SHT_PROGBITS) {
        std::cerr << "FAIL: .text section mismatch after round-trip" << std::endl;
        return 1;
    }
    std::cout << "Round-trip aarch64 ELF OK (" << outfile << ")" << std::endl;

    if (failed) {
        std::cerr << "HarmonyOS special test FAILED" << std::endl;
        return 1;
    }
    std::cout << "HarmonyOS special test PASSED (real OHOS ELF parsed + aarch64 round-trip)" << std::endl;
    return 0;
}
