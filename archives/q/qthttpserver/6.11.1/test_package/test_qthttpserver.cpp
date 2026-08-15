#include <QCoreApplication>
#include <QHttpServer>
#include <QtGlobal>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    QHttpServer server;
    if (!server.serverPorts().isEmpty())
        return 1;
    std::printf("Qt HTTP Server built with Qt %s\n", QT_VERSION_STR);
    return 0;
}
