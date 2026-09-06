#include <Gravatar/GravatarResolvUrlJob>

#include <QDebug>
#include <QGuiApplication>

namespace
{
int fail(const char *message)
{
    qCritical().noquote() << message;
    return 1;
}
}

int main(int argc, char **argv)
{
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);

    Gravatar::GravatarResolvUrlJob job;
    job.setEmail(QStringLiteral("ada@example.test"));
    if (job.email() != QStringLiteral("ada@example.test")) {
        return fail("email was not stored");
    }

    job.setSize(128);
    if (job.size() != 128) {
        return fail("size was not stored");
    }
    job.setSize(0);
    if (job.size() != 80) {
        return fail("non-positive size was not clamped to default");
    }
    job.setSize(4096);
    if (job.size() != 2048) {
        return fail("oversized value was not clamped");
    }

    job.setUseDefaultPixmap(true);
    if (!job.useDefaultPixmap()) {
        return fail("default pixmap flag was not stored");
    }
    job.setUseLibravatar(true);
    if (!job.useLibravatar()) {
        return fail("libravatar flag was not stored");
    }
    job.setFallbackGravatar(false);
    if (job.fallbackGravatar()) {
        return fail("fallback gravatar flag was not disabled");
    }

    qInfo().noquote() << "PASS: gravatar resolve job stores local options";
    return 0;
}
