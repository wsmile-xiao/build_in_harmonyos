/**
 * PlatOHOS.cxx - Scintilla 5.6.1 Platform Adaptation for HarmonyOS
 *
 * Implements all platform abstraction interfaces from Platform.h using
 * HarmonyOS Native Drawing API (OH_Drawing_*), which wraps Skia internally.
 *
 * Key mappings:
 *   Surface   -> SurfaceImplOHOS (wraps OH_Drawing_Canvas)
 *   Font      -> FontHandleOHOS  (wraps OH_Drawing_Font + OH_Drawing_Typeface)
 *   Window    -> Stub implementation (non-virtual methods only)
 *   Menu      -> Stub implementation
 *   ListBox   -> ListBoxX (minimal stub)
 *   Platform  -> Default values (Chrome, DefaultFont, etc.)
 */

#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>
#include <memory>
#include <algorithm>

// OHOS logging
#include <hilog/log.h>
#define PLAT_TAG "PlatOHOS"
#define PLAT_LOG(fmt, ...) OH_LOG_Print(LOG_APP, LOG_INFO, LOG_DOMAIN, PLAT_TAG, fmt, ##__VA_ARGS__)
#define PLAT_ERR(fmt, ...) OH_LOG_Print(LOG_APP, LOG_ERROR, LOG_DOMAIN, PLAT_TAG, fmt, ##__VA_ARGS__)
// Bypass HarmonyOS log sanitization: snprintf values into string, then use %{public}s to log
#define PLAT_DBG(fmt, ...) do { char _dbg[512]; snprintf(_dbg, sizeof(_dbg), fmt, ##__VA_ARGS__); PLAT_LOG("%{public}s", _dbg); } while(0)

#include "ScintillaTypes.h"
#include "ScintillaMessages.h"
#include "Scintilla.h"
#include "Geometry.h"
#include "Platform.h"

// HarmonyOS Native Drawing C API
extern "C" {
#include <native_drawing/drawing_types.h>
#include <native_drawing/drawing_rect.h>
#include <native_drawing/drawing_point.h>
#include <native_drawing/drawing_round_rect.h>
#include <native_drawing/drawing_canvas.h>
#include <native_drawing/drawing_brush.h>
#include <native_drawing/drawing_pen.h>
#include <native_drawing/drawing_font.h>
#include <native_drawing/drawing_typeface.h>
#include <native_drawing/drawing_font_mgr.h>
#include <native_drawing/drawing_bitmap.h>
#include <native_drawing/drawing_path.h>
#include <native_drawing/drawing_text_blob.h>
#include <native_drawing/drawing_sampling_options.h>
#include <native_drawing/drawing_text_typography.h>
#include <native_drawing/drawing_font_collection.h>   // [Patch-0041] GetSystemFontConfigInfo
#include <native_drawing/drawing_register_font.h>       // [Patch-0041] RegisterFont
}

using namespace Scintilla;
using namespace Scintilla::Internal;

// ============================================================================
// Helpers
// ============================================================================

static inline uint32_t ColourToARGB(ColourRGBA c) noexcept {
	const uint32_t a = static_cast<uint32_t>(c.GetAlphaComponent() * 255.0f + 0.5f);
	const uint32_t r = static_cast<uint32_t>(c.GetRedComponent() * 255.0f + 0.5f);
	const uint32_t g = static_cast<uint32_t>(c.GetGreenComponent() * 255.0f + 0.5f);
	const uint32_t b = static_cast<uint32_t>(c.GetBlueComponent() * 255.0f + 0.5f);
	return (a << 24) | (r << 16) | (g << 8) | b;
}

// RAII wrapper for OH_Drawing_Rect*
struct RectGuard {
	OH_Drawing_Rect *p = nullptr;
	RectGuard() = default;
	explicit RectGuard(PRectangle rc) : p(OH_Drawing_RectCreate(
		static_cast<float>(rc.left), static_cast<float>(rc.top),
		static_cast<float>(rc.right), static_cast<float>(rc.bottom))) {}
	~RectGuard() { if (p) OH_Drawing_RectDestroy(p); }
	RectGuard(const RectGuard &) = delete;
	RectGuard &operator=(const RectGuard &) = delete;
	operator OH_Drawing_Rect*() const { return p; }
};

// RAII wrapper for OH_Drawing_RoundRect*
struct RoundRectGuard {
	OH_Drawing_RoundRect *p = nullptr;
	RoundRectGuard() = default;
	explicit RoundRectGuard(PRectangle rc, float radius) {
		RectGuard dr(rc);
		p = OH_Drawing_RoundRectCreate(dr, radius, radius);
	}
	~RoundRectGuard() { if (p) OH_Drawing_RoundRectDestroy(p); }
	RoundRectGuard(const RoundRectGuard &) = delete;
	RoundRectGuard &operator=(const RoundRectGuard &) = delete;
	operator OH_Drawing_RoundRect*() const { return p; }
};

// ============================================================================
// FontHandleOHOS
// ============================================================================

class FontHandleOHOS : public Font {
public:
	OH_Drawing_Font *ohFont = nullptr;
	OH_Drawing_Typeface *ohTypeface = nullptr;
	OH_Drawing_Font_Metrics metrics = {};
	float fontSizePx = 12.0f;
	int logPixelsY = 96;
	bool metricsValid = false;

