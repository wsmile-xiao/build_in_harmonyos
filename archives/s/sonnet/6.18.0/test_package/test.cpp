#include <QCoreApplication>
#include <Sonnet/Highlighter>
#include <Sonnet/Speller>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    Sonnet::Speller speller;
    const QMetaObject *highlighterMetaObject = &Sonnet::Highlighter::staticMetaObject;
    std::printf("PASS: Sonnet speller valid=%d\n", speller.isValid() ? 1 : 0);
    std::printf("PASS: Sonnet UI meta-object = %s\n", highlighterMetaObject->className());
    return 0;
}
