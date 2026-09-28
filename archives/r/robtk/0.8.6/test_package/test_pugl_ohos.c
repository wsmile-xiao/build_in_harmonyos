/* HarmonyOS specific test for the pugl OHOS backend (pugl/pugl_ohos.c).
 *
 * It exercises the platform layer directly - EGL + OpenGL ES context and
 * drawable management, the input bridge that a HarmonyOS application uses to
 * forward ArkUI touch/mouse events, frame read-back, resize and the
 * hide/show cycle - without any robtk widget on top.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <EGL/egl.h>
#include <GLES3/gl3.h>

#include "pugl/pugl_ohos.h"

static unsigned int g_checks   = 0;
static unsigned int g_failures = 0;

#define CHECK(cond, ...)                                   \
	do {                                                   \
		++g_checks;                                        \
		if (!(cond)) {                                     \
			++g_failures;                                  \
			printf("FAIL  ");                              \
		} else {                                           \
			printf("ok    ");                              \
		}                                                  \
		printf(__VA_ARGS__);                               \
		printf("\n");                                      \
		fflush(stdout);                                    \
	} while (0)

static int g_reshape  = 0;
static int g_display  = 0;
static int g_motion   = 0;
static int g_move_x   = -1000;
static int g_move_y   = -1000;
static int g_buttons  = 0;
static int g_presses  = 0;
static int g_scrolls  = 0;
static int g_specials = 0;
static int g_focus    = 0;

static const float g_bg[4] = { 0.25f, 0.50f, 0.75f, 1.00f };

static void
on_reshape(PuglView* view, int width, int height)
{
	(void)view;
	glViewport(0, 0, width, height);
	glClearColor(g_bg[0], g_bg[1], g_bg[2], g_bg[3]);
	glClear(GL_COLOR_BUFFER_BIT);
	++g_reshape;
}

static void
on_display(PuglView* view)
{
	(void)view;
	glClearColor(g_bg[0], g_bg[1], g_bg[2], g_bg[3]);
	glClear(GL_COLOR_BUFFER_BIT);
	++g_display;
}

static void
on_motion(PuglView* view, int x, int y)
{
	(void)view;
	++g_motion;
	if (x < 0 || y < 0) {
		/* pointer left the view (reported as -1,-1) */
		return;
	}
	g_move_x = x;
	g_move_y = y;
}

static void
on_mouse(PuglView* view, int button, bool press, int x, int y)
{
	(void)view;
	(void)button;
	(void)x;
	(void)y;
	++g_buttons;
	if (press) { ++g_presses; }
}

static void
on_scroll(PuglView* view, int x, int y, float dx, float dy)
{
	(void)view;
	(void)x;
	(void)y;
	(void)dx;
	(void)dy;
	++g_scrolls;
}

static void
on_special(PuglView* view, bool press, PuglKey key)
{
	(void)view;
	(void)press;
	(void)key;
	++g_specials;
}

static void
on_focus(PuglView* view, bool enter)
{
	(void)view;
	(void)enter;
	++g_focus;
}