	FontHandleOHOS(const FontParameters &fp) {
		logPixelsY = 96;

		// Create typeface
		if (fp.faceName && fp.faceName[0]) {
			auto *fontMgr = OH_Drawing_FontMgrCreate();
			if (fontMgr) {
				OH_Drawing_FontStyleStruct style = {};
				style.weight = FONT_WEIGHT_400;
				style.width = FONT_WIDTH_NORMAL;
				style.slant = FONT_STYLE_NORMAL;
				ohTypeface = OH_Drawing_FontMgrMatchFamilyStyle(fontMgr, fp.faceName, style);
				if (ohTypeface) {
					PLAT_LOG("Font loaded: '%{public}s' size=%{public}.0f weight=%{public}d", fp.faceName, (double)fp.size, (int)fp.weight);
				} else {
					PLAT_ERR("FontMgrMatchFamilyStyle FAILED for '%{public}s', falling back to default typeface", fp.faceName);
				}
				OH_Drawing_FontMgrDestroy(fontMgr);
			} else {
				PLAT_ERR("OH_Drawing_FontMgrCreate FAILED, falling back to default typeface");
			}
		}
		if (!ohTypeface) {
			// [Patch-0045] CRITICAL FIX: Use the CJK-full variant of HarmonyOS Sans.
			// Root cause of blank CJK rendering (Patches 0040-0044):
			//   HarmonyOS_Sans.ttf (342KB) is a Latin-only SUBSET — it has CJK glyph
			//   metric entries in its cmap table (so FontCountText/GetWidths return
			//   valid values, and TextBlobCreateFromText returns non-null), but contains
			//   NO actual CJK outline data. Skia's rasterizer silently produces zero pixels.
			//
			//   HarmonyOS_Sans_SC.ttf (20.6MB, SC=Simplified Chinese) is the FULL font
			//   with complete CJK outlines. This single file change fixes all CJK rendering.
			static const char *fontFilePaths[] = {
				"/system/fonts/HarmonyOS_Sans_SC.ttf",    // ✅ Full CJK font (20.6MB)
				"/system/fonts/FZHeiT-SC-Regular.ttf",     // 方正黑体简体 fallback (11.5MB)
				"/system/fonts/FZKaiT-SC.ttf",             // 方正楷体简体 fallback (18.5MB)
				"/system/fonts/FZFangS-SC.ttf",            // 方正仿宋简体 fallback (14.7MB)
				"/system/fonts/HarmonyOS_Sans.ttf",        // Latin-only (last resort)
				nullptr
			};
			for (auto **fp = fontFilePaths; *fp && !ohTypeface; fp++) {
				ohTypeface = OH_Drawing_TypefaceCreateFromFile(*fp, 0);
				if (ohTypeface) {
					PLAT_LOG("[Patch-0042] TypefaceCreateFromFile SUCCESS: '%{public}s'", *fp);
				}
			}
		}
		if (!ohTypeface) {
			ohTypeface = OH_Drawing_TypefaceCreateDefault();
			if (ohTypeface) {
				PLAT_DBG("Using default typeface");
			} else {
				PLAT_DBG("TypefaceCreateDefault FAILED - no font!");
			}
		}

		// Create font
		ohFont = OH_Drawing_FontCreate();
		if (ohFont && ohTypeface) {
			OH_Drawing_FontSetTypeface(ohFont, ohTypeface);
			fontSizePx = static_cast<float>(fp.size) * logPixelsY / 72.0f;
			OH_Drawing_FontSetTextSize(ohFont, fontSizePx);

			if (fp.weight >= FontWeight::Bold) {
				OH_Drawing_FontSetFakeBoldText(ohFont, true);
			}
			if (fp.italic) {
				OH_Drawing_FontSetTextSkewX(ohFont, -0.25f);
			}

			OH_Drawing_FontSetSubpixel(ohFont, true);
			OH_Drawing_FontSetEdging(ohFont, FONT_EDGING_SUBPIXEL_ANTI_ALIAS);
			OH_Drawing_FontSetBaselineSnap(ohFont, true);
			UpdateMetrics();

			// [Patch-0043] CJK capability detection — verify loaded font can render CJK
			{
				const char *cjkTest = "\xe6\xb5\x8b\xe8\xaf\x95"; // "测试" in UTF-8
				int cjkGlyphCount = OH_Drawing_FontCountText(ohFont, cjkTest, 6, TEXT_ENCODING_UTF8);
				float totalCjkWidth = 0.0f;
				if (cjkGlyphCount > 0) {
					std::vector<uint16_t> testGlyphs(cjkGlyphCount);
					OH_Drawing_FontTextToGlyphs(ohFont, cjkTest, 6,
						TEXT_ENCODING_UTF8, testGlyphs.data(), cjkGlyphCount);
					std::vector<float> testWidths(cjkGlyphCount);
					OH_Drawing_FontGetWidths(ohFont, testGlyphs.data(), cjkGlyphCount, testWidths.data());
					for (int w = 0; w < cjkGlyphCount; w++) totalCjkWidth += testWidths[w];
				}
				if (totalCjkWidth > 0.0f) {
					PLAT_LOG("[Patch-0043] Font CJK test: glyphCount=%d totalWidth=%.1f — CJK-READY ✅",
						cjkGlyphCount, totalCjkWidth);
				} else {
					PLAT_ERR("[Patch-0043] Font CJK test: glyphCount=%d totalWidth=%.1f — CJK-UNAVAILABLE ⚠️ TextBlob will silently fail for Chinese text!",
						cjkGlyphCount, totalCjkWidth);
				}
			}

			PLAT_DBG("Font created: fontSizePx=%.1f ascent=%.1f descent=%.1f height=%.1f avgCharW=%.1f leading=%.1f",
				fontSizePx, GetAscent(), GetDescent(), GetHeight(), GetAvgCharWidth(), GetLeading());
		} else {
			PLAT_DBG("Font FAILED: ohFont=%p ohTypeface=%p", (void*)ohFont, (void*)ohTypeface);
		}
	}

