/**
 *  @brief c-turtle 1.0.5 HarmonyOS 专项消费者测试（test_package L1）。
 *
 *  以业务上层组件视角使用 c-turtle：仅通过已安装的公开头 CTurtle.hpp
 *  调用公开 API。headless 模式（CTURTLE_HEADLESS）下 CImg 显示后端
 *  (cimg_display=0) 自动关闭，无需 X11/图形栈；画面写为 GIF 文件。
 *
 *  验证内容：
 *    1. TurtleScreen + Turtle 创建与画方（forward/right 循环）；
 *    2. 公开坐标 API xcor()/ycor() 断言位置可观察；
 *    3. write() 文本绘制；
 *    4. scr.bye() 输出 GIF 文件存在且非空（可观察运行产物）。
 */
#define CTURTLE_HEADLESS
#define CTURTLE_HEADLESS_SAVEDIR "./cturtle_test.gif"
#define CTURTLE_HEADLESS_WIDTH 400
#define CTURTLE_HEADLESS_HEIGHT 300

#include <cstdio>
#include <cstdlib>
#include <sys/stat.h>

#include "CTurtle.hpp"

namespace ct = cturtle;

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
    ct::Turtle rt(scr);

    rt.speed(ct::TS_FASTEST);
    rt.pencolor({"black"});

    // 画一个 100x100 正方形：4 次 forward(100) + right(90)。
    for (int i = 0; i < 4; i++) {
        rt.forward(100);
        rt.right(90);
    }

    // 断言 1：回到起点附近（公开 API xcor/ycor，整数坐标）。
    int fx = rt.xcor();
    int fy = rt.ycor();
    if (fx != 0 || fy != 0) {
        std::printf("FAIL: after square, xcor=%d ycor=%d, expected (0,0)\n", fx, fy);
        return 1;
    }

    // 断言 2：中间步进位置可观察（前进 50 后 xcor 应 > 0，heading 向东）。
    rt.home();
    rt.forward(50);
    int mx = rt.xcor();
    if (!(mx > 0)) {
        std::printf("FAIL: after forward(50), xcor=%d, expected >0\n", mx);
        return 2;
    }

    // 文本绘制（公开 API write）。
    rt.write("cturtle-ohos-test");

    // 断言 3：headless 输出 GIF 非空（bye 触发写盘）。
    scr.bye();
    int sz = file_size("./cturtle_test.gif");
    if (sz <= 0) {
        std::printf("FAIL: cturtle_test.gif missing or empty (size=%d)\n", sz);
        return 3;
    }

    std::printf("PASS: c-turtle consumer test ok (gif size=%d bytes)\n", sz);
    return 0;
}
