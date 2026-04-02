/**
 * ScintillaOHOS.cxx - Complete Scintilla 5.6.1 integration for HarmonyOS
 *
 * Architecture:
 *   ScintillaOHOS (public Pimpl) → Impl → ScintillaOHOSEditor (ScintillaBase subclass)
 *                                            ├── WindowOHOSImpl (custom Window for size/invalidation)
 *                                            ├── SurfaceImplOHOS (from PlatOHOS.cxx)
 *                                            └── FontHandleOHOS  (from PlatOHOS.cxx)
 *
 * NAPI C exports wrap ScintillaOHOS for ArkTS binding.
 */

#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <cstdint>
#include <cassert>
#include <map>
#include <set>
#include <optional>
#include <string>
#include <memory>
#include <functional>
#include <algorithm>
#include <bitset>
#include <signal.h>
#include <setjmp.h>
#include <hilog/log.h>

// Scintilla core headers - must follow this exact order (same as GTK build)
#include "ScintillaTypes.h"
#include "ScintillaMessages.h"
#include "ScintillaStructures.h"
#include "ILexer.h"
#include "Debugging.h"
#include "Geometry.h"
#include "Platform.h"
#include "Scintilla.h"
#include "CharacterCategoryMap.h"
#include "Position.h"
#include "UniqueString.h"
#include "SplitVector.h"
#include "Partitioning.h"
#include "RunStyles.h"
#include "ContractionState.h"
#include "CellBuffer.h"
#include "CallTip.h"
#include "KeyMap.h"
#include "Indicator.h"
#include "LineMarker.h"
#include "Style.h"
#include "ViewStyle.h"
#include "CharClassify.h"
#include "Decoration.h"
#include "CaseFolder.h"
#include "ILoader.h"
#include "Document.h"
#include "CaseConvert.h"
#include "UniConversion.h"
#include "Selection.h"
#include "PositionCache.h"
#include "EditModel.h"
#include "MarginView.h"
#include "EditView.h"
#include "Editor.h"
#include "AutoComplete.h"
#include "ScintillaBase.h"

// HarmonyOS Native Drawing C API (used in OnDraw)
extern "C" {
#include <native_drawing/drawing_canvas.h>
#include <native_drawing/drawing_bitmap.h>
}

// Forward declarations from PlatOHOS.cxx
class SurfaceImplOHOS;

// Our public header
#include "ScintillaOHOS.h"

using namespace Scintilla;
using namespace Scintilla::Internal;

// ============================================================================
// SIGABRT guard — Scintilla has internal assert() calls that abort the process
// on unexpected states (e.g., ButtonMove without prior ButtonDown on 2in1
// devices with broken event sequences). We catch SIGABRT via sigaction+longjmp
// and gracefully recover instead of crashing.
// ============================================================================

static sigjmp_buf g_abortJump;
static volatile sig_atomic_t g_inAbortGuard = 0;

static void AbortSignalHandler(int signo) {
    (void)signo;
    if (g_inAbortGuard) {
        siglongjmp(g_abortJump, 1);
    }
    // If not under our guard, restore default and re-raise
    signal(SIGABRT, SIG_DFL);
    raise(SIGABRT);
}

/// RAII guard that installs a SIGABRT handler for the duration of a Scintilla call.
/// Returns true if the call completed normally, false if it was aborted.
class AbortGuard {
public:
    AbortGuard() {
        struct sigaction sa, oldSa;
        sa.sa_handler = AbortSignalHandler;
        sigemptyset(&sa.sa_mask);
        sa.sa_flags = 0;
        sigaction(SIGABRT, &sa, &m_oldAction);
        g_inAbortGuard = 1;
    }
    ~AbortGuard() {
        g_inAbortGuard = 0;
        sigaction(SIGABRT, &m_oldAction, nullptr);
    }
    // Must be called from the same stack frame as construction
    bool enter() { return sigsetjmp(g_abortJump, 1) == 0; }

private:
    struct sigaction m_oldAction;
};

// ============================================================================
// WindowOHOSImpl - Custom Window subclass providing real dimensions & repaint
// ============================================================================

/**
 * A minimal Window override that:
 * - Returns the actual editor dimensions from GetClientPosition()
 * - Stores a non-nullptr wid so CreateMeasurementSurface succeeds
 * - Tracks dirty state for the host to request redraws
 *
 * Note: Window's methods are non-virtual, so this class doesn't actually
 * override them polymorphically. Instead, we rely on the fact that
 * ScintillaOHOSEditor stores its own WindowOHOSImpl as wMain, and the
 * editor's GetClientRectangle() calls wMain.GetClientPosition().
 * We override via the Window class directly (the methods are non-virtual
 * but we replace the Window instance).
 *
 * IMPORTANT: Since Window's methods are non-virtual, we cannot truly
 * override them. Instead, we make wMain.GetClientPosition() work correctly
 * by setting wid to a sentinel pointer and using wMain.GetPosition() which
 * also returns GetClientPosition(). Actually, looking at Window in
 * Platform.h, the methods are inline non-virtual. We need a different approach:
 *
 * The real solution: Editor::GetClientRectangle() calls wMain.GetClientPosition().
 * Window::GetClientPosition() just returns GetPosition() by default, and
 * GetPosition() returns PRectangle(0,0,800,600) in our PlatOHOS.cxx stub.
 *
 * We work around this by overriding GetClientRectangle() in our Editor subclass
 * to return the real size. This is the correct approach since Editor already
 * has a virtual GetClientRectangle().
 */