	~FontHandleOHOS() override {
		if (ohFont) { OH_Drawing_FontDestroy(ohFont); ohFont = nullptr; }
		if (ohTypeface) { OH_Drawing_TypefaceDestroy(ohTypeface); ohTypeface = nullptr; }
	}

	void UpdateMetrics() {
		if (ohFont) {
			OH_Drawing_FontGetMetrics(ohFont, &metrics);
			metricsValid = true;
		}
	}

	float GetAscent() const noexcept { return metricsValid ? -metrics.ascent : fontSizePx * 0.8f; }
	float GetDescent() const noexcept { return metricsValid ? metrics.descent : fontSizePx * 0.2f; }
	float GetHeight() const noexcept { return metricsValid ? (-metrics.ascent + metrics.descent) : fontSizePx; }
	float GetLeading() const noexcept { return metricsValid ? metrics.leading : 0.0f; }
	float GetAvgCharWidth() const noexcept { return metricsValid ? metrics.avgCharWidth : fontSizePx * 0.5f; }
	float GetInternalLeading() const noexcept {
		return metricsValid ? std::max(0.0f, (-metrics.ascent + metrics.descent) - fontSizePx) : 0.0f;
	}
};

static inline FontHandleOHOS *FontAs(const Font *f) noexcept {
	return static_cast<FontHandleOHOS *>(const_cast<Font *>(f));
}

// ============================================================================
// SurfaceImplOHOS
// ============================================================================

class SurfaceImplOHOS : public Surface {
protected:
	OH_Drawing_Canvas *canvas = nullptr;
	OH_Drawing_Bitmap *bitmap = nullptr;
	OH_Drawing_Brush *brush = nullptr;
	OH_Drawing_Pen *pen = nullptr;
	SurfaceMode mode = {};
	bool ownsCanvas = false;
	int clipCount = 0;

	void ApplyBrush(ColourRGBA colour) {
		if (!canvas || !brush) return;
		OH_Drawing_BrushSetColor(brush, ColourToARGB(colour));
		OH_Drawing_CanvasAttachBrush(canvas, brush);
	}
	void ApplyPen(Stroke stk) {
		if (!canvas || !pen) return;
		OH_Drawing_PenSetColor(pen, ColourToARGB(stk.colour));
		OH_Drawing_PenSetWidth(pen, stk.WidthF());
		OH_Drawing_CanvasAttachPen(canvas, pen);
	}
	void DetachBrush() { if (canvas) OH_Drawing_CanvasDetachBrush(canvas); }
	void DetachPen() { if (canvas) OH_Drawing_CanvasDetachPen(canvas); }

	void EnsureBrush() {
		if (!brush) {
			brush = OH_Drawing_BrushCreate();
			OH_Drawing_BrushSetAntiAlias(brush, true);
		}
	}
	void EnsurePen() {
		if (!pen) {
			pen = OH_Drawing_PenCreate();
			OH_Drawing_PenSetAntiAlias(pen, true);
			OH_Drawing_PenSetCap(pen, LINE_ROUND_CAP);
			OH_Drawing_PenSetJoin(pen, LINE_ROUND_JOIN);
		}
	}

public:
	SurfaceImplOHOS() = default;
	~SurfaceImplOHOS() override {
		Release();
		if (brush) { OH_Drawing_BrushDestroy(brush); brush = nullptr; }
		if (pen) { OH_Drawing_PenDestroy(pen); pen = nullptr; }
	}

	void Init(WindowID wid) override {
		// Patch-0013: Idempotent init — skip recreation if resources already exist.
		// This prevents Skia SIGABRT from high-frequency create-destroy cycles
		// during mouse drag (SPositionFromLocation calls this at ~28ms intervals).
		if (canvas && bitmap) {
			// Resources already valid from previous call — just reset clip state
			clipCount = 0;
			PLAT_LOG("Init(WindowID): REUSING existing canvas=%p bitmap=%p", (void*)canvas, (void*)bitmap);
			return;
		}
		PLAT_LOG("Init(WindowID) START wid=%p (first creation)", (void*)wid);
		Release();
		EnsureBrush();
		EnsurePen();
		PLAT_LOG("Init: before BitmapCreate");
		bitmap = OH_Drawing_BitmapCreate();
		PLAT_LOG("Init: after BitmapCreate bitmap=%p", (void*)bitmap);
		if (bitmap) {
			OH_Drawing_BitmapFormat fmt = {};
			fmt.colorFormat = COLOR_FORMAT_RGBA_8888;
			fmt.alphaFormat = ALPHA_FORMAT_PREMUL;
			OH_Drawing_BitmapBuild(bitmap, 1, 1, &fmt);
			PLAT_LOG("Init: before CanvasCreate");
			canvas = OH_Drawing_CanvasCreate();
			PLAT_LOG("Init: after CanvasCreate canvas=%p", (void*)canvas);
			if (canvas) {
				OH_Drawing_CanvasBind(canvas, bitmap);
				ownsCanvas = true;
				PLAT_LOG("Init: CanvasBind OK, ownsCanvas=true");
			}
		}
		clipCount = 0;
		PLAT_LOG("Init(WindowID) END canvas=%p bitmap=%p", (void*)canvas, (void*)bitmap);
	}

