/* ANSI-C code produced by gperf version 3.1 */
/* Command-line: gperf -L ANSI-C -E -D -K key -H ohcount_hash_extension -N ohcount_hash_language_from_ext -t extensions.gperf  */
/* Computed positions: -k'1-3,$' */

#if !((' ' == 32) && ('!' == 33) && ('"' == 34) && ('#' == 35) \
      && ('%' == 37) && ('&' == 38) && ('\'' == 39) && ('(' == 40) \
      && (')' == 41) && ('*' == 42) && ('+' == 43) && (',' == 44) \
      && ('-' == 45) && ('.' == 46) && ('/' == 47) && ('0' == 48) \
      && ('1' == 49) && ('2' == 50) && ('3' == 51) && ('4' == 52) \
      && ('5' == 53) && ('6' == 54) && ('7' == 55) && ('8' == 56) \
      && ('9' == 57) && (':' == 58) && (';' == 59) && ('<' == 60) \
      && ('=' == 61) && ('>' == 62) && ('?' == 63) && ('A' == 65) \
      && ('B' == 66) && ('C' == 67) && ('D' == 68) && ('E' == 69) \
      && ('F' == 70) && ('G' == 71) && ('H' == 72) && ('I' == 73) \
      && ('J' == 74) && ('K' == 75) && ('L' == 76) && ('M' == 77) \
      && ('N' == 78) && ('O' == 79) && ('P' == 80) && ('Q' == 81) \
      && ('R' == 82) && ('S' == 83) && ('T' == 84) && ('U' == 85) \
      && ('V' == 86) && ('W' == 87) && ('X' == 88) && ('Y' == 89) \
      && ('Z' == 90) && ('[' == 91) && ('\\' == 92) && (']' == 93) \
      && ('^' == 94) && ('_' == 95) && ('a' == 97) && ('b' == 98) \
      && ('c' == 99) && ('d' == 100) && ('e' == 101) && ('f' == 102) \
      && ('g' == 103) && ('h' == 104) && ('i' == 105) && ('j' == 106) \
      && ('k' == 107) && ('l' == 108) && ('m' == 109) && ('n' == 110) \
      && ('o' == 111) && ('p' == 112) && ('q' == 113) && ('r' == 114) \
      && ('s' == 115) && ('t' == 116) && ('u' == 117) && ('v' == 118) \
      && ('w' == 119) && ('x' == 120) && ('y' == 121) && ('z' == 122) \
      && ('{' == 123) && ('|' == 124) && ('}' == 125) && ('~' == 126))
/* The character set is not based on ISO-646.  */
#error "gperf generated tables don't work with this execution character set. Please report a bug to <bug-gperf@gnu.org>."
#endif

#line 1 "extensions.gperf"

#include "../languages.h"

#define BINARY "\1"
#define DISAMBIGUATE(x) ("\2" x)
#line 7 "extensions.gperf"
struct ExtensionMap { const char *key; const char *value; };
/* maximum key range = 835, duplicates = 0 */

#ifdef __GNUC__
__inline
#else
#ifdef __cplusplus
inline
#endif
#endif
static unsigned int
ohcount_hash_extension (register const char *str, register size_t len)
{
  static unsigned short asso_values[] =
    {
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836,  80,  70, 836, 836, 836,   0,  20,
        5,  45,   0,  60,   0,  50,  30,  20,  39, 836,
      836, 836, 836, 836, 836, 836, 836,  20, 836, 836,
      836, 836,  15, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 125,  35,  50,
       65, 110,  10, 194, 235, 100, 190,  55,   0,  95,
      210, 209,  85, 244,  25,   5,   0, 120, 135,   9,
       20, 230, 160,   5, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836, 836, 836, 836,
      836, 836, 836, 836, 836, 836, 836
    };
  register unsigned int hval = len;

  switch (hval)
    {
      default:
        hval += asso_values[(unsigned char)str[2]];
      /*FALLTHROUGH*/
      case 2:
        hval += asso_values[(unsigned char)str[1]+1];
      /*FALLTHROUGH*/
      case 1:
        hval += asso_values[(unsigned char)str[0]];
        break;
    }
  return hval + asso_values[(unsigned char)str[len - 1]];
}

