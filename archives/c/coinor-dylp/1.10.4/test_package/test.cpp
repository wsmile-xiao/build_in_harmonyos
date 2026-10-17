#include <cstdio>

// dylp.h is a C header without extern "C" guards; wrap it for C++.
// dy_isscaled() etc. live under #ifdef DYLP_INTERNAL (internal-only);
// dy_defaults() is public API that allocates default options/tolerances.
extern "C" {
#include <coin/dylp.h>
}

int main() {
    lpopts_struct *opts = nullptr;
    lptols_struct *tols = nullptr;
    /* 调用 DyLP 核心公开 API，验证链接与运行 */
    dy_defaults(&opts, &tols);
    if (opts == nullptr || tols == nullptr) {
        std::printf("test coinor-dylp 1.10.4: dy_defaults() failed\n");
        return 1;
    }
    if (tols->inf < 1.0e300) {
        std::printf("test coinor-dylp 1.10.4: tol inf sanity failed\n");
        return 2;
    }
    std::printf("test coinor-dylp 1.10.4: OK\n");
    return 0;
}
