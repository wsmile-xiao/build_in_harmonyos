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
#include <mutex>   // [Patch-0037] std::mutex for IME pending buffer thread safety
#include <functional>
#include <algorithm>
#include "database/pasteboard/oh_pasteboard.h"
#include "database/udmf/udmf.h"
#include "database/udmf/uds.h"
#include "inputmethod/inputmethod_text_editor_proxy_capi.h"
#include "inputmethod/inputmethod_controller_capi.h"
#include "inputmethod/inputmethod_attach_options_capi.h"
#include <bitset>
#include <signal.h>
#include <setjmp.h>
#include <hilog/log.h>
#include "native_drawing/drawing_typeface.h"  // [Patch-0038e] OH_Drawing_TypefaceCreateDefault
#include "native_drawing/drawing_text_blob.h"  // [Patch-0038e] OH_Drawing_TextBlobCreateFromText
#include "native_drawing/drawing_brush.h"      // [Patch-0038e] OH_Drawing_BrushCreate for text test
#include "native_drawing/drawing_color.h"      // [Patch-0038e] OH_Drawing_ColorSetArgb
#include "native_drawing/drawing_text_global.h"  // [Patch-0041] SetTextUndefinedGlyphDisplay (TOFU)
#include "native_drawing/drawing_font_collection.h"   // [Patch-0041] GetSystemFontConfigInfo
#include "native_drawing/drawing_register_font.h"       // [Patch-0041] RegisterFont

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
#include <native_drawing/drawing_font.h>
}

