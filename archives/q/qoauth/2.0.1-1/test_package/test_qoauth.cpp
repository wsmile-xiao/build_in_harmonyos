#include <QCoreApplication>
#include <QUrl>
#include <QtOAuth/interface.h>
#include <QDebug>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    QOAuth::Interface oauth;
    oauth.setConsumerKey("test_key");
    oauth.setConsumerSecret("test_secret");
    oauth.setRequestTimeout(30000);
    oauth.setIgnoreSslErrors(false);
    if (oauth.consumerKey() != "test_key") {
        qCritical() << "consumerKey round-trip failed";
        return 1;
    }
    if (oauth.consumerSecret() != "test_secret") {
        qCritical() << "consumerSecret round-trip failed";
        return 1;
    }
    // 验证参数序列化（离线可验证的核心 API，不发起网络请求）
    QOAuth::ParamMap params;
    params.insert("oauth_version", QByteArray("1.0"));
    params.insert("oauth_nonce", QByteArray("abc123"));
    QByteArray parsed = oauth.inlineParameters(
        params, QOAuth::ParseForRequestContent);
    if (!parsed.contains("oauth_version=1.0") ||
        !parsed.contains("oauth_nonce=abc123")) {
        qCritical() << "inlineParameters output unexpected:" << parsed;
        return 1;
    }
    qDebug() << "qoauth library loaded successfully";
    qDebug() << "Consumer key:" << oauth.consumerKey();
    qDebug() << "inlineParameters:" << parsed;
    return 0;
}