// Dummy sentinel - wMain.GetID() must return non-nullptr for CreateMeasurementSurface
static const char kWindowSentinel = 'W';

// ============================================================================
// ScintillaOHOSEditor - ScintillaBase subclass for HarmonyOS
// ============================================================================

class ScintillaOHOSEditor : public ScintillaBase {
public:
    // External callbacks (set by ScintillaOHOS)
    std::function<void(int, int, int, const char *)> notifyHandler;
    std::function<std::string()> clipboardGetter;
    std::function<void(const std::string &)> clipboardSetter;

    // FineTicker support
    std::bitset<static_cast<size_t>(TickReason::dwell)> tickerReasons;

    // Size state
    int editorWidth = 800;
    int editorHeight = 600;
    bool needsRedraw = false;

    // Mouse capture state — tracks whether a mouse button is held down.
    // SetMouseCapture(true) is called by ButtonDown, (false) by ButtonUp.
    // HaveMouseCapture() must return the correct state so that ButtonMove
    // takes the safe "captured" branch (selection adjustment) instead of
    // the dangerous "uncaptured" branch (hover/cursor detection which creates
    // AutoSurface and can trigger OH_Drawing/Skia abort on 2in1 devices).
    bool mouseCaptured = false;

    ScintillaOHOSEditor() {
        // Ensure wMain has a non-null ID (required by CreateMeasurementSurface)
        wMain = reinterpret_cast<void *>(const_cast<char *>(&kWindowSentinel));
    }

    ~ScintillaOHOSEditor() override = default;

    // ----------------------------------------------------------------
    // Editor pure virtual overrides
    // ----------------------------------------------------------------

    void Initialise() override {
        // Called by ScintillaBase::Finalise is the pair
        // Nothing extra needed; ScintillaBase::Initialise() is already {} no-op
    }

    void Finalise() override {
        ScintillaBase::Finalise();
    }

    void SetHorizontalScrollPos() override {
        // No OS scrollbar to update
    }

    bool ModifyScrollBars(Sci::Line nMax, Sci::Line nPage) override {
        // No OS scrollbar to modify; return false = nothing changed
        (void)nMax;
        (void)nPage;
        return false;
    }

    void Copy() override {
        // Copy selection text to clipboard via external handler
        if (!clipboardSetter) return;
        SelectionText selText;
        CopySelectionRange(&selText);
        if (!selText.Empty()) {
            clipboardSetter(std::string(selText.Data(), selText.Length()));
        }
    }

    void CopyToClipboard(const SelectionText &selectedText) override {
        if (clipboardSetter) {
            clipboardSetter(std::string(selectedText.Data(), selectedText.Length()));
        }
    }

    bool CanPaste() override {
        if (!clipboardGetter) return false;
        std::string clipText = clipboardGetter();
        return !clipText.empty();
    }

    void Paste() override {
        if (!clipboardGetter || !CanPaste()) return;
        std::string clipText = clipboardGetter();
        InsertPaste(clipText.c_str(), static_cast<Sci::Position>(clipText.size()));
    }

    void ClaimSelection() override {
        // No OS clipboard ownership to claim
    }

    void NotifyChange() override {
        // Document changed notification is handled via NotifyParent
    }

    void NotifyParent(NotificationData scn) override {
        if (notifyHandler) {
            int code = static_cast<int>(scn.nmhdr.code);
            notifyHandler(code,
                          static_cast<int>(scn.nmhdr.idFrom),
                          static_cast<int>(scn.position),
                          scn.text ? scn.text : "");
        }
    }

    int KeyCommand(Message iMessage) override {
        return ScintillaBase::KeyCommand(iMessage);
    }

    sptr_t DefWndProc(Message iMessage, uptr_t wParam, sptr_t lParam) override {
        // Default window procedure - return 0 for unhandled messages
        (void)iMessage;
        (void)wParam;
        (void)lParam;
        return 0;
    }

    void SetMouseCapture(bool on) override {
        mouseCaptured = on;
    }

    bool HaveMouseCapture() override {
        return mouseCaptured;
    }

    // ----------------------------------------------------------------
    // ScintillaBase pure virtual overrides
    // ----------------------------------------------------------------

    void CreateCallTipWindow(PRectangle rc) override {
        // CallTip window not supported in initial implementation
        // The calltip functionality is handled internally by ScintillaBase
        // but the actual window creation is a no-op
        (void)rc;
    }

    void AddToPopUp(const char *label, int cmd, bool enabled) override {
        // Context menu not supported in initial implementation
        (void)label;
        (void)cmd;
        (void)enabled;
    }

    // ----------------------------------------------------------------
    // Editor virtual overrides
    // ----------------------------------------------------------------

