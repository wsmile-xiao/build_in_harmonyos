/* mini_compositor.c — 进程内迷你 Wayland 合成器（test_package 专用）
 *
 * kwayland 6.7.2 上游未注册 ctest 测试（见 notes.md），运行时验证由本
 * 合成器 + client_roundtrip 承担：合成器跑在独立线程，socketpair 一端
 * 经 wl_client_create 挂成 wl_client（已连接的 fd；监听 socket 那套
 * wl_display_add_socket_fd 对 socketpair 端点只会一直 accept() 失败），
 * 注册 wl_compositor v4 + wl_shm v1 两个 global；KWaylandClient 经
 * ConnectionThread::setSocketFd 从另一端接入，createSurface 请求到达
 * 服务端时计数。
 *
 * 实现表必须填满：libwayland 派发请求时若该资源的实现表项为 NULL 会直接
 * abort（"listener function for opcode N of X is NULL"），所以每个
 * wl_resource（surface/region/shm pool/buffer）都带完整实现结构体；
 * 迷你合成器不渲染，除 destroy 外的请求全部收下即丢。
 */
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <sys/socket.h>
#include <unistd.h>

#include <wayland-server.h>

static struct wl_display *g_display;
static pthread_t g_thread;
static atomic_int g_stop = 0;
static atomic_int g_surfaces = 0;

/* ---- 通用空实现（签名与目标请求一一对应，多余参数显式丢弃）---- */

static void
resource_destroy(struct wl_client *client, struct wl_resource *resource)
{
    (void)client;
    wl_resource_destroy(resource);
}

static void
resource_noop(struct wl_client *client, struct wl_resource *resource)
{
    (void)client;
    (void)resource;
}

static void
resource_noop_int(struct wl_client *client, struct wl_resource *resource,
                  int32_t value)
{
    (void)client;
    (void)resource;
    (void)value;
}

static void
resource_noop_pair(struct wl_client *client, struct wl_resource *resource,
                   int32_t first, int32_t second)
{
    (void)client;
    (void)resource;
    (void)first;
    (void)second;
}

static void
resource_noop_rect(struct wl_client *client, struct wl_resource *resource,
                   int32_t x, int32_t y, int32_t width, int32_t height)
{
    (void)client;
    (void)resource;
    (void)x;
    (void)y;
    (void)width;
    (void)height;
}

/* ---- wl_region ---- */

static const struct wl_region_interface region_impl = {
    .destroy = resource_destroy,
    .add = resource_noop_rect,
    .subtract = resource_noop_rect,
};

static void
compositor_create_region(struct wl_client *client, struct wl_resource *resource,
                         uint32_t id)
{
    (void)resource;
    struct wl_resource *region =
        wl_resource_create(client, &wl_region_interface, 1, id);
    wl_resource_set_implementation(region, &region_impl, NULL, NULL);
}

/* ---- wl_buffer / wl_shm_pool / wl_shm ---- */

static const struct wl_buffer_interface buffer_impl = {
    .destroy = resource_destroy,
};

static void
pool_create_buffer(struct wl_client *client, struct wl_resource *resource,
                   uint32_t id, int32_t offset, int32_t width, int32_t height,
                   int32_t stride, uint32_t format)
{
    /* 迷你合成器不 mmap 也不取像素：只把 buffer 资源建出来，保证客户端
     * 后续（若有）请求不会打到空实现 */
    (void)resource;
    (void)offset;
    (void)width;
    (void)height;
    (void)stride;
    (void)format;
    struct wl_resource *buffer =
        wl_resource_create(client, &wl_buffer_interface, 1, id);
    wl_resource_set_implementation(buffer, &buffer_impl, NULL, NULL);
}

static const struct wl_shm_pool_interface pool_impl = {
    .create_buffer = pool_create_buffer,
    .destroy = resource_destroy,
    .resize = resource_noop_int,
};

static void
shm_create_pool(struct wl_client *client, struct wl_resource *resource,
                uint32_t id, int32_t fd, int32_t size)
{
    /* fd 所有权随请求转移，收下即关（不 mmap） */
    (void)resource;
    (void)size;
    close(fd);
    struct wl_resource *pool =
        wl_resource_create(client, &wl_shm_pool_interface, 1, id);
    wl_resource_set_implementation(pool, &pool_impl, NULL, NULL);
}

static const struct wl_shm_interface shm_impl = {
    .create_pool = shm_create_pool,
};

