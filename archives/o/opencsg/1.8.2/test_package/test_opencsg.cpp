// test_package/test_opencsg.cpp — OpenCSG 消费者测试 (Conan L1)
//
// 验证件 test_opencsg 链接已安装的 libopencsg，并实质调用其公开 C++ API：
//   * OPENCSG_VERSION / OPENCSG_VERSION_STRING 版本宏
//   * OpenCSG::Primitive 基类的构造、运算、凸度、包围盒
//   * OpenCSG::setOption / getOption 全局选项
//   * OpenCSG::setContext / getContext 渲染上下文键
//
// 为什么这里不创建 GL context / 不调用 OpenCSG::render()：
//   CI worker 是无头 (headless) 环境，而 render() 需要真实 OpenGL context。
//   OpenCSG 自带的 glad 只在 render() 里才 dlopen 桌面 GL 库 (HarmonyOS 上是
//   libGLv4.so)，因此上述公开 API 可以在无 GL context 的情况下安全验证。
//   真正的 GL 渲染路径验证见 test_opencsg.cpp 末尾的 loader 探针以及
//   test_package/MANIFEST.yml 中记录的设备 shadow CI 计划。
//
// loader 探针会 dlopen HarmonyOS 的 libGLv4.so / libEGL.so 并解析
// glGetString / eglGetProcAddress 符号——这正是 patches/0001 所依赖的
// 平台前提；若设备上不存在这两个库则记为 skip，而不是 fail。

#include <opencsg.h>

#include <cstdio>
#include <cstring>
#include <string>

#if defined(__OHOS__) || defined(__linux__)
#include <dlfcn.h>
#endif

namespace {

int gFailures = 0;

void check(bool ok, const char* what) {
    if (ok) {
        std::printf("  [ok]   %s\n", what);
    } else {
        std::printf("  [FAIL] %s\n", what);
        ++gFailures;
    }
}

// Concrete Primitive: derives from the packaged OpenCSG::Primitive. The base
// constructor and the (virtual) destructor live in libopencsg, so constructing
// it forces a genuine link dependency on the packaged library (R34).
class BoxPrimitive : public OpenCSG::Primitive {
public:
    BoxPrimitive()
        : OpenCSG::Primitive(OpenCSG::Intersection, 1u) {}

    void render() override {}
};

// Probe the platform GL entry libraries the glad patch relies on. This only
// resolves symbols; it never creates a GL context, so it is headless-safe.
void probeGlLoader() {
#if defined(__OHOS__) || defined(__linux__)
    void* gl = ::dlopen("libGLv4.so", RTLD_LAZY | RTLD_LOCAL);
    if (gl == nullptr) {
        std::printf("  [skip] libGLv4.so not present on this system\n");
    } else {
        check(::dlsym(gl, "glGetString") != nullptr,
              "libGLv4.so exports glGetString");
        ::dlclose(gl);
    }

    void* egl = ::dlopen("libEGL.so", RTLD_LAZY | RTLD_LOCAL);
    if (egl == nullptr) {
        std::printf("  [skip] libEGL.so not present on this system\n");
    } else {
        check(::dlsym(egl, "eglGetProcAddress") != nullptr,
              "libEGL.so exports eglGetProcAddress");
        ::dlclose(egl);
    }
#endif
}

} // namespace

int main() {
    std::printf("OpenCSG version: %s (0x%04x)\n",
                OPENCSG_VERSION_STRING, OPENCSG_VERSION);
    check(std::string(OPENCSG_VERSION_STRING) == "OpenCSG 1.8.2",
          "OPENCSG_VERSION_STRING reports 1.8.2");
    check(OPENCSG_VERSION == 0x0182,
          "OPENCSG_VERSION == 0x0182");

    BoxPrimitive prim;

    prim.setOperation(OpenCSG::Subtraction);
    check(prim.getOperation() == OpenCSG::Subtraction,
          "Primitive::setOperation/getOperation round-trips");
    prim.setOperation(OpenCSG::Intersection);
    check(prim.getOperation() == OpenCSG::Intersection,
          "Primitive::setOperation restores Intersection");

    prim.setConvexity(2u);
    check(prim.getConvexity() == 2u,
          "Primitive::setConvexity/getConvexity round-trips");

    prim.setBoundingBox(-1.0f, -1.0f, -1.0f, 1.0f, 1.0f, 1.0f);
    float minx = 0.0f, miny = 0.0f, minz = 0.0f;
    float maxx = 0.0f, maxy = 0.0f, maxz = 0.0f;
    prim.getBoundingBox(minx, miny, minz, maxx, maxy, maxz);
    check(minx == -1.0f && miny == -1.0f && minz == -1.0f &&
              maxx == 1.0f && maxy == 1.0f && maxz == 1.0f,
          "Primitive::setBoundingBox/getBoundingBox round-trips");

    OpenCSG::setOption(OpenCSG::DepthBoundsOptimization,
                       OpenCSG::OptimizationOff);
    check(OpenCSG::getOption(OpenCSG::DepthBoundsOptimization) ==
              OpenCSG::OptimizationOff,
          "setOption/getOption(DepthBoundsOptimization) round-trips");
    OpenCSG::setOption(OpenCSG::AlgorithmSetting, OpenCSG::Goldfeather);
    check(OpenCSG::getOption(OpenCSG::AlgorithmSetting) ==
              OpenCSG::Goldfeather,
          "setOption/getOption(AlgorithmSetting) round-trips");

    OpenCSG::setContext(7);
    check(OpenCSG::getContext() == 7,
          "setContext/getContext round-trips");

    probeGlLoader();

    if (gFailures == 0) {
        std::printf("test_opencsg: PASS\n");
        return 0;
    }
    std::printf("test_opencsg: FAIL (%d assertion(s))\n", gFailures);
    return 1;
}
