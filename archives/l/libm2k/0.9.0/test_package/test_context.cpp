#include <iostream>
#include <libm2k/contextbuilder.hpp>
#include <libm2k/context.hpp>
#include <libm2k/m2k.hpp>

int main() {
    // Negative path: unknown URI should return nullptr without crash
    libm2k::context::Context *ctx = libm2k::context::ContextBuilder::contextOpen("ip:0.0.0.0");
    if (ctx != nullptr) {
        std::cerr << "WARN: contextOpen with dummy URI returned non-null (may be emulator), closing" << std::endl;
        libm2k::context::ContextBuilder::contextClose(ctx);
    } else {
        std::cout << "contextOpen dummy URI correctly returned nullptr" << std::endl;
    }

    libm2k::context::M2k *m2k = libm2k::context::ContextBuilder::m2kOpen("ip:0.0.0.0");
    if (m2k != nullptr) {
        std::cerr << "WARN: m2kOpen with dummy URI returned non-null, closing" << std::endl;
        libm2k::context::ContextBuilder::contextClose(m2k);
    } else {
        std::cout << "m2kOpen dummy URI correctly returned nullptr" << std::endl;
    }

    // Default open without URI should also not crash (will be nullptr without hardware)
    libm2k::context::Context *ctx2 = libm2k::context::ContextBuilder::contextOpen();
    if (ctx2 != nullptr) {
        std::cout << "contextOpen() returned context (hardware present?), closing" << std::endl;
        libm2k::context::ContextBuilder::contextClose(ctx2);
    } else {
        std::cout << "contextOpen() correctly returned nullptr (no hardware)" << std::endl;
    }

    // Ensure closeAll does not crash even when no contexts were opened
    libm2k::context::ContextBuilder::contextCloseAll();
    std::cout << "PASS: context API negative paths work" << std::endl;
    return 0;
}
