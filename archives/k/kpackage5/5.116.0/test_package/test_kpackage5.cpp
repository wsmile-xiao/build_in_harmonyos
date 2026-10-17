// Consumer check for the installed KF5Package package: link against
// KF5::Package and exercise KPackage::PackageLoader at run time.
//
// KF5 5.116.0's PackageLoader exposes loadPackageStructure(),
// addKnownPackageStructure(), listPackages() and loadPackage(). There is no
// listPackageStructures() in this release, which is what an earlier revision
// of this test called.
#include <KPackage/Package>
#include <KPackage/PackageLoader>
#include <KPackage/PackageStructure>

#include <KPluginMetaData>

#include <QCoreApplication>
#include <QDebug>
#include <QList>
#include <QString>

#include <cstdio>

namespace {
const char *kUnknownFormat = "KPackage5/ConsumerTestUnknownFormat";

int fail(const char *message)
{
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}
} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. the loader singleton must be constructible
    KPackage::PackageLoader *loader = KPackage::PackageLoader::self();
    if (!loader) {
        return fail("PackageLoader::self() returned null");
    }

    // 2. positive path: a structure registered under a format must come back
    //    out of the same format. This exercises the real registry, not just
    //    a null return, and the loader takes ownership of the structure.
    loader->addKnownPackageStructure(QString::fromLatin1(kUnknownFormat),
                                     new KPackage::PackageStructure());
    KPackage::PackageStructure *found =
        loader->loadPackageStructure(QString::fromLatin1(kUnknownFormat));
    if (!found) {
        return fail("registered package structure could not be loaded back");
    }

    // 3. listing packages for a format nothing ships must be empty, not a crash
    const QList<KPluginMetaData> packages =
        loader->listPackages(QString::fromLatin1(kUnknownFormat));
    if (!packages.isEmpty()) {
        return fail("listPackages returned entries for a format with none");
    }

    // 4. loading a package with no format installed must yield an invalid
    //    Package rather than throwing
    KPackage::Package package =
        loader->loadPackage(QString::fromLatin1(kUnknownFormat));
    if (package.isValid()) {
        return fail("loadPackage of a format with no packages returned a "
                    "valid Package");
    }

    std::printf("PASS: KPackage::PackageLoader registry round-trip OK "
                "(structure registered and reloaded; empty listing and "
                "invalid Package for an uninstalled format)\n");
    return 0;
}
