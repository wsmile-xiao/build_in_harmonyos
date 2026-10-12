#include <Config.h>
#include <Podcast.h>
#include <QCoreApplication>
#include <QVariantMap>
#include <iostream>
#include <stdexcept>

static void require(bool value, const char *name) {
    if (!value) throw std::runtime_error(name);
    std::cout << "CONSUMER " << name << " PASS\n";
}
int main(int argc, char **argv) {
    QCoreApplication application(argc, argv);
    mygpo::Config *config = mygpo::Config::instance();
    require(config->version() == QStringLiteral("1.2.0"), "library version");
    config->setUserAgentPrefix(QStringLiteral("harmony-consumer"));
    require(config->userAgent().contains(QStringLiteral("harmony-consumer")), "user agent");
    const QUrl base(QStringLiteral("https://example.invalid/podcasts/"));
    config->setMygpoBaseUrl(base);
    require(config->mygpoBaseUrl() == base, "base URL");
    QVariantMap data;
    data[QStringLiteral("url")] = QByteArray("https://example.invalid/feed.xml");
    data[QStringLiteral("title")] = QStringLiteral("Harmony podcast");
    data[QStringLiteral("description")] = QStringLiteral("Offline consumer");
    data[QStringLiteral("subscribers")] = 17;
    data[QStringLiteral("subscribers_last_week")] = 9;
    data[QStringLiteral("logo_url")] = QUrl(QStringLiteral("https://example.invalid/logo.png"));
    data[QStringLiteral("website")] = QUrl(QStringLiteral("https://example.invalid/"));
    data[QStringLiteral("mygpo_link")] = QUrl(QStringLiteral("https://example.invalid/podcast/17"));
    mygpo::Podcast podcast{QVariant(data)};
    require(podcast.title() == QStringLiteral("Harmony podcast") && podcast.description() == QStringLiteral("Offline consumer"), "podcast text");
    require(podcast.subscribers() == 17 && podcast.subscribersLastWeek() == 9, "subscriber counts");
    require(podcast.url() == QUrl::fromEncoded(data[QStringLiteral("url")].toByteArray()) && podcast.website() == data[QStringLiteral("website")].toUrl(), "podcast URLs");
    std::cout << "LIBMYGPO_CONSUMER_RESULT=6/6\n";
}
