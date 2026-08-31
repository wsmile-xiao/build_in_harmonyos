// kfilemetadata 6.14.0 consumer test (R34: exercises real API).
// Uses the in-memory SimpleExtractionResult and the PropertyInfo
// introspection API from the core libKF6FileMetaData library.
#include <KFileMetaData/PropertyInfo>
#include <KFileMetaData/Properties>
#include <KFileMetaData/SimpleExtractionResult>

#include <QCoreApplication>
#include <QString>
#include <QVariant>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    // SimpleExtractionResult stores properties/text/types in memory.
    KFileMetaData::SimpleExtractionResult result(
        QStringLiteral("test.txt"), QStringLiteral("text/plain"));
    result.add(KFileMetaData::Property::Title, QStringLiteral("OHOS"));
    result.append(QStringLiteral("full text body"));
    if (result.properties().isEmpty()) {
        std::printf("FAIL: SimpleExtractionResult did not store properties\n");
        return 1;
    }
    if (result.text().isEmpty()) {
        std::printf("FAIL: SimpleExtractionResult did not store text\n");
        return 1;
    }

    // PropertyInfo introspection.
    KFileMetaData::PropertyInfo info(KFileMetaData::Property::Title);
    if (info.property() != KFileMetaData::Property::Title) {
        std::printf("FAIL: PropertyInfo roundtrip mismatch\n");
        return 1;
    }
    if (info.name().isEmpty()) {
        std::printf("FAIL: PropertyInfo::name() is empty\n");
        return 1;
    }

    std::printf("PASS: KFileMetaData SimpleExtractionResult + PropertyInfo OK\n");
    return 0;
}
