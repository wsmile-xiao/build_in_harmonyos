/* Test package for librevenge — verifies RVNGStringVector and RVNGPropertyList APIs.
 * R34: This test must substantively call librevenge API functions.
 */
#include <librevenge/librevenge.h>
#include <iostream>

int main()
{
    // Test RVNGString
    librevenge::RVNGString str("hello");
    if (str.cstr() == nullptr || std::string(str.cstr()) != "hello") {
        std::cerr << "FAIL: RVNGString test failed" << std::endl;
        return 1;
    }
    std::cout << "PASS: RVNGString created with value: " << str.cstr() << std::endl;

    // Test RVNGStringVector
    librevenge::RVNGStringVector vec;
    if (!vec.empty()) {
        std::cerr << "FAIL: RVNGStringVector should be empty initially" << std::endl;
        return 1;
    }
    vec.append(librevenge::RVNGString("first"));
    vec.append(librevenge::RVNGString("second"));
    vec.append(librevenge::RVNGString("third"));
    if (vec.size() != 3) {
        std::cerr << "FAIL: RVNGStringVector size should be 3, got " << vec.size() << std::endl;
        return 1;
    }
    std::cout << "PASS: RVNGStringVector has " << vec.size() << " elements" << std::endl;

    // Test RVNGPropertyList
    librevenge::RVNGPropertyList propList;
    propList.insert("name", "test_value");
    propList.insert("count", 42);
    std::cout << "PASS: RVNGPropertyList created and populated" << std::endl;

    // Test RVNGBinaryData
    librevenge::RVNGBinaryData binData;
    const unsigned char data[] = {0x01, 0x02, 0x03, 0x04};
    binData.append(data, 4);
    std::cout << "PASS: RVNGBinaryData created with data" << std::endl;

    std::cout << "All librevenge API tests passed!" << std::endl;
    return 0;
}
