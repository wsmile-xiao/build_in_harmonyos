#include <pxr/base/gf/vec3d.h>
#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/gf/rotation.h>
#include <pxr/base/arch/errno.h>
#include <pxr/base/tf/getenv.h>

#include <cerrno>
#include <iostream>
#include <string>

int main() {
    // Gf: vector math
    pxr::GfVec3d v(1.0, 2.0, 3.0);
    if (v[0] != 1.0 || v[1] != 2.0 || v[2] != 3.0) {
        std::cerr << "FAIL: GfVec3d value mismatch" << std::endl;
        return 1;
    }

    // Gf: matrix determinant (identity scaled by 2)
    pxr::GfMatrix4d m(2.0);
    if (m.GetDeterminant() != 16.0) {
        std::cerr << "FAIL: GfMatrix4d determinant mismatch: "
                  << m.GetDeterminant() << std::endl;
        return 1;
    }

    // Gf: rotation
    pxr::GfRotation rot(pxr::GfVec3d::ZAxis(), 90.0);
    pxr::GfVec3d rotated = rot.TransformDir(pxr::GfVec3d::XAxis());
    if (std::abs(rotated[1] - 1.0) > 1e-9) {
        std::cerr << "FAIL: GfRotation transform mismatch" << std::endl;
        return 1;
    }

    // Arch: exercise errno handling (patched POSIX strerror_r path on OHOS)
    std::string err = pxr::ArchStrerror(ENOENT);
    if (err.empty()) {
        std::cerr << "FAIL: ArchStrerror returned empty string" << std::endl;
        return 1;
    }

    // Tf: getenv from foundation library
    std::string path = pxr::TfGetenv("PATH", "");
    if (path.empty()) {
        std::cerr << "FAIL: TfGetenv(PATH) returned empty" << std::endl;
        return 1;
    }

    std::cout << "pxr-gf smoke test: OK (ArchStrerror(ENOENT)=\"" << err
              << "\")" << std::endl;
    return 0;
}
