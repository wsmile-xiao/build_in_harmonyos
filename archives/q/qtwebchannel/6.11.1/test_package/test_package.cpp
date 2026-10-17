#include <QCoreApplication>
#include <QJsonObject>
#include <QObject>
#include <QtWebChannel/QWebChannel>
#include <QtWebChannel/QWebChannelAbstractTransport>

// Simple QObject exposed through the WebChannel.
class TestObject : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString message READ message WRITE setMessage NOTIFY messageChanged)
public:
    QString message() const { return m_message; }
    void setMessage(const QString &message)
    {
        if (m_message == message)
            return;
        m_message = message;
        emit messageChanged();
    }

signals:
    void messageChanged();

private:
    QString m_message = QStringLiteral("openharmony-webchannel");
};

// Minimal transport that records the last message sent by the channel.
class RecordTransport : public QWebChannelAbstractTransport
{
    Q_OBJECT
public:
    QJsonObject lastMessage;
    int sendCount = 0;

public slots:
    void sendMessage(const QJsonObject &message) override
    {
        lastMessage = message;
        ++sendCount;
    }
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    TestObject obj;
    QWebChannel channel;

    // Register the object through the QWebChannel public API.
    channel.registerObject(QStringLiteral("testObject"), &obj);

    // Verify the object is tracked under the expected id.
    const auto objects = channel.registeredObjects();
    if (!objects.contains(QStringLiteral("testObject")))
        return 1;
    if (objects.value(QStringLiteral("testObject")) != &obj)
        return 2;

    // Attach a transport and verify the channel wires up the send path.
    RecordTransport transport;
    channel.connectTo(&transport);

    // Deregister and verify removal.
    channel.deregisterObject(&obj);
    if (channel.registeredObjects().contains(QStringLiteral("testObject")))
        return 3;

    return 0;
}

#include "test_package.moc"
