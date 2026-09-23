/* Vendored libpaper-compatible shim for paperjam on OHOS.
 *
 * libpaper 1.1.28 in this repo is a legacy archive without a Conan recipe,
 * so paperjam cannot `requires("libpaper/...")`. paperjam (cmds.cc) uses
 * only three symbols: paperinfo(), paperpswidth(), paperpsheight().
 * This shim implements exactly that subset with a static table of common
 * paper sizes in PostScript points (1/72 inch), matching libpaper values
 * for the entries paperjam users actually address by name (a4, letter...).
 * Width/height are portrait; rotation is handled by paperjam itself.
 */
#ifndef PAPER_SHIM_H
#define PAPER_SHIM_H

#ifdef __cplusplus
extern "C" {
#endif

struct paper {
	const char *name;
	int pswidth;	/* width in PostScript points */
	int psheight;	/* height in PostScript points */
};
typedef struct paper paper;

const paper *paperinfo(const char *name);
int paperpswidth(const paper *p);
int paperpsheight(const paper *p);

#ifdef __cplusplus
}
#endif

#endif