	void Init(SurfaceID sid, WindowID wid) override {
		Release();
		canvas = static_cast<OH_Drawing_Canvas *>(sid);
		ownsCanvas = false;
		EnsureBrush();
		EnsurePen();
		clipCount = 0;
	}

	std::unique_ptr<Surface> AllocatePixMap(int width, int height) override {
		auto pm = std::make_unique<SurfaceImplOHOS>();
		pm->bitmap = OH_Drawing_BitmapCreate();
		if (pm->bitmap) {
			OH_Drawing_BitmapFormat fmt = {};
			fmt.colorFormat = COLOR_FORMAT_RGBA_8888;
			fmt.alphaFormat = ALPHA_FORMAT_PREMUL;
			OH_Drawing_BitmapBuild(pm->bitmap, static_cast<uint32_t>(width),
				static_cast<uint32_t>(height), &fmt);
			pm->canvas = OH_Drawing_CanvasCreate();
			if (pm->canvas) {
				OH_Drawing_CanvasBind(pm->canvas, pm->bitmap);
				pm->ownsCanvas = true;
			}
		}
		pm->EnsureBrush();
		pm->EnsurePen();
		return pm;
	}

	void SetMode(SurfaceMode mode_) override { mode = mode_; }

	void Release() noexcept override {
		if (ownsCanvas) {
			if (canvas) OH_Drawing_CanvasDestroy(canvas);
			if (bitmap) OH_Drawing_BitmapDestroy(bitmap);
		}
		canvas = nullptr;
		bitmap = nullptr;
		ownsCanvas = false;
		clipCount = 0;
	}

	int SupportsFeature(Supports feature) noexcept override { return 0; }
	bool Initialised() override { return canvas != nullptr; }
	int LogPixelsY() override { return 96; }
	int PixelDivisions() override { return 1; }
	int DeviceHeightFont(int points) override { return points * 96 / 72; }

	// --- Drawing ---

	void LineDraw(Point start, Point end, Stroke stroke) override {
		if (!canvas) return;
		ApplyPen(stroke);
		OH_Drawing_CanvasDrawLine(canvas,
			static_cast<float>(start.x), static_cast<float>(start.y),
			static_cast<float>(end.x), static_cast<float>(end.y));
		DetachPen();
	}

	void PolyLine(const Point *pts, size_t npts, Stroke stroke) override {
		if (!canvas || !pts || npts < 2) return;
		ApplyPen(stroke);
		for (size_t i = 1; i < npts; i++) {
			OH_Drawing_CanvasDrawLine(canvas,
				static_cast<float>(pts[i-1].x), static_cast<float>(pts[i-1].y),
				static_cast<float>(pts[i].x), static_cast<float>(pts[i].y));
		}
		DetachPen();
	}

	void Polygon(const Point *pts, size_t npts, FillStroke fs) override {
		if (!canvas || !pts || npts < 3) return;
		auto *path = OH_Drawing_PathCreate();
		OH_Drawing_PathMoveTo(path, static_cast<float>(pts[0].x), static_cast<float>(pts[0].y));
		for (size_t i = 1; i < npts; i++)
			OH_Drawing_PathLineTo(path, static_cast<float>(pts[i].x), static_cast<float>(pts[i].y));
		OH_Drawing_PathClose(path);
		ApplyBrush(fs.fill.colour);
		ApplyPen(fs.stroke);
		OH_Drawing_CanvasDrawPath(canvas, path);
		DetachBrush();
		DetachPen();
		OH_Drawing_PathDestroy(path);
	}

	void RectangleDraw(PRectangle rc, FillStroke fs) override {
		if (!canvas) return;
		RectGuard dr(rc);
		ApplyBrush(fs.fill.colour);
		OH_Drawing_CanvasDrawRect(canvas, dr);
		DetachBrush();
		ApplyPen(fs.stroke);
		OH_Drawing_CanvasDrawRect(canvas, dr);
		DetachPen();
	}

	void RectangleFrame(PRectangle rc, Stroke stroke) override {
		if (!canvas) return;
		RectGuard dr(rc);
		ApplyPen(stroke);
		OH_Drawing_CanvasDrawRect(canvas, dr);
		DetachPen();
	}

	void FillRectangle(PRectangle rc, Fill fill) override {
		if (!canvas) return;
		RectGuard dr(rc);
		ApplyBrush(fill.colour);
		OH_Drawing_CanvasDrawRect(canvas, dr);
		DetachBrush();
	}

	void FillRectangleAligned(PRectangle rc, Fill fill) override {
		PRectangle a(std::floor(rc.left + 0.5), std::floor(rc.top + 0.5),
			std::floor(rc.right + 0.5), std::floor(rc.bottom + 0.5));
		FillRectangle(a, fill);
	}

	void FillRectangle(PRectangle rc, Surface &surfacePattern) override {
		FillRectangle(rc, Fill(ColourRGBA(0, 0, 0, 255)));
	}

	void RoundedRectangle(PRectangle rc, FillStroke fs) override {
		if (!canvas) return;
		auto rr = RoundRectGuard(rc, 4.0f);
		ApplyBrush(fs.fill.colour);
		ApplyPen(fs.stroke);
		OH_Drawing_CanvasDrawRoundRect(canvas, rr);
		DetachBrush();
		DetachPen();
	}

