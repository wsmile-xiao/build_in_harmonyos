// Consumer test for hexdump 1.0.0 (header-only C++14 library).
// Real consumer verification: includes only the public header hexdump.hpp
// via the installed package and calls the public API:
//   - Hexdump (CustomHexdump<16,true> typedef)
//   - CustomHexdump<8,true>
//   - CustomHexdump<32,false>
//   - CustomHexdumpBase<T,RowSize,ShowAscii>
// Verifies observable hexdump-formatted output lines.
#include "hexdump.hpp"

#include <iostream>
#include <sstream>
#include <string>

static int check(bool ok, const char* what)
{
    std::cout << (ok ? "[PASS] " : "[FAIL] ") << what << std::endl;
    return ok ? 0 : 1;
}

int main()
{
    int failures = 0;

    unsigned char data[150];
    unsigned char c = 0;
    for (auto& val : data)
    {
        val = c++;
    }

    // 1. Default Hexdump (row 16, ASCII on)
    std::ostringstream out1;
    out1 << Hexdump(data, sizeof(data));
    std::string s1 = out1.str();
    // README 示例首行: "0x000000: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  ................"
    failures += check(s1.find("0x000000: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f") != std::string::npos,
                      "Hexdump<16,true> first row bytes");
    failures += check(s1.find("0x000010: 10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f") != std::string::npos,
                      "Hexdump<16,true> second row bytes");
    failures += check(s1.find("0x000080: 80 81 82 83 84 85 86 87 88 89 8a 8b 8c 8d 8e 8f") != std::string::npos,
                      "Hexdump<16,true> last full row");
    failures += check(s1.find("0x000090: 90 91 92 93 94 95") != std::string::npos,
                      "Hexdump<16,true> trailing partial row");
    failures += check(s1.find("....") != std::string::npos, "Hexdump<16,true> ASCII dots for non-printable");
    failures += check(s1.find(" !\"#$%&'()*+,-./") != std::string::npos, "Hexdump<16,true> printable ASCII panel");

    // 2. CustomHexdump<8,true> — row length 8
    std::ostringstream out2;
    out2 << CustomHexdump<8, true>(data, sizeof(data));
    std::string s2 = out2.str();
    failures += check(s2.find("0x000000: 00 01 02 03 04 05 06 07") != std::string::npos,
                      "CustomHexdump<8,true> row width");
    failures += check(s2.find("0x000000: 00 01 02 03 04 05 06 07 08") == std::string::npos,
                      "CustomHexdump<8,true> must NOT exceed 8 bytes per row");

    // 3. CustomHexdump<32,false> — row length 32, ASCII off
    std::ostringstream out3;
    out3 << CustomHexdump<32, false>(data, sizeof(data));
    std::string s3 = out3.str();
    failures += check(s3.find("0x000000: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f 10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f") != std::string::npos,
                      "CustomHexdump<32,false> 32-byte row");
    failures += check(s3.find("0x000000: 00 01 02") != std::string::npos && s3.find("0x000010:") == std::string::npos,
                      "CustomHexdump<32,false> no 0x000010 row (32-byte stride)");

    // 4. CustomHexdumpBase typed template instantiation
    std::ostringstream out4;
    out4 << CustomHexdumpBase<uint8_t, 8, true>(data, 16);
    std::string s4 = out4.str();
    failures += check(s4.find("0x000000: 00 01 02 03 04 05 06 07") != std::string::npos,
                      "CustomHexdumpBase<uint8_t,8,true> works");

    // 5. Empty buffer → no output lines
    std::ostringstream out5;
    out5 << Hexdump(data, 0);
    failures += check(out5.str().empty(), "Hexdump of length 0 emits no lines");

    // 6. getLength() public API
    CustomHexdump<16, true> dump(data, sizeof(data));
    failures += check(dump.getLength() == sizeof(data), "getLength() returns buffer size");

    std::cout << "hexdump consumer test: "
              << (failures == 0 ? "ALL PASS" : "FAILURES") << std::endl;
    return failures == 0 ? 0 : 1;
}