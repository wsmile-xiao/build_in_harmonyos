#include <assert.h>
#include <stdio.h>

#include <howl.h>

int main(void) {
    sw_text_record record;
    assert(sw_text_record_init(&record) == SW_OKAY);
    assert(sw_text_record_add_string(record, "foo=bar") == SW_OKAY);
    assert(sw_text_record_len(record) > 0);
    assert(sw_text_record_fina(record) == SW_OKAY);
    puts("HOWL text record test passed");
    return 0;
}
