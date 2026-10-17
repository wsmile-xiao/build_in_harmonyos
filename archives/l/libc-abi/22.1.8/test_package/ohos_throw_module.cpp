// ohos_throw_module.cpp — dlopen 边界测试用的动态模块（test_package 内部构建）
//
// 编译为 libohosthrow.so，导出 ohos_abi_throw()：从 .so 内部抛出异常，由主
// 可执行文件侧 catch。用于验证本包 libc++abi 在鸿蒙动态链接器下：
//   * 静态链接进 .so 时，__cxa_exception 的内存布局与主程序（同样链接本包）
//     一致，异常对象可跨模块边界传递；
//   * .so 的 unwind 表与主程序共用同一套 __cxa_* 实现，不会因重复定义而
//     出现"抛得出、接不住"。
#include <stdexcept>

#if defined(__GNUC__) || defined(__clang__)
#define OHOS_ABI_EXPORT __attribute__((visibility("default")))
#else
#define OHOS_ABI_EXPORT
#endif

extern "C" OHOS_ABI_EXPORT int ohos_abi_throw() {
    throw std::runtime_error("from-dlopen-module");
}

// 二次入口：抛出 std::exception 派生对象（走 __cxa_allocate_exception 的
// 非 runtime_error 分支）。
extern "C" OHOS_ABI_EXPORT const char* ohos_abi_type_name() {
    return "ohos_throw_module";
}
