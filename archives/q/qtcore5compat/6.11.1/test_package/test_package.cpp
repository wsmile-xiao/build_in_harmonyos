#include <QLinkedList>
#include <QRegExp>
#include <QStringRef>
#include <QTextCodec>
#include <QtCore/QString>
#include <QtCore/QCoreApplication>
#include <cstdio>

// Consumer test for the Qt Core5Compat module on HarmonyOS PC.
// Exercises Qt 5 compatibility APIs that Qt 6 moved into Qt6Core5Compat:
// QRegExp, QLinkedList, QStringRef and QTextCodec.

static int failures = 0;

#define CHECK(cond, name)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("[PASS] %s\n", name);                                  \
        } else {                                                               \
            std::printf("[FAIL] %s\n", name);                                  \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. QRegExp (Qt5-style regexp engine, removed from Qt6 Core).
    QRegExp rx(QStringLiteral("^(\\d{4})-(\\d{2})-(\\d{2})$"));
    const QString date = QStringLiteral("2026-08-12");
    CHECK(rx.isValid(), "QRegExp::isValid");
    CHECK(rx.exactMatch(date), "QRegExp::exactMatch");
    CHECK(rx.cap(1) == QStringLiteral("2026"), "QRegExp::cap(year)");
    CHECK(rx.cap(2) == QStringLiteral("08"), "QRegExp::cap(month)");
    CHECK(rx.cap(3) == QStringLiteral("12"), "QRegExp::cap(day)");
    // indexIn performs a substring search, so the pattern must not be
    // anchored with ^/$.
    QRegExp rxSearch(QStringLiteral("\\d{4}-\\d{2}-\\d{2}"));
    CHECK(rxSearch.indexIn(QStringLiteral("prefix 2026-08-12 suffix")) == 7,
          "QRegExp::indexIn");

    // 2. QLinkedList (Qt5 container moved to Core5Compat).
    QLinkedList<int> list;
    list.append(3);
    list.append(1);
    list.append(4);
    CHECK(list.size() == 3, "QLinkedList::size");
    CHECK(list.first() == 3, "QLinkedList::first");
    CHECK(list.last() == 4, "QLinkedList::last");
    int sum = 0;
    for (int value : list)
        sum += value;
    CHECK(sum == 8, "QLinkedList iteration");

    // 3. QStringRef (Qt5 string view, removed from Qt6 Core).
    const QString haystack = QStringLiteral("open harmony os");
    const QStringRef ref(&haystack, 5, 7);
    CHECK(ref.toString() == QStringLiteral("harmony"), "QStringRef slice");
    CHECK(ref.size() == 7, "QStringRef::size");
    CHECK(ref.startsWith(QStringLiteral("harm")), "QStringRef::startsWith");

    // 4. QTextCodec (Qt5 text codec registry).
    if (QTextCodec::codecForName("UTF-8"))
        std::printf("[INFO] QTextCodec UTF-8 available\n");
    else
        std::printf("[INFO] QTextCodec UTF-8 unavailable (built-in default)\n");
    CHECK(QTextCodec::availableCodecs().size() > 0
              || QTextCodec::codecForName("UTF-8"),
          "QTextCodec registry accessible");

    std::printf("qtcore5compat consumer test: %s\n",
                failures == 0 ? "ALL PASSED" : "FAILED");
    return failures == 0 ? 0 : 1;
}
