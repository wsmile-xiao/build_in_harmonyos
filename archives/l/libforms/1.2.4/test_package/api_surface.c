/*
 * api_surface.c — link-time contract for the installed libforms / libflimage.
 *
 * XForms has no upstream automated test suite (the release ships no TESTS and
 * no check_PROGRAMS, and this platform has no X server to drive the demo
 * programs), so the ABI of the shared objects is what a consumer can actually
 * check.  Every symbol below is referenced through __typeof__(&name), which
 * forces the compiler to type-check the declaration in the installed header
 * and the linker to emit a live relocation against the exported definition:
 * a renamed, removed or re-typed public entry point fails here at link time
 * instead of silently at a customer's runtime.  E530.
 */

#include <forms.h>
#include <flimage.h>

#define PROBE(name) static __typeof__(&name) volatile live_##name = &name

/* libforms.so.2 — form lifecycle */
PROBE(fl_free_form);
PROBE(fl_do_forms);
PROBE(fl_check_forms);
PROBE(fl_show_form);
PROBE(fl_set_form_title);
PROBE(fl_set_focus_object);
/* libforms.so.2 — widget construction and access */
PROBE(fl_add_button);
PROBE(fl_add_browser);
PROBE(fl_add_input);
PROBE(fl_add_timer);
PROBE(fl_get_button);
PROBE(fl_get_input);
PROBE(fl_get_browser);
PROBE(fl_set_input);
PROBE(fl_addto_browser);
PROBE(fl_replace_browser_line);
/* libforms.so.2 — Xlib / colormap surface (the platform specific part) */
PROBE(fl_create_colormap);
PROBE(fl_get_canvas_colormap);
PROBE(fl_get_visual_depth);
PROBE(fl_get_canvas_depth);
PROBE(fl_XEventsQueued);
PROBE(fl_get_real_object_window);
/* libflimage.so.2 — image and PostScript conversion surface */
PROBE(flimage_open);
PROBE(flimage_close);
PROBE(flimage_add_format);
PROBE(flimage_add_comments);
PROBE(fl_get_matrix);
PROBE(fl_make_matrix);
PROBE(fl_free_matrix);
PROBE(fl_init_RGBdatabase);
PROBE(fl_lookup_RGBcolor);
PROBE(fl_object_ps_dump);

#define PROBE_COUNT 32

int main(void)
{
    /* Touch every probe so none of them can be optimised away. */
    (void) live_fl_free_form;
    (void) live_fl_do_forms;
    (void) live_fl_check_forms;
    (void) live_fl_show_form;
    (void) live_fl_set_form_title;
    (void) live_fl_set_focus_object;
    (void) live_fl_add_button;
    (void) live_fl_add_browser;
    (void) live_fl_add_input;
    (void) live_fl_add_timer;
    (void) live_fl_get_button;
    (void) live_fl_get_input;
    (void) live_fl_get_browser;
    (void) live_fl_set_input;
    (void) live_fl_addto_browser;
    (void) live_fl_replace_browser_line;
    (void) live_fl_create_colormap;
    (void) live_fl_get_canvas_colormap;
    (void) live_fl_get_visual_depth;
    (void) live_fl_get_canvas_depth;
    (void) live_fl_XEventsQueued;
    (void) live_fl_get_real_object_window;
    (void) live_flimage_open;
    (void) live_flimage_close;
    (void) live_flimage_add_format;
    (void) live_flimage_add_comments;
    (void) live_fl_get_matrix;
    (void) live_fl_make_matrix;
    (void) live_fl_free_matrix;
    (void) live_fl_init_RGBdatabase;
    (void) live_fl_lookup_RGBcolor;
    (void) live_fl_object_ps_dump;

    /* SUMMARY: cases=1 assertions=0 probes=32 (22 libforms + 10 libflimage) */
    return 0;
}