    std::string UTF8FromEncoded(std::string_view encoded) const override {
        // We operate internally in UTF-8, so just pass through
        return std::string(encoded);
    }

    std::string EncodedFromUTF8(std::string_view utf8) const override {
        // We operate internally in UTF-8, so just pass through
        return std::string(utf8);
    }

    std::unique_ptr<Surface> CreateMeasurementSurface() const override {
        // Create a small off-screen surface for measuring text
        auto surf = Surface::Allocate(technology);
        if (surf) {
            surf->Init(wMain.GetID());
        }
        return surf;
    }

    std::unique_ptr<Surface> CreateDrawingSurface(SurfaceID sid,
            std::optional<Technology> technologyOpt) const override {
        // Create a surface bound to the given canvas (from OnDraw)
        (void)technologyOpt;
        auto surf = Surface::Allocate(technology);
        if (surf) {
            surf->Init(sid, wMain.GetID());
        }
        return surf;
    }

    PRectangle GetClientRectangle() const override {
        // Return the actual editor dimensions
        return PRectangle(0, 0,
                          static_cast<XYPOSITION>(editorWidth),
                          static_cast<XYPOSITION>(editorHeight));
    }

    void Redraw() override {
        // Mark that we need a repaint; host will call OnDraw on next frame
        needsRedraw = true;
    }

    void RedrawRect(PRectangle rc) override {
        needsRedraw = true;
        (void)rc;
    }

    // ----------------------------------------------------------------
    // FineTicker overrides (prevent Editor base class assert(false))
    // ----------------------------------------------------------------

    bool FineTickerRunning(TickReason reason) override {
        return tickerReasons.test(static_cast<size_t>(reason));
    }
    void FineTickerStart(TickReason reason, int millis, int tolerance) override {
        tickerReasons.set(static_cast<size_t>(reason));
        (void)millis; (void)tolerance;
    }
    void FineTickerCancel(TickReason reason) override {
        tickerReasons.reset(static_cast<size_t>(reason));
    }

    // Allow the host to check/clear the redraw flag
    bool CheckAndClearRedraw() {
        if (needsRedraw) {
            needsRedraw = false;
            return true;
        }
        return false;
    }

    void SetSize(int w, int h) {
        if (w != editorWidth || h != editorHeight) {
            editorWidth = w;
            editorHeight = h;
            ChangeSize();
            needsRedraw = true;
        }
    }

    // Focus management
    void FocusGained() {
        SetFocusState(true);
    }

    void FocusLost() {
        SetFocusState(false);
    }

    // PerformDraw - access protected wMain and technology
    void PerformDraw(OH_Drawing_Canvas *canvas) {
        if (!canvas) return;
        float cw_f = OH_Drawing_CanvasGetWidth(canvas);
        float ch_f = OH_Drawing_CanvasGetHeight(canvas);
        int cw = static_cast<int>(cw_f);
        int ch = static_cast<int>(ch_f);
        if (cw > 0 && ch > 0 && (cw != editorWidth || ch != editorHeight)) {
            SetSize(cw, ch);
        }
        auto surf = Surface::Allocate(technology);
        if (!surf) return;
        surf->Init(static_cast<SurfaceID>(canvas), wMain.GetID());
        if (!surf->Initialised()) return;
        PRectangle rcPaint = GetClientRectangle();
        CheckAndClearRedraw();
        Paint(surf.get(), rcPaint);
    }

    // Public wrappers for protected event methods
    void DoButtonDown(Point pt, unsigned int t, KeyMod m) { ButtonDownWithModifiers(pt, t, m); }
    void DoButtonMove(Point pt, unsigned int t, KeyMod m) {
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "DoButtonMove ENTER pt=(%.1f,%.1f) t=%u", pt.x, pt.y, t);
        ButtonMoveWithModifiers(pt, t, m);
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "DoButtonMove EXIT (returned normally)");
    }
    void DoButtonUp(Point pt, unsigned int t, KeyMod m) { ButtonUpWithModifiers(pt, t, m); }
    void DoRightButtonDown(Point pt, unsigned int t, KeyMod m) { RightButtonDownWithModifiers(pt, t, m); }
    void DoKeyDown(Keys k, KeyMod m, bool *c) { KeyDownWithModifiers(k, m, c); }
    void DoInsertChar(std::string_view sv, CharacterSource cs) { InsertCharacter(sv, cs); }

    // Public wrapper for protected TickFor
    void DoTick(TickReason reason) { TickFor(reason); }

    // Tick caret blink — checks if running then toggles + invalidates
    void DoTickCaret() {
        if (FineTickerRunning(TickReason::caret)) {
            TickFor(TickReason::caret);
        }
    }
};

// ============================================================================
// ScintillaOHOS::Impl - Pimpl implementation
// ============================================================================

struct ScintillaOHOS::Impl {
    std::unique_ptr<ScintillaOHOSEditor> editor;
    bool initialized = false;
    bool focused = false;

    Impl() = default;
    ~Impl() = default;
};

// ============================================================================
// ScintillaOHOS - Public API implementation
// ============================================================================

ScintillaOHOS::ScintillaOHOS()
    : m_impl(new Impl()) {}

