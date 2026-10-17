#include <astyle_main.h>

#include <cstdlib>
#include <cstring>

namespace {

void report_error(int, const char*) {}

char* allocate(unsigned long size) {
    return static_cast<char*>(std::malloc(size));
}

}  // namespace

int main() {
    const char source[] = "int main(){return 0;}\n";
    const char options[] = "--style=allman\n";

    char* formatted = AStyleMain(source, options, report_error, allocate);
    if (formatted == nullptr || std::strstr(formatted, "{\n") == nullptr) {
        std::free(formatted);
        return 1;
    }
    std::free(formatted);

    const char* version = AStyleGetVersion();
    return version != nullptr && std::strcmp(version, "3.6.18") == 0 ? 0 : 1;
}
