#include <mecab.h>
#include <iostream>

int main() {
    const char *version = mecab_version();
    if (version) {
        std::cout << "mecab version: " << version << std::endl;
        return 0;
    }
    return 1;
}