int
main(void)
{
	printf("== pugl HarmonyOS backend test ==\n");

	/* parent == 0 selects offscreen rendering (EGL pbuffer) */
	PuglView* view = puglCreate(0, "robtk-ohos-test", 64, 48, 64, 48,
			false, false, 0);
	CHECK(view != NULL, "puglCreate() built an offscreen EGL/GLES view");
	if (!view) {
		return 1;
	}

	CHECK(puglGetNativeWindow(view) == 0,
			"offscreen view has no native window");

	puglSetHandle(view, NULL);
	puglSetReshapeFunc(view, on_reshape);
	puglSetDisplayFunc(view, on_display);
	puglSetMotionFunc(view, on_motion);
	puglSetMouseFunc(view, on_mouse);
	puglSetScrollFunc(view, on_scroll);
	puglSetSpecialFunc(view, on_special);
	puglSetFocusFunc(view, on_focus);

	CHECK(puglProcessEvents(view) == PUGL_SUCCESS, "puglProcessEvents()");
	CHECK(g_reshape == 1, "initial reshape happened (%d)", g_reshape);
	CHECK(g_display == 1, "initial display happened (%d)", g_display);

	/* the device must expose an OpenGL ES context */
	const char* version = (const char*)glGetString(GL_VERSION);
	CHECK(version != NULL, "OpenGL ES context is current: %s",
			version ? version : "()");
	CHECK(glGetError() == GL_NO_ERROR, "no GL error after the first frame");

	/* --- read the rendered frame back --------------------------------- */
	int w = 0, h = 0;
	unsigned char* frame = (unsigned char*)calloc(4 * 64 * 48, 1);
	CHECK(puglGrabFrame(view, &w, &h, frame) == 0, "puglGrabFrame()");
	CHECK(w == 64 && h == 48, "frame is %dx%d", w, h);

	/* bottom-up RGBA, uniform colour from on_display() */
	const int expect[3] = { 64, 128, 191 };
	int r = frame[0], g = frame[1], b = frame[2];
	CHECK(r == expect[0] && g == expect[1] && b == expect[2],
			"framebuffer content is %d,%d,%d (expected %d,%d,%d)",
			r, g, b, expect[0], expect[1], expect[2]);

	/* --- input bridge (ArkUI events are pushed by the host) ----------- */
	puglSendMotion(view, 11, 22, PUGL_MOD_SHIFT);
	puglSendMouse(view, 1, true, 11, 22, 0);
	puglSendMouse(view, 1, false, 11, 22, 0);
	puglSendScroll(view, 11, 22, 0.0f, 1.0f, 0);
	puglSendSpecial(view, true, PUGL_KEY_F5, 0);
	puglSendSpecial(view, false, PUGL_KEY_F5, 0);
	puglSendEnterLeave(view, true, 11, 22, 0);
	puglSendEnterLeave(view, false, 11, 22, 0);
	CHECK(g_motion == 0 && g_buttons == 0,
			"input stays queued until puglProcessEvents()");

	puglProcessEvents(view);
	CHECK(g_motion >= 3, "motion events delivered (%d)", g_motion);
	CHECK(g_move_x == 11 && g_move_y == 22, "motion coordinates %d,%d",
			g_move_x, g_move_y);
	CHECK(g_buttons == 2 && g_presses == 1,
			"button press/release delivered (%d/%d)", g_buttons, g_presses);
	CHECK(g_scrolls == 1, "scroll delivered (%d)", g_scrolls);
	CHECK(g_specials == 2, "special keys delivered (%d)", g_specials);
	CHECK(g_focus == 2, "focus enter/leave delivered (%d)", g_focus);

	/* modifier state is carried with every event */
	puglSendMotion(view, 33, 44, PUGL_MOD_CTRL);
	puglProcessEvents(view);
	CHECK(puglGetModifiers(view) == PUGL_MOD_CTRL,
			"modifier state is tracked (0x%x)", puglGetModifiers(view));
	CHECK(g_move_x == 33 && g_move_y == 44, "motion coordinates %d,%d",
			g_move_x, g_move_y);

	/* --- redisplay and resize ---------------------------------------- */
	const int displays_before = g_display;
	puglPostRedisplay(view);
	puglProcessEvents(view);
	CHECK(g_display == displays_before + 1,
			"puglPostRedisplay() triggers one redraw (%d -> %d)",
			displays_before, g_display);

	const int reshapes_before = g_reshape;
	puglUpdateGeometryConstraints(view, 96, 72, false);
	puglPostResize(view);
	puglProcessEvents(view);
	CHECK(g_reshape == reshapes_before + 1,
			"puglPostResize() re-creates the drawable (%d -> %d)",
			reshapes_before, g_reshape);

	/* --- hide / show: hidden views must not be drawn ------------------ */
	puglHideWindow(view);
	puglPostRedisplay(view);
	const int displays_hidden = g_display;
	puglProcessEvents(view);
	CHECK(g_display == displays_hidden,
			"a hidden view is not rendered (%d)", g_display);
	puglShowWindow(view);
	puglProcessEvents(view);
	CHECK(g_display == displays_hidden + 1,
			"puglShowWindow() resumes rendering (%d)", g_display);

	/* --- detaching the native window keeps the UI alive -------------- */
	CHECK(puglSetNativeWindow(view, 0) == PUGL_SUCCESS,
			"puglSetNativeWindow(0) detaches the window");

	/* --- teardown: puglDestroy() must release the EGL context -------- */
	CHECK(eglGetCurrentContext() != EGL_NO_CONTEXT,
			"EGL context is current while the view lives");
	puglDestroy(view);
	CHECK(eglGetCurrentContext() == EGL_NO_CONTEXT,
			"puglDestroy() released the EGL context (current context = %p)",
			(void*)eglGetCurrentContext());
	free(frame);

	/* --- degenerate geometry must not break the offscreen drawable ---- */
	/* A UI whose text metrics are meaningless (host without usable fonts)
	 * can ask for a negative size; EGL would reject that with
	 * EGL_BAD_ATTRIBUTE, so the backend has to clamp it. */
	PuglView* degenerate = puglCreate(0, "robtk-ohos-degenerate",
			-1, -1, -1, -1, false, false, 0);
	CHECK(degenerate != NULL, "puglCreate() survives a degenerate size (-1x-1)");
	if (degenerate) {
		g_reshape = 0;
		g_display = 0;
		puglSetHandle(degenerate, NULL);
		puglSetReshapeFunc(degenerate, on_reshape);
		puglSetDisplayFunc(degenerate, on_display);
		puglProcessEvents(degenerate);
		CHECK(g_reshape == 1 && g_display == 1,
				"the clamped drawable is set up and rendered (%d reshape / %d display)",
				g_reshape, g_display);

		int sw = 0, sh = 0;
		unsigned char* sbuf = (unsigned char*)calloc(4 * 64 * 64, 1);
		const int src = puglGrabFrame(degenerate, &sw, &sh, sbuf);
		CHECK(src == 0 && sw >= 1 && sh >= 1,
				"the clamped drawable can be read back (%dx%d, rc=%d)", sw, sh, src);
		free(sbuf);
		puglDestroy(degenerate);
	}

	printf("== %u checks, %u failures ==\n", g_checks, g_failures);
	return g_failures ? 1 : 0;
}
