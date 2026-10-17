#ifndef MINI_COMPOSITOR_H
#define MINI_COMPOSITOR_H

#ifdef __cplusplus
extern "C" {
#endif

/* 起一个服务端线程，socketpair 的客户端端经 client_fd_out 返回。
 * 返回 0 成功，-1 失败。 */
int mini_compositor_start(int *client_fd_out);

/* 停止服务端线程并销毁 display（调用方须先断开客户端连接）。 */
void mini_compositor_stop(void);

/* 服务端 wl_compositor create_surface 请求到达次数。 */
int mini_compositor_surface_count(void);

#ifdef __cplusplus
}
#endif

#endif /* MINI_COMPOSITOR_H */
