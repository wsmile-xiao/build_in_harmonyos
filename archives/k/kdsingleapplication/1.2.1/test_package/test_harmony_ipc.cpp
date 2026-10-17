#include <kdsingleapplication.h>

#include <QtCore/QByteArray>
#include <QtCore/QCoreApplication>
#include <QtCore/QDateTime>
#include <QtCore/QEventLoop>
#include <QtCore/QProcess>
#include <QtCore/QString>
#include <QtCore/QTimer>

int main(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    const QStringList arguments = application.arguments();

    if (arguments.size() == 4 && arguments.at(1) == QStringLiteral("--secondary")) {
        KDSingleApplication secondary(
            arguments.at(2), KDSingleApplication::Option::None);
        if (secondary.isPrimaryInstance())
            return 10;
        return secondary.sendMessageWithTimeout(arguments.at(3).toUtf8(), 5000)
                   ? 0
                   : 11;
    }

    const QString name = QStringLiteral("harmony-pc-kdsa-%1-%2")
                             .arg(QCoreApplication::applicationPid())
                             .arg(QDateTime::currentMSecsSinceEpoch());
    const QByteArray expected("harmony-local-ipc-ok");
    QByteArray received;

    KDSingleApplication primary(name, KDSingleApplication::Option::None);
    if (!primary.isPrimaryInstance())
        return 1;

    QEventLoop loop;
    QTimer timeout;
    QProcess secondary;
    const auto quitWhenComplete = [&]() {
        if (received == expected && secondary.state() == QProcess::NotRunning)
            loop.quit();
    };
    timeout.setSingleShot(true);
    QObject::connect(&timeout, &QTimer::timeout, &loop, &QEventLoop::quit);
    QObject::connect(
        &primary,
        &KDSingleApplication::messageReceived,
        &loop,
        [&](const QByteArray &message) {
            received = message;
            quitWhenComplete();
        });
    QObject::connect(
        &secondary,
        qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
        &loop,
        [&](int, QProcess::ExitStatus) { quitWhenComplete(); });

    secondary.start(
        QCoreApplication::applicationFilePath(),
        {QStringLiteral("--secondary"), name, QString::fromUtf8(expected)});
    if (!secondary.waitForStarted(5000))
        return 2;

    timeout.start(10000);
    loop.exec();
    if (secondary.state() != QProcess::NotRunning) {
        secondary.kill();
        secondary.waitForFinished();
        return 3;
    }
    if (secondary.exitStatus() != QProcess::NormalExit || secondary.exitCode() != 0)
        return 4;
    if (received != expected)
        return 5;
    return 0;
}