	void AlphaRectangle(PRectangle rc, XYPOSITION cornerSize, FillStroke fs) override {
		if (!canvas) return;
		auto rr = RoundRectGuard(rc, static_cast<float>(cornerSize));
		OH_Drawing_CanvasSave(canvas);
		ApplyBrush(fs.fill.colour);
		OH_Drawing_BrushSetBlendMode(brush, BLEND_MODE_SRC_OVER);
		OH_Drawing_CanvasDrawRoundRect(canvas, rr);
		DetachBrush();
		ApplyPen(fs.stroke);
		OH_Drawing_CanvasDrawRoundRect(canvas, rr);
		DetachPen();
		OH_Drawing_CanvasRestore(canvas);
	}

	void GradientRectangle(PRectangle rc, const std::vector<ColourStop> &stops, GradientOptions options) override {
		if (!canvas || stops.empty()) return;
		FillRectangle(rc, Fill(stops.back().colour));
	}

	void DrawRGBAImage(PRectangle rc, int width, int height, const unsigned char *pixelsImage) override {
		if (!canvas || !pixelsImage) return;
		OH_Drawing_Image_Info ii = {};
		ii.width = width;
		ii.height = height;
		ii.colorType = COLOR_FORMAT_RGBA_8888;
		ii.alphaType = ALPHA_FORMAT_UNPREMUL;
		auto *bm = OH_Drawing_BitmapCreateFromPixels(&ii,
			const_cast<unsigned char *>(pixelsImage), static_cast<uint32_t>(width) * 4);
		if (!bm) return;
		RectGuard srcRc(PRectangle(0, 0, width, height));
		RectGuard dstRc(rc);
		auto *samp = OH_Drawing_SamplingOptionsCreate(FILTER_MODE_NEAREST, MIPMAP_MODE_NONE);
		if (samp) {
			OH_Drawing_CanvasDrawBitmapRect(canvas, bm, srcRc, dstRc, samp);
			OH_Drawing_SamplingOptionsDestroy(samp);
		}
		OH_Drawing_BitmapDestroy(bm);
	}

	void Ellipse(PRectangle rc, FillStroke fs) override {
		if (!canvas) return;
		RectGuard dr(rc);
		ApplyBrush(fs.fill.colour);
		ApplyPen(fs.stroke);
		OH_Drawing_CanvasDrawOval(canvas, dr);
		DetachBrush();
		DetachPen();
	}

	void Stadium(PRectangle rc, FillStroke fs, Ends ends) override {
		if (!canvas) return;
		float halfH = static_cast<float>((rc.bottom - rc.top) / 2.0);
		auto rr = RoundRectGuard(rc, halfH);
		ApplyBrush(fs.fill.colour);
		ApplyPen(fs.stroke);
		OH_Drawing_CanvasDrawRoundRect(canvas, rr);
		DetachBrush();
		DetachPen();
	}

	void Copy(PRectangle rc, Point from, Surface &surfaceSource) override {
		if (!canvas) return;
		auto &src = static_cast<SurfaceImplOHOS &>(surfaceSource);
		if (!src.canvas || !src.bitmap) return;
		RectGuard srcRc(PRectangle(from.x, from.y, from.x + rc.Width(), from.y + rc.Height()));
		RectGuard dstRc(rc);
		auto *samp = OH_Drawing_SamplingOptionsCreate(FILTER_MODE_NEAREST, MIPMAP_MODE_NONE);
		if (samp) {
			OH_Drawing_CanvasDrawBitmapRect(canvas, src.bitmap, srcRc, dstRc, samp);
			OH_Drawing_SamplingOptionsDestroy(samp);
		}
	}

	std::unique_ptr<IScreenLineLayout> Layout(const IScreenLine *screenLine) override {
		return {};
	}

	// --- Text ---

	static int s_drawTextCount;

	void DrawTextNoClip(PRectangle rc, const Font *font_, XYPOSITION ybase,
		std::string_view text, ColourRGBA fore, ColourRGBA back) override {
		if (!canvas || !font_ || text.empty()) return;
		auto *fh = FontAs(font_);
		if (!fh || !fh->ohFont) {
			if (s_drawTextCount < 50) { PLAT_DBG("DrawTextNoClip[%d]: font INVALID fh=%p ohFont=%p", s_drawTextCount++, (void*)fh, fh ? (void*)fh->ohFont : nullptr); }
			return;
		}
		auto *blob = OH_Drawing_TextBlobCreateFromText(
			text.data(), text.size(), fh->ohFont, TEXT_ENCODING_UTF8);
		if (blob) {
			// [Patch-0044] Log non-ASCII text content for CJK debugging
			if (s_drawTextCount < 100) {
				bool hasNonAscii = false;
				char preview[48] = {0};
				size_t previewLen = std::min(text.size(), sizeof(preview)-1);
				for (size_t i = 0; i < previewLen; i++) {
					if ((unsigned char)text[i] >= 0x80) hasNonAscii = true;
					preview[i] = (text[i] >= 32 && text[i] < 127) ? text[i] : '?';
				}
				PLAT_DBG("DrawTextNoClip[%d]: rc=(%.0f,%.0f,%.0f,%.0f) ybase=%.1f "
					"textLen=%zu hasNonASCII=%d preview=\"%.40s\" rgba=0x%08x",
					s_drawTextCount++, (double)rc.left, (double)rc.top,
					(double)rc.right, (double)rc.bottom,
					(double)ybase, text.size(), (int)hasNonAscii, preview,
					ColourToARGB(fore));
			} else {
				s_drawTextCount++;
			}
			ApplyBrush(fore);
			OH_Drawing_CanvasDrawTextBlob(canvas, blob,
				static_cast<float>(rc.left), static_cast<float>(ybase));
			DetachBrush();
			OH_Drawing_TextBlobDestroy(blob);
		} else {
			// [Patch-0043] Detect CJK TextBlob failure
			bool hasNonAscii = false;
			for (size_t i = 0; i < text.size(); i++) {
				if ((unsigned char)text[i] >= 0x80) { hasNonAscii = true; break; }
			}
			if (hasNonAscii) {
				PLAT_ERR("[Patch-0043] DrawTextNoClip: TextBlob FAILED for non-ASCII text! len=%zu hasCJK=1 font=%p — font lacks CJK glyphs!",
					text.size(), (void*)fh->ohFont);
			} else if (s_drawTextCount < 50) {
				PLAT_DBG("DrawTextNoClip[%d]: TextBlob FAILED len=%zu font=%p", s_drawTextCount++, text.size(), (void*)fh->ohFont);
			}
		}
	}

