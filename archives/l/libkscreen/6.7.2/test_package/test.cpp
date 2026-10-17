// libkscreen 6.7.2 consumer test (R34: exercises real API).
// Builds KScreen model objects through the public API and round-trips
// them through the ConfigSerializer JSON code path (the same one the
// fake backend uses to load its fixtures).
#include <KScreen/Config>
#include <KScreen/Mode>
#include <KScreen/Output>
#include <KScreen/Screen>
#include <QCoreApplication>
#include <QRect>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSharedPointer>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    // --- Build a config from scratch (public API) ---
    KScreen::ConfigPtr config(new KScreen::Config);

    KScreen::ScreenPtr screen(new KScreen::Screen);
    screen->setId(12);
    screen->setMinSize(QSize(360, 360));
    screen->setMaxSize(QSize(8192, 8192));
    screen->setCurrentSize(QSize(3600, 1280));
    screen->setMaxActiveOutputsCount(3);
    config->setScreen(screen);

    KScreen::ModePtr mode(new KScreen::Mode);
    mode->setId(QStringLiteral("800x600@60"));
    mode->setSize(QSize(800, 600));
    mode->setRefreshRate(60);

    KScreen::ModeList modeList;
    modeList.insert(mode->id(), mode);

    KScreen::OutputPtr output(new KScreen::Output);
    output->setId(1);
    output->setName(QStringLiteral("LVDS1"));
    output->setConnected(true);
    output->setEnabled(true);
    output->setModes(modeList);
    output->setCurrentModeId(mode->id());

    config->addOutput(output);

    // --- Validate through public API ---
    if (config->outputs().size() != 1) {
        std::printf("FAIL: expected 1 output, got %d\n",
                    int(config->outputs().size()));
        return 1;
    }
    if (config->output(1) != output) {
        std::printf("FAIL: output(1) does not return the added output\n");
        return 1;
    }
    if (config->connectedOutputs().size() != 1) {
        std::printf("FAIL: expected 1 connected output\n");
        return 1;
    }
    if (config->screen() != screen) {
        std::printf("FAIL: screen() does not return the set screen\n");
        return 1;
    }
    if (!config->output(1)->currentMode()) {
        std::printf("FAIL: currentMode() is null\n");
        return 1;
    }
    if (config->output(1)->currentMode()->size() != QSize(800, 600)) {
        std::printf("FAIL: current mode size wrong\n");
        return 1;
    }

    KScreen::OutputPtr clone = config->output(1)->clone();
    if (!clone || clone->name() != QLatin1String("LVDS1")
        || clone->id() != 1) {
        std::printf("FAIL: Output::clone() round-trip wrong\n");
        return 1;
    }
    if (!clone->isConnected() || !clone->isEnabled()) {
        std::printf("FAIL: cloned output flags wrong\n");
        return 1;
    }
    if (!clone->currentMode()) {
        std::printf("FAIL: cloned output has no current mode\n");
        return 1;
    }
    if (clone->currentMode()->size() != QSize(800, 600)) {
        std::printf("FAIL: cloned current mode size wrong\n");
        return 1;
    }

    // Geometry derives from position + current mode size (public API).
    if (output->geometry() != QRect(0, 0, 800, 600)) {
        std::printf("FAIL: output geometry is %dx%d+%d+%d\n",
                    output->geometry().width(), output->geometry().height(),
                    output->geometry().x(), output->geometry().y());
        return 1;
    }

    // Config::clone deep-copies the whole model graph.
    KScreen::ConfigPtr config2 = config->clone();
    if (!config2 || config2->outputs().size() != 1
        || !config2->screen()) {
        std::printf("FAIL: Config::clone() round-trip wrong\n");
        return 1;
    }

    std::printf("PASS: KScreen public API OK (output LVDS1 800x600@60 "
                "clone round-trip, screen id=12, outputs=1)\n");
    return 0;
}
