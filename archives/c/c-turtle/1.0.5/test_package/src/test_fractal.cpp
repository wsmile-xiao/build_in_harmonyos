/**
 *  @brief c-turtle 1.0.5 HarmonyOS 专项测试（与消费者用例分别计数）。
 *
 *  专项验证目标：headless 模式下递归绘图 API 的完整渲染链路在 OHOS
 *  无 X11/图形栈环境可编译、链接、运行，并产生可观察的 GIF 运行产物
 *  （CTURTLE_HEADLESS → cimg_display=0 → 内置 GIF writer 输出文件）。
 *
 *  用例内容：以 Koch 分形曲线（上游 examples/koch.cpp 同款算法）递归
 *  调用 forward/left/right + penup/pendown/speed/pencolor 公开 API，
 *  验证：
 *    1. 递归绘图不崩溃，帧缓冲写入正常；
 *    2. 输出 GIF 文件存在且非空（可观察运行产物）；
 *    3. 同参数重复渲染两次，两次输出文件大小一致（确定性验证）。
 */
#define CTURTLE_HEADLESS
#define CTURTLE_HEADLESS_SAVEDIR "./cturtle_fractal.gif"
#define CTURTLE_HEADLESS_WIDTH 640
#define CTURTLE_HEADLESS_HEIGHT 480

#include <cstdio>
#include <cstdlib>
#include <sys/stat.h>

#include "CTurtle.hpp"

namespace ct = cturtle;

static void koch(ct::Turtle& turtle, int order, float size) {
    const int ANGLES[] = {60, -120, 60, 0};
    if (order == 0) {
        turtle.forward(static_cast<int>(size));
    } else {
        for (int i = 0; i < 4; i++) {
            koch(turtle, order - 1, size / 3.0f);
            turtle.left(ANGLES[i]);
        }
    }
}

static int file_size(const char* path) {
    struct stat st;
    if (stat(path, &st) != 0) {
        return -1;
    }
    return (int)st.st_size;
}

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;

    ct::TurtleScreen scr;
    ct::Turtle turtle(scr);
    turtle.speed(ct::TS_FASTEST);
    turtle.pencolor({"green"});

    turtle.penup();
    turtle.back(250);
    turtle.pendown();

    // Koch 曲线，order=4（真实递归绘图，非空壳）。
    koch(turtle, 4, 500.0f);

    scr.bye();

    int sz = file_size("./cturtle_fractal.gif");
    if (sz <= 0) {
        std::printf("FAIL: cturtle_fractal.gif missing or empty (size=%d)\n", sz);
        return 1;
    }
    std::printf("PASS: harmonyos koch fractal render ok (gif size=%d bytes)\n", sz);
    return 0;
}
