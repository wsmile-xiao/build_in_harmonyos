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
private:
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
		PLAT_LOG("Init(WindowID) START wid=%p", (void*)wid);
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
			if (s_drawTextCount < 5) { PLAT_DBG("DrawTextNoClip[%d]: font INVALID fh=%p ohFont=%p", s_drawTextCount++, (void*)fh, fh ? (void*)fh->ohFont : nullptr); }
			return;
		}
		auto *blob = OH_Drawing_TextBlobCreateFromText(
			text.data(), text.size(), fh->ohFont, TEXT_ENCODING_UTF8);
		if (blob) {
			if (s_drawTextCount < 5) {
				PLAT_DBG("DrawTextNoClip[%d]: rc=(%.0f,%.0f,%.0f,%.0f) ybase=%.1f textLen=%zu rgba=0x%08x",
					s_drawTextCount++, (double)rc.left, (double)rc.top, (double)rc.right, (double)rc.bottom,
					(double)ybase, text.size(), ColourToARGB(fore));
			}
			ApplyBrush(fore);
			OH_Drawing_CanvasDrawTextBlob(canvas, blob,
				static_cast<float>(rc.left), static_cast<float>(ybase));
			DetachBrush();
			OH_Drawing_TextBlobDestroy(blob);
		} else {
			PLAT_DBG("DrawTextNoClip[%d]: TextBlob FAILED len=%zu font=%p", s_drawTextCount++, text.size(), (void*)fh->ohFont);
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
