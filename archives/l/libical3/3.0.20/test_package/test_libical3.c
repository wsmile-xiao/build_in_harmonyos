#include <libical/ical.h>
#include <libical-glib/libical-glib.h>

#include <stdio.h>
#include <string.h>

static int test_c_api(void)
{
    icalcomponent *event = icalcomponent_new(ICAL_VEVENT_COMPONENT);
    if (!event) {
        fprintf(stderr, "FAIL: could not create VEVENT\n");
        return 1;
    }
    icalcomponent_add_property(
        event, icalproperty_new_summary("libical3 OHOS smoke"));
    const char *text = icalcomponent_as_ical_string(event);
    if (!text || !strstr(text, "SUMMARY:libical3 OHOS smoke")) {
        fprintf(stderr, "FAIL: missing VEVENT summary\n");
        icalcomponent_free(event);
        return 1;
    }
    icalcomponent_free(event);

    struct icaltimetype now = icaltime_today();
    if (!icaltime_as_timet(now)) {
        fprintf(stderr, "FAIL: icaltime_today returned empty time\n");
        return 1;
    }
    printf("PASS: libical C API (VEVENT summary + today)\n");
    return 0;
}

static int test_glib_api(void)
{
    ICalComponent *event = i_cal_component_new(
        I_CAL_VEVENT_COMPONENT);
    if (!event) {
        fprintf(stderr, "FAIL: could not create GLib VEVENT\n");
        return 1;
    }
    ICalProperty *prop = i_cal_property_new_summary(
        "libical3 glib smoke");
    i_cal_component_take_property(event, prop);
    gchar *text = i_cal_component_as_ical_string(event);
    if (!text || !strstr(text, "SUMMARY:libical3 glib smoke")) {
        fprintf(stderr, "FAIL: missing GLib VEVENT summary\n");
        g_free(text);
        g_object_unref(event);
        return 1;
    }
    g_free(text);
    g_object_unref(event);
    printf("PASS: libical-glib bindings (VEVENT summary)\n");
    return 0;
}

int main(void)
{
    if (test_c_api()) {
        return 1;
    }
    if (test_glib_api()) {
        return 1;
    }
    return 0;
}
