#include <cstring>
#include <irrlicht.h>

int main() {
    using namespace irr;

    static_assert(sizeof(u32) == 4, "Irrlicht u32 type must be 32-bit");
    if (std::strlen(IRRLICHT_SDK_VERSION) == 0) {
        return 1;
    }

    IrrlichtDevice* device = createDevice(
        video::EDT_NULL,
        core::dimension2d<u32>(16, 16),
        16,
        false,
        false,
        false,
        nullptr);

    if (device == nullptr) {
        return 2;
    }

    video::IVideoDriver* driver = device->getVideoDriver();
    if (driver == nullptr) {
        device->drop();
        return 3;
    }
    if (driver->getDriverType() != video::EDT_NULL) {
        device->drop();
        return 4;
    }

    device->drop();
    return 0;
}
