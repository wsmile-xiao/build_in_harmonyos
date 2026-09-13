#include <QDebug>
#include <QCoreApplication>
#include <QString>

#include <alkimia/alkvalue.h>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    Q_UNUSED(app);

    // AlkValue: arbitrary precision monetary value on top of GMP (gmpxx)
    AlkValue a(123, 100);   // 1.23
    AlkValue b(456, 100);   // 4.56

    AlkValue sum = a + b;   // 5.79
    if (sum.toString() != QString("579/100")) {
        qWarning() << "unexpected sum:" << sum.toString();
        return 1;
    }

    // convertDenominator exercises the GMP mpq_class conversion path;
    // mpq_class canonicalizes (5790/1000 -> 579/100)
    AlkValue converted = sum.convertDenominator(1000);
    if (converted.toString() != QString("579/100")) {
        qWarning() << "unexpected converted:" << converted.toString();
        return 1;
    }

    // double conversion path (canonicalized to lowest terms)
    AlkValue fromDouble(1.5, 100);
    if (fromDouble.toString() != QString("3/2")) {
        qWarning() << "unexpected fromDouble:" << fromDouble.toString();
        return 1;
    }

    qDebug() << "alkimia AlkValue arithmetic OK:" << sum.toString()
             << converted.toString() << fromDouble.toString();
    return 0;
}
