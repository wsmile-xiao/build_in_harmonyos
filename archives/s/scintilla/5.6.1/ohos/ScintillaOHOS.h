/**
 * ScintillaOHOS.h - Complete Scintilla editor integration for HarmonyOS
 *
 * Provides:
 *   - ScintillaOHOS: ScintillaBase subclass with OHOS-specific window/surface/event handling
 *   - NAPI C exports for ArkTS integration
 *   - Input event bridging (touch/keyboard/scroll)
 *   - IME support
 *   - Clipboard integration hooks
 *
 * Usage from C++:
 *   auto editor = new ScintillaOHOS();
 *   editor->Init(800, 600);
 *   editor->SetText("Hello World\n");
 *   editor->OnDraw(ohDrawingCanvas);
 *
 * Usage from ArkTS (via NAPI):
 *   BN_Sci_Create()
 *   BN_Sci_SetText(editor, "Hello")
 *   BN_Sci_OnDraw(editor, drawContext)
 */

#ifndef SCINTILLA_OHOS_H
#define SCINTILLA_OHOS_H

#include <cstdint>
#include <cstddef>
#include <string>
#include <functional>

// Forward declare C API types
extern "C" {
typedef struct OH_Drawing_Canvas OH_Drawing_Canvas;
typedef struct ArkUI_NodeContent ArkUI_NodeContentHandle;
}

// ============================================================================
// ScintillaOHOS - The main editor class
// ============================================================================

class ScintillaOHOS {
public:
    ScintillaOHOS();
    ~ScintillaOHOS();

    // ---- Lifecycle ----
    void Init(int width, int height);
    void Destroy();

    // ---- Size ----
    void SetSize(int width, int height);
    int GetWidth() const;
    int GetHeight() const;

    // ---- Rendering (called from ContentSlot draw callback) ----
    void OnDraw(OH_Drawing_Canvas *canvas);

    // ---- Text operations ----
    void SetText(const char *text);
    const char *GetText(int *length = nullptr);
    void InsertText(int pos, const char *text);
    void ReplaceSel(const char *text);
    int GetLength();
    int GetLineCount();
    int GetCurLine();
    int GetCurPos();
    void SetCurPos(int pos);
    void SetSel(int start, int end);
    int GetSelStart();
    int GetSelEnd();
    void SelectAll();
    void Clear();
    void Undo();
    void Redo();
    bool CanUndo();
    bool CanRedo();
    bool GetModify();
    void SetSavePoint();

    // ---- Style ----
    void SetFont(const char *fontName, int sizePoints);
    void SetFontSize(int sizePoints);
    void SetTabSize(int tabSize);

    // ---- Scroll ----
    void ScrollTo(int line);
    int GetFirstVisibleLine();
    int GetLinesOnScreen();

    // ---- Focus ----
    void SetFocus(bool focused);
    bool HasFocus() const;

    // ---- Input events ----
    void OnTouchDown(float x, float y, uint32_t timestamp);
    void OnTouchMove(float x, float y, uint32_t timestamp);
    void OnTouchUp(float x, float y, uint32_t timestamp);
    void OnKeyDown(int keyCode, bool shift, bool ctrl, bool alt, bool meta);
    void OnCharInput(const char *utf8Char, int charLen);
    void OnScroll(float deltaX, float deltaY, bool ctrl);
    void OnRightClick(float x, float y, uint32_t timestamp);

    // ---- IME ----
    void OnIMEStart();
    void OnIMEEnd();
    void OnIMEComposition(const char *text, int cursorOffset);
    void OnIMECommit(const char *text);

    // ---- Clipboard (hooks for NAPI integration) ----
    using ClipboardGetFunc = std::function<std::string()>;
    using ClipboardSetFunc = std::function<void(const std::string&)>;
    void SetClipboardHandlers(ClipboardGetFunc getter, ClipboardSetFunc setter);

    // ---- Notifications (callbacks to host app) ----
    using NotifyFunc = std::function<void(int notificationCode, int wParam, int lParam,
                                           const char *text)>;
    void SetNotifyHandler(NotifyFunc handler);

