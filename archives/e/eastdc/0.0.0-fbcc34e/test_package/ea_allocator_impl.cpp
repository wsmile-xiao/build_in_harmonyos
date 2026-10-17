// eastdc 0.0.0-fbcc34e — test_package 消费者侧要求的 EA 生态分配器符号实现
//
// EAStdC 的 internal/Config.h 声明了一组 user-provided 的调试形式
// operator new/delete（带 name/flags/debugFlags/file/line 参数），注释明确：
// "A user-provided operator new of the following types is required."
// 上游 EAStdC 官方测试主文件（test/source/EAStdCTest.cpp）同样提供这些转发
// 实现（转发到 ::operator new）。这里是消费者/测试侧按该契约提供的实现，
// 不属于被测库本身的内容，也不修改被测库源码。

#include <cstdlib>
#include <cstddef>

void* operator new(size_t size, const char*, int, unsigned, const char*, int)
{
    return ::operator new(size);
}

void* operator new[](size_t size, const char*, int, unsigned, const char*, int)
{
    return ::operator new[](size);
}

void* operator new[](size_t size, size_t, size_t, const char*, int, unsigned, const char*, int)
{
    return ::operator new[](size);
}

void* operator new(size_t size, size_t /*alignment*/, size_t /*alignmentOffset*/,
                   const char* /*name*/, int /*flags*/, unsigned /*debugFlags*/,
                   const char* /*file*/, int /*line*/)
{
    return ::operator new(size);
}

void operator delete(void* p, size_t, size_t, const char*, int, unsigned, const char*, int)
{
    if (p)
        ::operator delete(p);
}

void operator delete(void* p, char const*, int, unsigned, char const*, int)
{
    if (p)
        ::operator delete(p);
}
