#include <QSerialPort>
#include <QSerialPortInfo>
#include <QtGlobal>
#include <cstdio>

int main(int argc, char **argv)
{
    Q_UNUSED(argc);
    Q_UNUSED(argv);

    const QList<QSerialPortInfo> ports = QSerialPortInfo::availablePorts();
    for (const QSerialPortInfo &port : ports) {
        std::printf("serial port: %s\n", port.portName().toUtf8().constData());
    }

    QSerialPortInfo emptyInfo;
    if (!emptyInfo.portName().isEmpty())
        return 1;

    QSerialPort port;
    if (port.isOpen())
        return 2;
    port.setPortName("ttyS0");
    if (port.portName() != "ttyS0")
        return 3;
    const QSerialPort::SerialPortError openError = port.error();
    Q_UNUSED(openError);

    port.setBaudRate(QSerialPort::Baud9600);
    if (port.baudRate() != QSerialPort::Baud9600)
        return 4;

    std::printf("Qt %s QSerialPort/QSerialPortInfo work, %lld port(s)\n",
                QT_VERSION_STR, static_cast<long long>(ports.size()));
    return 0;
}