    // ---- Tick / Timer (call periodically from host for caret blink) ----
    void Tick();  // calls TickFor(caret) + triggers redraw if needed

    // ---- Access underlying Scintilla for advanced use ----
    void *GetScintillaPtr() const;  // returns ScintillaBase*

private:
    struct Impl;
    Impl *m_impl;
};

// ============================================================================
// NAPI C exports for ArkTS integration
// ============================================================================

#ifdef __cplusplus
extern "C" {
#endif

// Lifecycle
void* BN_Sci_Create();
void BN_Sci_Destroy(void *editor);
void BN_Sci_Init(void *editor, int width, int height);

// Rendering
void BN_Sci_OnDraw(void *editor, void *drawContext);
void BN_Sci_SetSize(void *editor, int width, int height);

// Text
void BN_Sci_SetText(void *editor, const char *text);
const char* BN_Sci_GetText(void *editor, int *length);
void BN_Sci_InsertText(void *editor, int pos, const char *text);
void BN_Sci_ReplaceSel(void *editor, const char *text);
int BN_Sci_GetLength(void *editor);
int BN_Sci_GetLineCount(void *editor);
int BN_Sci_GetCurLine(void *editor);
int BN_Sci_GetCurPos(void *editor);
void BN_Sci_SetCurPos(void *editor, int pos);
void BN_Sci_SetSel(void *editor, int start, int end);
int BN_Sci_GetSelStart(void *editor);
int BN_Sci_GetSelEnd(void *editor);
void BN_Sci_SelectAll(void *editor);
void BN_Sci_Clear(void *editor);
void BN_Sci_Undo(void *editor);
void BN_Sci_Redo(void *editor);
int BN_Sci_CanUndo(void *editor);
int BN_Sci_CanRedo(void *editor);
int BN_Sci_GetModify(void *editor);
void BN_Sci_SetSavePoint(void *editor);

// Style
void BN_Sci_SetFont(void *editor, const char *fontName, int sizePoints);
void BN_Sci_SetTabSize(void *editor, int tabSize);

// Scroll
void BN_Sci_ScrollTo(void *editor, int line);
int BN_Sci_GetFirstVisibleLine(void *editor);

// Focus
void BN_Sci_SetFocus(void *editor, int focused);
int BN_Sci_HasFocus(void *editor);

// Redraw callback — set by host app to trigger display refresh
void BN_Sci_SetRedrawCallback(void (*cb)(void));

// Input events
void BN_Sci_OnTouchDown(void *editor, float x, float y, uint32_t timestamp);
void BN_Sci_OnTouchMove(void *editor, float x, float y, uint32_t timestamp);
void BN_Sci_OnTouchUp(void *editor, float x, float y, uint32_t timestamp);
void BN_Sci_OnKeyDown(void *editor, int keyCode, int shift, int ctrl, int alt, int meta);
void BN_Sci_OnChar(void *editor, const char *utf8, int len);
void BN_Sci_OnScroll(void *editor, float dx, float dy, int ctrl);
void BN_Sci_OnRightClick(void *editor, float x, float y, uint32_t timestamp);

// IME
void BN_Sci_OnIMEStart(void *editor);
void BN_Sci_OnIMEEnd(void *editor);
void BN_Sci_OnIMEComposition(void *editor, const char *text, int cursorOffset);
void BN_Sci_OnIMECommit(void *editor, const char *text);

// Clipboard handlers (set from ArkTS)
typedef const char* (*BN_ClipboardGetFunc)(void* userData);
typedef void (*BN_ClipboardSetFunc)(void* userData, const char* text);
void BN_Sci_SetClipboardHandlers(void *editor, BN_ClipboardGetFunc getter,
                                  BN_ClipboardSetFunc setter, void *userData);

// Notifications
typedef void (*BN_NotifyFunc)(void *userData, int code, int wParam, int lParam, const char *text);
void BN_Sci_SetNotifyHandler(void *editor, BN_NotifyFunc handler, void *userData);

// Tick — advance caret blink timer (call from ArkTS setInterval ~500ms)
void BN_Sci_Tick(void *editor);

#ifdef __cplusplus
}
#endif

#endif // SCINTILLA_OHOS_H
