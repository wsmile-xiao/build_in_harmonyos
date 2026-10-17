// baloo 26.04.3 (upstream 6.25.0) consumer test (R34: real API usage).
// Exercises the Baloo::Query value API from libKF6Baloo so the consumer
// really compiles against and links the installed library.
#include <Baloo/Query.h>

#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    Baloo::Query query;
    query.setSearchString(QStringLiteral("OHOS baloo porting test"));
    if (query.searchString() != QStringLiteral("OHOS baloo porting test")) {
        std::printf("FAIL: Baloo::Query searchString roundtrip mismatch\n");
        return 1;
    }
    query.setLimit(25);
    if (query.limit() != 25) {
        std::printf("FAIL: Baloo::Query limit() mismatch\n");
        return 1;
    }
    std::printf("PASS: Baloo::Query OK (search=%.12s...)\n",
                qPrintable(query.searchString()));
    return 0;
}
