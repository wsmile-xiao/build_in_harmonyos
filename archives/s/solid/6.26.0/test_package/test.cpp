#include <Solid/Device>

#include <QCoreApplication>
#include <QDebug>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const QList<Solid::Device> devices =
        Solid::Device::listFromType(Solid::DeviceInterface::Block);
    for (const Solid::Device &device : devices) {
        if (!device.isValid()) {
            qCritical() << "Solid returned an invalid block device";
            return 1;
        }
    }

    qInfo().noquote() << "PASS: Solid block-device query returned" << devices.count()
                      << "valid entries";
    return 0;
}
