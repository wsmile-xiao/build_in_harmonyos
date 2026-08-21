// cairomm test_package：消费者视角验证
// 1) 编译期：#include <cairomm/cairomm.h> 头闭包完整
// 2) 运行期：dlopen libcairomm-1.16.so 可加载
#include <cairomm/cairomm.h>
#include <dlfcn.h>
#include <cstdio>

#ifndef TARGET_SO
#define TARGET_SO "libcairomm-1.16.so"
#endif

int main(void) {
    // 头闭包编译期使用（防止被优化掉）
    auto ctx = Cairo::Context::create(
        Cairo::ImageSurface::create(Cairo::Surface::Format::ARGB32, 4, 4));
    if (!ctx) { std::fprintf(stderr, "cairomm: create context failed\n"); return 1; }

    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { std::fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    std::printf("cairomm: header OK, dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}
