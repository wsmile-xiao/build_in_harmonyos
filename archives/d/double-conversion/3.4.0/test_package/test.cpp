#include <double-conversion/double-conversion.h>
#include <double-conversion/double-to-string.h>
#include <double-conversion/string-to-double.h>
#include <iostream>

int main() {
    using namespace double_conversion;
    
    // Test: double to string
    const int kFlags = DoubleToStringConverter::UNIQUE_ZERO | DoubleToStringConverter::EMIT_POSITIVE_EXPONENT_SIGN;
    char buffer[256];
    DoubleToStringConverter converter(kFlags, "inf", "nan", 'e', -6, 21, 0, 0);
    StringBuilder builder(buffer, sizeof(buffer));
    bool success = converter.ToShortest(3.14159, &builder);
    if (!success) {
        std::cerr << "Failed to convert double to string" << std::endl;
        return 1;
    }
    std::cout << "double-to-string: 3.14159 -> " << buffer << std::endl;
    
    // Test: string to double
    int processed = 0;
    StringToDoubleConverter s2d_converter(StringToDoubleConverter::ALLOW_HEX, 0.0, 0.0, "inf", "nan");
    double result = s2d_converter.StringToDouble(buffer, builder.position(), &processed);
    std::cout << "string-to-double: " << buffer << " -> " << result << std::endl;
    
    if (result > 3.14 && result < 3.15) {
        std::cout << "TEST PASSED" << std::endl;
        return 0;
    } else {
        std::cerr << "TEST FAILED: expected ~3.14159, got " << result << std::endl;
        return 1;
    }
}
