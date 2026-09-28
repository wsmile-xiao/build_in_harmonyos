/* Test UI for the robtk HarmonyOS port.
 *
 * This file plays the role of the plugin specific UI source (the gui/ sources
 * of the x42 plugin projects) which is compiled into ui_gl.c through
 * PLUGIN_SOURCE.  It builds a small but real robtk user interface: a dial
 * (a font independent widget), and reports dial changes to the LV2 host
 * through the write function.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <assert.h>

/* ui_gl.c includes "robtk.h" (and thus the whole toolkit) before this file */

#define TEST_UI_PORT_DIAL 0

typedef struct {
	RobWidget* toplevel;
	RobWidget* vbox;
	RobTkDial* dial;

	LV2UI_Write_Function write;
	LV2UI_Controller     controller;

	float  value;
	size_t redraws;
	bool   enabled;   /* set by ui_enable()/ui_disable() */
} RTKTestUI;

/* Called by the toolkit when the UI becomes visible / is hidden again: port
 * events are only applied while the UI is on screen. */
static void
ui_enable(LV2UI_Handle handle)
{
	RTKTestUI* ui = (RTKTestUI*)handle;
	if (ui) { ui->enabled = true; }
}

static void
ui_disable(LV2UI_Handle handle)
{
	RTKTestUI* ui = (RTKTestUI*)handle;
	if (ui) { ui->enabled = false; }
}

static bool
ui_dial_changed(RobWidget* w, void* handle)
{
	(void)w;
	RTKTestUI* ui = (RTKTestUI*)handle;
	ui->value = robtk_dial_get_value(ui->dial);
	if (ui->write) {
		ui->write(ui->controller, TEST_UI_PORT_DIAL,
				sizeof(float), 0, &ui->value);
	}
	return TRUE;
}

static void
ui_scale_changed(RobWidget* w, void* handle)
{
	(void)w;
	(void)handle;
}

static LV2UI_Handle
instantiate(void *const               ui_toplevel,
		const LV2UI_Descriptor*  descriptor,
		const char*              plugin_uri,
		const char*              bundle_path,
		LV2UI_Write_Function     write_function,
		LV2UI_Controller         controller,
		RobWidget**              widget,
		const LV2_Feature* const* features)
{
	(void)descriptor;
	(void)plugin_uri;
	(void)bundle_path;
	(void)features;

	if (!widget) {
		return NULL;
	}

	RTKTestUI* ui = (RTKTestUI*)calloc(1, sizeof(RTKTestUI));
	if (!ui) {
		return NULL;
	}

	ui->write      = write_function;
	ui->controller = controller;
	ui->value      = 25.0f;

	/* The UI deliberately contains no text widget: the widget geometry of a
	 * label depends on pango/fontconfig metrics, and on a host without a
	 * usable font configuration those metrics are garbage (harmless for the
	 * layout thanks to the toolkit's bound, but text rendering itself is not
	 * something that can be asserted on such a host).  The dial is pure
	 * cairo, so the rendering pipeline is verified deterministically. */
	ui->dial  = robtk_dial_new(0.0f, 100.0f, 1.0f);
	robtk_dial_set_value(ui->dial, ui->value);
	robtk_dial_set_callback(ui->dial, ui_dial_changed, ui);

	ui->vbox = rob_vbox_new(FALSE, 0);
	rob_vbox_child_pack(ui->vbox, robtk_dial_widget(ui->dial), TRUE, TRUE);

	robwidget_make_toplevel(ui->vbox, ui_toplevel);
	robwidget_toplevel_enable_scaling(ui->vbox, ui_scale_changed, ui);

	ui->toplevel = ui->vbox;
	*widget = ui->toplevel;

	return ui;
}

static void
cleanup(LV2UI_Handle handle)
{
	RTKTestUI* ui = (RTKTestUI*)handle;
	if (!ui) {
		return;
	}
	robtk_dial_destroy(ui->dial);
	robwidget_destroy(ui->vbox);
	free(ui);
}

static enum LVGLResize
plugin_scale_mode(LV2UI_Handle handle)
{
	(void)handle;
	return LVGL_ZOOM_TO_ASPECT;
}

static void
port_event(LV2UI_Handle handle,
           uint32_t     port_index,
           uint32_t     buffer_size,
           uint32_t     format,
           const void*  buffer)
{
	RTKTestUI* ui = (RTKTestUI*)handle;
	if (format != 0 || buffer_size != sizeof(float) || port_index != TEST_UI_PORT_DIAL) {
		return;
	}
	if (!ui->enabled) {
		return;
	}
	ui->value = *(const float*)buffer;
	robtk_dial_set_value(ui->dial, ui->value);
}

static const void*
extension_data(const char* uri)
{
	(void)uri;
	return NULL;
}

/* Test-only helper: report where the dial ended up so that the harness can
 * aim its (synthetic) pointer input at the widget. */
void
rtk_test_ui_dial_center(PuglView* view, int* x, int* y, int* w, int* h)
{
	GLrobtkLV2UI* self = (GLrobtkLV2UI*)puglGetHandle(view);
	RTKTestUI* ui = (RTKTestUI*)self->ui;
	RobWidget* dial = robtk_dial_widget(ui->dial);
	*x = (int)(ui->toplevel->area.x + dial->trel.x);
	*y = (int)(ui->toplevel->area.y + dial->trel.y);
	*w = (int)dial->trel.width;
	*h = (int)dial->trel.height;
}