// Forward declarations from PlatOHOS.cxx
class SurfaceImplOHOS;
namespace Scintilla { namespace Internal { class Surface; } }
using Surface = Scintilla::Internal::Surface;
Surface* PlatOHOS_GetCachedMeasurementSurface();
OH_Drawing_Font* PlatOHOS_GetFontHandle(const Scintilla::Internal::Font *font);

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
    std::bitset<static_cast<size_t>(TickReason::dwell) + 1> tickerReasons;

    // Size state
    int editorWidth = 800;
    int editorHeight = 600;
    bool needsRedraw = false;

    // Font initialization tracking.
    // Fonts are initialized in PerformDraw using the real drawing canvas.
    bool fontsInitialized = false;

    // [Patch-0034] IME InputMethod integration
    InputMethod_TextEditorProxy *imeProxy = nullptr;
    InputMethod_InputMethodProxy *imeInputProxy = nullptr;
    std::u16string imeComposingText;  // Current composing text
    int32_t imeComposingStart = 0;     // Start position of composing text
    bool imeAttached = false;

    // [Patch-0037] IME pending buffer — IME callbacks arrive on IPC thread.
    // Scintilla is NOT thread-safe: WndProc from IPC thread while main thread is
    // in Paint() corrupts internal state → zero DrawTextNoClip on all subsequent paints.
    // Fix: callbacks only write here; PerformDraw (main thread) consumes before Paint().
    std::string imePendingText;
    std::mutex imePendingMutex;          // protects imePendingText + imePendingFlag
    bool imePendingFlag = false;

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
        // Copy selection text to clipboard via external handler (system clipboard)
        SelectionText selText;
        CopySelectionRange(&selText);
        if (!selText.Empty()) {
            if (clipboardSetter) {
                clipboardSetter(std::string(selText.Data(), selText.Length()));
            }
        }
    }

    void CopyToClipboard(const SelectionText &selectedText) override {
        if (clipboardSetter) {
            clipboardSetter(std::string(selectedText.Data(), selectedText.Length()));
        }
    }

    bool CanPaste() override {
        // [Patch-0033h-fix] Do NOT call clipboardGetter here — it does a full
        // OH_Pasteboard_GetData which may consume/invalidate the data, causing
        // the subsequent Paste() call's clipboardGetter() to return empty.
        // Instead, just check if the handler exists; Paste() will handle empty data.
        return static_cast<bool>(clipboardGetter);
    }

    void Paste() override {
        if (!CanPaste()) return;
        // [Patch-0033h] Try external handler first (system clipboard),
        // fall back to internal buffer for in-process copy/paste.
        std::string clipText;
        if (clipboardGetter) {
            clipText = clipboardGetter();
        }
        if (clipText.empty()) return;
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-CLIP",
            "Paste: inserting '%{public}s' (len=%{public}zu)", clipText.c_str(), clipText.size());
        InsertPaste(clipText.c_str(), static_cast<Sci::Position>(clipText.size()));
        WndProc(Message::Colourise, 0, -1);
        needsRedraw = true;  // Ensure redraw after paste
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-CLIP",
            "Paste: done, docLen=%{public}d", (int)pdoc->Length());
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

    // Patch-0023: Return nullptr to prevent T1 SPositionFromLocation from using
    // the measurement surface (Skia crashes on off-screen canvas text measurement).
    // Position correction is done via T2 (font-based measurement) in DoButtonDown.
    std::unique_ptr<Surface> CreateMeasurementSurface() const override {
        return nullptr;
    }

    std::string UTF8FromEncoded(std::string_view encoded) const override {
        // We operate internally in UTF-8, so just pass through
        return std::string(encoded);
    }

    std::string EncodedFromUTF8(std::string_view utf8) const override {
        // We operate internally in UTF-8, so just pass through
        return std::string(utf8);
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

    // [Patch-0035] Must call InvalidateAll() to notify the ArkTS host
    // to schedule an OnDraw → PerformDraw frame. Without this, IME InsertText
    // and Paste update the document (docLen grows) but the host never learns
    // it needs to repaint — so PerformDraw simply never runs and DrawTextNoClip=0.
    //
    // ROOT CAUSE: The previous override only set needsRedraw=true (internal flag)
    // but never triggered the host-side redraw callback chain:
    //   Redraw() → [was: just needsRedraw=true]
    //   InvalidateAll() → s_redrawRequested() → ArkTS XComponent.invalidate()
    //   → next frame OnDraw callback → PerformDraw → Paint → DrawTextNoClip ✓
    void Redraw() override {
        needsRedraw = true;
        wMain.InvalidateAll();
    }

    void RedrawRect(PRectangle rc) override {
        needsRedraw = true;
        (void)rc;
        wMain.InvalidateAll();
    }

    // ----------------------------------------------------------------
    // FineTicker overrides (prevent Editor base class assert(false))
    // ----------------------------------------------------------------

    bool FineTickerRunning(TickReason reason) override {
        const size_t idx = static_cast<size_t>(reason);
        return (idx < tickerReasons.size()) ? tickerReasons.test(idx) : false;
    }
    void FineTickerStart(TickReason reason, int millis, int tolerance) override {
        const size_t idx = static_cast<size_t>(reason);
        if (idx < tickerReasons.size()) tickerReasons.set(idx);
        (void)millis; (void)tolerance;
    }
    void FineTickerCancel(TickReason reason) override {
        const size_t idx = static_cast<size_t>(reason);
        if (idx < tickerReasons.size()) tickerReasons.reset(idx);
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

        // [Patch-0037] Consume pending IME text on main thread.
        // IME callbacks write to imePendingText from IPC thread; we process it here
        // (main thread) to avoid cross-thread Scintilla API corruption.
        {
            std::string pending;
            bool hasPending = false;
            {
                std::lock_guard<std::mutex> lock(imePendingMutex);
                if (imePendingFlag) {
                    pending = std::move(imePendingText);
                    imePendingText.clear();
                    imePendingFlag = false;
                    hasPending = true;
                }
            }
            if (hasPending && !pending.empty()) {
                OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-IME",
                    "PerformDraw: consuming pending IME text len=%{public}zu (main thread)",
                    pending.size());
                WndProc(Message::ReplaceSel, 0, reinterpret_cast<sptr_t>(pending.c_str()));
                WndProc(Message::Colourise, 0, -1);
                needsRedraw = true;
            }
        }
        
        // Plan C (Patch-0018): Initialize fonts using the REAL drawing canvas.
        // OH_Drawing/Skia text measurement only works reliably on the actual
        // drawing surface (not on a separate measurement surface).
        // On first paint, create a temporary Surface wrapper around the real canvas
        // and call vs.Refresh() to realize all fonts. After this, DrawTextNoClip
        // will have valid ohFont pointers and text will render correctly.
        if (!fontsInitialized) {
            auto surf = Surface::Allocate(technology);
            if (surf) {
                surf->Init(static_cast<SurfaceID>(canvas), wMain.GetID());
                if (surf->Initialised()) {
                    vs.Refresh(*surf.get(), 1);
                    OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-INIT",
                        "Fonts initialized via real drawing canvas — text should now display");
                }
            }
            fontsInitialized = true;
        }
        
        // Log caret state before painting for diagnostics
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-CARET",
            "PerformDraw: active=%{public}d on=%{public}d hasFocus=%{public}d period=%{public}d width=%.1f size=%dx%{public}d",
            (int)caret.active, (int)caret.on, (int)hasFocus, (int)caret.period,
            (float)vs.caret.width, cw, ch);
        
        auto surf = Surface::Allocate(technology);
        if (!surf) {
            OH_LOG_Print(LOG_APP, LOG_ERROR, 0xF100, "MNP-DRAW",
                "Surface::Allocate returned NULL!");
            return;
        }
        surf->Init(static_cast<SurfaceID>(canvas), wMain.GetID());
        if (!surf->Initialised()) {
            OH_LOG_Print(LOG_APP, LOG_ERROR, 0xF100, "MNP-DRAW",
                "Surface not initialised after Init(canvas=%p, wMainID=%p)!",
                (void*)canvas, (void*)wMain.GetID());
            return;
        }
        PRectangle rcPaint = GetClientRectangle();
        bool hadRedraw = CheckAndClearRedraw();
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-DRAW",
            "Paint: rc=(%d,%d,%d,%d) hadRedraw=%{public}d ps=%{public}d surfOK=%{public}d canvas=%p docLen=%{public}zd topLine=%{public}d linesOnScreen=%{public}d textStart=%{public}d lh=%{public}d",
            (int)rcPaint.left, (int)rcPaint.top, (int)rcPaint.right, (int)rcPaint.bottom,
            (int)hadRedraw, (int)paintState, (int)surf->Initialised(), (void*)canvas,
            pdoc ? pdoc->Length() : -1, (int)topLine, (int)LinesOnScreen(),
            (int)vs.textStart, (int)vs.lineHeight);

        // [Patch-0039] Protect canvas state across Paint() call.
        OH_Drawing_CanvasSave(canvas);
        Paint(surf.get(), rcPaint);
        OH_Drawing_CanvasRestore(canvas);

        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-DRAW",
            "Paint DONE: ps=%{public}d docLen=%{public}zd topLine=%{public}d linesOnScreen=%{public}d",
            (int)paintState,
            pdoc ? pdoc->Length() : -1, (int)topLine, (int)LinesOnScreen());
    }

    // Public wrappers for protected event methods
    void DoButtonDown(Point pt, unsigned int t, KeyMod m) {
        // Patch-0028: Complete bypass of ButtonDownWithModifiers.
        // Root cause: BDMW uses SPositionFromLocation which returns ~0
        // (surface=nullptr), setting anchor=0 and polluting multiple
        // selection states (originalAnchorPos, sel.Rectangular(),
        // selectionUnit, moveExtendsSelection, etc.).  No amount of
        // post-correction via SetSelection/sel.Clear/sel.SetSelection
        // can fully undo all side effects — the selection leaks as
        // [anchor=0 .. caret=correct] highlighting the whole line.
        //
        // Fix: Replicate only the minimal BDMW operations we need
        // (mouse capture, ptMouseLast, lastXChosen) and perform
        // all selection logic ourselves via T2 font measurement.
        if (!fontsInitialized) {
            OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                "DoButtonDown: fonts not ready, cursor to 0");
            SetSelection(0, 0);
            SetLastXChosen();
            return;
        }
        WndProc(Message::SetFocus, 1, 0);

        // --- Minimal BDMW state (no selection side effects) ---
        SetMouseCapture(true);
        ptMouseLast = pt;

        // --- T2 position correction (font-based measurement) ---
        const Sci::Position docLen = pdoc->Length();
        if (docLen <= 0) {
            SetLastXChosen();
            return;
        }

        const XYPOSITION xRel = pt.x - vs.textStart;
        const Sci::Line clickedLine = std::clamp<Sci::Line>(
            static_cast<Sci::Line>(pt.y / vs.lineHeight),
            0, pdoc->LinesTotal() - 1);
        const Sci::Position lineStart = pdoc->LineStart(clickedLine);
        const Sci::Position lineEnd = pdoc->LineEnd(clickedLine);
        const Sci::Position lineLen = lineEnd - lineStart;

        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
            "DoButtonDown: DIAG pt_x=%{public}d pt_y=%{public}d textStart=%{public}d "
            "xRel=%{public}d lh=%{public}d surfW=%{public}d surfH=%{public}d line=%{public}d docLen=%{public}d",
            (int)pt.x, (int)pt.y, (int)vs.textStart, (int)xRel,
            (int)vs.lineHeight, editorWidth, editorHeight,
            (int)clickedLine, (int)docLen);

        Sci::Position estimated = lineStart;

        if (xRel < 0) {
            OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                "DoButtonDown: margin click -> line=%{public}d pos=%{public}d",
                (int)clickedLine, (int)lineStart);
            estimated = lineStart;
        } else {
            std::string lineText(lineLen, '\0');
            pdoc->GetCharRange(lineText.data(), lineStart, lineLen);
            const Font *fontRaw = vs.styles[STYLE_DEFAULT].font.get();
            OH_Drawing_Font *ohFont = PlatOHOS_GetFontHandle(fontRaw);

            if (ohFont && !lineText.empty()) {
                int n = OH_Drawing_FontCountText(ohFont,
                    lineText.data(), lineText.size(), TEXT_ENCODING_UTF8);
                if (n > 0) {
                    std::vector<uint16_t> glyphs(n);
                    OH_Drawing_FontTextToGlyphs(ohFont,
                        lineText.data(), static_cast<uint32_t>(lineText.size()),
                        TEXT_ENCODING_UTF8, glyphs.data(), n);
                    std::vector<float> widths(n);
                    OH_Drawing_FontGetWidths(ohFont, glyphs.data(), n, widths.data());
                    float accX = 0.0f;
                    int charIdx = 0;
                    for (; charIdx < n; charIdx++) {
                        float halfW = widths[charIdx] * 0.5f;
                        if (accX + halfW > xRel) break;
                        accX += widths[charIdx];
                    }
                    int byteIdx = 0, utf8CharCount = 0;
                    while (byteIdx < static_cast<int>(lineText.size()) && utf8CharCount < charIdx) {
                        unsigned char c = static_cast<unsigned char>(lineText[byteIdx]);
                        byteIdx += (c < 0x80) ? 1 : ((c & 0xE0) == 0xC0) ? 2 :
                                 ((c & 0xF0) == 0xE0) ? 3 : 4;
                        utf8CharCount++;
                    }
                    estimated = lineStart + std::min(byteIdx, static_cast<int>(lineLen));
                } else {
                    estimated = lineStart + static_cast<Sci::Position>(xRel / vs.aveCharWidth);
                }
            } else {
                estimated = lineStart + static_cast<Sci::Position>(xRel / vs.aveCharWidth);
            }
            estimated = std::clamp(estimated, lineStart, lineEnd);

            OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                "DoButtonDown: T2 pos=%{public}d (line=%{public}d xRel=%{public}.1f ohFont=%{public}p len=%{public}d)",
                (int)estimated, (int)clickedLine, xRel, (void*)ohFont, (int)lineLen);
        }

        // --- Clean selection: zero-length range at corrected position ---
        sel.SetMoveExtends(false);
        sel.selType = Selection::SelTypes::stream;

        // [Patch-0030] Double/triple click detection
        // GetEventTime returns NANOSECONDS; convert to ms for comparison
        const uint32_t tMs = static_cast<uint32_t>(t / 1000000);
        // [Fix-0030f] lastClickTime is already stored as ms in DoButtonUp,
        // do NOT divide again! (was causing lastClickMs=0 always)
        const uint32_t lastClickMs = static_cast<uint32_t>(lastClickTime);
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
            "DoButtonDown: t=%{public}u(ms) lastClickTime=%{public}u(ms)", tMs, lastClickMs);
        const unsigned int clickDelta = (tMs >= lastClickMs) ? (tMs - lastClickMs) : 0;
        const bool isDoubleClick = (clickDelta > 0 && clickDelta < 500);   // < 500ms = double-click
        const bool isTripleClick = (isDoubleClick && sel.selType == Selection::SelTypes::stream
                                    && selectionUnit == TextUnit::word);

        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
            "DoButtonDown: click delta=%{public}u double=%{public}d triple=%{public}d unit=%{public}d",
            clickDelta, (int)isDoubleClick, (int)isTripleClick, (int)selectionUnit);

        if (isTripleClick) {
            // Triple-click: select entire line
            selectionUnit = TextUnit::wholeLine;
            originalAnchorPos = lineStart;
            sel.SetSelection(SelectionRange(lineStart, lineEnd));
            OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                "DoButtonDown: TRIPLE CLICK -> line [%{public}d,%{public}d]",
                (int)lineStart, (int)lineEnd);
        } else if (isDoubleClick) {
            // Double-click: select word under cursor
            selectionUnit = TextUnit::word;
            const Sci::Position wordStart = static_cast<Sci::Position>(
                WndProc(Message::WordStartPosition, estimated, 0));
            const Sci::Position wordEnd = static_cast<Sci::Position>(
                WndProc(Message::WordEndPosition, estimated, 0));
            originalAnchorPos = wordStart;
            sel.SetSelection(SelectionRange(wordStart, wordEnd));
            OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                "DoButtonDown: DOUBLE CLICK -> word [%{public}d,%{public}d]",
                (int)wordStart, (int)wordEnd);
        } else {
            // Single click: place cursor
            selectionUnit = TextUnit::character;
            originalAnchorPos = estimated;
            sel.SetSelection(SelectionRange(estimated));
        }

        SetLastXChosen();
        needsRedraw = true;
    }
    void DoButtonMove(Point pt, unsigned int t, KeyMod m) {
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
            "DoButtonMove ENTER pt=(%.1f,%.1f) t=%u haveCapture=%{public}d",
            pt.x, pt.y, t, (int)mouseCaptured);

        // Block DwellEnd path (same as before)
        bool wasDwelling = dwelling;
        if (wasDwelling) {
            dwelling = false;
            FineTickerCancel(TickReason::dwell);
        }

        // Run original Scintilla path (maintains mouseCapture state etc.)
        ButtonMoveWithModifiers(pt, t, m);

        // Patch-0026: T2 position correction for drag selection.
        // SPositionFromLocation returns ~0 (surface=nullptr), so
        // ButtonMoveWithModifiers moved selection to wrong position.
        // Correct it using font-based measurement (same as DoButtonDown).
        if (fontsInitialized && mouseCaptured) {
            const Sci::Position docLen = pdoc->Length();
            if (docLen > 0) {
                const XYPOSITION xRel = pt.x - vs.textStart;
                const Sci::Line clickedLine = std::clamp<Sci::Line>(
                    static_cast<Sci::Line>(pt.y / vs.lineHeight),
                    0, pdoc->LinesTotal() - 1);
                const Sci::Position lineStart = pdoc->LineStart(clickedLine);
                const Sci::Position lineEnd = pdoc->LineEnd(clickedLine);
                const Sci::Position lineLen = lineEnd - lineStart;

                Sci::Position corrected = lineStart;
                if (xRel >= 0 && lineLen > 0) {
                    std::string lineText(lineLen, '\0');
                    pdoc->GetCharRange(lineText.data(), lineStart, lineLen);
                    const Font *fontRaw = vs.styles[STYLE_DEFAULT].font.get();
                    OH_Drawing_Font *ohFont = PlatOHOS_GetFontHandle(fontRaw);
                    if (ohFont) {
                        int n = OH_Drawing_FontCountText(ohFont,
                            lineText.data(), lineText.size(), TEXT_ENCODING_UTF8);
                        if (n > 0) {
                            std::vector<uint16_t> glyphs(n);
                            OH_Drawing_FontTextToGlyphs(ohFont,
                                lineText.data(), static_cast<uint32_t>(lineText.size()),
                                TEXT_ENCODING_UTF8, glyphs.data(), n);
                            std::vector<float> widths(n);
                            OH_Drawing_FontGetWidths(ohFont, glyphs.data(), n, widths.data());
                            float accX = 0.0f;
                            int charIdx = 0;
                            for (; charIdx < n; charIdx++) {
                                float halfW = widths[charIdx] * 0.5f;
                                if (accX + halfW > xRel) break;
                                accX += widths[charIdx];
                            }
                            int byteIdx = 0, utf8CharCount = 0;
                            while (byteIdx < static_cast<int>(lineText.size()) && utf8CharCount < charIdx) {
                                unsigned char c = static_cast<unsigned char>(lineText[byteIdx]);
                                byteIdx += (c < 0x80) ? 1 : ((c & 0xE0) == 0xC0) ? 2 :
                                         ((c & 0xF0) == 0xE0) ? 3 : 4;
                                utf8CharCount++;
                            }
                            corrected = lineStart + std::min(byteIdx, static_cast<int>(lineLen));
                        } else {
                            corrected = lineStart + static_cast<Sci::Position>(xRel / vs.aveCharWidth);
                        }
                    } else {
                        corrected = lineStart + static_cast<Sci::Position>(xRel / vs.aveCharWidth);
                    }
                    corrected = std::clamp(corrected, lineStart, lineEnd);
                }

                // Extend selection to corrected position (stream selection from anchor)
                MovePositionTo(corrected, Selection::SelTypes::stream);
                needsRedraw = true;

                OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                    "DoButtonMove: T2 corrected pos=%{public}d", (int)corrected);
            }
        }

        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "DoButtonMove EXIT OK");
    }
    void DoButtonUp(Point pt, unsigned int t, KeyMod m) {
        // [Patch-0029] Skip ButtonUpWithModifiers — it calls SPositionFromLocation
        // which returns ~0 (surface=nullptr), then SetSelection(~0, anchor)
        // creates a selection [0..anchor] highlighting the entire line.
        // Only perform the minimal necessary cleanup:
        if (HaveMouseCapture()) {
            ChangeMouseCapture(false);
        }
        inDragDrop = DragDrop::none;
        // Store time in milliseconds (GetEventTime returns nanoseconds)
        lastClickTime = static_cast<unsigned int>(t / 1000000);
        lastClick = pt;
        lastXChosen = static_cast<int>(pt.x) + xOffset;
        EnsureCaretVisible(false);
        needsRedraw = true;

        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
            "DoButtonUp: skipped ButtonUpWithModifiers, released capture");
    }
    void DoRightButtonDown(Point pt, unsigned int t, KeyMod m) { RightButtonDownWithModifiers(pt, t, m); }
    void DoKeyDown(Keys k, KeyMod m, bool *c) {
        // Skip DwellEnd(false) — it calls NotifyDwelling → PositionFromLocation
        // → CreateMeasurementSurface → OH_Drawing/Skia abort on HarmonyOS.
        // Same root cause as DoButtonMove touch crash (patch 0010).
        // DwellEnd only cancels hover tooltips — non-essential for keyboard input.

        // [Patch-0032] For Up/Down keys, bypass SPositionFromLocation entirely.
        //
        // ROOT CAUSE CHAIN:
        //   WndProc(LineDown) → CursorUpOrDown → PositionUpOrDown
        //   → SPositionFromLocation(Point(lastX-xOffset, newY))
        //   → EditView::SPositionFromLocation() at line 714:
        //       if (surface && ll) { ... }  ← surface is nullptr!
        //   → falls through to line 756: return SelectionPosition(posLineStart)
        //   → ALWAYS returns target LINE START regardless of column!
        //
        // This is why pressing Down on any line jumps to line 2 start.
        // The previous Patch-0031 only fixed lastXChosen calculation but
        // SPositionFromLocation still can't work without a measurement surface.
        //
        // FIX: Use pure document APIs (GetColumn + FindColumn) that don't need
        // any surface/text measurement. This completely avoids the broken path.
        if (k == Keys::Up || k == Keys::Down) {
            const Sci::Position caretPos = sel.MainCaret();
            const Sci::Line caretLine = pdoc->LineFromPosition(caretPos);

            // GetColumn: counts from line start to caretPos, expanding tabs to tabWidth cols
            const int displayCol = static_cast<int>(pdoc->GetColumn(caretPos));

            // Compute target line (clamp to document bounds)
            const int direction = (k == Keys::Down) ? 1 : -1;
            const Sci::Line targetLine = caretLine + direction;

            if (targetLine >= 0 && targetLine < pdoc->LinesTotal()) {
                // FindColumn: convert display column back to document position on target line.
                // If target line is shorter than displayCol, clamps to end of line.
                const Sci::Position targetPos = pdoc->FindColumn(targetLine, displayCol);
                SetEmptySelection(targetPos);
                needsRedraw = true;

                OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                    "DoKeyDown: Up/Down direct line=%{public}d->%{public}d dCol=%{public}d pos=%{public}d->%{public}d",
                    (int)caretLine, (int)targetLine, displayCol,
                    (int)caretPos, (int)targetPos);

                if (c) *c = true;
                // Handled — skip WndProc to avoid broken SPositionFromLocation path
                return;
            }
            // [Patch-0032b] At document boundary (first line + Up or last line + Down):
            // Do NOT fall through to WndProc(LineDown/LineUp) — that path calls
            // SPositionFromLocation which returns posLineStart (line start) due
            // to surface=nullptr (EditView.cxx:714), causing the caret to jump
            // to an incorrect position. Just stay put.
            if (c) *c = true;
            OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                "DoKeyDown: Up/Down at boundary line=%{public}d direction=%{public}d — no-op",
                (int)caretLine, direction);
            return;
        }

        const Message msg = kmap.Find(k, m);
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
            "DoKeyDown: key=%{public}d mod=%{public}d msg=%{public}d", (int)k, (int)m, (int)msg);
        if (msg != static_cast<Message>(0)) {
            if (c) *c = true;
            WndProc(msg, 0, 0);
            needsRedraw = true;
            OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
                "DoKeyDown: WndProc completed OK");
            return;
        }
        if (c) *c = false;
        KeyDefault(k, m);
        needsRedraw = true;
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
            "DoKeyDown: KeyDefault completed OK");
    }
    void DoInsertChar(std::string_view sv, CharacterSource cs) { InsertCharacter(sv, cs); }

    // Public wrapper for protected TickFor
    void DoTick(TickReason reason) { TickFor(reason); }

    // Tick caret blink — unconditionally toggle caret visibility.
    // We drive ticking externally via SciTick (ArkTS setInterval),
    // so we do NOT check FineTickerRunning() — it's a no-op stub
    // that always returns false, which would prevent TickFrom from ever running.
    void DoTickCaret() {
        // Log caret state BEFORE toggle for diagnostics
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-CARET",
            "DoTickCaret: before active=%{public}d on=%{public}d hasFocus=%{public}d period=%{public}d",
            (int)caret.active, (int)caret.on, (int)hasFocus, (int)caret.period);
        TickFor(TickReason::caret);
        // Log caret state AFTER toggle
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-CARET",
            "DoTickCaret: after  active=%{public}d on=%{public}d hasFocus=%{public}d",
            (int)caret.active, (int)caret.on, (int)hasFocus);
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
    ed->WndProc(Message::SetCaretWidth, 2, 0);  // Explicit 2px width for visibility

    // Set default selection colours
    ed->WndProc(Message::SetSelFore, 1, 0xFFFFFF);
    ed->WndProc(Message::SetSelBack, 1, 0x0078D7);

    // Enable notifications
    ed->WndProc(Message::SetModEventMask, SC_MODEVENTMASKALL, 0);

    // Set some common settings
    ed->WndProc(Message::SetScrollWidth, 2000, 0);
    ed->WndProc(Message::SetScrollWidthTracking, 1, 0);
    ed->WndProc(Message::SetEndAtLastLine, 1, 0);

    // [Patch-0033h] Connect to system clipboard via OH_Pasteboard native API.
    // Scintilla's Copy()/Paste() overrides call clipboardSetter/clipboardGetter,
    // which we wire here to read/write the system pasteboard directly.
    ed->clipboardSetter = [ed](const std::string &text) {
        if (text.empty()) return;
        auto *pb = OH_Pasteboard_Create();
        if (!pb) return;
        auto *data = OH_UdmfData_Create();
        auto *record = OH_UdmfRecord_Create();
        auto *pt = OH_UdsPlainText_Create();
        OH_UdsPlainText_SetContent(pt, text.c_str());
        OH_UdmfRecord_AddPlainText(record, pt);
        OH_UdmfData_AddRecord(data, record);
        OH_Pasteboard_SetData(pb, data);
        OH_Pasteboard_Destroy(pb);
        OH_UdmfData_Destroy(data);
        OH_UdmfRecord_Destroy(record);
        OH_UdsPlainText_Destroy(pt);
    };
    ed->clipboardGetter = [ed]() -> std::string {
        auto *pb = OH_Pasteboard_Create();
        if (!pb || !OH_Pasteboard_HasType(pb, PASTEBOARD_MIMETYPE_TEXT_PLAIN)) {
            if (pb) OH_Pasteboard_Destroy(pb);
            return "";
        }
        int status = 0;
        auto *data = OH_Pasteboard_GetData(pb, &status);
        if (!data || status != 0) {
            OH_Pasteboard_Destroy(pb);
            return "";
        }
        OH_UdsPlainText *ptObj = OH_UdsPlainText_Create();
        int ret = (ptObj) ? OH_UdmfData_GetPrimaryPlainText(data, ptObj) : -1;
        std::string result;
        if (ret == 0 && ptObj) {
            const char *content = OH_UdsPlainText_GetContent(ptObj);
            if (content) result = content;
            OH_UdsPlainText_Destroy(ptObj);
        }
        OH_Pasteboard_Destroy(pb);
        OH_UdmfData_Destroy(data);
        return result;
    };

    m_impl->initialized = true;

    // [Patch-0041] Enable TOFU (□) display for missing glyphs instead of blank.
    // Without this, CJK characters with no matching glyph in the default typeface
    // render as completely invisible (blank space), making Chinese text lines
    // appear empty. With TOFU mode, they show as □ boxes — visible and debuggable.
    OH_Drawing_SetTextUndefinedGlyphDisplay(TEXT_NO_GLYPH_USE_TOFU);
    OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-INIT",
        "Init: TOFU (undefined glyph) display mode enabled");

    // [Patch-0034] Attach to InputMethod Framework for native IME support.
    // This allows Chinese/Japanese/Korean input methods to work directly
    // from the Native layer without going through ArkTS.
    {
        auto *ed = m_impl->editor.get();
        ed->imeProxy = OH_TextEditorProxy_Create();
        if (ed->imeProxy) {
            // Helper: static ptr for C callbacks
            static ScintillaOHOSEditor *s_imeEditor = ed;

            // InsertText: IME inserts text (composing or committed)
            OH_TextEditorProxy_SetInsertTextFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, const char16_t *text, size_t len) {
                    if (!s_imeEditor || !text || len == 0) return;
                    // [Patch-0037] Buffer only — DO NOT call WndProc from IPC thread!
                    // Convert char16_t to UTF-8 into pending buffer
                    std::string utf8;
                    utf8.reserve(len * 4);
                    for (size_t i = 0; i < len; i++) {
                        uint32_t cp = static_cast<uint16_t>(text[i]);
                        if (cp >= 0xD800 && cp <= 0xDBFF && i + 1 < len) {
                            uint32_t hi = cp, lo = static_cast<uint16_t>(text[++i]);
                            cp = (hi << 10) + lo - 0x35FDC00;
                        }
                        if (cp < 0x80) utf8.push_back(static_cast<char>(cp));
                        else if (cp < 0x800) { utf8.push_back(0xC0|(cp>>6)); utf8.push_back(0x80|(cp&0x3F)); }
                        else if (cp < 0x10000) { utf8.push_back(0xE0|(cp>>12)); utf8.push_back(0x80|((cp>>6)&0x3F)); utf8.push_back(0x80|(cp&0x3F)); }
                        else { utf8.push_back(0xF0|(cp>>18)); utf8.push_back(0x80|((cp>>12)&0x3F)); utf8.push_back(0x80|((cp>>6)&0x3F)); utf8.push_back(0x80|(cp&0x3F)); }
                    }
                    // Write to pending buffer (thread-safe)
                    {
                        std::lock_guard<std::mutex> lock(s_imeEditor->imePendingMutex);
                        s_imeEditor->imePendingText = std::move(utf8);
                        s_imeEditor->imePendingFlag = true;
                    }
                    OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-IME",
                        "InsertText: buffered len=%{public}zu (IPC thread, deferred to main)",
                        s_imeEditor->imePendingText.size());
                });

            // SetPreviewText: IME candidate/composing text preview
            OH_TextEditorProxy_SetSetPreviewTextFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, const char16_t *text, size_t length, int32_t start, int32_t end) -> int32_t {
                    if (!s_imeEditor || !text || length == 0) return -1;
                    // [Patch-0037] Buffer only — DO NOT call WndProc from IPC thread!
                    std::string utf8;
                    utf8.reserve(length * 4);
                    for (size_t i = 0; i < length; i++) {
                        uint32_t cp = static_cast<uint16_t>(text[i]);
                        if (cp < 0x80) utf8.push_back(static_cast<char>(cp));
                        else if (cp < 0x800) { utf8.push_back(0xC0|(cp>>6)); utf8.push_back(0x80|(cp&0x3F)); }
                        else { utf8.push_back(0xE0|(cp>>12)); utf8.push_back(0x80|((cp>>6)&0x3F)); utf8.push_back(0x80|(cp&0x3F)); }
                    }
                    {
                        std::lock_guard<std::mutex> lock(s_imeEditor->imePendingMutex);
                        s_imeEditor->imePendingText = std::move(utf8);
                        s_imeEditor->imePendingFlag = true;
                    }
                    (void)start; (void)end;
                    return 0;
                });

            // FinishTextPreview: composing finished, commit text
            OH_TextEditorProxy_SetFinishTextPreviewFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*) {
                    if (!s_imeEditor) return;
                    // Composing text is already inserted via SetPreviewText/InsertText
                    // Just clear the composing state
                    s_imeEditor->imeComposingText.clear();
                });

            // DeleteForward/Backward: IME deletion
            OH_TextEditorProxy_SetDeleteForwardFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, int32_t length) {
                    if (!s_imeEditor || length <= 0) return;
                    for (int i = 0; i < length; i++)
                        s_imeEditor->WndProc(Message::DeleteBackNotLine, 0, 0);
                    s_imeEditor->needsRedraw = true;
                });
            OH_TextEditorProxy_SetDeleteBackwardFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, int32_t length) {
                    if (!s_imeEditor || length <= 0) return;
                    for (int i = 0; i < length; i++)
                        s_imeEditor->WndProc(Message::DeleteBack, 0, 0);
                    s_imeEditor->needsRedraw = true;
                });

            // SendKeyboardStatus: keyboard show/hide → focus management
            OH_TextEditorProxy_SetSendKeyboardStatusFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, InputMethod_KeyboardStatus status) {
                    if (!s_imeEditor) return;
                    if (status == 1) s_imeEditor->FocusGained();
                    else s_imeEditor->FocusLost();
                });

            // SendEnterKey: IME enter key
            OH_TextEditorProxy_SetSendEnterKeyFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, InputMethod_EnterKeyType type) {
                    if (!s_imeEditor) return;
                    (void)type;
                    s_imeEditor->WndProc(Message::NewLine, 0, 0);
                    s_imeEditor->needsRedraw = true;
                });

            // MoveCursor: IME cursor movement request
            OH_TextEditorProxy_SetMoveCursorFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, InputMethod_Direction dir) {
                    if (!s_imeEditor) return;
                    Sci::Position pos = s_imeEditor->sel.MainCaret();
                    switch (dir) {
                        case 1: pos++; break;   // CURSOR_RIGHT
                        case 2: pos--; break;   // CURSOR_LEFT
                        case 3: pos = static_cast<Sci::Position>(s_imeEditor->WndProc(Message::Home, 0, 0)); break;
                        case 4: pos = static_cast<Sci::Position>(s_imeEditor->WndProc(Message::LineEnd, 0, 0)); break;
                        default: break;
                    }
                    s_imeEditor->WndProc(Message::SetCurrentPos, pos, 0);
                    s_imeEditor->WndProc(Message::SetAnchor, pos, 0);
                    s_imeEditor->WndProc(Message::ScrollCaret, 0, 0);
                    s_imeEditor->needsRedraw = true;
                });

            // HandleSetSelection: IME selection change
            OH_TextEditorProxy_SetHandleSetSelectionFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, int32_t start, int32_t end) {
                    if (!s_imeEditor) return;
                    s_imeEditor->WndProc(Message::SetSel, start, end);
                    s_imeEditor->needsRedraw = true;
                });

            // GetLeftTextOfCursor: provide context before cursor
            OH_TextEditorProxy_SetGetLeftTextOfCursorFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, int32_t number, char16_t text[], size_t *length) {
                    if (!s_imeEditor) { *length = 0; return; }
                    Sci::Position caret = s_imeEditor->sel.MainCaret();
                    Sci::Position start = (number > 0 && caret > number) ? caret - number : 0;
                    Sci::Position len = caret - start;
                    std::string context(len, '\0');
                    if (len > 0) s_imeEditor->pdoc->GetCharRange(const_cast<char*>(context.data()), start, len);
                    size_t idx = 0;
                    for (size_t i = 0; i < context.size() && idx < static_cast<size_t>(number); ) {
                        unsigned char c = static_cast<unsigned char>(context[i++]);
                        uint32_t cp;
                        if (c < 0x80) { cp = c; }
                        else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; i += 1; if (i <= context.size()) cp = (cp << 6) | (static_cast<unsigned char>(context[i-1]) & 0x3F); }
                        else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; i += 2; if (i <= context.size()) { cp = (cp << 12) | ((static_cast<unsigned char>(context[i-2]) & 0x3F) << 6); cp |= (static_cast<unsigned char>(context[i-1]) & 0x3F); } }
                        else { cp = c & 0x07; i += 3; }
                        if (cp < 0x10000) text[idx++] = static_cast<char16_t>(cp);
                        else { text[idx++] = static_cast<char16_t>(((cp-0x10000)>>10)+0xD800); text[idx++] = static_cast<char16_t>((cp&0x3FF)+0xDC00); }
                    }
                    *length = idx;
                });

            // GetRightTextOfCursor: provide context after cursor
            OH_TextEditorProxy_SetGetRightTextOfCursorFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, int32_t number, char16_t text[], size_t *length) {
                    if (!s_imeEditor) { *length = 0; return; }
                    Sci::Position caret = s_imeEditor->sel.MainCaret();
                    Sci::Position end = s_imeEditor->pdoc->Length();
                    Sci::Position limit = (caret + number < end) ? caret + number : end;
                    Sci::Position len = limit - caret;
                    std::string context(len, '\0');
                    if (len > 0) s_imeEditor->pdoc->GetCharRange(const_cast<char*>(context.data()), caret, len);
                    size_t idx = 0;
                    for (size_t i = 0; i < context.size() && idx < static_cast<size_t>(number); ) {
                        unsigned char c = static_cast<unsigned char>(context[i++]);
                        uint32_t cp;
                        if (c < 0x80) { cp = c; }
                        else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; i += 1; if (i <= context.size()) cp = (cp << 6) | (static_cast<unsigned char>(context[i-1]) & 0x3F); }
                        else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; i += 2; if (i <= context.size()) { cp = (cp << 12) | ((static_cast<unsigned char>(context[i-2]) & 0x3F) << 6); cp |= (static_cast<unsigned char>(context[i-1]) & 0x3F); } }
                        else { cp = c & 0x07; i += 3; }
                        if (cp < 0x10000) text[idx++] = static_cast<char16_t>(cp);
                        else { text[idx++] = static_cast<char16_t>(((cp-0x10000)>>10)+0xD800); text[idx++] = static_cast<char16_t>((cp&0x3FF)+0xDC00); }
                    }
                    *length = idx;
                });

            // GetTextIndexAtCursor: current cursor position
            OH_TextEditorProxy_SetGetTextIndexAtCursorFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*) -> int32_t {
                    if (!s_imeEditor) return 0;
                    return static_cast<int32_t>(s_imeEditor->sel.MainCaret());
                });

            // GetTextConfig: report input config to IME
            OH_TextEditorProxy_SetGetTextConfigFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, InputMethod_TextConfig *config) {
                    // Default config - let IME use its defaults
                    (void)config;
                });

            // HandleExtendAction: required by ImsaKit IsValidTextEditorProxy validation
            OH_TextEditorProxy_SetHandleExtendActionFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, InputMethod_ExtendAction action) {
                    if (!s_imeEditor) return;
                    (void)action;  // No special handling for extend actions yet
                });

            // ReceivePrivateCommand: required by ImsaKit IsValidTextEditorProxy validation
            OH_TextEditorProxy_SetReceivePrivateCommandFunc(ed->imeProxy,
                [](InputMethod_TextEditorProxy*, InputMethod_PrivateCommand *cmds[], size_t size) -> int32_t {
                    (void)cmds; (void)size;
                    return 0;  // Acknowledge but don't process
                });

            // Execute callbacks on main thread (safer for Scintilla)
            // [Patch-0034-fix] Set to false to allow direct IPC thread delivery.
            // With true, callbacks are posted to main thread message queue which
            // may not be processed correctly in our XComponent rendering context,
            // causing IMF insertText changes to hang (PrintTextChangeLogCount > 0).
            OH_TextEditorProxy_SetCallbackInMainThread(ed->imeProxy, false);

            // Attach to IME framework
            auto *options = OH_AttachOptions_Create(true);  // showKeyboard=true
            InputMethod_InputMethodProxy *inputProxy = nullptr;
            int ret = OH_InputMethodController_Attach(ed->imeProxy, options, &inputProxy);
            if (ret == 0 && inputProxy) {
                ed->imeInputProxy = inputProxy;
                ed->imeAttached = true;
                OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-IME",
                    "Init: IME attached successfully");
            } else {
                OH_LOG_Print(LOG_APP, LOG_WARN, 0xF100, "MNP-IME",
                    "Init: IME attach failed ret=%{public}d", ret);
                // Don't destroy proxy - may retry later
            }

            if (options) OH_AttachOptions_Destroy(options);
        } else {
            OH_LOG_Print(LOG_APP, LOG_WARN, 0xF100, "MNP-IME",
                "Init: Failed to create TextEditorProxy");
        }
    }
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