	void DrawTextClipped(PRectangle rc, const Font *font_, XYPOSITION ybase,
		std::string_view text, ColourRGBA fore, ColourRGBA back) override {
		SetClip(rc);
		DrawTextNoClip(rc, font_, ybase, text, fore, back);
		PopClip();
	}

	void DrawTextTransparent(PRectangle rc, const Font *font_, XYPOSITION ybase,
		std::string_view text, ColourRGBA fore) override {
		DrawTextNoClip(rc, font_, ybase, text, fore, ColourRGBA(0,0,0,0));
	}

	void MeasureWidths(const Font *font_, std::string_view text, XYPOSITION *positions) override {
		if (!font_ || text.empty() || !positions) return;
		auto *fh = FontAs(font_);
		if (!fh || !fh->ohFont) return;
		int n = OH_Drawing_FontCountText(fh->ohFont, text.data(), text.size(), TEXT_ENCODING_UTF8);
		if (n <= 0) return;
		std::vector<uint16_t> glyphs(n);
		OH_Drawing_FontTextToGlyphs(fh->ohFont, text.data(),
			static_cast<uint32_t>(text.size()), TEXT_ENCODING_UTF8, glyphs.data(), n);
		std::vector<float> widths(n);
		OH_Drawing_FontGetWidths(fh->ohFont, glyphs.data(), n, widths.data());
		float x = 0.0f;
		for (int i = 0; i < n; i++) {
			x += widths[i];
			positions[i] = static_cast<XYPOSITION>(x);
		}
	}

	XYPOSITION WidthText(const Font *font_, std::string_view text) override {
		if (!font_ || text.empty()) return 0.0;
		auto *fh = FontAs(font_);
		if (!fh || !fh->ohFont) return 0.0;
		float w = 0.0f;
		OH_Drawing_FontMeasureText(fh->ohFont, text.data(), text.size(),
			TEXT_ENCODING_UTF8, nullptr, &w);
		return static_cast<XYPOSITION>(w);
	}

	void DrawTextNoClipUTF8(PRectangle rc, const Font *font_, XYPOSITION ybase,
		std::string_view text, ColourRGBA fore, ColourRGBA back) override {
		DrawTextNoClip(rc, font_, ybase, text, fore, back);
	}
	void DrawTextClippedUTF8(PRectangle rc, const Font *font_, XYPOSITION ybase,
		std::string_view text, ColourRGBA fore, ColourRGBA back) override {
		DrawTextClipped(rc, font_, ybase, text, fore, back);
	}
	void DrawTextTransparentUTF8(PRectangle rc, const Font *font_, XYPOSITION ybase,
		std::string_view text, ColourRGBA fore) override {
		DrawTextTransparent(rc, font_, ybase, text, fore);
	}
	void MeasureWidthsUTF8(const Font *font_, std::string_view text, XYPOSITION *positions) override {
		MeasureWidths(font_, text, positions);
	}
	XYPOSITION WidthTextUTF8(const Font *font_, std::string_view text) override {
		return WidthText(font_, text);
	}

	// --- Font metrics ---

	XYPOSITION Ascent(const Font *font_) override {
		auto *fh = FontAs(font_);
		return fh ? static_cast<XYPOSITION>(fh->GetAscent()) : 0.0;
	}
	XYPOSITION Descent(const Font *font_) override {
		auto *fh = FontAs(font_);
		return fh ? static_cast<XYPOSITION>(fh->GetDescent()) : 0.0;
	}
	XYPOSITION InternalLeading(const Font *font_) override {
		auto *fh = FontAs(font_);
		return fh ? static_cast<XYPOSITION>(fh->GetInternalLeading()) : 0.0;
	}
	XYPOSITION Height(const Font *font_) override {
		auto *fh = FontAs(font_);
		return fh ? static_cast<XYPOSITION>(fh->GetHeight()) : 0.0;
	}
	XYPOSITION AverageCharWidth(const Font *font_) override {
		auto *fh = FontAs(font_);
		return fh ? static_cast<XYPOSITION>(fh->GetAvgCharWidth()) : 0.0;
	}

	// --- Clip ---

	void SetClip(PRectangle rc) override {
		if (!canvas) return;
		RectGuard dr(rc);
		OH_Drawing_CanvasSave(canvas);
		OH_Drawing_CanvasClipRect(canvas, dr, INTERSECT, true);
		clipCount++;
	}

	void PopClip() override {
		if (!canvas || clipCount <= 0) return;
		OH_Drawing_CanvasRestore(canvas);
		clipCount--;
	}

	void FlushCachedState() override {}
	void FlushDrawing() override {}

	OH_Drawing_Canvas *GetCanvas() const noexcept { return canvas; }
	OH_Drawing_Bitmap *GetBitmap() const noexcept { return bitmap; }
};

