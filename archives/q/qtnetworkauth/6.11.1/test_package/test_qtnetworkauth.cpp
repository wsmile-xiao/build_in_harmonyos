// Consumer test for Qt6NetworkAuth on HarmonyOS PC.
// Exercises the public QOAuth1Signature API without opening any network
// socket: it verifies the RFC 5849 PLAINTEXT signature form and that
// HMAC-SHA1 produces a 20-byte digest, proving the packaged Qt6::NetworkAuth
// library is usable.

#include <QtNetworkAuth/qoauth1signature.h>

#include <QByteArray>
#include <QUrl>
#include <QString>
#include <cstdio>

int main()
{
    const QString clientSecret = QStringLiteral("kd94hf93k423kf44");
    const QString tokenSecret = QStringLiteral("pfkkdhi9sl3r4s00");

    // RFC 5849: PLAINTEXT signature is clientSecret & tokenSecret.
    const QByteArray plain = QOAuth1Signature::plainText(clientSecret, tokenSecret);
    if (plain != QByteArray("kd94hf93k423kf44&pfkkdhi9sl3r4s00")) {
        std::fprintf(stderr, "test_qtnetworkauth: unexpected PLAINTEXT signature: %s\n",
                     plain.constData());
        return 1;
    }

    // HMAC-SHA1 must return a raw 20-byte SHA-1 digest.
    QUrl url(QStringLiteral("http://photos.example.net/photos"));
    QOAuth1Signature signature(
        url, clientSecret, tokenSecret,
        QOAuth1Signature::HttpRequestMethod::Get);
    signature.insert(QStringLiteral("file"), QStringLiteral("vacation.jpg"));
    signature.insert(QStringLiteral("size"), QStringLiteral("original"));

    const QByteArray hmac = signature.hmacSha1();
    if (hmac.size() != 20) {
        std::fprintf(stderr, "test_qtnetworkauth: unexpected HMAC-SHA1 size: %d\n",
                     hmac.size());
        return 1;
    }

    std::printf("test_qtnetworkauth: PLAINTEXT + HMAC-SHA1 OK\n");
    return 0;
}
