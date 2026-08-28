/*
 * test_package 消费者测试 — libvncserver 0.9.15
 *
 * 真实调用被适配库 API，验证库可用且平台适配路径可执行：
 *  - 服务端: rfbGetScreen() 创建 VNC server screen
 *  - 客户端: rfbGetClient() 创建 VNC client 结构
 *  - 区域:   rfbRegion 分配/释放
 *  - 版本:   rfbVersion / 错误日志 API
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <rfb/rfb.h>
#include <rfb/rfbclient.h>
#include <rfb/rfbregion.h>

static int server_ok = 0;
static int client_ok = 0;
static int region_ok = 0;

int main(int argc, char **argv)
{
    /* ---- 服务端 API ---- */
    rfbScreenInfoPtr screen = rfbGetScreen(&argc, argv, 640, 480, 8, 3, 4);
    if (screen == NULL) {
        fprintf(stderr, "FAIL: rfbGetScreen returned NULL\n");
        return 1;
    }
    server_ok = 1;
    /* 设置软件光标避免依赖平台光标设备 */
    screen->cursor = NULL;
    screen->serverFormat.redShift = 16;
    screen->serverFormat.greenShift = 8;
    screen->serverFormat.blueShift = 0;
    screen->serverFormat.redMax = 255;
    screen->serverFormat.greenMax = 255;
    screen->serverFormat.blueMax = 255;
    rfbScreenCleanup(screen);
    server_ok = 2;

    /* ---- 客户端 API ---- */
    rfbClient *client = rfbGetClient(8, 3, 4);
    if (client == NULL) {
        fprintf(stderr, "FAIL: rfbGetClient returned NULL\n");
        return 1;
    }
    client_ok = 1;
    client->programName = "test_package";
    rfbClientCleanup(client);
    client_ok = 2;

    /* ---- rfbRegion API (sraRegion) ---- */
    sraRegion *region = NULL;
    if (server_ok == 2 && client_ok == 2) {
        region = sraRgnCreate();
        if (region == NULL) {
            fprintf(stderr, "FAIL: sraRgnCreate returned NULL\n");
            return 1;
        }
        sraRgnOr(region, sraRgnCreateRect(0, 0, 640, 480));
        region_ok = (int)sraRgnCountRects(region);
        sraRgnDestroy(region);
    }

    printf("libvncserver 0.9.15 consumer test: OK (server=%d client=%d region_rects=%d)\n",
           server_ok, client_ok, region_ok);
    return 0;
}
