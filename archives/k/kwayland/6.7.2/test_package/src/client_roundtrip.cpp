/* client_roundtrip.cpp — KWaylandClient E2E 往返（test_package）
 *
 * kwayland 6.7.2 上游没有注册 ctest 测试（tests/CMakeLists.txt 只构建
 * 可执行文件，运行依赖的 testserver 已移出本仓库），本程序承担运行时
 * 验证：进程内起迷你合成器线程（见 mini_compositor.c），用 KWaylandClient
 * 走完整链路：
 *
 *   ConnectionThread::setSocketFd → initConnection → connected
 *   → Registry::create/setup → interfacesAnnounced
 *   → createCompositor → createSurface → commit → flush
 *   → 断言服务端 create_surface 计数 == 1
 *
 * 5 项运行时断言逐条打印 PASS/FAIL（[kwayland-e2e] 前缀，便于 CI 取证），
 * 末尾打 SUMMARY；任一断言失败返回 1，全部通过返回 0。
 */
#include <QCoreApplication>
#include <QEventLoop>
#include <QTimer>

#include <cstdio>

#include <KWayland/Client/compositor.h>
#include <KWayland/Client/connection_thread.h>
#include <KWayland/Client/registry.h>
#include <KWayland/Client/surface.h>

#include "mini_compositor.h"

using KWayland::Client::Compositor;
using KWayland::Client::ConnectionThread;
using KWayland::Client::Registry;
using KWayland::Client::Surface;

static int g_failed = 0;

static void
report(int index, const char *what, bool ok)
{
    std::printf("[kwayland-e2e] assert%d %s: %s\n", index, what,
                ok ? "PASS" : "FAIL");
    std::fflush(stdout);
    if (!ok) {
        ++g_failed;
    }
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    /* 前置：迷你合成器起线程 + socketpair 就绪（失败即无法继续） */
    int client_fd = -1;
    if (mini_compositor_start(&client_fd) != 0) {
        std::printf("[kwayland-e2e] mini_compositor_start: FAIL\n");
        std::fflush(stdout);
        return 2;
    }

    ConnectionThread connection;
    bool connected = false;
    {
        QEventLoop loop;
        QTimer timeout;
        timeout.setSingleShot(true);
        QObject::connect(&connection, &ConnectionThread::connected, [&] {
            connected = true;
            loop.quit();
        });
        QObject::connect(&timeout, &QTimer::timeout, &loop,
                         &QEventLoop::quit);
        connection.setSocketFd(client_fd);
        connection.initConnection();
        timeout.start(5000);
        loop.exec();
    }

    /* 断言 1：连接建立（connected 信号 5s 内） */
    report(1, "ConnectionThread::connected within 5s", connected);

    Registry registry;
    bool announced = false;
    {
        QEventLoop loop;
        QTimer timeout;
        timeout.setSingleShot(true);
        QObject::connect(&registry, &Registry::interfacesAnnounced, [&] {
            announced = true;
            loop.quit();
        });
        QObject::connect(&timeout, &QTimer::timeout, &loop,
                         &QEventLoop::quit);
        registry.create(&connection);
        registry.setup();
        timeout.start(5000);
        loop.exec();
    }

    /* 断言 2：Registry 接口公告（interfacesAnnounced 信号 5s 内） */
    report(2, "Registry::interfacesAnnounced within 5s", announced);

    /* 断言 3：wl_compositor global 已公告 */
    report(3, "Registry::hasInterface(Compositor)",
           registry.hasInterface(Registry::Interface::Compositor));

    /* 断言 4：createCompositor / createSurface 返回有效对象 */
    Compositor *compositor = nullptr;
    Surface *surface = nullptr;
    if (announced) {
        const auto ann = registry.interface(Registry::Interface::Compositor);
        compositor = registry.createCompositor(ann.name, ann.version);
        if (compositor) {
            surface = compositor->createSurface();
        }
    }
    report(4, "createCompositor/createSurface returned non-null",
           compositor && surface);

    /* 断言 5：commit + flush 后 create_surface 到达服务端且计数 == 1。
     * 服务端线程每 ≤10ms dispatch 一次，1s 等待在进程内是确定性时序 */
    int count = -1;
    if (surface) {
        surface->commit();
        connection.flush();
        QEventLoop loop;
        QTimer::singleShot(1000, &loop, &QEventLoop::quit);
        loop.exec();
        count = mini_compositor_surface_count();
    }
    report(5, "server create_surface count == 1", count == 1);

    /* 清理：surface/compositor 无父对象须手动释放（先于 connection 断开），
     * connection/registry 栈对象析构即断开客户端连接 */
    delete surface;
    delete compositor;
    mini_compositor_stop();

    std::printf("[kwayland-e2e] SUMMARY: %d passed, %d failed\n",
                5 - g_failed, g_failed);
    std::fflush(stdout);
    return g_failed > 0 ? 1 : 0;
}
