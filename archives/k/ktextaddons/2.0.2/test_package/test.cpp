/*
   Consumer smoke test for ktextaddons 2.0.2 on HarmonyOS PC.

   Exercises real public APIs of the leaf libraries:
   - TextEmoticonsCore::EmoticonUnicodeUtils::escapeUnicodeEmoji (KF6TextEmoticonsCore,
     headless static helper)
   - TextUtils::ConvertText::normalize / upperCase / lowerCase (KF6TextUtils)
   - TextAddonsWidgets::SlideContainer (KF6TextAddonsWidgets, QWidget-based,
     run with QT_QPA_PLATFORM=offscreen)
*/
#include <QApplication>
#include <QTextCursor>
#include <QTextDocument>
#include <QWidget>

#include <TextAddonsWidgets/SlideContainer>
#include <TextEmoticonsCore/EmoticonUnicodeUtils>
#include <TextUtils/ConvertText>

#include <cstdio>

int main(int argc, char **argv)
{
    // QApplication (not QCoreApplication): the SlideContainer section below
    // constructs QWidget instances; run headless via QT_QPA_PLATFORM=offscreen.
    QApplication app(argc, argv);

    int failures = 0;

    // --- KF6TextEmoticonsCore: escapeUnicodeEmoji --------------------------
    {
        // "1F600" is the code point of GRINNING FACE; the helper expands the
        // surrogate pair for the platform emoji font.
        const QString emoji = TextEmoticonsCore::EmoticonUnicodeUtils::escapeUnicodeEmoji(QStringLiteral("1F600"));
        const QString expected = QString::fromUcs4(U"\U0001F600");
        if (emoji != expected) {
            std::printf("FAIL escapeUnicodeEmoji: got %d chars\n", int(emoji.size()));
            ++failures;
        } else {
            std::printf("PASS escapeUnicodeEmoji\n");
        }
        if (TextEmoticonsCore::EmoticonUnicodeUtils::emojiFontName().isEmpty()) {
            std::printf("FAIL emojiFontName is empty\n");
            ++failures;
        } else {
            std::printf("PASS emojiFontName\n");
        }
    }

    // --- KF6TextUtils: ConvertText::normalize -----------------------------
    {
        // QString::fromUtf8 treats the \303\251 escape bytes as the UTF-8
        // encoding of U+00E9 (LATIN SMALL LETTER E WITH ACUTE), whose
        // canonical decomposition is "e" + combining acute -> "numerique".
        const QString in = QString::fromUtf8("num\303\251rique");
        const QString out = TextUtils::ConvertText::normalize(QStringView(in));
        if (out != QStringLiteral("numerique")) {
            std::printf("FAIL normalize: got '%s'\n", qPrintable(out));
            ++failures;
        } else {
            std::printf("PASS normalize\n");
        }
    }

    // --- KF6TextUtils: ConvertText::upperCase / lowerCase -----------------
    {
        QTextDocument doc;
        QTextCursor cursor(&doc);
        cursor.insertText(QStringLiteral("hello"));

        cursor.movePosition(QTextCursor::Start, QTextCursor::MoveAnchor);
        cursor.movePosition(QTextCursor::End, QTextCursor::KeepAnchor);
        TextUtils::ConvertText::upperCase(cursor);
        const QString upper = doc.toPlainText();
        if (upper != QStringLiteral("HELLO")) {
            std::printf("FAIL upperCase: got '%s'\n", qPrintable(upper));
            ++failures;
        } else {
            std::printf("PASS upperCase\n");
        }

        cursor.movePosition(QTextCursor::Start, QTextCursor::MoveAnchor);
        cursor.movePosition(QTextCursor::End, QTextCursor::KeepAnchor);
        TextUtils::ConvertText::lowerCase(cursor);
        const QString lower = doc.toPlainText();
        if (lower != QStringLiteral("hello")) {
            std::printf("FAIL lowerCase: got '%s'\n", qPrintable(lower));
            ++failures;
        } else {
            std::printf("PASS lowerCase\n");
        }
    }

    // --- KF6TextAddonsWidgets: SlideContainer ------------------------------
    {
        // The conan test env sets QT_QPA_PLATFORM=offscreen, so QWidget
        // construction is safe under the QApplication created above.
        QWidget host;
        TextAddonsWidgets::SlideContainer *container = new TextAddonsWidgets::SlideContainer(&host);
        QWidget *content = new QWidget(container);
        container->setContent(content);
        if (container->content() != content) {
            std::printf("FAIL SlideContainer::content round-trip\n");
            ++failures;
        } else {
            std::printf("PASS SlideContainer::content round-trip\n");
        }
        const int h = container->slideHeight();
        container->setSlideHeight(h);
        std::printf("PASS SlideContainer constructed, slideHeight=%d\n", h);
        delete container;
    }

    if (failures == 0) {
        std::printf("ALL PASS\n");
        return 0;
    }
    std::printf("%d FAILURE(S)\n", failures);
    return 1;
}
