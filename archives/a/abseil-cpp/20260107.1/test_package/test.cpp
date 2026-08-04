#include <absl/strings/str_cat.h>
#include <absl/strings/string_view.h>

#include <cstdio>
#include <string>

int main() {
    const std::string value = absl::StrCat("abseil-cpp ", "20260107.1");
    const absl::string_view view(value);
    if (view != "abseil-cpp 20260107.1") {
        return 1;
    }
    std::printf("%s\n", value.c_str());
    return 0;
}