static void
shm_bind(struct wl_client *client, void *data, uint32_t version, uint32_t id)
{
    struct wl_resource *resource =
        wl_resource_create(client, &wl_shm_interface, version, id);
    wl_resource_set_implementation(resource, &shm_impl, data, NULL);
}

/* ---- wl_surface ---- */

static void
surface_attach(struct wl_client *client, struct wl_resource *resource,
               struct wl_resource *buffer, int32_t x, int32_t y)
{
    (void)client;
    (void)resource;
    (void)buffer;
    (void)x;
    (void)y;
}

static void
surface_frame(struct wl_client *client, struct wl_resource *resource,
              uint32_t callback)
{
    /* 不渲染也就不回 wl_callback.done；本测试不等帧回调 */
    (void)client;
    (void)resource;
    (void)callback;
}

static void
surface_set_region(struct wl_client *client, struct wl_resource *resource,
                   struct wl_resource *region)
{
    (void)client;
    (void)resource;
    (void)region;
}

static const struct wl_surface_interface surface_impl = {
    .destroy = resource_destroy,
    .attach = surface_attach,
    .damage = resource_noop_rect,
    .frame = surface_frame,
    .set_opaque_region = surface_set_region,
    .set_input_region = surface_set_region,
    .commit = resource_noop,
    .set_buffer_transform = resource_noop_int,
    .set_buffer_scale = resource_noop_int,
    .damage_buffer = resource_noop_rect,
    .offset = resource_noop_pair,
};

static void
compositor_create_surface(struct wl_client *client,
                          struct wl_resource *resource, uint32_t id)
{
    /* 关键断言点：客户端 createSurface 到达即计数，并给客户端一个
     * 合法的 wl_surface 资源让请求完整生效 */
    (void)resource;
    atomic_fetch_add(&g_surfaces, 1);
    struct wl_resource *surface =
        wl_resource_create(client, &wl_surface_interface, 4, id);
    wl_resource_set_implementation(surface, &surface_impl, NULL, NULL);
}

static const struct wl_compositor_interface compositor_impl = {
    .create_surface = compositor_create_surface,
    .create_region = compositor_create_region,
};

static void
compositor_bind(struct wl_client *client, void *data, uint32_t version,
                uint32_t id)
{
    struct wl_resource *resource =
        wl_resource_create(client, &wl_compositor_interface, version, id);
    wl_resource_set_implementation(resource, &compositor_impl, data, NULL);
}

static void *
server_thread(void *arg)
{
    struct wl_display *display = arg;
    struct wl_event_loop *loop = wl_display_get_event_loop(display);
    while (!atomic_load(&g_stop)) {
        wl_event_loop_dispatch(loop, 10);
        wl_display_flush_clients(display);
    }
    return NULL;
}

int
mini_compositor_start(int *client_fd_out)
{
    int sv[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0)
        return -1;

    g_display = wl_display_create();
    if (!g_display) {
        close(sv[0]);
        close(sv[1]);
        return -1;
    }

    /* 先注册 global 再接入连接：客户端对象建立后请求 registry 时
     * 两个 global 都会完整公告 */
    wl_global_create(g_display, &wl_compositor_interface, 4, NULL,
                     compositor_bind);
    wl_global_create(g_display, &wl_shm_interface, 1, NULL, shm_bind);

    /* socketpair 端点已经是"连上的 fd"，必须走 wl_client_create（socket
     * activation 同款接口）；wl_display_add_socket_fd 要求**监听** socket，
     * 拿 socketpair 端点会每个事件循环轮询都 accept() 失败（真机上刷屏
     * "failed to accept: Invalid argument"，客户端对象永远建不出来，
     * registry 一个 global 都公告不出去）。fd 所有权随 wl_client_create
     * 交给 display，destroy 时一并关闭 */
    if (!wl_client_create(g_display, sv[0])) {
        wl_display_destroy(g_display);
        close(sv[1]);
        return -1;
    }

    atomic_store(&g_stop, 0);
    atomic_store(&g_surfaces, 0);
    if (pthread_create(&g_thread, NULL, server_thread, g_display) != 0) {
        wl_display_destroy(g_display);
        close(sv[1]);
        return -1;
    }

    *client_fd_out = sv[1];
    return 0;
}

void
mini_compositor_stop(void)
{
    atomic_store(&g_stop, 1);
    pthread_join(g_thread, NULL);
    wl_display_destroy(g_display);
    g_display = NULL;
}

int
mini_compositor_surface_count(void)
{
    return atomic_load(&g_surfaces);
}