ScintillaOHOS::~ScintillaOHOS() {
    Destroy();
    delete m_impl;
}

void ScintillaOHOS::Init(int width, int height) {
    if (m_impl->initialized) return;

    m_impl->editor = std::make_unique<ScintillaOHOSEditor>();
    auto *ed = m_impl->editor.get();

    // Set size before any WndProc calls
    ed->SetSize(width, height);

    // Set code page to UTF-8
    ed->WndProc(Message::SetCodePage, SC_CP_UTF8, 0);

    // Set default font - must be done before any text rendering
    // Use the same default as Platform::DefaultFont()
    const char *defaultFont = "HarmonyOS Sans";
    int defaultSize = Platform::DefaultFontSize();

    // Set font for STYLE_DEFAULT first
    ed->WndProc(Message::StyleSetFont, STYLE_DEFAULT,
                reinterpret_cast<sptr_t>(defaultFont));
    ed->WndProc(Message::StyleSetSize, STYLE_DEFAULT, defaultSize);

    // Apply STYLE_DEFAULT to all styles
    ed->WndProc(Message::StyleClearAll, 0, 0);

    // Configure basic appearance
    // Set tab width to 4 spaces
    ed->WndProc(Message::SetTabWidth, 4, 0);

    // Enable line numbering in margin
    ed->WndProc(Message::SetMarginTypeN, 0, SC_MARGIN_NUMBER);
    ed->WndProc(Message::SetMarginWidthN, 0, 40);
    ed->WndProc(Message::SetMarginMaskN, 0, 0);

    // Set caret properties
    ed->WndProc(Message::SetCaretPeriod, 500, 0);
    ed->WndProc(Message::SetCaretStyle, CARETSTYLE_LINE, 0);

    // Set default selection colours
    ed->WndProc(Message::SetSelFore, 1, 0xFFFFFF);
    ed->WndProc(Message::SetSelBack, 1, 0x0078D7);

    // Enable notifications
    ed->WndProc(Message::SetModEventMask, SC_MODEVENTMASKALL, 0);

    // Set some common settings
    ed->WndProc(Message::SetScrollWidth, 2000, 0);
    ed->WndProc(Message::SetScrollWidthTracking, 1, 0);
    ed->WndProc(Message::SetEndAtLastLine, 1, 0);

    m_impl->initialized = true;
}

void ScintillaOHOS::Destroy() {
    if (!m_impl->initialized) return;
    m_impl->editor->Finalise();
    m_impl->editor.reset();
    m_impl->initialized = false;
}

// ---- Size ----

void ScintillaOHOS::SetSize(int width, int height) {
    if (m_impl->editor) {
        m_impl->editor->SetSize(width, height);
    }
}

int ScintillaOHOS::GetWidth() const {
    return m_impl->editor ? m_impl->editor->editorWidth : 0;
}

int ScintillaOHOS::GetHeight() const {
    return m_impl->editor ? m_impl->editor->editorHeight : 0;
}

// ---- Rendering ----

void ScintillaOHOS::OnDraw(OH_Drawing_Canvas *canvas) {
    if (!m_impl->editor || !canvas) return;
    m_impl->editor->PerformDraw(canvas);
}

// ---- Text operations ----

void ScintillaOHOS::SetText(const char *text) {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::SetText, 0,
                              reinterpret_cast<sptr_t>(text ? text : ""));
}

const char *ScintillaOHOS::GetText(int *length) {
    if (!m_impl->editor) {
        if (length) *length = 0;
        return "";
    }
    // SCI_GETTEXT requires wParam = buffer size, lParam = buffer
    // For simplicity, we get the length first, then the text
    // But since we need to return a pointer, we use GetCharacterPointer
    sptr_t len = m_impl->editor->WndProc(Message::GetLength, 0, 0);
    if (length) *length = static_cast<int>(len);

    // SCI_GETCHARACTERPOINTER returns a direct pointer to the document buffer
    sptr_t ptr = m_impl->editor->WndProc(Message::GetCharacterPointer, 0, 0);
    return reinterpret_cast<const char *>(ptr);
}

void ScintillaOHOS::InsertText(int pos, const char *text) {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::InsertText, static_cast<uptr_t>(pos),
                              reinterpret_cast<sptr_t>(text ? text : ""));
}

void ScintillaOHOS::ReplaceSel(const char *text) {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::ReplaceSel, 0,
                              reinterpret_cast<sptr_t>(text ? text : ""));
}

int ScintillaOHOS::GetLength() {
    if (!m_impl->editor) return 0;
    return static_cast<int>(m_impl->editor->WndProc(Message::GetLength, 0, 0));
}

int ScintillaOHOS::GetLineCount() {
    if (!m_impl->editor) return 0;
    return static_cast<int>(m_impl->editor->WndProc(Message::GetLineCount, 0, 0));
}

int ScintillaOHOS::GetCurLine() {
    if (!m_impl->editor) return 0;
    sptr_t pos = m_impl->editor->WndProc(Message::GetCurrentPos, 0, 0);
    return static_cast<int>(m_impl->editor->WndProc(Message::LineFromPosition, pos, 0));
}

