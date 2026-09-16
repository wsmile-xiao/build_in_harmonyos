// test_package for syndication 6.14.0 (R34: real API usage).
//
// Parses a hard-coded RSS 2.0 feed through the public Syndication API
// (Syndication::parserCollection / Syndication::DocumentSource) and
// validates the parsed feed title and items. Exits non-zero on failure.

#include <Syndication/DocumentSource>
#include <Syndication/Feed>
#include <Syndication/Global>
#include <Syndication/ParserCollection>

#include <QByteArray>
#include <QList>
#include <QString>

#include <cstdio>

int main()
{
    const QByteArray rss = QByteArrayLiteral(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<rss version=\"2.0\"><channel>"
        "<title>KDE.news</title>"
        "<link>https://www.kde.org</link>"
        "<description>News from the KDE community</description>"
        "<item><title>KDE Frameworks 6.14 released</title>"
        "<link>https://www.kde.org/announcements</link>"
        "<description>A new release</description></item>"
        "<item><title>Plasma 6 beta</title>"
        "<link>https://www.kde.org/plasma</link>"
        "<description>Testing begins</description></item>"
        "</channel></rss>");

    Syndication::DocumentSource src(rss, QStringLiteral("https://www.kde.org/rss.xml"));
    Syndication::FeedPtr feed = Syndication::parserCollection()->parse(src);

    if (!feed) {
        std::fprintf(stderr, "FAILED: parserCollection()->parse() returned null\n");
        return 1;
    }
    const QString title = feed->title();
    if (title != QStringLiteral("KDE.news")) {
        std::fprintf(stderr, "FAILED: unexpected feed title '%s' (expected 'KDE.news')\n",
                     qPrintable(title));
        return 1;
    }
    const QList<Syndication::ItemPtr> items = feed->items();
    if (items.size() != 2) {
        std::fprintf(stderr, "FAILED: expected 2 items, got %lld\n",
                     static_cast<long long>(items.size()));
        return 1;
    }
    std::printf("PASS: parsed RSS 2.0 feed, title='%s', items=%lld\n",
                qPrintable(title), static_cast<long long>(items.size()));
    return 0;
}
