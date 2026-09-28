#include <KWallet>

#include <QCoreApplication>
#include <QDebug>
#include <QString>
#include <QStringList>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const QString walletName = KWallet::Wallet::NetworkWallet();
    if (walletName.isEmpty()) {
        qCritical() << "KWallet network wallet name is empty";
        return 1;
    }

    const QString localWalletName = KWallet::Wallet::LocalWallet();
    if (localWalletName.isEmpty()) {
        qCritical() << "KWallet local wallet name is empty";
        return 1;
    }

    // Pure-local API surface (fixed literals, no daemon round-trip).
    if (KWallet::Wallet::PasswordFolder() != QStringLiteral("Passwords")) {
        qCritical() << "KWallet::PasswordFolder() mismatch";
        return 1;
    }
    if (KWallet::Wallet::FormDataFolder() != QStringLiteral("Form Data")) {
        qCritical() << "KWallet::FormDataFolder() mismatch";
        return 1;
    }

    // KConfigGroup/KSharedConfig read path behind the KWallet API (the
    // pinned KF6::ConfigCore dependency) is exercised by LocalWallet() and
    // NetworkWallet(); verify the returned defaults are the upstream ones.
    if (walletName != QStringLiteral("kdewallet")) {
        qCritical() << "Unexpected default network wallet:" << walletName;
        return 1;
    }

    qDebug().noquote() << "PASS: KF6Wallet API" << walletName << localWalletName
                       << KWallet::Wallet::PasswordFolder()
                       << KWallet::Wallet::FormDataFolder();
    return 0;
}