int ScintillaOHOS::GetCurPos() {
    if (!m_impl->editor) return 0;
    return static_cast<int>(m_impl->editor->WndProc(Message::GetCurrentPos, 0, 0));
}

void ScintillaOHOS::SetCurPos(int pos) {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::SetCurrentPos, static_cast<uptr_t>(pos), 0);
    m_impl->editor->WndProc(Message::SetAnchor, static_cast<uptr_t>(pos), 0);
    m_impl->editor->WndProc(Message::ScrollCaret, 0, 0);
}

void ScintillaOHOS::SetSel(int start, int end) {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::SetSel,
                              static_cast<uptr_t>(start), static_cast<sptr_t>(end));
}

int ScintillaOHOS::GetSelStart() {
    if (!m_impl->editor) return 0;
    return static_cast<int>(m_impl->editor->WndProc(Message::GetSelectionStart, 0, 0));
}

int ScintillaOHOS::GetSelEnd() {
    if (!m_impl->editor) return 0;
    return static_cast<int>(m_impl->editor->WndProc(Message::GetSelectionEnd, 0, 0));
}

void ScintillaOHOS::SelectAll() {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::SelectAll, 0, 0);
}

void ScintillaOHOS::Clear() {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::Clear, 0, 0);
}

void ScintillaOHOS::Undo() {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::Undo, 0, 0);
}

void ScintillaOHOS::Redo() {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::Redo, 0, 0);
}

bool ScintillaOHOS::CanUndo() {
    if (!m_impl->editor) return false;
    return m_impl->editor->WndProc(Message::CanUndo, 0, 0) != 0;
}

bool ScintillaOHOS::CanRedo() {
    if (!m_impl->editor) return false;
    return m_impl->editor->WndProc(Message::CanRedo, 0, 0) != 0;
}

bool ScintillaOHOS::GetModify() {
    if (!m_impl->editor) return false;
    return m_impl->editor->WndProc(Message::GetModify, 0, 0) != 0;
}

void ScintillaOHOS::SetSavePoint() {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::SetSavePoint, 0, 0);
}

// ---- Style ----

void ScintillaOHOS::SetFont(const char *fontName, int sizePoints) {
    if (!m_impl->editor) return;
    // Set font on STYLE_DEFAULT
    m_impl->editor->WndProc(Message::StyleSetFont, STYLE_DEFAULT,
                              reinterpret_cast<sptr_t>(fontName ? fontName : "HarmonyOS Sans"));
    m_impl->editor->WndProc(Message::StyleSetSize, STYLE_DEFAULT,
                              static_cast<sptr_t>(sizePoints > 0 ? sizePoints : 14));
    // Apply to all styles
    m_impl->editor->WndProc(Message::StyleClearAll, 0, 0);
}

void ScintillaOHOS::SetFontSize(int sizePoints) {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::StyleSetSize, STYLE_DEFAULT,
                              static_cast<sptr_t>(sizePoints > 0 ? sizePoints : 14));
    m_impl->editor->WndProc(Message::StyleClearAll, 0, 0);
}

void ScintillaOHOS::SetTabSize(int tabSize) {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::SetTabWidth, static_cast<uptr_t>(tabSize), 0);
}

// ---- Scroll ----

void ScintillaOHOS::ScrollTo(int line) {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::SetFirstVisibleLine, static_cast<uptr_t>(line), 0);
}

int ScintillaOHOS::GetFirstVisibleLine() {
    if (!m_impl->editor) return 0;
    return static_cast<int>(m_impl->editor->WndProc(Message::GetFirstVisibleLine, 0, 0));
}

int ScintillaOHOS::GetLinesOnScreen() {
    if (!m_impl->editor) return 0;
    return static_cast<int>(m_impl->editor->WndProc(Message::LinesOnScreen, 0, 0));
}

// ---- Focus ----

void ScintillaOHOS::SetFocus(bool focused) {
    if (!m_impl->editor) return;
    m_impl->focused = focused;
    m_impl->editor->WndProc(Message::SetFocus, focused ? 1 : 0, 0);
    if (focused) {
        m_impl->editor->FocusGained();
    } else {
        m_impl->editor->FocusLost();
    }
}

bool ScintillaOHOS::HasFocus() const {
    return m_impl->focused;
}

// ---- Input events ----

/**
 * Map ArkUI keyCode to Scintilla::Keys.
 * ArkUI uses the same numeric values as the standard SCK_* constants
 * defined in Scintilla.h for most common keys.
 */
static Keys MapArkUIKeyToScintilla(int keyCode) {
    switch (keyCode) {
        case 8:    return Keys::Back;
        case 9:    return Keys::Tab;
        case 13:   return Keys::Return;
        case 7:    return Keys::Escape;
        case 37:   // JS keyCode for Left
        case 302:  return Keys::Left;
        case 39:   // JS keyCode for Right
        case 303:  return Keys::Right;
        case 38:   // JS keyCode for Up
        case 301:  return Keys::Up;
        case 40:   // JS keyCode for Down
        case 300:  return Keys::Down;
        case 36:   // JS keyCode for Home
        case 304:  return Keys::Home;
        case 35:   // JS keyCode for End
        case 305:  return Keys::End;
        case 33:   // JS keyCode for PageUp
        case 306:  return Keys::Prior;
        case 34:   // JS keyCode for PageDown
        case 307:  return Keys::Next;
        case 46:   // JS keyCode for Delete
        case 308:  return Keys::Delete;
        case 45:   return Keys::Insert;
        case 310:  return Keys::Add;
        case 311:  return Keys::Subtract;
        default:   return static_cast<Keys>(keyCode);
    }
}

