#include <QByteArray>
#include <QtGlobal>

extern "C" Q_DECL_EXPORT int qtbase_consumer_bridge()
{
    return QByteArray("QtBase").toHex() == "517442617365" ? 42 : 0;
}
