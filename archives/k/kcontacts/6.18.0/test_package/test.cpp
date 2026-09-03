#include <KContacts/Addressee>

#include <QStringList>
#include <cstdio>

int main()
{
    KContacts::Addressee contact;
    contact.setName(QStringLiteral("Ada Lovelace"));
    contact.setEmails({QStringLiteral("ada@example.test")});

    if (contact.name() != QStringLiteral("Ada Lovelace")) {
        std::printf("FAIL: unexpected contact name\n");
        return 1;
    }
    if (contact.preferredEmail() != QStringLiteral("ada@example.test")) {
        std::printf("FAIL: unexpected preferred email\n");
        return 1;
    }

    std::printf(
        "PASS: KContacts addressee = %s <%s>\n",
        qPrintable(contact.name()),
        qPrintable(contact.preferredEmail())
    );
    return 0;
}
