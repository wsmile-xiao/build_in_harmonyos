#include <QCoreApplication>
#include <QTimer>
#include <QtConcurrent/QtConcurrent>
#include <iostream>

#include "asyncfuture.h"

using namespace AsyncFuture;

// 简单断言辅助（避免引入 QtTest 重依赖）
static int g_failures = 0;
#define CHECK(cond)                                                        \
    do {                                                                   \
        if (!(cond)) {                                                     \
            std::cerr << "CHECK failed: " #cond " (line " << __LINE__      \
                      << ")" << std::endl;                                 \
            g_failures++;                                                  \
        }                                                                  \
    } while (0)

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // 1. observe: 把 QObject 信号转成 QFuture（observe + subscribe 回调）
    QTimer *timer = new QTimer(&app);
    timer->setSingleShot(true);
    bool signalObserved = false;
    QFuture<void> signalFuture = observe(timer, &QTimer::timeout).future();
    observe(signalFuture).subscribe([&]() { signalObserved = true; });
    timer->start(10);

    // 2. deferred: 手动 complete/cancel，Promise 语义
    auto defer = deferred<int>();
    QFuture<int> deferredFuture = defer.future();
    defer.complete(42);

    // 3. combine: 合并不同类型 future（QtConcurrent 线程 + 信号 future）
    QFuture<int> worker = QtConcurrent::run([]() { return 7 * 6; });
    QFuture<int> combined = (combine() << worker << signalFuture)
                                .subscribe([&]() { return worker.result(); })
                                .future();

    // 4. observe(QtConcurrent) + subscribe 链式回调
    QFuture<int> chained =
        observe(worker).subscribe([](int) { return 100; }).future();

    bool done = false;
    QTimer finishGuard;
    finishGuard.setSingleShot(true);
    QObject::connect(&finishGuard, &QTimer::timeout, [&]() {
        // deferred 已同步 complete
        CHECK(deferredFuture.isFinished());
        CHECK(deferredFuture.isCanceled() == false);
        CHECK(deferredFuture.result() == 42);

        // combine 等待两个输入全部完成
        CHECK(combined.isFinished());
        CHECK(combined.isCanceled() == false);
        CHECK(combined.result() == 42);

        // 链式 subscribe 返回新值
        CHECK(chained.isFinished());
        CHECK(chained.result() == 100);

        // 信号转 future 已触发
        CHECK(signalObserved);
        CHECK(signalFuture.isFinished());

        done = true;
        app.quit();
    });

    QObject::connect(&app, &QCoreApplication::aboutToQuit, [&]() {
        if (!done) {
            std::cerr << "Event loop quit before verification" << std::endl;
            g_failures++;
        }
    });

    finishGuard.start(3000);
    app.exec();

    delete timer;
    if (g_failures != 0) {
        std::cerr << g_failures << " check(s) failed" << std::endl;
        return 1;
    }
    std::cout << "asyncfuture consumer test: all checks passed" << std::endl;
    return 0;
}
