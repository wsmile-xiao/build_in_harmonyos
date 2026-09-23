#include <sass.h>

#include <cstdlib>
#include <cstring>
#include <iostream>

int main() {
    constexpr const char source_text[] = "body { color: #123456; }\n";
    char* source = static_cast<char*>(std::malloc(sizeof(source_text)));
    if (!source) {
        std::cerr << "failed to allocate Sass source\n";
        return 1;
    }
    std::memcpy(source, source_text, sizeof(source_text));
    Sass_Data_Context* data = sass_make_data_context(source);
    if (!data) {
        std::cerr << "sass_make_data_context returned null\n";
        std::free(source);
        return 1;
    }

    const int status = sass_compile_data_context(data);
    Sass_Context* context = sass_data_context_get_context(data);
    const char* output = context ? sass_context_get_output_string(context) : nullptr;
    const bool valid = status == 0 && output && std::strstr(output, "body") &&
                       std::strstr(output, "#123456");
    if (!valid) {
        std::cerr << "LibSass compilation failed: "
                  << (context ? sass_context_get_error_message(context) : "no context")
                  << "\n";
    }
    sass_delete_data_context(data);
    return valid ? 0 : 1;
}
