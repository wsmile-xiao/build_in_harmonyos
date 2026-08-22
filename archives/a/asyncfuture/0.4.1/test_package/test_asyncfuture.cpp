#include <QCoreApplication>
#include "asyncfuture.h"

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    auto deferred = AsyncFuture::deferred<int>();
    int observed = 0;
    deferred.future().then([&](int value) { observed = value; });
    deferred.complete(42);
    if (deferred.future().result() != 42) return 1;
    if (observed != 42) return 2;
    return 0;
}
