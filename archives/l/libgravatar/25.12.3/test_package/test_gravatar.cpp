// SPDX-License-Identifier: LGPL-2.0-or-later

#include <Gravatar/GravatarResolvUrlJob>

#include <QGuiApplication>
#include <QDebug>

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
    if (!job.email().isEmpty()) {
        return fail("new job did not start with an empty email");
    }

    const QString email = QStringLiteral("ada@example.test");
    job.setEmail(email);
    if (job.email() != email) {
        return fail("email setter/getter did not preserve the address");
    }

    if (!job.fallbackGravatar() || job.useLibravatar() || job.useDefaultPixmap()) {
        return fail("job backend/default options are unexpected");
    }
    job.setFallbackGravatar(false);
    job.setUseLibravatar(true);
    job.setUseDefaultPixmap(true);
    if (job.fallbackGravatar() || !job.useLibravatar() || !job.useDefaultPixmap()) {
        return fail("backend/default option setters did not take effect");
    }

    job.setSize(0);
    if (job.size() != 80) {
        return fail("non-positive size was not reset to the default");
    }
    job.setSize(256);
    if (job.size() != 256) {
        return fail("valid size was not retained");
    }
    job.setSize(4096);
    if (job.size() != 2048) {
        return fail("oversized image request was not clamped");
    }

    qInfo().noquote() << "PASS: libgravatar consumer API validation";
    return 0;
}