void ScintillaOHOS::Copy() {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::Copy, 0, 0);
}

void ScintillaOHOS::Cut() {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::Cut, 0, 0);
}

void ScintillaOHOS::Paste() {
    if (!m_impl->editor) return;
    m_impl->editor->WndProc(Message::Paste, 0, 0);
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
        case 309:  return Keys::Insert;
        case 310:  return Keys::End;       // SCK_END (was wrong: Keys::Add)
        case 311:  return Keys::Prior;     // SCK_PRIOR/PageUp (was wrong: Keys::Subtract)
        case 312:  return Keys::Next;      // SCK_NEXT/PageDown
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

    // Guard against any remaining abort sources (defense-in-depth)
    AbortGuard guard;
    if (guard.enter()) {
        bool consumed = false;
        ed->DoKeyDown(key, modifiers, &consumed);
    } else {
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnKeyDown recovered from abort via longjmp");
    }
}

void ScintillaOHOS::OnCharInput(const char *utf8Char, int charLen) {
    if (!m_impl->editor || !utf8Char || charLen <= 0) return;
    auto *ed = m_impl->editor.get();

    // [Patch-0034-fix] When IME is attached, let non-ASCII text be handled
    // exclusively by the IME InsertText callback. This prevents double-insertion
    // where both OnCharInput (keyboard path) and InsertText (IME path) insert
    // the same character for Chinese/Japanese/Korean input.
    if (ed->imeAttached) {
        unsigned char firstByte = static_cast<unsigned char>(utf8Char[0]);
        if (firstByte >= 0x80) {  // Non-ASCII (UTF-8 multi-byte start)
            OH_LOG_Print(LOG_APP, LOG_DEBUG, 0xF100, "MNP-IME",
                "OnCharInput: skipping non-ASCII (len=%{public}d), IME handles it", charLen);
            return;
        }
    }

    OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
        "OnCharInput: char='%s' len=%{public}d editor=%p", utf8Char, charLen, (void*)ed);

    // Insert the character directly (with abort guard for safety)
    std::string_view sv(utf8Char, static_cast<size_t>(charLen));
    AbortGuard guard;
    if (guard.enter()) {
        ed->DoInsertChar(sv, CharacterSource::DirectInput);
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH",
            "OnCharInput: DoInsertChar completed OK");
    } else {
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-TOUCH", "OnCharInput recovered from abort via longjmp");
    }
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

// ---- Reset Fonts (Fix C-05) ----

void ScintillaOHOS::ResetFonts() {
    if (m_impl && m_impl->editor) {
        m_impl->editor->fontsInitialized = false;
        OH_LOG_Print(LOG_APP, LOG_INFO, 0xF100, "MNP-RESET",
            "ScintillaOHOS::ResetFonts: fontsInitialized reset to false");
    }
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

void BN_Sci_Copy(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->Copy();
    }
}

void BN_Sci_Cut(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->Cut();
    }
}

void BN_Sci_Paste(void *editor) {
    if (editor) {
        static_cast<ScintillaOHOS *>(editor)->Paste();
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

// ---- ResetFonts (Fix C-05) ----

void BN_Sci_ResetFonts(void *editor) {
    if (!editor) return;
    static_cast<ScintillaOHOS*>(editor)->ResetFonts();
}

} // extern "C"
