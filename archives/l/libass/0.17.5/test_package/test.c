// test_package 实质测试：链接 libass 并调用字幕库 API（R34 反空壳）。
// 创建 ass_library、设置消息回调、分配样式、解析内存字幕并请求渲染尺寸。
#include <ass/ass.h>
#include <stdio.h>
#include <string.h>

static int msg_count = 0;
static void msg_cb(int level, const char *fmt, va_list va, void *data) {
    (void)level; (void)fmt; (void)va; (void)data;
    msg_count++;
}

int main(void) {
    // 断言 1: 库初始化（ass_library_init 返回非 NULL）
    ASS_Library *lib = ass_library_init();
    if (!lib) {
        fprintf(stderr, "FAIL: ass_library_init returned NULL\n");
        return 2;
    }

    // 断言 2: 消息回调注册后解析不崩溃
    ass_set_message_cb(lib, msg_cb, NULL);
    ASS_Renderer *renderer = ass_renderer_init(lib);
    if (!renderer) {
        fprintf(stderr, "FAIL: ass_renderer_init returned NULL\n");
        ass_library_done(lib);
        return 3;
    }

    // 断言 3: 内存字幕解析（简单 SRT/ASS 行）并设置帧尺寸不崩溃
    const char *subs =
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Text\n"
        "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,Hello HarmonyOS\n";
    ASS_Track *track = ass_read_memory(lib, subs, (int)strlen(subs), NULL);
    if (!track) {
        fprintf(stderr, "FAIL: ass_read_memory returned NULL\n");
        ass_renderer_done(renderer);
        ass_library_done(lib);
        return 4;
    }
    ass_set_frame_size(renderer, 1280, 720);
    ass_render_frame(renderer, track, 1500, NULL);

    printf("PASS: libass linked, track n_events=%d, msg_cb invoked=%d\n",
           track->n_events, msg_count);

    ass_free_track(track);
    ass_renderer_done(renderer);
    ass_library_done(lib);
    return 0;
}
