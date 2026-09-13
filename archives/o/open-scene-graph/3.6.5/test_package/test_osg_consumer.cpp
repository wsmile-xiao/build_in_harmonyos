#include <cstdio>
#include <string>

#include <osg/Version>
#include <osgDB/Registry>
#include <OpenThreads/Thread>

int main()
{
    // 1. core version API (returns "3.6.5"; osgGetLibraryName returns
    // "OpenSceneGraph Library")
    const char* ver = osgGetVersion();
    std::printf("osgGetVersion() = %s\n", ver);
    std::printf("osgGetLibraryName() = %s\n", osgGetLibraryName());
    std::string expected = "3.6.5";
    if (expected != ver) {
        std::printf("FAIL: version mismatch, expected %s\n", expected.c_str());
        return 1;
    }
    std::string libname = osgGetLibraryName();
    if (libname.find("OpenSceneGraph") == std::string::npos) {
        std::printf("FAIL: library name mismatch: %s\n", libname.c_str());
        return 1;
    }

    // 2. osgDB registry (dynamic plugin manager) - touches libosgDB state
    osgDB::Registry* reg = osgDB::Registry::instance();
    if (reg == nullptr) {
        std::printf("FAIL: osgDB::Registry::instance() returned null\n");
        return 1;
    }

    // 3. OpenThreads runtime
    int numProcessors = OpenThreads::GetNumberOfProcessors();
    std::printf("OpenThreads::GetNumberOfProcessors() = %d\n", numProcessors);
    if (numProcessors < 1) {
        std::printf("FAIL: GetNumberOfProcessors < 1\n");
        return 1;
    }

    std::printf("test_osg_consumer: OK\n");
    return 0;
}
