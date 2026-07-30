#include <string.h>

#include <eb/eb.h>
#include <eb/error.h>
#include <eb/text.h>

int main(void) {
    EB_Book book;

    if (strcmp(EB_VERSION_STRING, "4.4.3") != 0) {
        return 1;
    }
    if (!eb_pthread_enabled()) {
        return 2;
    }
    if (eb_initialize_library() != EB_SUCCESS) {
        return 3;
    }

    eb_initialize_book(&book);
    if (eb_is_bound(&book)) {
        eb_finalize_book(&book);
        eb_finalize_library();
        return 4;
    }
    if (eb_is_text_stopped(&book)) {
        eb_finalize_book(&book);
        eb_finalize_library();
        return 5;
    }
    eb_finalize_book(&book);

    if (strcmp(eb_error_string(EB_SUCCESS), "EB_SUCCESS") != 0) {
        eb_finalize_library();
        return 6;
    }

    eb_finalize_library();
    return 0;
}
