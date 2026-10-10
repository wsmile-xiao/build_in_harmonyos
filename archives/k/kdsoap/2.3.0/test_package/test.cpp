#include <KDSoapClient/KDSoapValue.h>

#include <QtCore/QString>

int main()
{
    const KDSoapValue value(QStringLiteral("sample"), QStringLiteral("ohos"));
    if (value.isNull())
        return 1;
    if (value.name() != QStringLiteral("sample"))
        return 2;
    if (value.value().toString() != QStringLiteral("ohos"))
        return 3;
    return 0;
}
