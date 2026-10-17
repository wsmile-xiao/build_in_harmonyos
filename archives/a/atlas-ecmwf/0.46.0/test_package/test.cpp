/* test_package/test.cpp — atlas-ecmwf 0.46.0 consumer test (R34 合规)
 *
 * L1 test:
 * 1. 编译并链接 libatlas（含头文件与库）；
 * 2. 运行时调用 atlas::Library::instance().version() 获取版本并断言
 *    非空——真实调用库 API 验证可用。
 */
#include <atlas/library/Library.h>
#include <cstdio>
#include <string>

int main() {
    const std::string version = atlas::Library::instance().version();
    if (version.empty()) {
        std::printf("atlas-ecmwf 0.46.0 consumer test FAILED: "
                    "empty version\n");
        return 1;
    }
    std::printf("atlas-ecmwf 0.46.0 consumer test OK (version %s)\n",
                version.c_str());
    return 0;
}
