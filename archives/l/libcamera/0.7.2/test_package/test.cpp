#include <libcamera/camera_manager.h>
#include <libcamera/pixel_format.h>

#include <cstdlib>
#include <iostream>
#include <string>

int main()
{
    const char *ipa_module_path = std::getenv("LIBCAMERA_IPA_MODULE_PATH");
    const char *ipa_proxy_path = std::getenv("LIBCAMERA_IPA_PROXY_PATH");
    if (!ipa_module_path || !ipa_proxy_path) {
        std::cerr << "libcamera IPA runtime paths are not configured\n";
        return 5;
    }

    const std::string &version = libcamera::CameraManager::version();
    if (version.find("0.7.2") == std::string::npos) {
        std::cerr << "unexpected libcamera version: " << version << '\n';
        return 1;
    }

    libcamera::PixelFormat nv12 = libcamera::PixelFormat::fromString("NV12");
    if (!nv12.isValid() || nv12.toString() != "NV12") {
        std::cerr << "NV12 public pixel-format API failed\n";
        return 2;
    }

    libcamera::CameraManager manager;
    if (manager.start() != 0) {
        std::cerr << "CameraManager::start() failed\n";
        return 3;
    }
    const auto cameras = manager.cameras();
    if (manager.get("__definitely_missing_camera__")) {
        std::cerr << "unexpected camera lookup result\n";
        manager.stop();
        return 4;
    }
    manager.stop();

    std::cout << "libcamera consumer test: version=" << version
              << ", cameras=" << cameras.size()
              << ", ipa_module_path=" << ipa_module_path
              << ", ipa_proxy_path=" << ipa_proxy_path << '\n';
    return 0;
}
