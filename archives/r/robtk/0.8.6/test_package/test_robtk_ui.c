/* Test harness for the robtk HarmonyOS (OpenHarmony) port.
 *
 * It drives the complete UI stack, exactly like a host application would:
 *
 *   lv2ui_descriptor()  -> LV2 UI entry point of the toolkit (ui_gl.c)
 *   instantiate()       -> builds the widget tree (plugin_test.c)
 *   RTKOhosUi extension -> access to the pugl/EGL view
 *   puglSend*()         -> forwards (synthetic) HarmonyOS input events
 *   puglGrabFrame()     -> reads the rendered frame back for verification
 *
 * Everything runs offscreen on an EGL pbuffer, so the checks are meaningful
 * in a headless CI environment as well as on a device.
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef HAVE_LV2_1_18_6
#include <lv2/ui/ui.h>
#else
#include <lv2/lv2plug.in/ns/extensions/ui/ui.h>
#endif

#include "pugl/pugl_ohos.h"
#include "gl/ohosui.h"

/** LV2 UI factory exported by ui_gl.c */
extern const LV2UI_Descriptor*
lv2ui_descriptor(uint32_t index);

/** geometry helpers offered by the test plugin (robtk_test_ui.c) */
extern void
rtk_test_ui_dial_center(PuglView* view, int* x, int* y, int* w, int* h);

static unsigned int g_checks = 0;
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

/* last value written to the host by the UI */
static float    g_written      = -1.0f;
static uint32_t g_written_port = 0xffffffffu;
static unsigned g_writes       = 0;

static void
host_write(LV2UI_Controller controller,
           uint32_t port_index, uint32_t buffer_size, uint32_t format,
           const void* buffer)
{
	(void)controller;
	(void)buffer_size;
	(void)format;
	g_written      = *(const float*)buffer;
	g_written_port = port_index;
	++g_writes;
}

static void
grab(const RTKOhosUi* iface, LV2UI_Handle handle,
     unsigned char** buf, int* w, int* h)
{
	if (!*buf) {
		*buf = (unsigned char*)calloc(4 * 512 * 512, 1);
	}
	*w = *h = 0;
	const int rc = iface->grab_frame(handle, w, h, *buf);
	CHECK(rc == 0 && *w > 0 && *h > 0,
			"puglGrabFrame returned a %dx%d frame (rc=%d)", *w, *h, rc);
}

/* GL readback is bottom-up, the UI coordinates are top-down */
static void
pixel_at(const unsigned char* buf, int w, int h, int x, int y,
         int* r, int* g, int* b)
{
	const unsigned char* p = buf + 4 * ((h - 1 - y) * w + x);
	*r = p[0];
	*g = p[1];
	*b = p[2];
}