void ScintillaOHOS::OnTouchDown(float x, float y, uint32_t timestamp) {
    if (!m_impl->editor) return;
    Point pt(static_cast<XYPOSITION>(x), static_cast<XYPOSITION>(y));
    KeyMod modifiers = KeyMod::Norm;
    OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchDown ENTER x=%.1f y=%.1f t=%u editor=%p",
            x, y, timestamp, (void*)m_impl->editor.get());
    AbortGuard guard;
    if (guard.enter()) {
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchDown calling DoButtonDown pt=(%.1f,%.1f)", pt.x, pt.y);
        m_impl->editor->DoButtonDown(pt, timestamp, modifiers);
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchDown DoButtonDown returned OK");
    } else {
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchDown recovered from abort via longjmp");
    }
    OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchDown EXIT");
}

void ScintillaOHOS::OnTouchMove(float x, float y, uint32_t timestamp) {
    if (!m_impl->editor) return;
    Point pt(static_cast<XYPOSITION>(x), static_cast<XYPOSITION>(y));
    KeyMod modifiers = KeyMod::Norm;
    OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchMove ENTER x=%.1f y=%.1f t=%u editor=%p",
            x, y, timestamp, (void*)m_impl->editor.get());
    AbortGuard guard;
    if (guard.enter()) {
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchMove calling DoButtonMove pt=(%.1f,%.1f)", pt.x, pt.y);
        m_impl->editor->DoButtonMove(pt, timestamp, modifiers);
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchMove DoButtonMove returned OK");
    } else {
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchMove recovered from abort via longjmp");
    }
    OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnTouchMove EXIT");
}

void ScintillaOHOS::OnTouchUp(float x, float y, uint32_t timestamp) {
    if (!m_impl->editor) return;
    Point pt(static_cast<XYPOSITION>(x), static_cast<XYPOSITION>(y));
    KeyMod modifiers = KeyMod::Norm;
    AbortGuard guard;
    if (guard.enter()) {
        m_impl->editor->DoButtonUp(pt, timestamp, modifiers);
    }
}

void ScintillaOHOS::OnKeyDown(int keyCode, bool shift, bool ctrl, bool alt, bool meta) {
    if (!m_impl->editor) return;
    auto *ed = m_impl->editor.get();

    // Build KeyMod from modifier flags
    KeyMod modifiers = KeyMod::Norm;
    if (shift) modifiers = static_cast<KeyMod>(static_cast<int>(modifiers) | static_cast<int>(KeyMod::Shift));
    if (ctrl)  modifiers = static_cast<KeyMod>(static_cast<int>(modifiers) | static_cast<int>(KeyMod::Ctrl));
    if (alt)   modifiers = static_cast<KeyMod>(static_cast<int>(modifiers) | static_cast<int>(KeyMod::Alt));
    if (meta)  modifiers = static_cast<KeyMod>(static_cast<int>(modifiers) | static_cast<int>(KeyMod::Super));

    // Map keyCode to Scintilla::Keys
    Keys key = MapArkUIKeyToScintilla(keyCode);

    // Try KeyDownWithModifiers first
    bool consumed = false;
    ed->DoKeyDown(key, modifiers, &consumed);
}

void ScintillaOHOS::OnCharInput(const char *utf8Char, int charLen) {
    if (!m_impl->editor || !utf8Char || charLen <= 0) return;
    auto *ed = m_impl->editor.get();

    // Insert the character directly
    std::string_view sv(utf8Char, static_cast<size_t>(charLen));
    ed->DoInsertChar(sv, CharacterSource::DirectInput);
}

void ScintillaOHOS::OnScroll(float deltaX, float deltaY, bool ctrl) {
    if (!m_impl->editor) return;
    auto *ed = m_impl->editor.get();

    if (ctrl) {
        // Ctrl+scroll = horizontal scroll
        int xPos = static_cast<int>(ed->WndProc(Message::GetXOffset, 0, 0));
        int newX = xPos - static_cast<int>(deltaY);
        ed->WndProc(Message::SetXOffset, static_cast<uptr_t>(newX), 0);
    } else {
        // Normal scroll = vertical scroll
        if (deltaY > 0) {
            int lines = static_cast<int>(deltaY);
            for (int i = 0; i < lines; i++) {
                ed->WndProc(Message::LineScroll, 0, 1);
            }
        } else if (deltaY < 0) {
            int lines = static_cast<int>(-deltaY);
            for (int i = 0; i < lines; i++) {
                ed->WndProc(Message::LineScroll, 0, -1);
            }
        }
        // Horizontal scroll from trackpad
        if (deltaX != 0.0f) {
            int xPos = static_cast<int>(ed->WndProc(Message::GetXOffset, 0, 0));
            int newX = xPos - static_cast<int>(deltaX);
            ed->WndProc(Message::SetXOffset, static_cast<uptr_t>(newX), 0);
        }
    }
}

