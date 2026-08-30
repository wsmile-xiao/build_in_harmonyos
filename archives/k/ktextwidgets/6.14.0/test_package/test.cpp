// ktextwidgets 6.14.0 consumer test (R34: exercises real API).
// Verifies KRichTextEdit / KTextEdit behavior, including the spell-check
// toggle path that exercises the linked KF6::Sonnet integration.
#include <KRichTextEdit>
#include <KTextEdit>

#include <QApplication>
#include <QString>

#include <cstdio>

static int failures = 0;

#define CHECK(cond)                                             \
    do {                                                        \
        if (!(cond)) {                                          \
            std::printf("FAIL: %s (line %d)\n", #cond, __LINE__); \
            ++failures;                                         \
        }                                                       \
    } while (0)

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    {
        KRichTextEdit editor;
        CHECK(QString::fromLatin1(editor.metaObject()->className())
              == QLatin1String("KRichTextEdit"));

        editor.setPlainText(QStringLiteral("The quick brown fox"));
        CHECK(editor.toPlainText() == QStringLiteral("The quick brown fox"));

        // Rich-text document model is active on KRichTextEdit.
        editor.insertHtml(QStringLiteral("<b>bold</b> word"));
        CHECK(editor.toPlainText().contains(QStringLiteral("bold")));

        CHECK(editor.isReadOnly() == false);
        editor.setReadOnly(true);
        CHECK(editor.isReadOnly() == true);
        editor.setReadOnly(false);

        // Spell-check toggle: KTextEdit::setCheckSpellingEnabled drives the
        // Sonnet-backed highlighter (KF6::Sonnet link is exercised here).
        editor.setCheckSpellingEnabled(false);
        CHECK(editor.checkSpellingEnabled() == false);
        editor.setCheckSpellingEnabled(true);
        CHECK(editor.checkSpellingEnabled() == true);
    }

    {
        KTextEdit plain;
        plain.setPlainText(QStringLiteral("hello"));
        plain.append(QStringLiteral("world"));
        CHECK(plain.toPlainText().startsWith(QStringLiteral("hello")));
        CHECK(plain.toPlainText().contains(QStringLiteral("world")));
    }

    if (failures == 0) {
        std::printf("PASS: ktextwidgets consumer test OK\n");
        return 0;
    }
    std::printf("FAILED: %d checks\n", failures);
    return 1;
}
