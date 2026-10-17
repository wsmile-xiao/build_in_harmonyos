#include <QCoreApplication>
#include <QEventLoop>
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

// 运行事件循环让 QTimer 信号与 observe() 回调得到投递，随后退出
static void pumpEvents(int ms)
{
    QEventLoop loop;
    QTimer::singleShot(ms, &loop, &QEventLoop::quit);
    loop.exec();
}

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
    pumpEvents(500);
    CHECK(signalObserved);

    // 2. deferred: 手动 complete，Promise 语义
    auto defer = deferred<int>();
    QFuture<int> deferredFuture = defer.future();
    defer.complete(42);
    deferredFuture.waitForFinished();
    CHECK(deferredFuture.isFinished());
    CHECK(deferredFuture.result() == 42);

    // 3. combine: 合并不同类型 future（QtConcurrent 线程 + 信号 future）
    QFuture<int> worker = QtConcurrent::run([]() { return 7 * 6; });
    QFuture<int> combined = (combine() << worker << signalFuture)
                                .subscribe([&]() { return worker.result(); })
                                .future();
    pumpEvents(500);
    combined.waitForFinished();
    CHECK(combined.isFinished());
    CHECK(combined.result() == 42);

    // 4. deferred().cancel(): Promise 语义的取消路径
    auto cancelDefer = deferred<void>();
    QFuture<void> cancelFuture = cancelDefer.future();
    cancelDefer.cancel();
    cancelFuture.waitForFinished();
    CHECK(cancelFuture.isCanceled());

    if (g_failures == 0) {
        std::cout << "test_asyncfuture: ALL CHECKS PASSED" << std::endl;
        return 0;
    }
    std::cerr << g_failures << " check(s) FAILED" << std::endl;
    return 1;
}