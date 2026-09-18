// kio 6.14.0 consumer test (R34: exercises real API through libKF6KIOCore).
#include <KIO/UDSEntry>
#include <kprotocolinfo.h>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    // Deterministic KIOCore API roundtrip: UDSEntry field write + read back.
    KIO::UDSEntry entry;
    entry.fastInsert(KIO::UDSEntry::UDS_NAME, QStringLiteral("kio-ohos-smoke"));
    entry.fastInsert(KIO::UDSEntry::UDS_SIZE, static_cast<long long>(1234));
    if (entry.stringValue(KIO::UDSEntry::UDS_NAME)
        != QLatin1String("kio-ohos-smoke")) {
        std::printf("FAIL: UDS_NAME roundtrip mismatch\n");
        return 1;
    }
    if (entry.numberValue(KIO::UDSEntry::UDS_SIZE) != 1234) {
        std::printf("FAIL: UDS_SIZE roundtrip mismatch\n");
        return 1;
    }

    // KProtocolInfo smoke: query the KSycoca-backed protocol registry.
    // The absolute result is environment-dependent (a headless sandbox may
    // have an empty KSycoca), so the call verifies the lookup path executes
    // through KIOCore/KService without asserting on registry contents.
    const bool fileKnown =
        KProtocolInfo::isKnownProtocol(QStringLiteral("file"), false);
    std::printf("KProtocolInfo::isKnownProtocol(file) = %s\n",
                fileKnown ? "true" : "false");

    std::printf("PASS: KIO UDSEntry roundtrip OK\n");
    return 0;
}
