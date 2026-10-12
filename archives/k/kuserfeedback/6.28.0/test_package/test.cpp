#include <KUserFeedback/Provider>

#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char **argv)
{
    // Offscreen smoke test: exercise the public KUserFeedback::Provider API.
    // Provider only needs QCoreApplication (Core+Network); telemetry
    // submission is disabled by default (NoTelemetry), so nothing leaves
    // the process and no event loop is required.
    QCoreApplication app(argc, argv);

    KUserFeedback::Provider provider;
    provider.setProductIdentifier(QStringLiteral("kuserfeedback-smoke"));

    if (!provider.productIdentifier().endsWith(QStringLiteral("kuserfeedback-smoke"))) {
        std::fprintf(stderr, "FAIL: productIdentifier mismatch\n");
        return 1;
    }
    if (provider.telemetryMode() != KUserFeedback::Provider::NoTelemetry) {
        std::fprintf(stderr, "FAIL: default telemetry mode is not NoTelemetry\n");
        return 1;
    }
    provider.setTelemetryMode(KUserFeedback::Provider::BasicUsageStatistics);
    if (provider.telemetryMode() != KUserFeedback::Provider::BasicUsageStatistics) {
        std::fprintf(stderr, "FAIL: setTelemetryMode not reflected\n");
        return 1;
    }
    provider.setSubmissionInterval(30);
    if (provider.submissionInterval() != 30) {
        std::fprintf(stderr, "FAIL: setSubmissionInterval not reflected\n");
        return 1;
    }
    provider.setSurveyInterval(7);
    if (provider.surveyInterval() != 7) {
        std::fprintf(stderr, "FAIL: setSurveyInterval not reflected\n");
        return 1;
    }
    if (provider.dataSource(QStringLiteral("doesNotExist")) != nullptr) {
        std::fprintf(stderr, "FAIL: unknown data source must be nullptr\n");
        return 1;
    }
    std::printf("kuserfeedback test_package: all assertions passed\n");
    return 0;
}
