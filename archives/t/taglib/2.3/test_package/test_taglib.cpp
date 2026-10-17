#include <taglib/tstring.h>
#include <taglib/tbytevector.h>

#include <iostream>

int main() {
    const TagLib::String text("HarmonyOS", TagLib::String::UTF8);
    if (text.to8Bit(true) != "HarmonyOS") {
        std::cerr << "TagLib::String UTF-8 conversion failed\n";
        return 1;
    }

    const TagLib::ByteVector bytes("abc", 3);
    if (bytes.size() != 3 || bytes[1] != 'b') {
        std::cerr << "TagLib::ByteVector validation failed\n";
        return 2;
    }
    return 0;
}