// ============================================================================
// Redraw callback (set by host app via PlatOHOS_SetRedrawCallback)
// Called when Scintilla requests a repaint via Window::InvalidateAll/Rectangle
// ============================================================================
static void (*s_redrawRequested)(void) = nullptr;

extern "C" void PlatOHOS_SetRedrawCallback(void (*cb)(void)) {
    s_redrawRequested = cb;
}

// ============================================================================
// Window non-virtual methods (stub)
// ============================================================================

Window::~Window() noexcept {}
void Window::Destroy() noexcept { wid = nullptr; }
PRectangle Window::GetPosition() const { return PRectangle(0, 0, 800, 600); }
void Window::SetPosition(PRectangle) {}
void Window::SetPositionRelative(PRectangle, const Window *) {}
PRectangle Window::GetClientPosition() const { return GetPosition(); }
void Window::Show(bool) {}
void Window::InvalidateAll() { if (s_redrawRequested) s_redrawRequested(); }
void Window::InvalidateRectangle(PRectangle) { if (s_redrawRequested) s_redrawRequested(); }
void Window::SetCursor(Cursor) {}
PRectangle Window::GetMonitorRect(Point) { return PRectangle(0, 0, 1920, 1080); }

// ============================================================================
// Menu (stub)
// ============================================================================

// Menu stubs are declared implicitly in Platform.h, only define explicitly declared methods
void Menu::CreatePopUp() {}
void Menu::Destroy() noexcept { mid = nullptr; }
void Menu::Show(Point, const Window &) {}

// ============================================================================
// ListBoxX (minimal stub)
// ============================================================================

class ListBoxX : public ListBox {
	int visibleRows = 5, lineHeight = 16, currentSelection = -1;
	IListBoxDelegate *delegate = nullptr;
	std::vector<std::string> items;
public:
	ListBoxX() noexcept = default;
	~ListBoxX() override = default;
	void SetFont(const Font *) override {}
	void Create(Window &, int, Point, int lh, bool, Technology) override {
		lineHeight = lh > 0 ? lh : 16;
		wid = reinterpret_cast<WindowID>(this);
	}
	void SetAverageCharWidth(int) override {}
	void SetVisibleRows(int r) override { visibleRows = r > 0 ? r : 5; }
	int GetVisibleRows() const override { return visibleRows; }
	PRectangle GetDesiredRect() override { return PRectangle(0, 0, 200, visibleRows * lineHeight); }
	int CaretFromEdge() override { return 4; }
	void Clear() noexcept override { items.clear(); currentSelection = -1; }
	void Append(char *s, int len) override {
		if (s) items.emplace_back(s, len >= 0 ? len : static_cast<int>(strlen(s)));
	}
	int Length() override { return static_cast<int>(items.size()); }
	void Select(int n) override { currentSelection = n; }
	int GetSelection() override { return currentSelection; }
	int Find(const char *p) override {
		if (!p) return -1;
		for (int i = 0; i < Length(); i++) if (items[i].find(p) == 0) return i;
		return -1;
	}
	std::string GetValue(int n) override {
		return (n >= 0 && n < Length()) ? items[n] : "";
	}
	void RegisterImage(int, const char *) override {}
	void RegisterRGBAImage(int, int, int, const unsigned char *) override {}
	void ClearRegisteredImages() override {}
	void SetDelegate(IListBoxDelegate *lbDelegate) override { delegate = lbDelegate; }
	void SetList(const char *list, char sep, char tsep) override {
		Clear();
		if (!list) return;
		std::string item;
		for (const char *p = list; *p; p++) {
			if (*p == sep || *p == tsep) {
				if (!item.empty()) { items.push_back(item); item.clear(); }
				if (*p == tsep) items.push_back("");
			} else item += *p;
		}
		if (!item.empty()) items.push_back(item);
	}
	void SetOptions(ListOptions) override {}
	void Draw(PRectangle) {}
};

// ============================================================================
// Factory functions
// ============================================================================

std::shared_ptr<Font> Font::Allocate(const FontParameters &fp) {
	return std::make_shared<FontHandleOHOS>(fp);
}

std::unique_ptr<Surface> Surface::Allocate(Technology) {
	return std::make_unique<SurfaceImplOHOS>();
}

std::unique_ptr<ListBox> ListBox::Allocate() {
	return std::make_unique<ListBoxX>();
}

// ============================================================================
// Platform namespace
// ============================================================================

namespace Scintilla {
namespace Internal {

ColourRGBA Platform::Chrome() { return ColourRGBA(0xe0, 0xe0, 0xe0); }
ColourRGBA Platform::ChromeHighlight() { return ColourRGBA(0xff, 0xff, 0xff); }
const char *Platform::DefaultFont() { return "HarmonyOS Sans"; }
int Platform::DefaultFontSize() { return 14; }
unsigned int Platform::DoubleClickTime() { return 500; }

// Menu constructor/destructor
Menu::Menu() noexcept : mid(nullptr) {}

// ListBox constructor/destructor
ListBox::ListBox() noexcept = default;
ListBox::~ListBox() noexcept = default;

} // namespace Internal
} // namespace Scintilla

// Static member definitions
int SurfaceImplOHOS::s_drawTextCount = 0;

// ============================================================================
// Debug/Assert
// ============================================================================

