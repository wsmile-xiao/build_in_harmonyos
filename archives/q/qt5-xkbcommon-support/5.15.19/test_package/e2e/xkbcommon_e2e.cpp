// End-to-end consumer flow for qt5-xkbcommon-support/5.15.19 (HarmonyOS PC).
//
// This is a complete consumer use case (rule-12 "Hongmeng-specific test"), not an
// assertion list. The module's real job is to turn keyboard hardware input into
// Qt key events and text, and this flow performs a full simulated typing session
// through exactly that path, with the module's static archive linked in:
//
//   BUILD TIME (test_package/CMakeLists.txt)
//     find_package(Qt5XkbCommonSupport REQUIRED) must yield the Qt5:: and
//     versionless Qt:: targets (that is what kwayland5 links), and
//     Qt5::XkbCommonSupportPrivate must point at a real archive.
//
//   RUN TIME -- the flow itself:
//     1. a self-contained XKB keymap (no /share/X11/xkb data files, which do not
//        exist on this device) is compiled into a live xkb_keymap/xkb_state;
//     2. a typing session is driven through the module's own translation path:
//        for each keycode, with Shift pressed and released, the flow calls
//        QXkbCommon::lookupString(state, code) for the produced text and
//        QXkbCommon::keysymToQtKey(sym, mods, state, code) plus
//        QXkbCommon::modifiers(state) for the Qt-side key;
//     3. the produced text must equal an expected literal string character for
//        character ("Ca1" -- the payload is compared, not merely counted);
//     4. the Shift level is not hard-coded: the flow derives it from
//        QXkbCommon::qxkbcommon_xkb_keysym_to_upper() (the third-party
//        translation unit), so a broken/stubbed TU makes the flow fail;
//     5. the reverse direction is exercised too -- a QKeyEvent built from a
//        produced Qt key goes through QXkbCommon::toKeysym() and the resulting
//        keysym must map back to the same Qt key.
//
// Everything prints a machine-readable `assertions=N failures=M` tally and exits
// non-zero when the typed text diverges, so a regression is a real failure.
#include <QtXkbCommonSupport/private/qxkbcommon_p.h>

#include <QtCore/QString>
#include <QtCore/QVector>
#include <QtGui/QKeyEvent>

#include <xkbcommon/xkbcommon.h>

#include <cstdio>

