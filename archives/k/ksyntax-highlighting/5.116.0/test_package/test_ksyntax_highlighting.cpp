#include <KSyntaxHighlighting/Definition>
#include <KSyntaxHighlighting/Repository>
#include <KSyntaxHighlighting/Theme>

#include <QCoreApplication>
#include <QDebug>
#include <QString>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // Consumer: use the real public API of KSyntaxHighlighting.
    KSyntaxHighlighting::Repository repository;
    const KSyntaxHighlighting::Definition cpp =
        repository.definitionForName(QStringLiteral("C++"));
    if (!cpp.isValid()) {
        qCritical().noquote() << "FAIL: C++ syntax definition was not loaded";
        return 1;
    }

    const KSyntaxHighlighting::Theme theme =
        repository.defaultTheme(KSyntaxHighlighting::Repository::LightTheme);
    if (!theme.isValid()) {
        qCritical().noquote() << "FAIL: default syntax theme was not loaded";
        return 1;
    }

    qInfo().noquote() << "PASS: KSyntaxHighlighting loaded" << cpp.name()
                      << "with" << theme.name();
    return 0;
}
