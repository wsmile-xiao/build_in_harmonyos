/*
 * test_package for gpgme 1.24.0.
 *
 * Verifies the C library, the GpgME++ binding and the Qt 6 binding can be
 * found, linked and loaded without requiring a GnuPG runtime.
 */
#include <cstring>
#include <iostream>

#include <gpgme.h>
#include <gpgme++/global.h>
#include <gpgme++/gpgmepp_version.h>
#include <qgpgme/protocol.h>
#include <qgpgme/qgpgme_version.h>

int main()
{
    const char *version = gpgme_check_version(nullptr);
    if (!version || std::strncmp(version, "1.24", 4) != 0) {
        std::cerr << "FAIL: unexpected gpgme version "
                  << (version ? version : "<null>") << '\n';
        return 1;
    }

    GpgME::initializeLibrary();
    auto qgpgme_openpgp = &QGpgME::openpgp;
    if (!qgpgme_openpgp) {
        std::cerr << "FAIL: QGpgME::openpgp symbol unavailable\n";
        return 1;
    }

    std::cout << "PASS: gpgme " << version << '\n';
    std::cout << "PASS: gpgmepp " << GPGMEPP_VERSION_STRING << '\n';
    std::cout << "PASS: qgpgme " << QGPGME_VERSION_STRING << '\n';
    return 0;
}
