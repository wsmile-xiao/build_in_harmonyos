// Test program for nuspell 5.1.8
// Verifies the nuspell library can be linked and its API is callable
#include <nuspell/dictionary.hxx>
#include <nuspell/finder.hxx>
#include <nuspell/suggester.hxx>
#include <iostream>

int main() {
    // Test basic API availability - verify library symbols are linked
    // nuspell::Dictionary and related classes are the core API
    try {
        // Try to create a finder instance (will not find dictionaries but tests linking)
        nuspell::Dictionary dict;
        // If we get here without linker errors, the test passes
        std::cout << "nuspell library linked successfully" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        // Exception is fine - we just need to verify linking works
        std::cout << "nuspell library linked, exception (expected): " << e.what() << std::endl;
        return 0;
    }
}