void ScintillaOHOS::OnRightClick(float x, float y, uint32_t timestamp) {
    if (!m_impl->editor) return;
    Point pt(static_cast<XYPOSITION>(x), static_cast<XYPOSITION>(y));
    KeyMod modifiers = KeyMod::Norm;
    m_impl->editor->DoRightButtonDown(pt, timestamp, modifiers);
}

// ---- IME ----

void ScintillaOHOS::OnIMEStart() {
    // IME composition started - Scintilla handles this internally
}

void ScintillaOHOS::OnIMEEnd() {
    // IME composition ended
}

void ScintillaOHOS::OnIMEComposition(const char *text, int cursorOffset) {
    if (!m_impl->editor) return;
    // Remove previous composition text, insert new one
    // This is a simplified IME handling; full implementation would
    // use indicators and proper composition state tracking
    (void)cursorOffset;
    if (text && text[0]) {
        m_impl->editor->WndProc(Message::ChangeInsertion, 0,
                                  reinterpret_cast<sptr_t>(text));
    }
}

void ScintillaOHOS::OnIMECommit(const char *text) {
    if (!m_impl->editor || !text) return;
    std::string_view sv(text);
    m_impl->editor->DoInsertChar(sv, CharacterSource::ImeResult);
}

// ---- Clipboard hooks ----

void ScintillaOHOS::SetClipboardHandlers(ClipboardGetFunc getter, ClipboardSetFunc setter) {
    if (!m_impl->editor) return;
    m_impl->editor->clipboardGetter = std::move(getter);
    m_impl->editor->clipboardSetter = std::move(setter);
}

// ---- Notifications ----

void ScintillaOHOS::SetNotifyHandler(NotifyFunc handler) {
    if (!m_impl->editor) return;
    m_impl->editor->notifyHandler = std::move(handler);
}

// ---- Access underlying Scintilla ----

void *ScintillaOHOS::GetScintillaPtr() const {
    return static_cast<void *>(m_impl->editor.get());
}

// ---- Tick / Timer ----

void ScintillaOHOS::Tick() {
    if (!m_impl->editor) return;
    m_impl->editor->DoTickCaret();
}

// ============================================================================
// NAPI C Exports for ArkTS integration
// ============================================================================

extern "C" {

// ---- Lifecycle ----

void* BN_Sci_Create() {
    try {
        return new ScintillaOHOS();
    } catch (...) {
        return nullptr;
    }
}

void BN_Sci_Destroy(void *editor) {
    if (editor) {
        delete static_cast<ScintillaOHOS *>(editor);
    }
}

void BN_Sci_Init(void *editor, int width, int height) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->Init(width, height);
    }
}

// ---- Rendering ----

void BN_Sci_OnDraw(void *editor, void *drawContext) {
    if (editor && drawContext) {
        auto *canvas = static_cast<OH_Drawing_Canvas *>(drawContext);
        static_cast<ScintillaOHOS *>(editor)->OnDraw(canvas);
    }
}

void BN_Sci_SetSize(void *editor, int width, int height) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SetSize(width, height);
    }
}

// ---- Text ----

void BN_Sci_SetText(void *editor, const char *text) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SetText(text);
    }
}

const char* BN_Sci_GetText(void *editor, int *length) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetText(length);
    }
    if (length) *length = 0;
    return "";
}

void BN_Sci_InsertText(void *editor, int pos, const char *text) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->InsertText(pos, text);
    }
}

void BN_Sci_ReplaceSel(void *editor, const char *text) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->ReplaceSel(text);
    }
}

int BN_Sci_GetLength(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetLength();
    }
    return 0;
}

int BN_Sci_GetLineCount(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetLineCount();
    }
    return 0;
}

int BN_Sci_GetCurLine(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetCurLine();
    }
    return 0;
}

int BN_Sci_GetCurPos(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetCurPos();
    }
    return 0;
}

void BN_Sci_SetCurPos(void *editor, int pos) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SetCurPos(pos);
    }
}

void BN_Sci_SetSel(void *editor, int start, int end) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SetSel(start, end);
    }
}

int BN_Sci_GetSelStart(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetSelStart();
    }
    return 0;
}

int BN_Sci_GetSelEnd(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetSelEnd();
    }
    return 0;
}

void BN_Sci_SelectAll(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SelectAll();
    }
}

void BN_Sci_Clear(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->Clear();
    }
}

void BN_Sci_Undo(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->Undo();
    }
}

void BN_Sci_Redo(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->Redo();
    }
}

int BN_Sci_CanUndo(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->CanUndo() ? 1 : 0;
    }
    return 0;
}

int BN_Sci_CanRedo(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->CanRedo() ? 1 : 0;
    }
    return 0;
}

int BN_Sci_GetModify(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetModify() ? 1 : 0;
    }
    return 0;
}

void BN_Sci_SetSavePoint(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SetSavePoint();
    }
}