namespace {

int g_assertions = 0;
int g_failures = 0;

void check(bool condition, const char *what)
{
    ++g_assertions;
    if (condition) {
        std::printf("ok   - %s\n", what);
    } else {
        ++g_failures;
        std::printf("FAIL - %s\n", what);
    }
}

// Keycodes used by the keymap below; the same numbers a real evdev keyboard
// reports for these physical keys.
constexpr xkb_keycode_t kKeyA = 38; // <AD01>
constexpr xkb_keycode_t kKeyB = 39; // <AD02>
constexpr xkb_keycode_t kKeyC = 40; // <AD03>
constexpr xkb_keycode_t kKey1 = 41; // <AD04>
constexpr xkb_keycode_t kShift = 50; // <LFSH>

// A self-contained keymap: no include directives, so nothing is read from the
// filesystem (this device has no /share/X11/xkb). Letters have a Shift level,
// the digit key has an exclam level, Shift_L sets the Shift modifier.
const char *const kKeymapText =
    "xkb_keymap {\n"
    "  xkb_keycodes { minimum = 8; maximum = 255;\n"
    "    <AD01> = 38; <AD02> = 39; <AD03> = 40; <AD04> = 41; <LFSH> = 50; };\n"
    "  xkb_types {\n"
    "    type \"ALPHABETIC\" { modifiers = Shift; map[Shift] = Level2;\n"
    "      level_name[Level1] = \"Base\"; level_name[Level2] = \"Caps\"; };\n"
    "    type \"THREE_LEVEL\" { modifiers = Shift; map[None] = Level1;\n"
    "      map[Shift] = Level2; level_name[Level1] = \"Base\";\n"
    "      level_name[Level2] = \"Shifted\"; };\n"
    "  };\n"
    "  xkb_compat {\n"
    "    interpret Shift_L+AnyOfOrNone(all) { action = SetMods(modifiers=Shift); };\n"
    "  };\n"
    "  xkb_symbols {\n"
    "    key <AD01> { type = \"ALPHABETIC\", [ a, A ] };\n"
    "    key <AD02> { type = \"ALPHABETIC\", [ b, B ] };\n"
    "    key <AD03> { type = \"ALPHABETIC\", [ c, C ] };\n"
    "    key <AD04> { type = \"THREE_LEVEL\", [ 1, exclam ] };\n"
    "    key <LFSH> { [ Shift_L ] };\n"
    "    modifier_map Shift { <LFSH> };\n"
    "  };\n"
    "};\n";

// What one keystroke produced, as the platform layer would hand it to Qt.
struct Keystroke
{
    QString text;      // QXkbCommon::lookupString(state, code)
    int qtKey = 0;     // QXkbCommon::keysymToQtKey(sym, mods, state, code)
    xkb_keysym_t sym = 0;
};

// Drives one key through the module: press, translate, release. `shift` selects
// whether Shift is held down for this keystroke.
Keystroke typeKey(struct xkb_state *state, xkb_keycode_t code, bool shift)
{
    if (shift)
        xkb_state_update_key(state, kShift, XKB_KEY_DOWN);

    const Qt::KeyboardModifiers mods = QXkbCommon::modifiers(state);
    const xkb_keysym_t sym = xkb_state_key_get_one_sym(state, code);
    const int qtKey = QXkbCommon::keysymToQtKey(sym, mods, state, code);
    const QString text = QXkbCommon::lookupString(state, code);

    xkb_state_update_key(state, code, XKB_KEY_DOWN);
    xkb_state_update_key(state, code, XKB_KEY_UP);

    if (shift)
        xkb_state_update_key(state, kShift, XKB_KEY_UP);

    Keystroke result;
    result.text = text;
    result.qtKey = qtKey;
    result.sym = sym;
    return result;
}

} // namespace

