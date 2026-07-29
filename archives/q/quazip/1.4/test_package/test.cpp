#include <QuaZip.h>
#include <QuaZipFile.h>
#include <QuaZipNewInfo.h>

#include <QByteArray>
#include <QTemporaryDir>

#include <iostream>

int main() {
    QTemporaryDir temporaryDir;
    if (!temporaryDir.isValid()) {
        std::cerr << "failed to create temporary directory\n";
        return 1;
    }

    const QByteArray expected("QuaZip OpenHarmony round trip");
    const QString archivePath = temporaryDir.filePath("roundtrip.zip");

    QuaZip archive(archivePath);
    if (!archive.open(QuaZip::mdCreate)) {
        std::cerr << "failed to create archive\n";
        return 2;
    }

    QuaZipFile output(&archive);
    if (!output.open(QIODevice::WriteOnly, QuaZipNewInfo("payload.txt")) ||
        output.write(expected) != expected.size()) {
        std::cerr << "failed to write archive entry\n";
        return 3;
    }
    output.close();
    if (output.getZipError() != 0) {
        std::cerr << "failed to close archive entry\n";
        return 4;
    }
    archive.close();
    if (archive.getZipError() != 0) {
        std::cerr << "failed to finalize archive\n";
        return 5;
    }

    if (!archive.open(QuaZip::mdUnzip) ||
        !archive.setCurrentFile("payload.txt")) {
        std::cerr << "failed to reopen archive entry\n";
        return 6;
    }

    QuaZipFile input(&archive);
    if (!input.open(QIODevice::ReadOnly) || input.readAll() != expected) {
        std::cerr << "archive entry content mismatch\n";
        return 7;
    }

    input.close();
    if (input.getZipError() != 0) {
        std::cerr << "failed to close archive input\n";
        return 8;
    }
    archive.close();
    if (archive.getZipError() != 0) {
        std::cerr << "failed to close archive input\n";
        return 9;
    }
    std::cout << "QuaZip round-trip test passed\n";
    return 0;
}
