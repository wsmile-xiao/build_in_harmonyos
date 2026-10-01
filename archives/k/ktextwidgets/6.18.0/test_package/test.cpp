#include <KFind>
#include <KReplace>
#include <cstdio>
#include <QString>
#include <QRegularExpressionMatch>

int main() {
    const QString text = QStringLiteral("Akonadi contacts consume text widgets");
    int matchedLength = 0;
    const int index = KFind::find(
        text,
        QStringLiteral("contacts"),
        0,
        KFind::RegularExpression,
        &matchedLength,
        nullptr
    );

    if (index != 8 || matchedLength != 8) {
        std::fprintf(stderr, "FAIL: KFind returned index=%d length=%d\n", index, matchedLength);
        return 1;
    }

    QString replaced = text;
    int replacedLength = 0;
    const int replacedIndex = KReplace::replace(
        replaced,
        QStringLiteral("contacts"),
        QStringLiteral("libraries"),
        0,
        KFind::RegularExpression,
        &replacedLength
    );

    if (replacedIndex <= index || replacedLength != 9 ||
        replaced != QStringLiteral("Akonadi libraries consume text widgets")) {
        std::fprintf(
            stderr,
            "FAIL: KReplace returned index=%d length=%d\n",
            replacedIndex,
            replacedLength
        );
        return 1;
    }

    std::printf("PASS: KTextWidgets KFind matched at %d\n", index);
    std::printf("PASS: KTextWidgets KReplace produced %s\n", replaced.toUtf8().constData());
    return 0;
}