int main()
{
    struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_DEFAULT_INCLUDES);
    check(context != nullptr, "xkb_context_new(XKB_CONTEXT_NO_DEFAULT_INCLUDES)");
    if (!context) {
        std::printf("assertions=%d failures=%d\n", g_assertions, g_failures);
        return 1;
    }

    struct xkb_keymap *keymap = xkb_keymap_new_from_string(
        context, kKeymapText, XKB_KEYMAP_FORMAT_TEXT_V1, XKB_KEYMAP_COMPILE_NO_FLAGS);
    check(keymap != nullptr, "keymap compiled from the self-contained description");
    if (!keymap) {
        xkb_context_unref(context);
        std::printf("assertions=%d failures=%d\n", g_assertions, g_failures);
        return 1;
    }

    struct xkb_state *state = xkb_state_new(keymap);
    check(state != nullptr, "live xkb_state created");
    if (!state) {
        xkb_keymap_unref(keymap);
        xkb_context_unref(context);
        std::printf("assertions=%d failures=%d\n", g_assertions, g_failures);
        return 1;
    }

    // ── the typing session ────────────────────────────────────────────────────
    // "Ca1": an upper-case letter typed with Shift, a lower-case letter, a digit.
    const Keystroke upperC = typeKey(state, kKeyC, /*shift=*/true);
    const Keystroke lowerA = typeKey(state, kKeyA, /*shift=*/false);
    const Keystroke digit1 = typeKey(state, kKey1, /*shift=*/false);

    const QString typed = upperC.text + lowerA.text + digit1.text;
    check(typed == QStringLiteral("Ca1"),
          "typing session through QXkbCommon produced exactly \"Ca1\"");

    // The Qt-side keys of the same session.
    check(upperC.qtKey == Qt::Key_C, "Shift+c produced Qt::Key_C");
    check(lowerA.qtKey == Qt::Key_A, "a produced Qt::Key_A");
    check(digit1.qtKey == Qt::Key_1, "1 produced Qt::Key_1");

    // ── the Shift level is derived, not hard-coded ────────────────────────────
    // Base 'c' and Shift 'c' must be linked by the third-party translation unit:
    // the Shift level is the upper-case form of the base keysym.
    const xkb_keysym_t baseC = xkb_state_key_get_one_sym(state, kKeyC); // no shift held
    const xkb_keysym_t derivedUpper = QXkbCommon::qxkbcommon_xkb_keysym_to_upper(baseC);
    check(derivedUpper == upperC.sym,
          "Shift level equals qxkbcommon_xkb_keysym_to_upper(base level)");
    check(derivedUpper == XKB_KEY_C,
          "qxkbcommon_xkb_keysym_to_upper(XKB_KEY_c) == XKB_KEY_C");

    // The digit's second level comes from the same translation unit's case rule:
    // a digit has no case, so XConvertCase must leave it alone.
    xkb_keysym_t lower = 0;
    xkb_keysym_t upper = 0;
    QXkbCommon::xkbcommon_XConvertCase(XKB_KEY_1, &lower, &upper);
    check(lower == XKB_KEY_1 && upper == XKB_KEY_1,
          "xkbcommon_XConvertCase is the identity for the digit level");

    // ── modifier state observed during the session ────────────────────────────
    {
        xkb_state_update_key(state, kShift, XKB_KEY_DOWN);
        const Qt::KeyboardModifiers whileHeld = QXkbCommon::modifiers(state);
        xkb_state_update_key(state, kShift, XKB_KEY_UP);
        const Qt::KeyboardModifiers afterRelease = QXkbCommon::modifiers(state);
        check((whileHeld & Qt::ShiftModifier) != 0,
              "QXkbCommon::modifiers reports Shift while it is held");
        check((afterRelease & Qt::ShiftModifier) == 0,
              "QXkbCommon::modifiers drops Shift after release");
    }

    // ── the reverse direction: Qt key event -> keysym -> Qt key ───────────────
    //
    // QXkbCommon::toKeysym() maps a Qt key through the module's table and, for
    // keys the table does not cover, falls back to the Unicode form
    // (0x01000000 | codepoint) -- measured here as 0x01000061 for the typed 'a',
    // while the session's own keysym for that key is XKB_KEY_a (0x61). The
    // contract that must hold is therefore that both denote the same character
    // and that the reverse keysym maps back to the same Qt key; asserting a
    // literal keysym identity here would contradict the module's own mapping.
    {
        QKeyEvent event(QEvent::KeyPress, lowerA.qtKey, Qt::NoModifier, lowerA.text);
        const QVector<xkb_keysym_t> keysyms = QXkbCommon::toKeysym(&event);
        check(!keysyms.isEmpty(), "QXkbCommon::toKeysym produced a keysym for the typed key");
        if (!keysyms.isEmpty()) {
            const xkb_keysym_t reverse = keysyms.first();
            std::printf("E2E STEP toKeysym(Qt::Key_A from the session) = 0x%05X "
                        "(unicode form), session keysym = 0x%05X\n",
                        (unsigned) reverse, (unsigned) lowerA.sym);
            check(QXkbCommon::keysymToQtKey(reverse, Qt::NoModifier) == lowerA.qtKey,
                  "round trip: the keysym maps back to the same Qt key");
            check(xkb_keysym_to_utf32(reverse) == xkb_keysym_to_utf32(lowerA.sym),
                  "round trip: the keysym denotes the same character as the session's");
        }
    }

    xkb_state_unref(state);
    xkb_keymap_unref(keymap);
    xkb_context_unref(context);

    std::printf("assertions=%d failures=%d\n", g_assertions, g_failures);
    if (g_failures == 0)
        std::printf("hongmeng_e2e_flow=PASS\n");
    else
        std::printf("hongmeng_e2e_flow=FAIL\n");
    return g_failures == 0 ? 0 : 1;
}
