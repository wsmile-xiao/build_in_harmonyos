// solid 6.14.0 consumer test (R34: exercises real API).
// Verifies Solid::Device::listFromType works (returns a list, possibly empty
// in a headless environment, which still proves linking and API usability).
#include <Solid/Device>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const QList<Solid::Device> devices =
        Solid::Device::listFromType(Solid::DeviceInterface::Block);
    // devices.count() returns qsizetype (long long in Qt6); cast to a
    // matching width before printf (P3: avoid %d/qsizetype mismatch).
    std::printf("PASS: Solid::Device::listFromType OK (count=%lld)\n",
                static_cast<long long>(devices.count()));
    return 0;
}
