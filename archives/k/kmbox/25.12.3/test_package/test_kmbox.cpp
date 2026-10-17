#include <KMbox/MBox>
#include <KMbox/MBoxEntry>
#include <KMime/Message>

#include <QByteArray>
#include <QCoreApplication>
#include <QDebug>
#include <QFile>
#include <QString>
#include <QTemporaryDir>

namespace
{
int fail(const char *message)
{
    qCritical().noquote() << message;
    return 1;
}

KMime::Message::Ptr makeMessage()
{
    KMime::Message::Ptr message(new KMime::Message);
    message->subject()->fromUnicodeString(QStringLiteral("KMbox smoke"));
    message->from()->fromUnicodeString(QStringLiteral("ada@example.test"));
    message->to()->fromUnicodeString(QStringLiteral("akonadi@example.test"));
    message->setBody(QByteArray("Hello from KMbox.\n"));
    message->assemble();
    return message;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail("temporary directory was not created");
    }

    const QString mboxPath = tempDir.filePath(QStringLiteral("mail.mbox"));
    QFile initialFile(mboxPath);
    if (!initialFile.open(QIODevice::WriteOnly)) {
        return fail("mbox file could not be initialized");
    }
    initialFile.close();

    KMBox::MBox writer;
    if (!writer.setLockType(KMBox::MBox::None)) {
        return fail("lock type could not be set to none");
    }
    if (!writer.load(mboxPath)) {
        return fail("empty mbox could not be loaded");
    }

    const KMBox::MBoxEntry entry = writer.appendMessage(makeMessage());
    if (entry.messageSize() == 0) {
        return fail("message was not appended");
    }
    if (!writer.save()) {
        return fail("mbox could not be saved");
    }

    KMBox::MBox reader;
    if (!reader.setLockType(KMBox::MBox::None)) {
        return fail("reader lock type could not be set to none");
    }
    if (!reader.load(mboxPath)) {
        return fail("saved mbox could not be reloaded");
    }

    const KMBox::MBoxEntry::List entries = reader.entries();
    if (entries.size() != 1) {
        return fail("saved mbox did not contain exactly one message");
    }

    const QByteArray raw = reader.readRawMessage(entries.constFirst());
    if (!raw.contains("Subject: KMbox smoke")) {
        return fail("raw message content was not readable");
    }

    const QByteArray headers = reader.readMessageHeaders(entries.constFirst());
    if (!headers.contains("Subject: KMbox smoke")) {
        return fail("message headers were not readable");
    }

    qInfo().noquote() << "PASS: KMbox wrote and reread one MIME message";
    return 0;
}
