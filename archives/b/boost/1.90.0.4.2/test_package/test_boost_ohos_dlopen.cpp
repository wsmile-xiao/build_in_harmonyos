// OHOS-specific consumer for boost/1.90.0.4.2.
//
// Validates the real OHOS deployment contract of the package shared libraries:
//   - every compiled component lib (libboost_*.so) can be dlopen()'d with
//     RTLD_NOW (signature/codesign + relocation must succeed on the OHOS
//     loader — this is what breaks with stale/missing .codesign on HMDFS),
//   - a real exported symbol is dlsym()'d from each lib and actually CALLED
//     (not just resolved), proving the library body is loadable and callable.
//
// The package lib directory is supplied via BOOST_PACKAGE_LIB_DIR (set by
// test_package/conanfile.py test() from the Conan package_folder).
//
// Chosen per-lib symbols are no-argument functions exported by the OHOS build
// (verified with llvm-nm -D); the only exception is libboost_container's
// dlmalloc_malloc(size_t), which we round-trip with dlmalloc_free(void*).

#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

namespace {

typedef void (*NoArgFn)();
typedef void *(*MallocFn)(std::size_t);
typedef void (*FreeFn)(void *);

const char *g_lib_dir = nullptr;

int dlopen_call_atomic() {
    void *h = dlopen((std::string(g_lib_dir) + "/libboost_atomic.so").c_str(), RTLD_NOW);
    if (!h) { std::fprintf(stderr, "FAIL dlopen libboost_atomic.so: %s\n", dlerror()); return 1; }
    void *s = dlsym(h, "_ZN5boost7atomics6detail9lock_pool12signal_fenceEv");
    if (!s) { std::fprintf(stderr, "FAIL dlsym atomic lock_pool::signal_fence: %s\n", dlerror()); return 1; }
    reinterpret_cast<NoArgFn>(s)();  // call it
    std::printf("OK  libboost_atomic.so  -> boost::atomics::detail::lock_pool::signal_fence() called\n");
    return 0;
}

int dlopen_call_container() {
    void *h = dlopen((std::string(g_lib_dir) + "/libboost_container.so").c_str(), RTLD_NOW);
    if (!h) { std::fprintf(stderr, "FAIL dlopen libboost_container.so: %s\n", dlerror()); return 1; }
    MallocFn m = reinterpret_cast<MallocFn>(dlsym(h, "_ZN5boost9container15dlmalloc_mallocEm"));
    FreeFn f = reinterpret_cast<FreeFn>(dlsym(h, "_ZN5boost9container13dlmalloc_freeEPv"));
    if (!m || !f) { std::fprintf(stderr, "FAIL dlsym container dlmalloc_malloc/free: %s\n", dlerror()); return 1; }
    void *p = m(256);  // call malloc
    if (!p) { std::fprintf(stderr, "FAIL container dlmalloc_malloc(256) returned NULL\n"); return 1; }
    f(p);              // call free
    std::printf("OK  libboost_container.so -> boost::container::dlmalloc_malloc(256)/dlmalloc_free round-trip\n");
    return 0;
}

int dlopen_call_filesystem() {
    void *h = dlopen((std::string(g_lib_dir) + "/libboost_filesystem.so").c_str(), RTLD_NOW);
    if (!h) { std::fprintf(stderr, "FAIL dlopen libboost_filesystem.so: %s\n", dlerror()); return 1; }
    void *s = dlsym(h, "_ZN5boost10filesystem16filesystem_error14get_empty_pathEv");
    if (!s) { std::fprintf(stderr, "FAIL dlsym filesystem filesystem_error::get_empty_path: %s\n", dlerror()); return 1; }
    reinterpret_cast<NoArgFn>(s)();  // call it (returns const path&, ignored)
    std::printf("OK  libboost_filesystem.so -> boost::filesystem::filesystem_error::get_empty_path() called\n");
    return 0;
}

int dlopen_call_program_options() {
    void *h = dlopen((std::string(g_lib_dir) + "/libboost_program_options.so").c_str(), RTLD_NOW);
    if (!h) { std::fprintf(stderr, "FAIL dlopen libboost_program_options.so: %s\n", dlerror()); return 1; }
    void *s = dlsym(h, "_ZN5boost15program_options11bool_switchEv");
    if (!s) { std::fprintf(stderr, "FAIL dlsym program_options bool_switch: %s\n", dlerror()); return 1; }
    reinterpret_cast<NoArgFn>(s)();  // call it (returns typed_value<bool>*, ignored)
    std::printf("OK  libboost_program_options.so -> boost::program_options::bool_switch() called\n");
    return 0;
}

int dlopen_call_unit_test_framework() {
    void *h = dlopen((std::string(g_lib_dir) + "/libboost_unit_test_framework.so").c_str(), RTLD_NOW);
    if (!h) { std::fprintf(stderr, "FAIL dlopen libboost_unit_test_framework.so: %s\n", dlerror()); return 1; }
    void *s = dlsym(h, "_ZN5boost9unit_test9framework12test_abortedEv");
    if (!s) { std::fprintf(stderr, "FAIL dlsym unit_test framework::test_aborted: %s\n", dlerror()); return 1; }
    reinterpret_cast<NoArgFn>(s)();  // call it
    std::printf("OK  libboost_unit_test_framework.so -> boost::unit_test::framework::test_aborted() called\n");
    return 0;
}

}  // namespace

int main() {
    g_lib_dir = std::getenv("BOOST_PACKAGE_LIB_DIR");
    if (!g_lib_dir || !*g_lib_dir) {
        std::fprintf(stderr, "BOOST_PACKAGE_LIB_DIR is not set; cannot locate package libraries\n");
        return 2;
    }

    int failures = 0;
    failures += dlopen_call_atomic();
    failures += dlopen_call_container();
    failures += dlopen_call_filesystem();
    failures += dlopen_call_program_options();
    failures += dlopen_call_unit_test_framework();

    if (failures) {
        std::fprintf(stderr, "test_boost_ohos_dlopen: %d component(s) FAILED\n", failures);
        return 1;
    }
    std::printf("test_boost_ohos_dlopen: all 5 compiled component libraries dlopen+dlsym+call OK\n");
    return 0;
}