// ---- Style ----

void BN_Sci_SetFont(void *editor, const char *fontName, int sizePoints) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SetFont(fontName, sizePoints);
    }
}

void BN_Sci_SetTabSize(void *editor, int tabSize) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SetTabSize(tabSize);
    }
}

// ---- Scroll ----

void BN_Sci_ScrollTo(void *editor, int line) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->ScrollTo(line);
    }
}

int BN_Sci_GetFirstVisibleLine(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->GetFirstVisibleLine();
    }
    return 0;
}

// ---- Focus ----

void BN_Sci_SetFocus(void *editor, int focused) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->SetFocus(focused != 0);
    }
}

// ---- Redraw callback ----
// Delegate to PlatOHOS (where the Window::InvalidateAll stub lives)
extern "C" void PlatOHOS_SetRedrawCallback(void (*cb)(void));

void BN_Sci_SetRedrawCallback(void (*cb)(void)) {
    PlatOHOS_SetRedrawCallback(cb);
}

int BN_Sci_HasFocus(void *editor) {
    if (editor) {
        return static_cast<ScintillaOHOS *>(editor)->HasFocus() ? 1 : 0;
    }
    return 0;
}

// ---- Input events ----

void BN_Sci_OnTouchDown(void *editor, float x, float y, uint32_t timestamp) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnTouchDown(x, y, timestamp);
    }
}

void BN_Sci_OnTouchMove(void *editor, float x, float y, uint32_t timestamp) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnTouchMove(x, y, timestamp);
    }
}

void BN_Sci_OnTouchUp(void *editor, float x, float y, uint32_t timestamp) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnTouchUp(x, y, timestamp);
    }
}

void BN_Sci_OnKeyDown(void *editor, int keyCode, int shift, int ctrl, int alt, int meta) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnKeyDown(
            keyCode, shift != 0, ctrl != 0, alt != 0, meta != 0);
    }
}

void BN_Sci_OnChar(void *editor, const char *utf8, int len) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnCharInput(utf8, len);
    }
}

void BN_Sci_OnScroll(void *editor, float dx, float dy, int ctrl) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnScroll(dx, dy, ctrl != 0);
    }
}

void BN_Sci_OnRightClick(void *editor, float x, float y, uint32_t timestamp) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnRightClick(x, y, timestamp);
    }
}

// ---- IME ----

void BN_Sci_OnIMEStart(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnIMEStart();
    }
}

void BN_Sci_OnIMEEnd(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnIMEEnd();
    }
}

void BN_Sci_OnIMEComposition(void *editor, const char *text, int cursorOffset) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnIMEComposition(text, cursorOffset);
    }
}

void BN_Sci_OnIMECommit(void *editor, const char *text) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->OnIMECommit(text);
    }
}

// ---- Clipboard handlers ----

namespace {

struct ClipboardUserData {
    BN_ClipboardGetFunc getter;
    BN_ClipboardSetFunc setter;
    void *userData;
};

static std::string ClipboardGetterBridge(void *ud) {
    auto *data = static_cast<ClipboardUserData *>(ud);
    if (data && data->getter) {
        const char *result = data->getter(data->userData);
        return result ? std::string(result) : std::string();
    }
    return std::string();
}

static void ClipboardSetterBridge(void *ud, const std::string &text) {
    auto *data = static_cast<ClipboardUserData *>(ud);
    if (data && data->setter) {
        data->setter(data->userData, text.c_str());
    }
}

} // anonymous namespace

void BN_Sci_SetClipboardHandlers(void *editor, BN_ClipboardGetFunc getter,
                                  BN_ClipboardSetFunc setter, void *userData) {
    if (!editor) return;
    static std::unique_ptr<ClipboardUserData> s_clipboardData;
    s_clipboardData = std::make_unique<ClipboardUserData>();
    s_clipboardData->getter = getter;
    s_clipboardData->setter = setter;
    s_clipboardData->userData = userData;

    static_cast<ScintillaOHOS *>(editor)->SetClipboardHandlers(
        [](void) -> std::string {
            return ClipboardGetterBridge(s_clipboardData.get());
        },
        [](const std::string &text) {
            ClipboardSetterBridge(s_clipboardData.get(), text);
        }
    );
}

// ---- Notification handler ----

namespace {

struct NotifyUserData {
    BN_NotifyFunc handler;
    void *userData;
};

static std::unique_ptr<NotifyUserData> s_notifyData;

} // anonymous namespace

void BN_Sci_SetNotifyHandler(void *editor, BN_NotifyFunc handler, void *userData) {
    if (!editor) return;
    s_notifyData = std::make_unique<NotifyUserData>();
    s_notifyData->handler = handler;
    s_notifyData->userData = userData;

    static_cast<ScintillaOHOS *>(editor)->SetNotifyHandler(
        [](int code, int wParam, int lParam, const char *text) {
            if (s_notifyData && s_notifyData->handler) {
                s_notifyData->handler(s_notifyData->userData, code, wParam, lParam,
                                      text ? text : "");
            }
        }
    );
}

// ---- Tick ----

void BN_Sci_Tick(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->Tick();
    }
}

} // extern "C"
