#include <GrantleeTheme/GenericFormatter>
#include <GrantleeTheme/GrantleeTheme>

#include <QCoreApplication>
#include <QDebug>
#include <QVariantHash>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    GrantleeTheme::Theme theme;
    if (theme.isValid() || !theme.name().isEmpty()) {
        qCritical() << "Unexpected valid default GrantleeTheme::Theme";
        return 1;
    }

    GrantleeTheme::GenericFormatter formatter;
    formatter.setTemplateContent(QStringLiteral("Hello {{ name }}"));
    QVariantHash data;
    data.insert(QStringLiteral("name"), QStringLiteral("Akonadi"));
    const QString rendered = formatter.render(data).trimmed();
    if (rendered != QStringLiteral("Hello Akonadi")) {
        qCritical() << "Unexpected GrantleeTheme render output" << rendered
                    << formatter.errorMessage();
        return 1;
    }

    qInfo() << "PASS: GrantleeTheme default theme invalid";
    qInfo() << "PASS: GrantleeTheme rendered" << rendered;
    return 0;
}
