// knewstuff 6.14.0 consumer test (R34: exercises real API of both libs).
// KNSCore::Entry is a Q_GADGET value type from libKF6NewStuffCore;
// KNSWidgets::Button is a QPushButton subclass from libKF6NewStuffWidgets
// (construction also pulls in the engine/KNSCore runtime linkage).
#include <KNSCore/Entry>
#include <KNSWidgets/Button>

#include <QApplication>
#include <QPushButton>

#include <cstdio>

static int failures = 0;

#define CHECK(cond)                                                \
    do {                                                           \
        if (!(cond)) {                                             \
            std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);  \
            ++failures;                                            \
        }                                                          \
    } while (0)

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    {
        KNSCore::Entry entry;
        CHECK(!entry.isValid());
        entry.setStatus(KNSCore::Entry::Downloadable);
        CHECK(entry.status() == KNSCore::Entry::Downloadable);
        entry.setStatus(KNSCore::Entry::Installed);
        CHECK(entry.status() == KNSCore::Entry::Installed);
    }

    {
        KNSWidgets::Button button(nullptr);
        CHECK(dynamic_cast<QPushButton *>(&button) != nullptr);
        button.setText(QStringLiteral("Install Stuff"));
        CHECK(button.text() == QStringLiteral("Install Stuff"));
        CHECK(button.isEnabled());
        button.setEnabled(false);
        CHECK(!button.isEnabled());
    }

    if (failures == 0) {
        std::printf("PASS: knewstuff consumer test OK\n");
        return 0;
    }
    std::printf("FAILED: %d checks\n", failures);
    return 1;
}
