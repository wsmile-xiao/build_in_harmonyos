// test_aeolus.cpp — aeolus 0.10.4 consumer-side plugin smoke test.
//
// dlopen()s the packaged aeolus_txt.so text-mode interface plugin and
// resolves its "create_iface" entry point (the same symbol the aeolus
// binary resolves before starting its user interface). Proves the plugin
// is loadable in the OHOS runtime and exposes its interface factory.
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>

int main(int argc, char *argv[])
{
    if (argc < 2)
    {
        std::fprintf(stderr, "usage: %s <aeolus_txt.so>\n", argv[0]);
        return 2;
    }

    void *handle = dlopen(argv[1], RTLD_NOW);
    if (!handle)
    {
        std::fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    void *create_iface = dlsym(handle, "create_iface");
    if (!create_iface)
    {
        std::fprintf(stderr, "dlsym(create_iface) failed: %s\n", dlerror());
        return 1;
    }

    std::printf("OK: loaded %s, create_iface=%p\n", argv[1], create_iface);
    dlclose(handle);
    return 0;
}
