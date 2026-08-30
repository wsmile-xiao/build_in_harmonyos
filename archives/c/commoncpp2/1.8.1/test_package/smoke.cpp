// commoncpp2 smoke test: use a real commoncpp2 class (ost::String —
// ost::Thread 是抽象类不能直接实例化)
#include <cc++/string.h>
#include <cstdio>

int main() {
    ost::String s("commoncpp2");
    if (s.length() < 1) return 1;
    printf("commoncpp2 String API OK: %s\n", (const char *)s);
    return 0;
}
