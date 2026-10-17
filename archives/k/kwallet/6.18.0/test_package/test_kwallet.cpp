#include <KWallet>

#include <QCoreApplication>
#include <QDebug>
#include <QString>

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

    qDebug().noquote() << "PASS: KF6Wallet API" << walletName << localWalletName;
    return 0;
}
