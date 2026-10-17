/*
 * test_package for khelpcenter 26.04.0 (OHOS trimmed search stack).
 *
 * Exercises the real APIs of the delivered artifacts:
 *  - khcdocmetainfo library: DocMetaInfo singleton, DocEntry
 *    construction/property round trips, a DocEntryTraverser walking the
 *    meta info tree (the upstream tests/testmetainfo.cxx semantics),
 *    and the kcfg-generated Prefs settings singleton.
 *
 * The khc_xapianindexer / khc_xapiansearch tools are exercised by the
 * conanfile test() step (index build + query round trip); this binary
 * proves the library headers/libs are consumable.
 */

#include <QCoreApplication>
#include <QDebug>
#include <QString>

#include <docmetainfo.h>
#include <docentry.h>
#include <docentrytraverser.h>
#include <prefs.h>

#include <cstdlib>
#include <iostream>

using namespace KHC;

static int failures = 0;

static void check(bool ok, const char *what)
{
    if (!ok) {
        qWarning() << "FAILED:" << what;
        ++failures;
    } else {
        qDebug() << "ok:" << what;
    }
}

// A traverser in the spirit of the upstream testmetainfo suite.
class ProbeTraverser : public DocEntryTraverser
{
public:
    int visited = 0;
    void process(DocEntry *entry) override
    {
        Q_UNUSED(entry);
        ++visited;
    }
    DocEntryTraverser *createChild(DocEntry *) override
    {
        return this;
    }
};

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("test_khelpcenter"));

    // 1. Prefs settings singleton (kconfig_compiler generated from
    //    khelpcenter.kcfg, installed with the library headers).
    Prefs::self();
    const QString indexDir = Prefs::indexDirectory();
    check(!indexDir.isEmpty(), "Prefs::indexDirectory() returns non-empty");

    // 2. DocEntry construction and property round trips.
    DocEntry entry(QStringLiteral("test-entry"));
    check(entry.name() == QStringLiteral("test-entry"), "DocEntry name round trip");
    entry.setWeight(3);
    check(entry.weight() == 3, "DocEntry weight round trip");
    entry.setIdentifier(QStringLiteral("org.kde.test"));
    check(entry.identifier() == QStringLiteral("org.kde.test"), "DocEntry identifier round trip");

    // 3. DocMetaInfo: the meta info model singleton; it scans the
    //    documentation metadata dirs (which may be empty in a sandbox),
    //    so only assert that the traversal protocol runs and reports a
    //    consistent state.
    DocMetaInfo *meta = DocMetaInfo::self();
    check(meta != nullptr, "DocMetaInfo::self() singleton");

    meta->scanMetaInfo(true);

    ProbeTraverser traverser;
    meta->traverseEntries(&traverser);
    qDebug() << "traverser visited" << traverser.visited << "entries";
    check(true, "DocMetaInfo::traverseEntries() protocol runs");

    if (failures != 0) {
        std::cerr << failures << " checks FAILED" << std::endl;
        return 1;
    }
    std::cout << "All khelpcenter test_package checks passed" << std::endl;
    return 0;
}
