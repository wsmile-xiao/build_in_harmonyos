#include <zeitgeist.h>
#include <glib.h>
#include <stdio.h>

int main(void) {
    ZeitgeistSubject *subject;
    ZeitgeistEvent *event;
    const char *uri;

    subject = zeitgeist_subject_new();
    if (subject == NULL) {
        fprintf(stderr, "zeitgeist_subject_new returned NULL\n");
        return 1;
    }
    zeitgeist_subject_set_uri(subject, "file:///tmp/harmonyos");
    event = zeitgeist_event_new();
    if (event == NULL) {
        g_object_unref(subject);
        fprintf(stderr, "zeitgeist_event_new returned NULL\n");
        return 1;
    }
    zeitgeist_event_set_interpretation(event, "access");
    zeitgeist_event_add_subject(event, subject);
    uri = zeitgeist_subject_get_uri(subject);
    g_object_unref(event);
    return (uri != NULL && uri[0] != '\0') ? 0 : 1;
}
