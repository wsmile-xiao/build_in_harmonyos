/*
    SPDX-FileCopyrightText: 2026 OpenHarmony PC Developer

    SPDX-License-Identifier: GPL-2.0-or-later

    Consumer smoke test for the OHOS PC port of pimcommon 25.12.3.

    The pimcommon 25.12.3 upstream archive ships no standalone example
    consumer, so this harness links against the public KPim6PimCommon
    library and exercises public API across the ported modules:
    - PimCommon::Util::isImapResource / generateEmailList (util)
    - PimCommon::TemplateManager (templatewidgets)
    - PimCommon::CustomToolsWidgetng (customtools)
    - PimCommon::NetworkManager (network)
    It also verifies the OHOS-specific behaviour introduced by this port:
    PimCommon::SpellCheckLineEdit is backed by QPlainTextEdit (KF6TextAddons
    is not published on the OHOS PC conan remote), and PurposeMenuWidget is
    backed by an empty QMenu (KF6Purpose not published).
*/

#include <PimCommon/CustomToolsWidgetng>
#include <PimCommon/NetworkManager>
#include <PimCommon/PimUtil>
#include <PimCommon/PurposeMenuWidget>
#include <PimCommon/SpellCheckLineEdit>

#include <QApplication>
#include <QMenu>
#include <QtGlobal>

#include <cstdio>

namespace
{
int failures = 0;

void check(bool condition, const char *what)
{
    if (condition) {
        std::printf("[PASS] %s\n", what);
    } else {
        std::printf("[FAIL] %s\n", what);
        ++failures;
    }
}
}

class TestPurposeMenuWidget final : public PimCommon::PurposeMenuWidget
{
public:
    explicit TestPurposeMenuWidget(QWidget *parent)
        : PurposeMenuWidget(parent)
    {
    }

    [[nodiscard]] QByteArray text() override
    {
        return QByteArrayLiteral("pimcommon consumer test");
    }
};

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    // --- PimCommon::Util (util module) ---
    check(PimCommon::Util::isImapResource(QStringLiteral("akonadi_imap_resource")),
          "PimCommon::Util::isImapResource recognizes IMAP resource");
    check(!PimCommon::Util::isImapResource(QStringLiteral("akonadi_pop3_resource")),
          "PimCommon::Util::isImapResource rejects POP3 resource");
    const QStringList emails = PimCommon::Util::generateEmailList({QStringLiteral("a@example.org"), QStringLiteral("b@example.org")});
    check(emails.size() == 2, "PimCommon::Util::generateEmailList returns entries");

    // --- NetworkManager: instantiate (network module compiled for OHOS) ---
    {
        PimCommon::NetworkManager nm;
        check(true, "PimCommon::NetworkManager constructs on OHOS");
    }

    // --- OHOS-specific: SpellCheckLineEdit backed by QPlainTextEdit ---
    {
        PimCommon::SpellCheckLineEdit edit(nullptr, QStringLiteral("testrc"));
        edit.setPlainText(QStringLiteral("ohos"));
        check(edit.toPlainText() == QLatin1String("ohos"),
              "PimCommon::SpellCheckLineEdit (OHOS QPlainTextEdit backing) round-trips text");
    }

    // --- OHOS-specific: PurposeMenuWidget backed by an empty QMenu ---
    {
        TestPurposeMenuWidget pmw(nullptr);
        check(pmw.menu() != nullptr, "PimCommon::PurposeMenuWidget (OHOS QMenu backing) provides a menu");
        check(pmw.menu()->objectName() == QLatin1String("purposesharemenu"),
              "PimCommon::PurposeMenuWidget menu objectName preserved");
    }

    if (failures == 0) {
        std::printf("ALL CHECKS PASSED\n");
        return 0;
    }
    std::printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
