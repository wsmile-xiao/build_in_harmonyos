#include <AdwaitaQt6/adwaita.h>

#include <QApplication>
#include <QPalette>
#include <QPushButton>
#include <QStyle>
#include <QStyleFactory>
#include <QStyleOptionButton>
#include <QtGlobal>

#include <cstdio>
#include <memory>

int main(int argc, char **argv)
{
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication application(argc, argv);
    if (application.platformName() != QLatin1String("offscreen"))
        return 1;

    const QStringList styles = QStyleFactory::keys();
    if (!styles.contains(QStringLiteral("Adwaita"), Qt::CaseInsensitive))
        return 2;

    std::unique_ptr<QStyle> style(QStyleFactory::create(QStringLiteral("Adwaita")));
    if (!style)
        return 3;

    QApplication::setStyle(style.release());
    QStyle *activeStyle = QApplication::style();
    if (!activeStyle)
        return 4;

    QPushButton button(QStringLiteral("Adwaita"));
    QStyleOptionButton option;
    option.initFrom(&button);
    option.text = button.text();
    if (activeStyle->pixelMetric(QStyle::PM_ButtonMargin, &option, &button) < 0)
        return 5;

    const Adwaita::StyleOptions styleOptions(QApplication::palette(), Adwaita::Adwaita);
    if (styleOptions.colorVariant() != Adwaita::Adwaita)
        return 6;

    const QColor textColor =
        QApplication::palette().color(QPalette::Active, QPalette::ButtonText);
    if (!textColor.isValid())
        return 7;

    if (Adwaita::Metrics::Button_MinHeight <= 0)
        return 8;

    std::printf("adwaita-qt plugin and AdwaitaQt6 library loaded with Qt %s\n", QT_VERSION_STR);
    return 0;
}
