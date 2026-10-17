#include <cstdlib>
#include <iostream>
#include <string>
#include "mini_chromium/base/logging.h"
#include "mini_chromium/base/strings/stringprintf.h"
#include "mini_chromium/base/files/file_path.h"
#include "mini_chromium/base/strings/string_number_conversions.h"

int main() {
    std::string formatted = base::StringPrintf("Hello %s %d", "World", 42);
    if (formatted != "Hello World 42") { std::cerr << "FAIL: StringPrintf" << std::endl; return 1; }
    base::FilePath path("/tmp/test/file.txt");
    if (path.DirName().value() != "/tmp/test") { std::cerr << "FAIL: DirName" << std::endl; return 1; }
    if (path.BaseName().value() != "file.txt") { std::cerr << "FAIL: BaseName" << std::endl; return 1; }
    int number = 0;
    if (!base::StringToInt("12345", &number) || number != 12345) { std::cerr << "FAIL: StringToInt" << std::endl; return 1; }
    if (logging::GetMinLogLevel() != logging::LOG_INFO) { std::cerr << "FAIL: GetMinLogLevel" << std::endl; return 1; }
    std::cout << "All tests passed!" << std::endl;
    return 0;
}
