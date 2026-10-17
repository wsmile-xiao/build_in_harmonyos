#include <QCoreApplication>
#include <cprime.h>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // Test 1: Verify CPrime::Variables::CC_CoreApps_ConfigDir() returns a non-empty string
    QString configDir = CPrime::Variables::CC_CoreApps_ConfigDir();
    if (configDir.isEmpty()) {
        return 1;
    }

    // Test 2: Verify CPrime::Variables::CC_CoreApps_BookMarkFile() returns expected value
    QString bookmarkFile = CPrime::Variables::CC_CoreApps_BookMarkFile();
    if (bookmarkFile.isEmpty()) {
        return 2;
    }

    // Test 3: Verify CPrime::AppsName enum is accessible
    int imageApp = CPrime::CoreImage;
    if (imageApp != 0x0002) {
        return 3;
    }

    return 0;
}