struct ExtensionMap *
ohcount_hash_language_from_ext (register const char *str, register size_t len)
{
  enum
    {
      TOTAL_KEYWORDS = 235,
      MIN_WORD_LENGTH = 1,
      MAX_WORD_LENGTH = 10,
      MIN_HASH_VALUE = 1,
      MAX_HASH_VALUE = 835
    };

  static struct ExtensionMap wordlist[] =
    {
#line 211 "extensions.gperf"
      {"t", LANG_PERL},
#line 220 "extensions.gperf"
      {"ts", LANG_TYPESCRIPT},
#line 193 "extensions.gperf"
      {"s", LANG_ASSEMBLER},
#line 203 "extensions.gperf"
      {"ss", LANG_SCHEME},
#line 84 "extensions.gperf"
      {"fs", DISAMBIGUATE("fs")},
#line 78 "extensions.gperf"
      {"frt", LANG_FORTH},
#line 69 "extensions.gperf"
      {"f", DISAMBIGUATE("fortran")},
#line 241 "extensions.gperf"
      {"xsl", LANG_XSLT},
#line 239 "extensions.gperf"
      {"xs", LANG_C},
#line 187 "extensions.gperf"
      {"rkt", LANG_RACKET},
#line 189 "extensions.gperf"
      {"rktl", LANG_RACKET},
#line 11 "extensions.gperf"
      {"H", LANG_CPP},
#line 190 "extensions.gperf"
      {"rs", DISAMBIGUATE("rs")},
#line 202 "extensions.gperf"
      {"sql", LANG_SQL},
#line 10 "extensions.gperf"
      {"C", LANG_CPP},
#line 76 "extensions.gperf"
      {"fr", LANG_FORTH},
#line 221 "extensions.gperf"
      {"tsx", LANG_TYPESCRIPT},
#line 210 "extensions.gperf"
      {"swf", BINARY},
#line 177 "extensions.gperf"
      {"r", DISAMBIGUATE("r")},
#line 73 "extensions.gperf"
      {"f90", DISAMBIGUATE("fortran")},
#line 214 "extensions.gperf"
      {"tex", LANG_TEX},
#line 47 "extensions.gperf"
      {"cs", DISAMBIGUATE("cs")},
#line 83 "extensions.gperf"
      {"frx", LANG_VISUALBASIC},
#line 121 "extensions.gperf"
      {"latex", LANG_TEX},
#line 49 "extensions.gperf"
      {"css", LANG_CSS},
#line 213 "extensions.gperf"
      {"tcl", LANG_TCL},
#line 26 "extensions.gperf"
      {"b", DISAMBIGUATE("b")},
#line 178 "extensions.gperf"
      {"r3", LANG_REBOL},
#line 28 "extensions.gperf"
      {"bat", LANG_BAT},
#line 183 "extensions.gperf"
      {"rebol", LANG_REBOL},
#line 184 "extensions.gperf"
      {"rex", LANG_REXX},
#line 185 "extensions.gperf"
      {"rexx", LANG_REXX},
#line 46 "extensions.gperf"
      {"cr", LANG_CRYSTAL},
#line 27 "extensions.gperf"
      {"bas", DISAMBIGUATE("basic")},
#line 212 "extensions.gperf"
      {"tar", BINARY},
#line 173 "extensions.gperf"
      {"ps", LANG_POSTSCRIPT},
#line 71 "extensions.gperf"
      {"f08", DISAMBIGUATE("fortran")},
#line 188 "extensions.gperf"
      {"rktd", LANG_RACKET},
#line 181 "extensions.gperf"
      {"rbw", LANG_RUBY},
#line 55 "extensions.gperf"
      {"def", DISAMBIGUATE("def")},
#line 35 "extensions.gperf"
      {"c", LANG_C},
#line 54 "extensions.gperf"
      {"dat", DISAMBIGUATE("dat")},
#line 233 "extensions.gperf"
      {"wl", LANG_MATHEMATICA},
#line 234 "extensions.gperf"
      {"wlt", LANG_MATHEMATICA},
#line 182 "extensions.gperf"
      {"reb", LANG_REBOL},
#line 180 "extensions.gperf"
      {"rb", LANG_RUBY},
#line 200 "extensions.gperf"
      {"sls", LANG_SCHEME},
#line 120 "extensions.gperf"
      {"lc", LANG_LIVECODE},
#line 66 "extensions.gperf"
      {"erl", LANG_ERLANG},
#line 194 "extensions.gperf"
      {"sc", LANG_SCHEME},
#line 70 "extensions.gperf"
      {"f03", DISAMBIGUATE("fortran")},
#line 155 "extensions.gperf"
      {"perl", LANG_PERL},
#line 75 "extensions.gperf"
      {"factor", LANG_FACTOR},
#line 204 "extensions.gperf"
      {"st", DISAMBIGUATE("st")},
#line 236 "extensions.gperf"
      {"xls", BINARY},
#line 186 "extensions.gperf"
      {"rhtml", LANG_RHTML},
#line 53 "extensions.gperf"
      {"d", LANG_DMD},
#line 16 "extensions.gperf"
      {"as", LANG_ACTIONSCRIPT},
#line 154 "extensions.gperf"
      {"pas", LANG_PASCAL},
#line 237 "extensions.gperf"
      {"xlw", BINARY},
#line 153 "extensions.gperf"
      {"p6", LANG_PERL},
#line 128 "extensions.gperf"
      {"m3", LANG_MODULA3},
#line 72 "extensions.gperf"
      {"f77", DISAMBIGUATE("fortran")},
#line 107 "extensions.gperf"
      {"i3", LANG_MODULA3},
#line 79 "extensions.gperf"
      {"for", DISAMBIGUATE("fortran")},
#line 132 "extensions.gperf"
      {"mk", LANG_MAKE},
#line 240 "extensions.gperf"
      {"xsd", LANG_XMLSCHEMA},
#line 235 "extensions.gperf"
      {"xaml", LANG_XAML},
#line 129 "extensions.gperf"
      {"m4", LANG_AUTOCONF},
#line 41 "extensions.gperf"
      {"cls", LANG_TEX},
#line 124 "extensions.gperf"
      {"ltx", LANG_TEX},
#line 38 "extensions.gperf"
      {"cc", LANG_CPP},
#line 21 "extensions.gperf"
      {"asx", DISAMBIGUATE("asx")},
#line 74 "extensions.gperf"
      {"f95", DISAMBIGUATE("fortran")},
#line 123 "extensions.gperf"
      {"lsp", LANG_LISP},
#line 228 "extensions.gperf"
      {"vert", LANG_GLSL},
#line 119 "extensions.gperf"
      {"kt", LANG_KOTLIN},
#line 205 "extensions.gperf"
      {"str", LANG_STRATEGO},
#line 163 "extensions.gperf"
      {"pl", DISAMBIGUATE("pl")},
#line 242 "extensions.gperf"
      {"z80", LANG_ASSEMBLER},
#line 63 "extensions.gperf"
      {"eclass", LANG_EBUILD},
#line 179 "extensions.gperf"
      {"ra", BINARY},
#line 17 "extensions.gperf"
      {"as8", LANG_ASSEMBLER},
#line 127 "extensions.gperf"
      {"m", DISAMBIGUATE("m")},
#line 133 "extensions.gperf"
      {"ml", LANG_OCAML},
#line 134 "extensions.gperf"
      {"ml4", LANG_OCAML},
#line 116 "extensions.gperf"
      {"js", LANG_JAVASCRIPT},
#line 227 "extensions.gperf"
      {"vbs", LANG_VISUALBASIC},
#line 18 "extensions.gperf"
      {"ascx", DISAMBIGUATE("aspx")},
#line 94 "extensions.gperf"
      {"gs", LANG_GENIE},
#line 65 "extensions.gperf"
      {"el", LANG_EMACSLISP},
#line 82 "extensions.gperf"
      {"frm", LANG_VISUALBASIC},
#line 216 "extensions.gperf"
      {"tif", BINARY},
#line 217 "extensions.gperf"
      {"tiff", BINARY},
#line 143 "extensions.gperf"
      {"mt", LANG_MATHEMATICA},
#line 156 "extensions.gperf"
      {"pdf", BINARY},
#line 60 "extensions.gperf"
      {"e", LANG_EIFFEL},
#line 225 "extensions.gperf"
      {"vb", LANG_VISUALBASIC},
#line 62 "extensions.gperf"
      {"ec", LANG_EC},
#line 58 "extensions.gperf"
      {"dtx", LANG_TEX_DTX},
#line 238 "extensions.gperf"
      {"xml", LANG_XML},
#line 20 "extensions.gperf"
      {"aspx", DISAMBIGUATE("aspx")},
#line 219 "extensions.gperf"
      {"uc", LANG_UNREALSCRIPT},
#line 125 "extensions.gperf"
      {"lgt", LANG_LOGTALK},
#line 29 "extensions.gperf"
      {"bf", LANG_BRAINFUCK},
#line 102 "extensions.gperf"
      {"hs", LANG_HASKELL},
#line 101 "extensions.gperf"
      {"hrl", LANG_ERLANG},
#line 218 "extensions.gperf"
      {"tpl", LANG_HTML},
#line 14 "extensions.gperf"
      {"ads", LANG_ADA},
#line 37 "extensions.gperf"
      {"cache", BINARY},
#line 57 "extensions.gperf"
      {"doc", BINARY},
#line 25 "extensions.gperf"
      {"awk", LANG_AWK},
#line 43 "extensions.gperf"
      {"coffee", LANG_COFFEESCRIPT},
#line 201 "extensions.gperf"
      {"sps", LANG_SCHEME},
#line 198 "extensions.gperf"
      {"scm", LANG_SCHEME},
#line 224 "extensions.gperf"
      {"v", LANG_COQ},
#line 150 "extensions.gperf"
      {"ob2", LANG_OBERON},
#line 197 "extensions.gperf"
      {"sci", LANG_SCILAB},
#line 160 "extensions.gperf"
      {"php4", LANG_PHP},
#line 112 "extensions.gperf"
      {"jar", BINARY},
#line 191 "extensions.gperf"
      {"ru", LANG_RUBY},
#line 36 "extensions.gperf"
      {"c++", LANG_CPP},
#line 122 "extensions.gperf"
      {"lisp", LANG_LISP},
#line 33 "extensions.gperf"
      {"bmx", LANG_BLITZMAX},
#line 196 "extensions.gperf"
      {"sce", LANG_SCILAB},
#line 168 "extensions.gperf"
      {"pnt", BINARY},
#line 89 "extensions.gperf"
      {"glsl", LANG_GLSL},
#line 222 "extensions.gperf"
      {"vala", LANG_VALA},
#line 131 "extensions.gperf"
      {"mf", LANG_METAFONT},
#line 93 "extensions.gperf"
      {"grc", LANG_GRACE},
#line 169 "extensions.gperf"
      {"pod", LANG_PERL},
#line 230 "extensions.gperf"
      {"vhdl", LANG_VHDL},
#line 118 "extensions.gperf"
      {"kdebuild-1", LANG_EBUILD},
#line 51 "extensions.gperf"
      {"cu", LANG_CUDA},
#line 13 "extensions.gperf"
      {"adb", LANG_ADA},
#line 138 "extensions.gperf"
      {"mod", DISAMBIGUATE("mod")},
#line 232 "extensions.gperf"
      {"wav", BINARY},
#line 19 "extensions.gperf"
      {"asm", LANG_ASSEMBLER},
#line 159 "extensions.gperf"
      {"php3", LANG_PHP},
#line 52 "extensions.gperf"
      {"cxx", LANG_CPP},
#line 195 "extensions.gperf"
      {"scala", LANG_SCALA},
#line 31 "extensions.gperf"
      {"bi", DISAMBIGUATE("basic")},
#line 44 "extensions.gperf"
      {"com", LANG_DCL},
#line 48 "extensions.gperf"
      {"csproj", LANG_XML},
#line 171 "extensions.gperf"
      {"ppt", BINARY},
#line 161 "extensions.gperf"
      {"php5", LANG_PHP},
#line 24 "extensions.gperf"
      {"avi", BINARY},
#line 77 "extensions.gperf"
      {"frag", LANG_GLSL},
#line 15 "extensions.gperf"
      {"aiff", BINARY},
#line 199 "extensions.gperf"
      {"sh", LANG_SHELL},
#line 50 "extensions.gperf"
      {"ctp", LANG_PHP},
#line 61 "extensions.gperf"
      {"ebuild", LANG_EBUILD},
#line 144 "extensions.gperf"
      {"mustache", LANG_HTML},
#line 87 "extensions.gperf"
      {"gemspec", LANG_RUBY},
#line 56 "extensions.gperf"
      {"di", LANG_DMD},
#line 158 "extensions.gperf"
      {"php", LANG_PHP},
#line 223 "extensions.gperf"
      {"vapi", LANG_VALA},
#line 80 "extensions.gperf"
      {"forth", LANG_FORTH},
#line 95 "extensions.gperf"
      {"gz", BINARY},
#line 117 "extensions.gperf"
      {"jsp", LANG_JSP},
#line 176 "extensions.gperf"
      {"qt", BINARY},
#line 229 "extensions.gperf"
      {"vhd", LANG_VHDL},
#line 98 "extensions.gperf"
      {"haml", LANG_HAML},
#line 208 "extensions.gperf"
      {"svgz", BINARY},
#line 39 "extensions.gperf"
      {"chai", LANG_CHAISCRIPT},
#line 68 "extensions.gperf"
      {"exlib", LANG_EXHERES},
#line 111 "extensions.gperf"
      {"j", LANG_OBJECTIVE_J},
#line 22 "extensions.gperf"
      {"au", BINARY},
#line 108 "extensions.gperf"
      {"icns", BINARY},
#line 126 "extensions.gperf"
      {"lua", LANG_LUA},
#line 137 "extensions.gperf"
      {"mo", LANG_MODELICA},
#line 164 "extensions.gperf"
      {"pm", LANG_PERL},
#line 135 "extensions.gperf"
      {"mli", LANG_OCAML},
#line 165 "extensions.gperf"
      {"pmc", LANG_C},
#line 136 "extensions.gperf"
      {"mm", LANG_OBJECTIVE_C},
#line 30 "extensions.gperf"
      {"bfpp", LANG_BFPP},
#line 207 "extensions.gperf"
      {"svg", BINARY},
#line 88 "extensions.gperf"
      {"gif", BINARY},
#line 130 "extensions.gperf"
      {"m4a", BINARY},
#line 110 "extensions.gperf"
      {"inc", DISAMBIGUATE("inc")},
#line 148 "extensions.gperf"
      {"nsi", LANG_NSIS},
#line 170 "extensions.gperf"
      {"pp", DISAMBIGUATE("pp")},
#line 32 "extensions.gperf"
      {"bmp", BINARY},
#line 157 "extensions.gperf"
      {"ph", LANG_PERL},
#line 145 "extensions.gperf"
      {"mxml", LANG_MXML},
#line 140 "extensions.gperf"
      {"mp", LANG_METAPOST_WITH_TEX},
#line 81 "extensions.gperf"
      {"fpp", DISAMBIGUATE("fortran")},
#line 141 "extensions.gperf"
      {"mp3", BINARY},
#line 147 "extensions.gperf"
      {"nse", LANG_LUA},
#line 209 "extensions.gperf"
      {"svn", BINARY},
#line 226 "extensions.gperf"
      {"vba", LANG_VISUALBASIC},
#line 92 "extensions.gperf"
      {"grace", LANG_GRACE},
#line 59 "extensions.gperf"
      {"dylan", LANG_DYLAN},
#line 146 "extensions.gperf"
      {"nix", LANG_NIX},
#line 162 "extensions.gperf"
      {"pike", LANG_PIKE},
#line 64 "extensions.gperf"
      {"eh", LANG_EC},
#line 139 "extensions.gperf"
      {"mov", BINARY},
#line 104 "extensions.gperf"
      {"html", LANG_HTML},
#line 175 "extensions.gperf"
      {"qml", LANG_QML},
#line 45 "extensions.gperf"
      {"cpp", LANG_CPP},
#line 97 "extensions.gperf"
      {"h++", LANG_CPP},
#line 96 "extensions.gperf"
      {"h", DISAMBIGUATE("h")},
#line 174 "extensions.gperf"
      {"py", LANG_PYTHON},
#line 105 "extensions.gperf"
      {"hx", LANG_HAXE},
#line 12 "extensions.gperf"
      {"ada", LANG_ADA},
#line 113 "extensions.gperf"
      {"java", LANG_JAVA},
#line 90 "extensions.gperf"
      {"go", LANG_GOLANG},
#line 42 "extensions.gperf"
      {"cmake", LANG_CMAKE},
#line 106 "extensions.gperf"
      {"hxx", LANG_CPP},
#line 172 "extensions.gperf"
      {"pro", DISAMBIGUATE("pro")},
#line 231 "extensions.gperf"
      {"vim", LANG_VIM},
#line 109 "extensions.gperf"
      {"in", DISAMBIGUATE("in")},
#line 243 "extensions.gperf"
      {"zip", BINARY},
#line 40 "extensions.gperf"
      {"clj", LANG_CLOJURE},
#line 34 "extensions.gperf"
      {"boo", LANG_BOO},
#line 103 "extensions.gperf"
      {"htm", LANG_HTML},
#line 86 "extensions.gperf"
      {"ftn", DISAMBIGUATE("fortran")},
#line 215 "extensions.gperf"
      {"tgz", BINARY},
#line 99 "extensions.gperf"
      {"hh", LANG_CPP},
#line 166 "extensions.gperf"
      {"pmod", LANG_PIKE},
#line 192 "extensions.gperf"
      {"run", LANG_AMPL},
#line 67 "extensions.gperf"
      {"exheres-0", LANG_EXHERES},
#line 206 "extensions.gperf"
      {"sty", LANG_TEX},
#line 9 "extensions.gperf"
      {"4th", LANG_FORTH},
#line 85 "extensions.gperf"
      {"fth", LANG_FORTH},
#line 91 "extensions.gperf"
      {"groovy", LANG_GROOVY},
#line 23 "extensions.gperf"
      {"aug", LANG_AUGEAS},
#line 100 "extensions.gperf"
      {"hpp", LANG_CPP},
#line 151 "extensions.gperf"
      {"obn", LANG_OBERON},
#line 149 "extensions.gperf"
      {"nsh", LANG_NSIS},
#line 167 "extensions.gperf"
      {"png", BINARY},
#line 142 "extensions.gperf"
      {"mpg", BINARY},
#line 114 "extensions.gperf"
      {"jpeg", BINARY},
#line 115 "extensions.gperf"
      {"jpg", BINARY},
#line 152 "extensions.gperf"
      {"ogg", BINARY}
    };

  static short lookup[] =
    {
       -1,   0,  -1,  -1,  -1,  -1,  -1,   1,  -1,  -1,
       -1,   2,   3,  -1,  -1,  -1,  -1,   4,   5,  -1,
       -1,   6,  -1,   7,  -1,  -1,  -1,   8,   9,  10,
       -1,  11,  12,  13,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  14,  15,  16,  -1,  -1,  -1,  -1,  17,  -1,
       -1,  18,  19,  20,  -1,  -1,  -1,  21,  22,  -1,
       23,  -1,  -1,  24,  -1,  -1,  -1,  -1,  25,  -1,
       -1,  26,  27,  28,  -1,  29,  -1,  -1,  30,  31,
       -1,  -1,  32,  33,  -1,  -1,  -1,  -1,  34,  -1,
       -1,  -1,  35,  36,  37,  -1,  38,  -1,  39,  -1,
       -1,  40,  -1,  41,  -1,  -1,  42,  43,  44,  -1,
       -1,  -1,  45,  46,  -1,  -1,  -1,  47,  48,  -1,
       -1,  -1,  49,  50,  51,  -1,  52,  53,  54,  -1,
       55,  56,  57,  58,  -1,  -1,  59,  60,  -1,  -1,
       -1,  -1,  61,  62,  -1,  -1,  -1,  63,  64,  -1,
       -1,  -1,  65,  66,  67,  -1,  -1,  68,  69,  -1,
       -1,  -1,  -1,  70,  -1,  -1,  -1,  71,  72,  -1,
       -1,  -1,  73,  74,  75,  -1,  -1,  76,  77,  -1,
       -1,  -1,  78,  79,  -1,  -1,  80,  81,  82,  -1,
       -1,  83,  84,  85,  -1,  -1,  -1,  86,  87,  88,
       -1,  89,  -1,  -1,  -1,  -1,  -1,  90,  91,  -1,
       -1,  -1,  -1,  92,  93,  -1,  -1,  94,  95,  -1,
       -1,  96,  97,  -1,  -1,  -1,  -1,  98,  99,  -1,
       -1,  -1,  -1, 100, 101,  -1,  -1, 102, 103,  -1,
       -1, 104, 105, 106,  -1,  -1,  -1, 107, 108,  -1,
      109,  -1,  -1, 110,  -1,  -1,  -1,  -1, 111,  -1,
       -1, 112, 113, 114,  -1,  -1,  -1,  -1,  -1,  -1,
       -1, 115, 116, 117, 118,  -1,  -1,  -1, 119,  -1,
       -1,  -1, 120, 121, 122,  -1,  -1,  -1, 123,  -1,
       -1,  -1,  -1, 124,  -1,  -1,  -1, 125, 126, 127,
       -1, 128, 129, 130, 131, 132,  -1, 133, 134,  -1,
       -1,  -1,  -1, 135,  -1,  -1,  -1, 136, 137, 138,
       -1,  -1,  -1, 139,  -1, 140,  -1, 141, 142,  -1,
       -1, 143, 144,  -1, 145,  -1,  -1, 146, 147, 148,
       -1,  -1, 149, 150,  -1,  -1,  -1,  -1,  -1,  -1,
       -1, 151,  -1, 152,  -1,  -1, 153, 154, 155, 156,
      157, 158,  -1, 159,  -1,  -1, 160,  -1, 161, 162,
       -1,  -1, 163,  -1,  -1,  -1,  -1,  -1,  -1, 164,
      165, 166, 167,  -1, 168,  -1,  -1,  -1, 169,  -1,
       -1, 170, 171, 172,  -1,  -1,  -1,  -1, 173,  -1,
       -1,  -1, 174, 175,  -1, 176,  -1, 177, 178,  -1,
       -1,  -1, 179, 180,  -1,  -1, 181,  -1, 182,  -1,
       -1,  -1, 183,  -1, 184,  -1, 185, 186,  -1,  -1,
       -1,  -1, 187, 188,  -1,  -1,  -1, 189, 190, 191,
      192,  -1,  -1, 193, 194,  -1,  -1, 195,  -1,  -1,
       -1,  -1,  -1, 196, 197,  -1,  -1, 198,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1, 199, 200,  -1,
       -1, 201,  -1,  -1,  -1,  -1,  -1, 202,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1, 203, 204, 205,
      206,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
      207,  -1,  -1,  -1,  -1,  -1,  -1,  -1, 208,  -1,
       -1, 209,  -1,  -1,  -1,  -1,  -1,  -1, 210,  -1,
       -1, 211,  -1, 212,  -1,  -1,  -1,  -1, 213,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1, 214,  -1,  -1,  -1,  -1,  -1,  -1, 215,  -1,
       -1,  -1,  -1, 216,  -1,  -1,  -1,  -1, 217,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1, 218, 219,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1, 220, 221,  -1,  -1,  -1, 222,  -1,
       -1,  -1,  -1, 223,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1, 224,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1, 225,  -1,  -1,  -1,  -1,  -1,
       -1, 226, 227,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1, 228, 229,  -1, 230,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
      231,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1, 232,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1, 233,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1, 234
    };

  if (len <= MAX_WORD_LENGTH && len >= MIN_WORD_LENGTH)
    {
      register unsigned int key = ohcount_hash_extension (str, len);

      if (key <= MAX_HASH_VALUE)
        {
          register int index = lookup[key];

          if (index >= 0)
            {
              register const char *s = wordlist[index].key;

              if (*str == *s && !strcmp (str + 1, s + 1))
                return &wordlist[index];
            }
        }
    }
  return 0;
}
