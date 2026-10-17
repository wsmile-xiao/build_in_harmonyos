#include <QSerialPort>
#include <QSerialPortInfo>
#include <QtGlobal>

#include <cstdio>

int main(int argc, char **argv)
{
    Q_UNUSED(argc);
    Q_UNUSED(argv);

    // QSerialPortInfo: enumerate available serial ports. This is the primary
    // public entry point of Qt SerialPort and exercises the platform backend
    // (qserialportinfo_unix.cpp) on HarmonyOS.
    const QList<QSerialPortInfo> ports = QSerialPortInfo::availablePorts();
    for (const QSerialPortInfo &port : ports) {
        const QString name = port.portName();
        const QString desc = port.description();
        const QString vendor = port.vendorIdentifier()
            ? QString::number(port.vendorIdentifier(), 16)
            : QString();
        std::printf("serial port: %s (%s) vendor=0x%s\n",
                    name.toUtf8().constData(),
                    desc.toUtf8().constData(),
                    vendor.toUtf8().constData());
    }

    // QSerialPortInfo: constructors / accessors must work even with no
    // physical serial device present on the device under test.
    QSerialPortInfo emptyInfo;
    if (!emptyInfo.portName().isEmpty())
        return 1;

    // QSerialPort: construct a port object bound to a (possibly absent)
    // device and verify error reporting works end to end.
    QSerialPort port;
    if (port.isOpen())
        return 2;
    port.setPortName("ttyS0");
    if (port.portName() != "ttyS0")
        return 3;
    const QSerialPort::SerialPortError openError = port.error();
    Q_UNUSED(openError); // error() must be callable without crashing

    std::printf("Qt %s QSerialPort/QSerialPortInfo work, %lld port(s)\n",
                QT_VERSION_STR, static_cast<long long>(ports.size()));
    return 0;
}
