#include <KNSCore/Entry>
#include <cstdio>
#include <QString>

int main() {
    KNSCore::Entry entry;
    entry.setName(QStringLiteral("Akonadi contact theme"));
    entry.setUniqueId(QStringLiteral("akonadi-contact-theme"));
    entry.setStatus(KNSCore::Entry::Installed);

    if (entry.name() != QStringLiteral("Akonadi contact theme") ||
        entry.uniqueId() != QStringLiteral("akonadi-contact-theme") ||
        entry.status() != KNSCore::Entry::Installed) {
        std::fprintf(stderr, "FAIL: KNewStuff entry state mismatch\n");
        return 1;
    }

    std::printf("PASS: KNewStuff entry %s\n", entry.name().toUtf8().constData());
    std::printf("PASS: KNewStuff status %d\n", int(entry.status()));
    return 0;
}
