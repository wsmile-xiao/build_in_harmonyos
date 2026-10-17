#include <CException.h>

static void throw_from_helper(void) {
    Throw(0xBEEFu);
}

int main(void) {
    unsigned int caught = CEXCEPTION_NONE;
    volatile int reached_after_throw = 0;
    int catch_count = 0;

    Try {
        throw_from_helper();
        reached_after_throw = 1;
    } Catch (caught) {
        catch_count++;
    }
    if (reached_after_throw != 0 || catch_count != 1 || caught != 0xBEEFu) {
        return 1;
    }

    int no_throw_catch_count = 0;
    unsigned int no_throw_value = 0;
    Try {
        no_throw_value = 7;
    } Catch (no_throw_value) {
        no_throw_catch_count++;
    }
    if (no_throw_value != 7 || no_throw_catch_count != 0) {
        return 2;
    }

    volatile int reached_after_exit = 0;
    int exit_catch_count = 0;
    caught = CEXCEPTION_NONE;
    Try {
        reached_after_exit = 1;
        ExitTry();
        reached_after_exit = 2;
    } Catch (caught) {
        exit_catch_count++;
    }
    if (reached_after_exit != 1 || exit_catch_count != 0 ||
        caught != CEXCEPTION_NONE) {
        return 3;
    }
    return 0;
}
