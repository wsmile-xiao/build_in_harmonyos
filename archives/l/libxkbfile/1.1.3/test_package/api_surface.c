#include <stddef.h>
#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/XKBstr.h>
/* XKBfile.h includes nothing itself and hides the Xkm* TOC API
 * (XkmReadTOC/XkmFindTOCEntry/XkmReadFileSection/XkmReadFileSectionName)
 * behind #ifdef _XKMFORMAT_H_, which is evaluated as the header is parsed.
 * XKMformat.h (which defines _XKMFORMAT_H_) must therefore be included
 * BEFORE XKBfile.h for those declarations to be visible. */
#include <X11/extensions/XKMformat.h>
#include <X11/extensions/XKBfile.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libxkbfile.so.1 exported API (XKBfile.h), 54 linkable symbols.
 * XkbGetOrderedDrawables/XkbFreeOrderedDrawables are excluded: XKBfile.h
 * guards them behind _XKBGEOM_H_, but no shipped header defines that guard,
 * so they are not reachable through the public headers. */
DECLARE_SYMBOL(XkbAccessXDetailText);
DECLARE_SYMBOL(XkbActionText);
DECLARE_SYMBOL(XkbActionTypeText);
DECLARE_SYMBOL(XkbAtomGetString);
DECLARE_SYMBOL(XkbAtomText);
DECLARE_SYMBOL(XkbBehaviorText);
DECLARE_SYMBOL(XkbChangeAtomDisplay);
DECLARE_SYMBOL(XkbChangeKbdDisplay);
DECLARE_SYMBOL(XkbConfigText);
DECLARE_SYMBOL(XkbControlsMaskText);
DECLARE_SYMBOL(XkbConvertGetByNameComponents);
DECLARE_SYMBOL(XkbConvertXkbComponents);
DECLARE_SYMBOL(XkbDetermineFileType);
DECLARE_SYMBOL(XkbDoodadTypeText);
DECLARE_SYMBOL(XkbEnsureSafeMapName);
DECLARE_SYMBOL(XkbFindKeycodeByName);
DECLARE_SYMBOL(XkbGeomFPText);
DECLARE_SYMBOL(XkbIMWhichStateMaskText);
DECLARE_SYMBOL(XkbIndentText);
DECLARE_SYMBOL(XkbInitAtoms);
DECLARE_SYMBOL(XkbInternAtom);
DECLARE_SYMBOL(XkbKeyNameText);
DECLARE_SYMBOL(XkbKeysymText);
DECLARE_SYMBOL(XkbLookupCanonicalRGBColor);
DECLARE_SYMBOL(XkbLookupGroupAndLevel);
DECLARE_SYMBOL(XkbMergeFile);
DECLARE_SYMBOL(XkbModIndexText);
DECLARE_SYMBOL(XkbModMaskText);
DECLARE_SYMBOL(XkbNKNDetailMaskText);
DECLARE_SYMBOL(XkbNameMatchesPattern);
DECLARE_SYMBOL(XkbReadFromServer);
DECLARE_SYMBOL(XkbSIMatchText);
DECLARE_SYMBOL(XkbStringText);
DECLARE_SYMBOL(XkbVModIndexText);
DECLARE_SYMBOL(XkbVModMaskText);
DECLARE_SYMBOL(XkbWriteCFile);
DECLARE_SYMBOL(XkbWriteToServer);
DECLARE_SYMBOL(XkbWriteXKBCompatMap);
DECLARE_SYMBOL(XkbWriteXKBFile);
DECLARE_SYMBOL(XkbWriteXKBGeometry);
DECLARE_SYMBOL(XkbWriteXKBKeyTypes);
DECLARE_SYMBOL(XkbWriteXKBKeycodes);
DECLARE_SYMBOL(XkbWriteXKBKeymap);
DECLARE_SYMBOL(XkbWriteXKBKeymapForNames);
DECLARE_SYMBOL(XkbWriteXKBLayout);
DECLARE_SYMBOL(XkbWriteXKBSemantics);
DECLARE_SYMBOL(XkbWriteXKBSymbols);
DECLARE_SYMBOL(XkbWriteXKMFile);
DECLARE_SYMBOL(XkmFindTOCEntry);
DECLARE_SYMBOL(XkmProbe);
DECLARE_SYMBOL(XkmReadFile);
DECLARE_SYMBOL(XkmReadFileSection);
DECLARE_SYMBOL(XkmReadFileSectionName);
DECLARE_SYMBOL(XkmReadTOC);

int main(void) {
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libxkbfile.so.1 fails at link or load
     * time, not silently at runtime. */
    Display *volatile dpy = (Display *)0;
    (void)dpy;
    (void)probe_XkbAccessXDetailText;
    (void)probe_XkbActionText;
    (void)probe_XkbActionTypeText;
    (void)probe_XkbAtomGetString;
    (void)probe_XkbAtomText;
    (void)probe_XkbBehaviorText;
    (void)probe_XkbChangeAtomDisplay;
    (void)probe_XkbChangeKbdDisplay;
    (void)probe_XkbConfigText;
    (void)probe_XkbControlsMaskText;
    (void)probe_XkbConvertGetByNameComponents;
    (void)probe_XkbConvertXkbComponents;
    (void)probe_XkbDetermineFileType;
    (void)probe_XkbDoodadTypeText;
    (void)probe_XkbEnsureSafeMapName;
    (void)probe_XkbFindKeycodeByName;
    (void)probe_XkbGeomFPText;
    (void)probe_XkbIMWhichStateMaskText;
    (void)probe_XkbIndentText;
    (void)probe_XkbInitAtoms;
    (void)probe_XkbInternAtom;
    (void)probe_XkbKeyNameText;
    (void)probe_XkbKeysymText;
    (void)probe_XkbLookupCanonicalRGBColor;
    (void)probe_XkbLookupGroupAndLevel;
    (void)probe_XkbMergeFile;
    (void)probe_XkbModIndexText;
    (void)probe_XkbModMaskText;
    (void)probe_XkbNKNDetailMaskText;
    (void)probe_XkbNameMatchesPattern;
    (void)probe_XkbReadFromServer;
    (void)probe_XkbSIMatchText;
    (void)probe_XkbStringText;
    (void)probe_XkbVModIndexText;
    (void)probe_XkbVModMaskText;
    (void)probe_XkbWriteCFile;
    (void)probe_XkbWriteToServer;
    (void)probe_XkbWriteXKBCompatMap;
    (void)probe_XkbWriteXKBFile;
    (void)probe_XkbWriteXKBGeometry;
    (void)probe_XkbWriteXKBKeyTypes;
    (void)probe_XkbWriteXKBKeycodes;
    (void)probe_XkbWriteXKBKeymap;
    (void)probe_XkbWriteXKBKeymapForNames;
    (void)probe_XkbWriteXKBLayout;
    (void)probe_XkbWriteXKBSemantics;
    (void)probe_XkbWriteXKBSymbols;
    (void)probe_XkbWriteXKMFile;
    (void)probe_XkmFindTOCEntry;
    (void)probe_XkmProbe;
    (void)probe_XkmReadFile;
    (void)probe_XkmReadFileSection;
    (void)probe_XkmReadFileSectionName;
    (void)probe_XkmReadTOC;
    return 0;
}
