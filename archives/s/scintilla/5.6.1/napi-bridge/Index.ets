import libentry from 'libentry.so';

// Custom XComponentController to manage Surface lifecycle
class SciXComponentController extends XComponentController {
  public onSurfaceReady: (() => void) | undefined = undefined;

  onSurfaceCreated(surfaceId: string): void {
    console.info(`[MyNotePad] onSurfaceCreated: surfaceId=${surfaceId}`);
    try {
      libentry.sciRegisterXComponent(surfaceId);
      console.info(`[MyNotePad] sciRegisterXComponent called`);
    } catch (e) {
      console.error(`[MyNotePad] sciRegisterXComponent failed: ${e}`);
    }
  }
  onSurfaceChanged(surfaceId: string, rect: SurfaceRect): void {
    console.info(`[MyNotePad] onSurfaceChanged: ${rect.surfaceWidth}x${rect.surfaceHeight}`);
    if (rect.surfaceWidth > 0 && rect.surfaceHeight > 0) {
      try {
        libentry.sciOnSurfaceChanged(rect.surfaceWidth, rect.surfaceHeight);
        if (this.onSurfaceReady) {
          this.onSurfaceReady();
        }
      } catch (e) {
        console.error(`[MyNotePad] sciOnSurfaceChanged failed: ${e}`);
      }
    }
  }
  onSurfaceDestroyed(surfaceId: string): void {
    console.info(`[MyNotePad] onSurfaceDestroyed`);
  }
}

@Entry
@Component
struct Index {
  @State message: string = 'Loading Scintilla...';
  @State lineCount: number = 0;
  @State charCount: number = 0;
  private editorHandle: number = 0;
  private xcController: SciXComponentController = new SciXComponentController();
  private textInitialized: boolean = false;
  private caretTimerId: number = -1;  // setInterval ID for caret blink

  aboutToAppear(): void {
    try {
      this.editorHandle = libentry.sciCreate() as number;
      if (this.editorHandle === 0) {
        this.message = 'Failed to create editor';
        return;
      }
      this.message = 'Editor created, waiting for XComponent...';
    } catch (e) {
      this.message = `Init error: ${e}`;
    }

    // Set callback for when surface is ready
    this.xcController.onSurfaceReady = () => {
      if (this.textInitialized) return;
      this.textInitialized = true;
      const editor = this.editorHandle;
      if (!editor) return;
      libentry.sciSetFont(editor, 'HarmonyOS Sans', 16);
      const sampleText =
        'Hello HarmonyOS!\n\n' +
        '欢迎使用 MyNotePad\n' +
        '基于 Scintilla 5.6.1 的原生文本编辑器\n\n' +
        'Features:\n' +
        '  - Scintilla 5.6.1 editor core\n' +
        '  - HarmonyOS Native Drawing API\n' +
        '  - NAPI bridge\n' +
        '  - XComponent integration\n\n' +
        'function hello() {\n' +
        '  console.log("Hello World!");\n' +
        '}\n';
      libentry.sciSetText(editor, sampleText);
      this.lineCount = libentry.sciGetLineCount(editor) as number;
      this.charCount = libentry.sciGetLength(editor) as number;
      this.message = `Ready - ${this.lineCount}L ${this.charCount}C`;

      // Start caret blink timer — Scintilla's FineTicker is a stub,
      // we drive TickFor(caret) from ArkTS side via setInterval
      if (this.caretTimerId < 0) {
        this.caretTimerId = setInterval(() => {
          try { libentry.sciTick(this.editorHandle); } catch (e) {}
        }, 500);  // matches SetCaretPeriod(500) in ScintillaOHOS::Init
      }
    };
  }

  aboutToDisappear(): void {
    // Stop caret blink timer
    if (this.caretTimerId >= 0) {
      clearInterval(this.caretTimerId);
      this.caretTimerId = -1;
    }
    // Destroy editor
    try {
      libentry.sciDestroy(this.editorHandle);
    } catch (e) {}
  }

  build() {
    Column() {
      // Title bar
      Row() {
        Text('MyNotePad')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .padding({ left: 16, top: 10, bottom: 10 })
        Blank()
        Text(`${this.lineCount}L  ${this.charCount}C`)
          .fontSize(12)
          .fontColor('#666666')
          .padding({ right: 16 })
      }
      .width('100%')
      .backgroundColor('#F5F5F5')
      .borderWidth({ bottom: 1 })
      .borderColor('#E0E0E0')

      // Editor: declarative XComponent (NO libraryname!)
      XComponent({
        type: XComponentType.SURFACE,
        controller: this.xcController
      })
        .id('scintilla_editor')
        .width('100%')
        .height('100%')
        .focusable(true)
        .focusOnTouch(true)
        .defaultFocus(true)
        .onTouch((event: TouchEvent) => {
          if (!event || !event.touches || event.touches.length === 0) return;
          const touch = event.touches[0];
          const editor = this.editorHandle;
          switch (event.type) {
            case TouchType.Down:
              libentry.sciOnTouch(editor, 0, touch.x, touch.y, event.timestamp);
              break;
            case TouchType.Move:
              libentry.sciOnTouch(editor, 2, touch.x, touch.y, event.timestamp);
              break;
            case TouchType.Up:
              libentry.sciOnTouch(editor, 1, touch.x, touch.y, event.timestamp);
              break;
            default:
              break;
          }
          // Request redraw after touch processing (async flush to screen)
          try { libentry.sciRequestRedraw(); } catch (e) {}
        })
        .onKeyEvent((event: KeyEvent) => {
          if (!event || event.type !== KeyType.Down) return;
          const editor = this.editorHandle;
          if (event.keyText && event.keyText.length === 1) {
            libentry.sciOnChar(editor, event.keyText);
          } else {
            let sciKey = 0;
            switch (event.keyCode) {
              case 2048: sciKey = 8; break;   // Backspace
              case 2054: sciKey = 13; break;  // Enter
              case 2049: sciKey = 9; break;   // Tab
              case 2070: sciKey = 27; break;  // Escape
              case 2002: sciKey = 37; break;  // Left arrow
              case 2003: sciKey = 39; break;  // Right arrow
              case 2000: sciKey = 38; break;  // Up arrow
              case 2001: sciKey = 40; break;  // Down arrow
              case 2055: sciKey = 46; break;  // Delete
              case 2016: sciKey = 36; break;  // Home
              case 2017: sciKey = 35; break;  // End
              default:
                break;
            }
            if (sciKey > 0) {
              libentry.sciOnKeyDown(editor, sciKey, 0, 0, 0, 0);
            }
          }
          // Request redraw after key processing
          try { libentry.sciRequestRedraw(); } catch (e) {}
        })
        .layoutWeight(1)

      // Status bar
      Row() {
        Text(this.message)
          .fontSize(12)
          .fontColor('#666666')
          .padding({ left: 16, top: 4, bottom: 4 })
      }
      .width('100%')
      .backgroundColor('#F0F0F0')
      .borderWidth({ top: 1 })
      .borderColor('#E0E0E0')
    }
    .width('100%')
    .height('100%')
  }
}