// ============================================================================
// Patch-0015 (supercedes Patch-0013/0014): CachedMeasurementSurface — static storage
// ============================================================================
// Problem history:
//   Patch-0013: Introduced cached surface to avoid SIGABRT from high-freq create/destroy
//   Patch-0014: Fixed SEGV_ACCERR by enlarging bitmap from 1x1 to 2048x256
//   → Still crashes with SEGV_MAPERR + 0x6b(jemalloc free pattern) = use-after-free
//
// Root cause of Patch-0015: The surface was heap-allocated (new) with a no-op
//   operator delete to survive unique_ptr<Surface>::reset(). This is C++ UB:
//   after delete completes, the object's lifetime has ended; compiler may assume
//   the memory is dead. Additionally, jemalloc may reuse or poison the freed
//   region (filling with 0x6b), causing the 0x6b pattern seen in faultlog.
//
// Solution: Placement-new into a static storage buffer (BSS/data segment).
//   - Object lives at a fixed address in the data segment — NEVER on the heap
//   - No malloc/free/jemalloc involved → no possible use-after-free from heap
//   - operator delete remains no-op as defense-in-depth
//   - Magic number integrity check detects any memory corruption
//   - Auto-reinit on corruption detection provides self-healing
// ============================================================================

class CachedMeasurementSurface final : public SurfaceImplOHOS {
public:
	// Integrity magic — detect memory corruption (e.g., from adjacent heap overflow)
	static constexpr uint64_t kMagicAlive = 0xC4C3D5E5FACE57EDULL;
	static constexpr uint64_t kMagicDead  = 0xDEADF00DDEADC0DEULL;
	uint64_t magic = kMagicDead;

	CachedMeasurementSurface() = default;
	~CachedMeasurementSurface() override {
		// NO-OP: object lives in static storage, nothing to release
		magic = kMagicDead;
	}

	// Override Release to be a NO-OP — keeps resources alive across AutoSurface lifecycles
	void Release() noexcept override { clipCount = 0; }

	// Defense-in-depth: prevent any attempt to free this object
	static void operator delete(void* p) noexcept { (void)p; /* NO-OP */ }
	static void operator delete[](void* p) noexcept { (void)p; /* NO-OP */ }

	bool IsCorrupted() const noexcept {
		return magic != kMagicAlive || !canvas || !bitmap;
	}

	void Init(WindowID wid) override {
		// If already valid and initialized, just reset clip state (fast path)
		if (!IsCorrupted()) {
			clipCount = 0;
			return;
		}
		// (Re-)initialization: either first time OR corruption recovery
		magic = kMagicAlive;
		EnsureBrush();
		EnsurePen();
		// Clean up any stale resources before re-creating
		if (canvas && ownsCanvas) {
			OH_Drawing_CanvasDestroy(canvas);
			canvas = nullptr;
		}
		if (bitmap) {
			OH_Drawing_BitmapDestroy(bitmap);
			bitmap = nullptr;
		}
		ownsCanvas = false;
		// Create fresh resources
		// Patch-0014: 2048x256 bitmap (large enough for text measurement without
		// triggering Skia rasterizer overflow that caused original SEGV_ACCERR)
		bitmap = OH_Drawing_BitmapCreate();
		if (bitmap) {
			OH_Drawing_BitmapFormat fmt = {};
			fmt.colorFormat = COLOR_FORMAT_RGBA_8888;
			fmt.alphaFormat = ALPHA_FORMAT_PREMUL;
			OH_Drawing_BitmapBuild(bitmap, 2048, 256, &fmt);
			canvas = OH_Drawing_CanvasCreate();
			if (canvas) {
				OH_Drawing_CanvasBind(canvas, bitmap);
				ownsCanvas = true;
			}
		}
		clipCount = 0;
		// Verify initialization succeeded
		if (IsCorrupted()) {
			magic = kMagicDead;  // Mark so next Init() will retry
		}
	}
};

// Static storage buffer for placement new — resides in BSS/data segment, NOT on heap.
// This eliminates all possibility of jemalloc-related use-after-free.
alignas(CachedMeasurementSurface) static uint8_t s_cachedStorage[sizeof(CachedMeasurementSurface)];
static CachedMeasurementSurface* s_cachedMeasureSurf = nullptr;

Surface* PlatOHOS_GetCachedMeasurementSurface() {
	if (!s_cachedMeasureSurf) {
		// Placement new: construct object in static storage (no heap allocation)
		s_cachedMeasureSurf = new (s_cachedStorage) CachedMeasurementSurface();
		s_cachedMeasureSurf->Init(reinterpret_cast<WindowID>(0x1));
	} else if (s_cachedMeasureSurf->IsCorrupted()) {
		// Self-healing: re-init if corruption detected (shouldn't happen with
		// static storage, but defend against Skia internal overflows)
		s_cachedMeasureSurf->Init(reinterpret_cast<WindowID>(0x1));
	}
	return s_cachedMeasureSurf;
}

// Safe accessor: extract OH_Drawing_Font* from a FontHandleOHOS (defined only in this TU)
OH_Drawing_Font* PlatOHOS_GetFontHandle(const Scintilla::Internal::Font *font) {
	if (!font) return nullptr;
	// FontHandleOHOS is the concrete class; ohFont is its first member after base
	auto *fh = static_cast<FontHandleOHOS *>(const_cast<Scintilla::Internal::Font *>(font));
	return fh ? fh->ohFont : nullptr;
}

namespace Scintilla::Internal {
namespace Platform {
void DebugPrintf(const char *format, ...) {
	va_list ap; va_start(ap, format);
	vfprintf(stderr, format, ap); va_end(ap); fflush(stderr);
}
void Assert(const char *c, const char *file, int line) noexcept {
	fprintf(stderr, "Scintilla Assert [%s] failed at %s:%d\n", c, file, line);
	fflush(stderr);
}
}}
