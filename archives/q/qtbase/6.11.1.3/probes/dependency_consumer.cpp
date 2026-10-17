#include <cstdio>

extern "C" int qtbase_dependency_probe();

int main()
{
    int result = qtbase_dependency_probe();
    if (result) {
        std::fprintf(stderr, "[FAIL] dependency runtime stage=%d\n", result);
        return result;
    }
    std::puts("[PASS] DBus, Expat, OpenSSL, XKB and Wayland shared dependency closure");
    return 0;
}
