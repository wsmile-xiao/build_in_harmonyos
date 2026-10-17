#include <libfirm/firm.h>
#include <assert.h>
#include <string.h>

int main(void) {
    /* Initialize libFirm and build a minimal IR graph so the consumer
     * actually exercises the library (R34: no empty-shell test). */
    ir_init();

    ir_prog *prog = new_ir_prog("testprog");
    assert(prog != NULL);
    set_irp(prog);
    assert(get_irp() == prog);
    assert(strcmp(get_irp_name(), "testprog") == 0);

    /* A real code-generation-ish call: new_id_from_str must round-trip. */
    ident *id = new_id_from_str("roundtrip");
    assert(id != NULL);
    assert(strcmp(get_id_str(id), "roundtrip") == 0);

    ir_finish();
    return 0;
}
