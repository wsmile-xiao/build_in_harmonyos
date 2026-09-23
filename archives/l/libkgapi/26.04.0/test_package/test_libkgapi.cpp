#include <KGAPI/Calendar/Calendar>
#include <KGAPI/Account>

#include <QCoreApplication>
#include <QDate>
#include <QDebug>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // Exercise the real KPim6GAPICore/KPim6GAPICalendar API surface:
    // construct calendar objects, round-trip through the KGAPI object
    // model and verify the getters return what was set.
    KGAPI2::Calendar calendar;
    calendar.setTitle(QStringLiteral("ohpc-smoke"));
    calendar.setTimezone(QStringLiteral("UTC"));
    if (calendar.title() != QLatin1String("ohpc-smoke")) {
        qCritical() << "Calendar summary round-trip failed";
        return 1;
    }
    if (calendar.timezone() != QLatin1String("UTC")) {
        qCritical() << "Calendar timezone round-trip failed";
        return 1;
    }

    KGAPI2::Account account;
    account.setAccountName(QStringLiteral("ohpc-test-account"));
    if (account.accountName() != QLatin1String("ohpc-test-account")) {
        qCritical() << "Account name round-trip failed";
        return 1;
    }

    qDebug().noquote() << "PASS: KPim6GAPI API" << calendar.title() << account.accountName();
    return 0;
}
