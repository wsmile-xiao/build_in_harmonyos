#include <KPackage/Package>
#include <KPackage/PackageStructure>

#include <QCoreApplication>
#include <QString>

#include <iostream>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    KPackage::Package package(new KPackage::PackageStructure);
    if (!package.hasValidStructure()) {
        std::cerr << "package structure is invalid\n";
        return 1;
    }

    package.addDirectoryDefinition("data", QStringLiteral("contents/data"));
    package.setRequired("data", true);
    package.setDefaultPackageRoot(QStringLiteral("kpackage-test"));

    if (!package.isRequired("data")) {
        std::cerr << "package directory requirement was not retained\n";
        return 1;
    }

    if (package.defaultPackageRoot() != QStringLiteral("kpackage-test/")) {
        std::cerr << "package default root was not retained\n";
        return 1;
    }

    std::cout << "PASS: KPackage structure smoke OK\n";
    return 0;
}
