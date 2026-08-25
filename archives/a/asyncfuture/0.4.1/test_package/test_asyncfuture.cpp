#include <QCoreApplication>
#include "asyncfuture.h"

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    auto deferred = AsyncFuture::deferred<int>();
    int observed = 0;
    auto future = deferred.future();
    future.waitForFinished();
    if (future.result() != 42) return 1;
    deferred.complete(42);
    if (deferred.future().result() != 42) return 1;
    if (observed != 42) return 2;
    return 0;
}
