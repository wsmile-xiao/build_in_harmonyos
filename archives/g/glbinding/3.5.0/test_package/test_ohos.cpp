// test_ohos.cpp — HarmonyOS 专项测试（消费者视角）
//
// 验证 glbinding 在 HarmonyOS PC (aarch64-linux-ohos) 上的真实可用性：
// 1) 通过公开头文件与公开 API 使用 glbinding（Version、aux::Meta）；
// 2) OHOS 运行时集成点：HarmonyOS PC 的系统 GL 实现是 libGLESv3.so /
//    libEGL.so（不存在 Linux 上的 libGL.so）。glbinding 内置 getProcAddress
//    在 Linux 分支 dlopen("libGL.so")，因此 OHOS 消费者必须能自行加载
//    GLES/EGL 运行时并向 glbinding 提供 proc-address 回调——本测试验证
//    这两个系统库可加载且可解析真实入口（eglGetError / glGetString 等）。
#include <dlfcn.h>

#include <glbinding/gl/gl.h>
#include <glbinding/Version.h>
#include <glbinding-aux/Meta.h>

#include <iostream>
#include <string>

int main()
{
    // ── 1) glbinding 公开 API（与 GL 上下文无关）──
    const glbinding::Version v(3, 5);
    if (!(v >= glbinding::Version(3, 5))) {
        std::cerr << "FAIL: Version(3,5) >= Version(3,5) expected true" << std::endl;
        return 1;
    }
    const std::string & s = glbinding::aux::Meta::getString(gl::GL_FALSE);
    std::cout << "Meta::getString(GL_FALSE) = " << s << std::endl;
    if (s != "GL_FALSE") {
        std::cerr << "FAIL: Meta::getString(GL_FALSE) expected 'GL_FALSE'" << std::endl;
        return 2;
    }

    // ── 2) OHOS 系统 GL 运行时加载（GLESv3 + EGL）──
    void * gles = dlopen("/system/lib64/libGLESv3.so", RTLD_LAZY);
    if (!gles) {
        std::cerr << "FAIL: dlopen(/system/lib64/libGLESv3.so): " << dlerror() << std::endl;
        return 3;
    }
    void * egl = dlopen("/system/lib64/libEGL.so", RTLD_LAZY);
    if (!egl) {
        std::cerr << "FAIL: dlopen(/system/lib64/libEGL.so): " << dlerror() << std::endl;
        return 4;
    }
    typedef int (*EglGetErrorFn)();
    typedef const char * (*GlGetStringFn)(unsigned int);
    EglGetErrorFn eglGetError = reinterpret_cast<EglGetErrorFn>(dlsym(egl, "eglGetError"));
    GlGetStringFn glGetString = reinterpret_cast<GlGetStringFn>(dlsym(gles, "glGetString"));
    if (!eglGetError) {
        std::cerr << "FAIL: dlsym(eglGetError): " << dlerror() << std::endl;
        return 5;
    }
    if (!glGetString) {
        std::cerr << "FAIL: dlsym(glGetString from libGLESv3): " << dlerror() << std::endl;
        return 6;
    }
    // eglGetError() 初始应为 EGL_NO_ERROR（EGL 定义 EGL_NO_ERROR = 0x3000 =
    // 12288，注意不是 0）；glGetString 入口可解析即证明 OHOS GLESv3 运行时
    // 符号表可被 glbinding 消费者使用。
    const int err = eglGetError();
    std::cout << "eglGetError() = " << err << " (EGL_NO_ERROR=0x3000)" << std::endl;
    if (err != 0x3000) {
        std::cerr << "FAIL: eglGetError() expected EGL_NO_ERROR (0x3000), got " << err << std::endl;
        return 7;
    }
    std::cout << "glGetString symbol resolved from libGLESv3.so" << std::endl;
    dlclose(egl);
    dlclose(gles);

    std::cout << "glbinding 3.5.0 HarmonyOS-specific test: OK" << std::endl;
    return 0;
}
