#include <gpgme++/error.h>
#include <gpgme.h>
#include <qgpgme/protocol.h>
#include <QCoreApplication>
#include <iostream>
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    GpgME::Error error;
    const char *version = gpgme_check_version(nullptr);
    if (!version || QGpgME::cryptoConfig() == nullptr) return 1;
    std::cout << "Gpgmepp and QGpgmeQt6 linked; GPGME " << version << "; OpenPGP protocol "
              << 1 << "; error=" << error.code() << "\n";
    return 0;
}
