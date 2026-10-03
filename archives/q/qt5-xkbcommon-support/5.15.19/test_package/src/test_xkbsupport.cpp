// test_package consumer for qt5-xkbcommon-support/5.15.19 (HarmonyOS PC).
//
// This is a real consumer of the package: it links Qt5::XkbCommonSupportPrivate
// and calls QXkbCommon API from BOTH translation units of the module
// (qxkbcommon.cpp and qxkbcommon_3rdparty.cpp), asserting non-trivial
// behaviour. It prints a machine-readable assertion tally and returns
// non-zero on the first mismatch.
#include <QtXkbCommonSupport/private/qxkbcommon_p.h>

#include <QtCore/QString>
#include <QtCore/QVector>

#include <xkbcommon/xkbcommon.h>

#include <cstdio>

static int g_assertions = 0;
static int g_failures = 0;

static void check(bool condition, const char *what)
{
    ++g_assertions;
    if (condition) {
        std::printf("ok   - %s\n", what);
    } else {
        ++g_failures;
        std::printf("FAIL - %s\n", what);
    }
}

int main()
{
    // ── 1. qxkbcommon.cpp: keysym -> Qt::Key translation table ────────────
    // XKB_KEY_A must map to Qt::Key_A; this walks the compiled KeyTbl.
    {
        const int key = QXkbCommon::keysymToQtKey(XKB_KEY_A, Qt::NoModifier);
        check(key == Qt::Key_A, "keysymToQtKey(XKB_KEY_A) == Qt::Key_A");
    }
    {
        // Shift must not change the produced Qt key for a letter keysym.
        const int plain = QXkbCommon::keysymToQtKey(XKB_KEY_A, Qt::NoModifier);
        const int shifted = QXkbCommon::keysymToQtKey(XKB_KEY_A, Qt::ShiftModifier);
        check(plain == shifted, "keysymToQtKey is modifier-stable for XKB_KEY_A");
    }
    {
        // A keypad keysym must stay inside the Qt keypad range.
        const int key = QXkbCommon::keysymToQtKey(XKB_KEY_KP_0, Qt::KeypadModifier);
        check(key == Qt::Key_0,
              "keysymToQtKey(XKB_KEY_KP_0) == Qt::Key_0");
        check(QXkbCommon::isKeypad(XKB_KEY_KP_5), "isKeypad(XKB_KEY_KP_5) is true");
        check(!QXkbCommon::isKeypad(XKB_KEY_A), "isKeypad(XKB_KEY_A) is false");
    }
    {
        // Non-Latin1 keysym must be reported as such (inline helpers).
        check(QXkbCommon::isLatin1(0x41), "isLatin1(0x41) is true");
        check(!QXkbCommon::isLatin1(0x1000001),
              "isLatin1(0x1000001) is false");
    }

    // ── 2. qxkbcommon_3rdparty.cpp: case conversion helpers ───────────────
    {
        const xkb_keysym_t upper = QXkbCommon::qxkbcommon_xkb_keysym_to_upper(XKB_KEY_a);
        check(upper == XKB_KEY_A,
              "qxkbcommon_xkb_keysym_to_upper(XKB_KEY_a) == XKB_KEY_A");
    }
    {
        xkb_keysym_t lower = 0;
        xkb_keysym_t upper = 0;
        QXkbCommon::xkbcommon_XConvertCase(XKB_KEY_b, &lower, &upper);
        check(lower == XKB_KEY_b, "xkbcommon_XConvertCase lower bound for XKB_KEY_b");
        check(upper == XKB_KEY_B, "xkbcommon_XConvertCase upper bound for XKB_KEY_b");
    }
    {
        // Digits have no case: both bounds must stay the digit.
        xkb_keysym_t lower = 0;
        xkb_keysym_t upper = 0;
        QXkbCommon::xkbcommon_XConvertCase(XKB_KEY_1, &lower, &upper);
        check(lower == XKB_KEY_1 && upper == XKB_KEY_1,
              "xkbcommon_XConvertCase is identity for XKB_KEY_1");
    }
    {
        const QString text = QXkbCommon::lookupStringNoKeysymTransformations(XKB_KEY_A);
        check(!text.isEmpty(), "lookupStringNoKeysymTransformations(XKB_KEY_A) is non-empty");
    }

    // ── 3. libxkbcommon linkage: build a real keymap through the module's
    //       dependency chain and translate a keycode with the module helper.
    //
    // NOTE (measured on this HarmonyOS PC image): libxkbcommon 1.6.0 is built
    // with its default XKB data dir /share/X11/xkb, which does NOT exist on the
    // device, so xkb_context_new(XKB_CONTEXT_NO_FLAGS) legitimately returns
    // nullptr here (it logs "failed to add default include path /share/X11/xkb").
    // The test therefore uses XKB_CONTEXT_NO_DEFAULT_INCLUDES plus a
    // self-contained keymap string, which is the only form that needs no data
    // filesystem at all -- it still exercises the real library, the compiled
    // archive and the module's keycode -> Qt key translation path.
    {
        struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_DEFAULT_INCLUDES);
        check(context != nullptr,
              "xkb_context_new(XKB_CONTEXT_NO_DEFAULT_INCLUDES) succeeded (libxkbcommon linked)");
        if (context) {
            static const char *const kSelfContainedKeymap =
                "xkb_keymap {\n"
                "  xkb_keycodes { minimum = 8; maximum = 255; <AD01> = 38; };\n"
                "  xkb_types { type \"ONE_LEVEL\" { modifiers = None; map[None] = Level1;"
                " level_name[Level1] = \"Any\"; }; };\n"
                "  xkb_compat { };\n"
                "  xkb_symbols { key <AD01> { type = \"ONE_LEVEL\", [ a ] }; };\n"
                "};\n";
            struct xkb_keymap *keymap = xkb_keymap_new_from_string(
                context, kSelfContainedKeymap,
                XKB_KEYMAP_FORMAT_TEXT_V1, XKB_KEYMAP_COMPILE_NO_FLAGS);
            check(keymap != nullptr, "xkb_keymap_new_from_string() succeeded");
            if (keymap) {
                struct xkb_state *state = xkb_state_new(keymap);
                check(state != nullptr, "xkb_state_new() succeeded");
                if (state) {
                    // Keycode 38 is AD01 in the keymap above and carries the
                    // Latin-1 'a' keysym; feeding it through the module's own
                    // translation path proves the static archive links and
                    // behaves against a live xkb_state.
                    const xkb_keysym_t sym = xkb_state_key_get_one_sym(state, 38);
                    check(sym == XKB_KEY_a,
                          "xkb_state_key_get_one_sym(38) == XKB_KEY_a");
                    const int qtKey = QXkbCommon::keysymToQtKey(
                        sym, Qt::NoModifier, state, 38);
                    check(qtKey == Qt::Key_A,
                          "QXkbCommon::keysymToQtKey(live state, keycode 38) == Qt::Key_A");
                    const Qt::KeyboardModifiers mods = QXkbCommon::modifiers(state);
                    check((mods & Qt::ShiftModifier) == 0,
                          "QXkbCommon::modifiers(live state) has no ShiftModifier");
                    xkb_state_unref(state);
                }
                xkb_keymap_unref(keymap);
            }
            xkb_context_unref(context);
        }
    }

    std::printf("assertions=%d failures=%d\n", g_assertions, g_failures);
    return g_failures == 0 ? 0 : 1;
}
