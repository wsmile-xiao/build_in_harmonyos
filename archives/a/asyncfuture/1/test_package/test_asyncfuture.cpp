#include <QCoreApplication>
#include "asyncfuture.h"
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    auto deferred = AsyncFuture::deferred<int>();
    auto future = deferred.future();
    deferred.complete(42);
    future.waitForFinished();
    if (future.result() != 42) return 1;
    return 0;
}