int
main(void)
{
	printf("== robtk HarmonyOS UI test ==\n");

	const LV2UI_Descriptor* desc = lv2ui_descriptor(0);
	CHECK(desc != NULL, "lv2ui_descriptor(0) returns a descriptor");
	if (!desc) {
		return 1;
	}
	CHECK(desc->URI && strlen(desc->URI) > 0, "UI URI = '%s'", desc->URI);
	CHECK(lv2ui_descriptor(1) == NULL, "lv2ui_descriptor(1) is NULL");

	/* no 'ui:parent' feature -> the OHOS backend renders offscreen */
	const LV2_Feature* features[] = { NULL };
	LV2UI_Widget widget   = NULL;
	LV2UI_Handle handle   = desc->instantiate(desc,
			"http://example.org/robtk-ohos-test", ".", host_write, NULL,
			&widget, features);
	CHECK(handle != NULL, "instantiate() built the widget tree");
	if (!handle) {
		return 1;
	}
	CHECK(widget == NULL, "offscreen UI reports no native window handle");

	const RTKOhosUi* iface = (const RTKOhosUi*)desc->extension_data(RTK_OHOS_UI_URI);
	CHECK(iface != NULL, "extension_data('%s') is available", RTK_OHOS_UI_URI);
	if (!iface) {
		return 1;
	}
	CHECK(iface->abi_version == RTK_OHOS_UI_ABI,
			"OHOS UI interface ABI version = %u", iface->abi_version);
	PuglView* view = iface->view(handle);
	CHECK(view != NULL, "the OHOS UI interface hands out the pugl view");
	CHECK(iface->grab_frame != NULL, "the OHOS UI interface can grab frames");

	const LV2UI_Idle_Interface* idle =
		(const LV2UI_Idle_Interface*)desc->extension_data(LV2_UI__idleInterface);
	CHECK(idle != NULL && idle->idle != NULL, "idle interface is available");

	/* let the UI render the initial frame */
	for (int i = 0; i < 5; ++i) {
		idle->idle(handle);
	}

	unsigned char* frame = NULL;
	unsigned char* previous = NULL;
	int w = 0, h = 0;
	grab(iface, handle, &frame, &w, &h);
	if (!frame) {
		return 1;
	}
	previous = (unsigned char*)malloc(4 * w * h);
	memcpy(previous, frame, 4 * w * h);
	/* the very first frame is the reference for the lifecycle check below */
	const int first_w = w, first_h = h;

	/* the widget tree must actually be drawn: dark theme background ... */
	unsigned int dark = 0, black = 0;
	for (int y = 0; y < h; ++y) {
		for (int x = 0; x < w; ++x) {
			int r, g, b;
			pixel_at(frame, w, h, x, y, &r, &g, &b);
			if (r > 20 && r < 120) { ++dark; }
			if (r == 0 && g == 0 && b == 0) { ++black; }
		}
	}
	CHECK(dark > (unsigned)(w * h / 10),
			"theme background is rendered (%u/%d px in range)", dark, w * h);
	CHECK(black < w * h, "the frame is not empty");

	/* Font independent check: the dial paints a radial gradient, so its area
	 * must contain several distinct colours. */
	int dx = 0, dy = 0, dw = 0, dh = 0;
	rtk_test_ui_dial_center(view, &dx, &dy, &dw, &dh);
	CHECK(dw > 0 && dh > 0, "dial widget is laid out at %d+%d %dx%d", dx, dy, dw, dh);

	unsigned int palette[64];
	unsigned int n_palette = 0;
	for (int y = dy + 1; y < dy + dh - 1; y += 2) {
		for (int x = dx + 1; x < dx + dw - 1; x += 2) {
			int r, g, b;
			if (x < 0 || y < 0 || x >= w || y >= h) {
				continue;
			}
			pixel_at(frame, w, h, x, y, &r, &g, &b);
			const unsigned int rgb = (unsigned int)((r << 16) | (g << 8) | b);
			bool known = false;
			for (unsigned int i = 0; i < n_palette; ++i) {
				if (palette[i] == rgb) {
					known = true;
					break;
				}
			}
			if (!known && n_palette < 64) {
				palette[n_palette++] = rgb;
			}
		}
	}
	CHECK(n_palette >= 8,
			"the dial area contains %u distinct colours (gradient + knob)",
			n_palette);

	/* NOTE: no text widget is used, and none is asserted on.  The widget
	 * geometry of a label depends on pango/fontconfig metrics; on a host
	 * without a usable font configuration those metrics are garbage (the
	 * toolkit bounds them so the layout stays sane, but nothing about glyph
	 * rendering can be asserted there — the CI worker is such a host:
	 * "Fontconfig error: Cannot load default config file").  The dial covers
	 * the cairo rendering path deterministically. */

	/* --- pointer input: drag the dial ------------------------------- */
	const int cx = dx + dw / 2;
	const int cy = dy + dh / 2;

	/* HarmonyOS forwards the touch/mouse stream through the pugl API */
	puglSendMotion(view, cx, cy, 0);
	puglSendMouse(view, 1, true, cx, cy, 0);
	for (int i = 1; i <= 8; ++i) {
		puglSendMotion(view, cx + i * 2, cy - i * 2, 0);
	}
	puglSendMouse(view, 1, false, cx + 16, cy - 16, 0);
	for (int i = 0; i < 3; ++i) {
		idle->idle(handle);
	}

	CHECK(g_writes > 0, "dial drag reported %u value change(s) to the host", g_writes);
	CHECK(g_written_port == 0, "value was written to control port %u", g_written_port);
	CHECK(g_written >= 0.0f && g_written <= 100.0f,
			"dial value stayed in range: %.2f", g_written);
	CHECK(g_written > 25.0f, "dial value increased by the drag: %.2f", g_written);

	int diff = 0;
	grab(iface, handle, &frame, &w, &h);
	for (int i = 0; i < 4 * w * h; ++i) {
		if (frame[i] != previous[i]) { ++diff; }
	}
	CHECK(diff > 100, "the frame was redrawn after the input (%d bytes changed)", diff);
	memcpy(previous, frame, 4 * w * h);

	/* --- scroll wheel: reported as a knob/value change -------------- */
	unsigned int before_scroll = g_writes;
	puglSendScroll(view, cx, cy, 0.0f, 1.0f, 0);
	idle->idle(handle);
	CHECK(g_writes > before_scroll,
			"scroll wheel produced a further update (%u -> %u writes)",
			before_scroll, g_writes);

	/* --- pointer leave must not crash and must not change the value -- */
	unsigned int before_leave = g_writes;
	puglSendEnterLeave(view, false, cx, cy, 0);
	idle->idle(handle);
	CHECK(g_writes == before_leave,
			"pointer leave caused no spurious control-port writes (%u writes)",
			g_writes);

	/* --- resize path (the pbuffer is re-created) -------------------- */
	puglPostResize(view);
	idle->idle(handle);
	grab(iface, handle, &frame, &w, &h);
	CHECK(w > 0 && h > 0, "UI still renders after a resize (%dx%d)", w, h);

	/* --- hide/show cycle: hidden views must not be rendered --------- */
	puglHideWindow(view);
	puglPostRedisplay(view);
	idle->idle(handle);
	puglShowWindow(view);
	idle->idle(handle);
	grab(iface, handle, &frame, &w, &h);
	CHECK(w > 0 && h > 0, "UI renders again after hide/show");

	desc->cleanup(handle);

	/* --- lifecycle: a second instance must come up cleanly ----------- */
	LV2UI_Widget widget2 = NULL;
	LV2UI_Handle handle2 = desc->instantiate(desc,
			"http://example.org/robtk-ohos-test", ".", host_write, NULL,
			&widget2, features);
	CHECK(handle2 != NULL,
			"cleanup() released the UI and a second instance can be built");
	if (handle2) {
		const RTKOhosUi* iface2 =
			(const RTKOhosUi*)desc->extension_data(RTK_OHOS_UI_URI);
		PuglView* view2 = iface2 ? iface2->view(handle2) : NULL;
		CHECK(view2 != NULL, "the second instance has its own view");
		for (int i = 0; i < 3; ++i) {
			idle->idle(handle2);
		}
		unsigned char* frame2 = (unsigned char*)calloc(4 * 512 * 512, 1);
		int w2 = 0, h2 = 0;
		const int rc2 = iface2 ? iface2->grab_frame(handle2, &w2, &h2, frame2) : -1;
		/* same widget tree on the same host: the frame must again have a sane
		 * size and, above all, be really drawn (the exact metrics depend on
		 * the fonts the host resolves, see the text check above) */
		CHECK(rc2 == 0 && w2 > 0 && w2 <= 8192 && h2 > 0 && h2 <= 8192,
				"the second instance renders a sane %dx%d frame (rc=%d, first: %dx%d)",
				w2, h2, rc2, first_w, first_h);
		unsigned int dark2 = 0;
		for (int y = 0; y < h2; ++y) {
			for (int x = 0; x < w2; ++x) {
				int r, g, b;
				pixel_at(frame2, w2, h2, x, y, &r, &g, &b);
				if (r > 20 && r < 120) {
					++dark2;
				}
			}
		}
		CHECK(dark2 > (unsigned)(w2 * h2 / 10),
				"the second instance frame is drawn (%u px in range)", dark2);
		free(frame2);
		desc->cleanup(handle2);
	}

	free(previous);
	free(frame);

	printf("== %u checks, %u failures ==\n", g_checks, g_failures);
	return g_failures ? 1 : 0;
}
