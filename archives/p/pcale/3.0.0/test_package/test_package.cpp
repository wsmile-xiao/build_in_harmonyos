#include <ale_message.h>
#include <iostream>

int main() {
    int tests = 0, passed = 0;

    // Test 1: Create MessageAssembler and verify inactive
    tests++;
    ale::MessageAssembler assembler;
    if (!assembler.is_active()) passed++;
    else std::cerr << "FAIL Test 1: MessageAssembler should be inactive on construction" << std::endl;

    // Test 2: Create another MessageAssembler (independent default construction)
    tests++;
    ale::MessageAssembler assembler2;
    if (!assembler2.is_active()) passed++;
    else std::cerr << "FAIL Test 2: second MessageAssembler should be inactive on construction" << std::endl;

    // Test 3: Verify MessageAssembler doesn't throw
    tests++;
    try {
        ale::MessageAssembler a3;
        passed++;
    } catch (const std::exception& e) {
        std::cerr << "FAIL Test 3: MessageAssembler construction threw: " << e.what() << std::endl;
    } catch (...) {
        std::cerr << "FAIL Test 3: MessageAssembler construction threw unknown exception" << std::endl;
    }

    std::cout << "PC-ALE tests: " << passed << "/" << tests << " passed" << std::endl;
    return passed == tests ? 0 : 1;
}
