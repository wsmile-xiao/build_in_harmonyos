#include <QApplication>
#include <Qsci/qsciscintilla.h>
#include <Qsci/qsciglobal.h>

#include <cstdlib>
#include <cstring>
#include <iostream>

int main(int argc, char **argv) {
    if (std::strcmp(QSCINTILLA_VERSION_STR, "2.14.1") != 0) {
        std::cerr << "unexpected QScintilla version: " << QSCINTILLA_VERSION_STR << "\n";
        return EXIT_FAILURE;
    }
    QApplication app(argc, argv);
    QsciScintilla editor;
    editor.setText("OpenHarmony QScintilla smoke test");
    if (editor.text() != "OpenHarmony QScintilla smoke test") {
        std::cerr << "unexpected editor text: " << editor.text().toStdString() << "\n";
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
