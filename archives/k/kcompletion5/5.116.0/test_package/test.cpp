#include <KCompletion>
#include <KLineEdit>

#include <QApplication>
#include <QTest>

#include <sys/utsname.h>

#include <cstdio>
#include <cstring>

int main(int argc, char **argv)
{
#if defined(__OHOS__)
    struct utsname systemInfo {};
    if (uname(&systemInfo) != 0) {
        std::perror("uname");
        return 1;
    }
    if (std::strcmp(systemInfo.sysname, "HarmonyOS") != 0 ||
        std::strcmp(systemInfo.machine, "aarch64") != 0) {
        std::fprintf(stderr, "Unexpected HarmonyOS test host: %s/%s\n",
                     systemInfo.sysname, systemInfo.machine);
        return 1;
    }
#else
    std::fprintf(stderr, "This integration test must run on HarmonyOS.\n");
    return 1;
#endif

    QApplication app(argc, argv);
    KLineEdit lineEdit;
    lineEdit.setCompletionMode(KCompletion::CompletionAuto);

    KCompletion *completion = lineEdit.completionObject();
    if (!completion) {
        std::fprintf(stderr, "KLineEdit did not create its completion object.\n");
        return 1;
    }
    completion->clear();
    completion->addItem(QStringLiteral("HarmonyOS"));

    lineEdit.show();
    QTest::keyClicks(&lineEdit, QStringLiteral("Har"));
    app.processEvents();

    const QString completedText = lineEdit.text();
    if (completedText != QStringLiteral("HarmonyOS")) {
        std::fprintf(stderr, "KLineEdit completed 'Har' as '%s'.\n",
                     completedText.toUtf8().constData());
        return 1;
    }

    std::printf("PASS: HarmonyOS/aarch64 Qt keyboard event completed 'Har' to '%s'.\n",
                completedText.toUtf8().constData());
    return 0;
}
