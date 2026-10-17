#include <libical/ical.h>
#include <libical/vcard.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    icalcomponent *event = icalcomponent_new(ICAL_VEVENT_COMPONENT);
    if (!event) {
        fprintf(stderr, "FAIL: could not create VEVENT\n");
        return 1;
    }

    icalcomponent_add_property(event, icalproperty_new_summary("Akonadi calendar smoke"));
    const char *ical_text = icalcomponent_as_ical_string(event);
    if (!ical_text || !strstr(ical_text, "SUMMARY:Akonadi calendar smoke")) {
        fprintf(stderr, "FAIL: missing event summary\n");
        icalcomponent_free(event);
        return 1;
    }
    icalcomponent_free(event);

    vcardcomponent *card = vcardcomponent_new(VCARD_VCARD_COMPONENT);
    if (!card) {
        fprintf(stderr, "FAIL: could not create VCARD\n");
        return 1;
    }
    vcardcomponent_add_property(card, vcardproperty_new_fn("Ada Lovelace"));
    const char *vcard_text = vcardcomponent_as_vcard_string(card);
    if (!vcard_text || !strstr(vcard_text, "FN:Ada Lovelace")) {
        fprintf(stderr, "FAIL: missing vCard FN\n");
        vcardcomponent_free(card);
        return 1;
    }
    vcardcomponent_free(card);

    printf("PASS: libical generated VEVENT summary\n");
    printf("PASS: libicalvcard generated FN property\n");
    return 0;
}
