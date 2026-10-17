/*
 * liblastfm 1.2.0-git20250222.81e8f9d — test_package smoke test
 *
 * 链路级验证（无网络 I/O）：
 *   1. UrlBuilder::encode() —— 上游 UrlBuilderTest::encode 同款断言
 *   2. MutableTrack/Track 值语义 —— 上游 TrackTest::testClone 同款断言
 *   3. ws::scheme() —— OHOS QT_NO_SSL 回落路径（API 契约：无 SSL 支持
 *      时返回 Http）
 *   4. Audioscrobbler::enabled() —— Scrobble 核心类实例化
 * 任何一步失败以非零码退出。
 */
#include <lastfm5/global.h>
#include <lastfm5/UrlBuilder.h>
#include <lastfm5/Track.h>
#include <lastfm5/Audioscrobbler.h>
#include <lastfm5/ws.h>

#include <QCoreApplication>
#include <QDebug>
#include <QString>
#include <QtGlobal>
#include <cstdio>

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);

    int failures = 0;

    // 1. UrlBuilder::encode（上游 UrlBuilderTest::encode 断言复刻）
    {
        struct { const char* in; const char* out; } cases[] = {
            { "Metallica",                         "Metallica" },
            { "Apollo 440",                        "Apollo+440" },
            { "Would?",                            "Would%3F" },
            { "Survivalism [Revision #1]",         "Survivalism+%5BRevision+%231%5D" },
        };
        for (const auto& c : cases) {
            const QByteArray got = lastfm::UrlBuilder::encode(QString::fromLatin1(c.in));
            if (QString::fromLatin1(got) != QString::fromLatin1(c.out)) {
                qWarning() << "encode FAIL:" << c.in << "got" << got << "expected" << c.out;
                ++failures;
            }
        }
    }

    // 2. Track 值语义（上游 TrackTest::testClone 断言复刻）
    {
        lastfm::MutableTrack t;
        t.setTitle(QStringLiteral("Test Title"));
        t.setArtist(QStringLiteral("Test Artist"));
        t.setAlbum(QStringLiteral("Test Album"));
        lastfm::Track copy = t;
        if (copy.title() != t.title() || copy.artist() != t.artist() || copy.album() != t.album()) {
            qWarning() << "Track clone FAIL";
            ++failures;
        }
    }

    // 3. ws::scheme()：QT_NO_SSL 下按 API 契约回落 Http
    {
        const lastfm::ws::Scheme s = lastfm::ws::scheme();
#ifdef QT_NO_SSL
        if (s != lastfm::ws::Http) { qWarning() << "scheme FAIL: expected Http under QT_NO_SSL"; ++failures; }
#else
        Q_UNUSED(s);
#endif
    }

    // 4. Scrobble 核心类实例化（构造/析构不崩溃即链路可用）。
    //    Audioscrobbler 构造内部会创建 ScrobbleCache(username)，其
    //    Q_ASSERT(username.length()) 要求 lastfm::ws::Username 非空
    //    ——先按 API 约定赋值
    {
        lastfm::ws::Username = QStringLiteral("smoke-test-user");
        lastfm::Audioscrobbler scrobbler(QStringLiteral("smoke-test"));
    }

    if (failures == 0) {
        std::printf("liblastfm smoke test: ALL PASS\n");
        return 0;
    }
    std::printf("liblastfm smoke test: %d FAILURES\n", failures);
    return 1;
}
