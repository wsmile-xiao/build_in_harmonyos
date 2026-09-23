/*
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Consumer-side smoke test for libkeduvocdocument 26.04.0 on HarmonyOS PC.
 *
 * It exercises the public API of the *packaged* library end to end:
 *   KEduVocDocument construction -> identifiers -> root lesson -> entry with
 *   two translations -> saveAs(Kvtml) -> open() again and compare.
 * Nothing is stubbed: every assertion below runs against the installed
 * libKEduVocDocument.so.5 / libkeduvocdocument headers.
 *
 * The document is written to a QTemporaryFile created directly in
 * QDir::tempPath() - the same pattern upstream's own
 * keduvocdocument/autotests/keduvocdocumenttest.cpp uses. Writing into a
 * freshly created QTemporaryDir() (mode 0700) instead reproducibly fails on
 * this HarmonyOS 6.0 device: KEduVocDocument::saveAs() cannot create its
 * autosave/lock companion next to the target and returns FileCannotLock
 * ("Cannot lock file <path>"). The shared temporary directory works.
 */

#include <keduvocdocument.h>
#include <keduvoccontainer.h>
#include <keduvocexpression.h>
#include <keduvocidentifier.h>
#include <keduvoclesson.h>
#include <keduvoctranslation.h>

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QTemporaryFile>
#include <QUrl>

#include <cstdio>

static int g_failures = 0;

static void check(bool condition, const char *what)
{
    if (condition) {
        std::printf("  ok   : %s\n", what);
    } else {
        std::printf("  FAIL : %s\n", what);
        ++g_failures;
    }
    std::fflush(stdout);
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    QTemporaryFile tempFile(QDir::tempPath()
                            + QStringLiteral("/libkeduvocdocument-smoke-XXXXXX.kvtml"));
    tempFile.setAutoRemove(false);
    check(tempFile.open(), "temporary KVTML file created in QDir::tempPath()");
    if (!tempFile.isOpen()) {
        return 1;
    }
    const QString path = tempFile.fileName();
    tempFile.close();

    /* 1. build a document through the public API ------------------------- */
    KEduVocDocument doc;
    doc.setTitle(QStringLiteral("OpenDesk OHOS smoke"));

    KEduVocIdentifier english;
    english.setName(QStringLiteral("English"));
    english.setLocale(QStringLiteral("en"));

    KEduVocIdentifier german;
    german.setName(QStringLiteral("German"));
    german.setLocale(QStringLiteral("de"));

    check(doc.appendIdentifier(english) >= 0, "appendIdentifier(English)");
    check(doc.appendIdentifier(german) >= 0, "appendIdentifier(German)");
    check(doc.identifierCount() == 2, "identifierCount() == 2");

    KEduVocLesson *lesson = doc.lesson();
    check(lesson != nullptr, "root lesson available");
    if (!lesson) {
        return 1;
    }

    auto *entry = new KEduVocExpression();
    entry->setTranslation(0, QStringLiteral("hello"));
    entry->setTranslation(1, QStringLiteral("hallo"));
    lesson->appendEntry(entry);
    check(lesson->entryCount() == 1, "root lesson holds one entry");

    /* 2. write KVTML 2.0 -------------------------------------------------- */
    const KEduVocDocument::ErrorCode saved =
        doc.saveAs(QUrl::fromLocalFile(path), KEduVocDocument::Kvtml);
    check(saved == KEduVocDocument::NoError, "saveAs(Kvtml) returns NoError");
    check(QFileInfo(path).size() > 0, "written KVTML file is not empty");

    /* 3. read it back and compare ---------------------------------------- */
    KEduVocDocument reread;
    const KEduVocDocument::ErrorCode opened =
        reread.open(QUrl::fromLocalFile(path), KEduVocDocument::FileOpenReadOnly);
    check(opened == KEduVocDocument::NoError, "open() returns NoError");
    check(reread.title() == doc.title(), "title round trip");
    check(reread.identifierCount() == 2, "identifier count round trip");

    if (reread.identifierCount() == 2) {
        check(reread.identifier(0).locale() == QStringLiteral("en"),
              "identifier 0 locale round trip");
        check(reread.identifier(1).locale() == QStringLiteral("de"),
              "identifier 1 locale round trip");
    } else {
        g_failures += 2;
        std::printf("  FAIL : identifier locale round trip (count != 2)\n");
    }

    KEduVocLesson *rereadLesson = reread.lesson();
    check(rereadLesson != nullptr, "root lesson available after open()");
    KEduVocExpression *rereadEntry = nullptr;
    if (rereadLesson) {
        if (rereadLesson->entryCount() == 1) {
            rereadEntry = rereadLesson->entry(0);
        } else if (rereadLesson->childContainerCount() > 0) {
            /* KVTML2 may nest the entries one level deeper (child lesson). */
            KEduVocContainer *child = rereadLesson->childContainer(0);
            if (child && child->entryCount() == 1) {
                rereadEntry = child->entry(0);
            }
        }
    }
    check(rereadEntry != nullptr, "entry round trip");
    if (rereadEntry) {
        KEduVocTranslation *t0 = rereadEntry->translation(0);
        KEduVocTranslation *t1 = rereadEntry->translation(1);
        check(t0 && t0->text() == QStringLiteral("hello"),
              "translation 0 text round trip");
        check(t1 && t1->text() == QStringLiteral("hallo"),
              "translation 1 text round trip");
    }

    /* 4. the packaged library must be a real, versioned KVTML2 writer ---- */
    check(doc.detectFileType(path) == KEduVocDocument::Kvtml,
          "detectFileType() recognises the produced file as KVTML2");

    if (g_failures == 0) {
        std::printf(
            "libkeduvocdocument test_package: all assertions passed\n");
        return 0;
    }
    std::printf("libkeduvocdocument test_package: %d assertion(s) FAILED\n",
                g_failures);
    return 1;
}
