#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <filesystem>
#include <string>
#include <system_error>

int main() {
    void* const handle = dlopen("./" MBITS_LNGS_SHARED_LIBRARY_NAME, RTLD_NOW | RTLD_LOCAL);
    if (handle == nullptr) {
        std::error_code cwd_error;
        std::filesystem::path const cwd = std::filesystem::current_path(cwd_error);
        std::string const cwd_text = cwd_error ? "<unavailable>" : cwd.string();
        std::fprintf(stderr, "dlopen ./%s failed from working directory %s: %s\n",
                     MBITS_LNGS_SHARED_LIBRARY_NAME, cwd_text.c_str(), dlerror());
        return 2;
    }

    using Consumer = int (*)() noexcept;
    void* const symbol = dlsym(handle, "mbits_lngs_shared_consumer");
    Consumer consumer = nullptr;
    static_assert(sizeof(Consumer) == sizeof(void*), "POSIX loader function pointer size mismatch");
    std::memcpy(&consumer, &symbol, sizeof(consumer));
    if (consumer == nullptr) {
        std::fprintf(stderr, "dlsym failed: %s\n", dlerror());
        if (dlclose(handle) != 0) {
            std::fprintf(stderr, "dlclose failed: %s\n", dlerror());
        }
        return 3;
    }

    int const result = consumer();
    if (dlclose(handle) != 0) {
        std::fprintf(stderr, "warning: dlclose failed after consumer completed: %s\n", dlerror());
    }
    if (result != 1) {
        std::fprintf(stderr, "shared consumer returned %d (expected 1)\n", result);
        return 1;
    }
    std::printf("mbits-lngs shared consumer: dlopen+eval(2) ok (returned %d)\n", result);
    return 0;
}
