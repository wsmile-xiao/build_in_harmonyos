#include <apngasm.h>
#include <iostream>

int main() {
    apngasm::APNGAsm asm_obj;
    const char* ver = asm_obj.version();
    std::cout << "apngasm version: " << ver << std::endl;
    if (ver == nullptr || ver[0] == '\0') {
        std::cerr << "ERROR: version() returned empty string" << std::endl;
        return 1;
    }
    std::cout << "apngasm library test PASSED" << std::endl;
    return 0;
}
