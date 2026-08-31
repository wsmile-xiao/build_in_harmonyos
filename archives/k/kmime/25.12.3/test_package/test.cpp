#include <KMime/Message>
#include <QString>
#include <cstdio>

int main()
{
    KMime::Message message;
    message.subject()->fromUnicodeString(QStringLiteral("Akonadi downstream smoke"));
    message.from()->fromUnicodeString(QStringLiteral("sender@example.test"));
    message.to()->fromUnicodeString(QStringLiteral("receiver@example.test"));
    message.setBody("hello from kmime\n");
    message.assemble();

    const QString subject = message.subject()->asUnicodeString();
    if (subject != QStringLiteral("Akonadi downstream smoke")) {
        std::printf("FAIL: unexpected subject: %s\n", qPrintable(subject));
        return 1;
    }
    std::printf("PASS: KMime message subject = %s\n", qPrintable(subject));
    return 0;
}
