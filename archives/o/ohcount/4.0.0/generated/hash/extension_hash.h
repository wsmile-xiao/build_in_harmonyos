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
/* maximum key range = 724, duplicates = 0 */

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
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725,  35,  30, 725, 725, 725,   0, 120,
        0,  60,   0,   5,   0,   0,  80,  40,  20, 725,
      725, 725, 725, 725, 725, 725, 725,  30, 725, 725,
      725, 725,  25, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 155,  15,  10,
       70,  55,  45, 163, 220, 115, 145,  20,  60, 150,
      209,  44, 125, 245,  20,   5,   0, 200,  40, 139,
       35, 210, 235,   0, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725, 725, 725, 725,
      725, 725, 725, 725, 725, 725, 725
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
      TOTAL_KEYWORDS = 240,
      MIN_WORD_LENGTH = 1,
      MAX_WORD_LENGTH = 10,
      MIN_HASH_VALUE = 1,
      MAX_HASH_VALUE = 724
    };

  static struct ExtensionMap wordlist[] =
    {
#line 212 "extensions.gperf"
      {"t", LANG_PERL},
#line 223 "extensions.gperf"
      {"ts", LANG_TYPESCRIPT},
#line 194 "extensions.gperf"
      {"s", LANG_ASSEMBLER},
#line 204 "extensions.gperf"
      {"ss", LANG_SCHEME},
#line 47 "extensions.gperf"
      {"cs", DISAMBIGUATE("cs")},
#line 35 "extensions.gperf"
      {"c", LANG_C},
#line 49 "extensions.gperf"
      {"css", LANG_CSS},
#line 191 "extensions.gperf"
      {"rs", DISAMBIGUATE("rs")},
#line 26 "extensions.gperf"
      {"b", DISAMBIGUATE("b")},
#line 28 "extensions.gperf"
      {"bat", LANG_BAT},
#line 46 "extensions.gperf"
      {"cr", LANG_CRYSTAL},
#line 213 "extensions.gperf"
      {"tac", LANG_PYTHON},
#line 178 "extensions.gperf"
      {"r", DISAMBIGUATE("r")},
#line 243 "extensions.gperf"
      {"xs", LANG_C},
#line 27 "extensions.gperf"
      {"bas", DISAMBIGUATE("basic")},
#line 181 "extensions.gperf"
      {"rb", LANG_RUBY},
#line 11 "extensions.gperf"
      {"H", LANG_CPP},
#line 84 "extensions.gperf"
      {"fs", DISAMBIGUATE("fs")},
#line 78 "extensions.gperf"
      {"frt", LANG_FORTH},
#line 150 "extensions.gperf"
      {"ob2", LANG_OBERON},
#line 215 "extensions.gperf"
      {"tar", BINARY},
#line 10 "extensions.gperf"
      {"C", LANG_CPP},
#line 230 "extensions.gperf"
      {"vbs", LANG_VISUALBASIC},
#line 228 "extensions.gperf"
      {"vb", LANG_VISUALBASIC},
#line 73 "extensions.gperf"
      {"f90", DISAMBIGUATE("fortran")},
#line 76 "extensions.gperf"
      {"fr", LANG_FORTH},
#line 224 "extensions.gperf"
      {"tsx", LANG_TYPESCRIPT},
#line 74 "extensions.gperf"
      {"f95", DISAMBIGUATE("fortran")},
#line 227 "extensions.gperf"
      {"v", LANG_COQ},
#line 179 "extensions.gperf"
      {"r3", LANG_REBOL},
#line 188 "extensions.gperf"
      {"rkt", LANG_RACKET},
#line 195 "extensions.gperf"
      {"sc", LANG_SCHEME},
#line 54 "extensions.gperf"
      {"dat", DISAMBIGUATE("dat")},
#line 69 "extensions.gperf"
      {"f", DISAMBIGUATE("fortran")},
#line 38 "extensions.gperf"
      {"cc", LANG_CPP},
#line 37 "extensions.gperf"
      {"cache", BINARY},
#line 75 "extensions.gperf"
      {"factor", LANG_FACTOR},
#line 183 "extensions.gperf"
      {"reb", LANG_REBOL},
#line 231 "extensions.gperf"
      {"vert", LANG_GLSL},
#line 60 "extensions.gperf"
      {"e", LANG_EIFFEL},
#line 36 "extensions.gperf"
      {"c++", LANG_CPP},
#line 121 "extensions.gperf"
      {"latex", LANG_TEX},
#line 217 "extensions.gperf"
      {"tex", LANG_TEX},
#line 83 "extensions.gperf"
      {"frx", LANG_VISUALBASIC},
#line 153 "extensions.gperf"
      {"p6", LANG_PERL},
#line 72 "extensions.gperf"
      {"f77", DISAMBIGUATE("fortran")},
#line 174 "extensions.gperf"
      {"ps", LANG_POSTSCRIPT},
#line 211 "extensions.gperf"
      {"swf", BINARY},
#line 62 "extensions.gperf"
      {"ec", LANG_EC},
#line 185 "extensions.gperf"
      {"rex", LANG_REXX},
#line 186 "extensions.gperf"
      {"rexx", LANG_REXX},
#line 53 "extensions.gperf"
      {"d", LANG_DMD},
#line 120 "extensions.gperf"
      {"lc", LANG_LIVECODE},
#line 190 "extensions.gperf"
      {"rktl", LANG_RACKET},
#line 184 "extensions.gperf"
      {"rebol", LANG_REBOL},
#line 203 "extensions.gperf"
      {"sql", LANG_SQL},
#line 116 "extensions.gperf"
      {"js", LANG_JAVASCRIPT},
#line 155 "extensions.gperf"
      {"pas", LANG_PASCAL},
#line 189 "extensions.gperf"
      {"rktd", LANG_RACKET},
#line 129 "extensions.gperf"
      {"m4", LANG_AUTOCONF},
#line 245 "extensions.gperf"
      {"xsl", LANG_XSLT},
#line 16 "extensions.gperf"
      {"as", LANG_ACTIONSCRIPT},
#line 201 "extensions.gperf"
      {"sls", LANG_SCHEME},
#line 94 "extensions.gperf"
      {"gs", LANG_GENIE},
#line 169 "extensions.gperf"
      {"pnt", BINARY},
#line 41 "extensions.gperf"
      {"cls", LANG_TEX},
#line 107 "extensions.gperf"
      {"i3", LANG_MODULA3},
#line 244 "extensions.gperf"
      {"xsd", LANG_XMLSCHEMA},
#line 110 "extensions.gperf"
      {"inc", DISAMBIGUATE("inc")},
#line 66 "extensions.gperf"
      {"erl", LANG_ERLANG},
#line 197 "extensions.gperf"
      {"sce", LANG_SCILAB},
#line 93 "extensions.gperf"
      {"grc", LANG_GRACE},
#line 180 "extensions.gperf"
      {"ra", BINARY},
#line 216 "extensions.gperf"
      {"tcl", LANG_TCL},
#line 63 "extensions.gperf"
      {"eclass", LANG_EBUILD},
#line 240 "extensions.gperf"
      {"xls", BINARY},
#line 187 "extensions.gperf"
      {"rhtml", LANG_RHTML},
#line 112 "extensions.gperf"
      {"jar", BINARY},
#line 18 "extensions.gperf"
      {"ascx", DISAMBIGUATE("aspx")},
#line 205 "extensions.gperf"
      {"st", DISAMBIGUATE("st")},
#line 55 "extensions.gperf"
      {"def", DISAMBIGUATE("def")},
#line 128 "extensions.gperf"
      {"m3", LANG_MODULA3},
#line 79 "extensions.gperf"
      {"for", DISAMBIGUATE("fortran")},
#line 239 "extensions.gperf"
      {"xhtml", LANG_HTML},
#line 57 "extensions.gperf"
      {"doc", BINARY},
#line 173 "extensions.gperf"
      {"pro", DISAMBIGUATE("pro")},
#line 119 "extensions.gperf"
      {"kt", LANG_KOTLIN},
#line 14 "extensions.gperf"
      {"ads", LANG_ADA},
#line 29 "extensions.gperf"
      {"bf", LANG_BRAINFUCK},
#line 102 "extensions.gperf"
      {"hs", LANG_HASKELL},
#line 21 "extensions.gperf"
      {"asx", DISAMBIGUATE("asx")},
#line 34 "extensions.gperf"
      {"boo", LANG_BOO},
#line 132 "extensions.gperf"
      {"mk", LANG_MAKE},
#line 25 "extensions.gperf"
      {"awk", LANG_AWK},
#line 235 "extensions.gperf"
      {"wav", BINARY},
#line 219 "extensions.gperf"
      {"tif", BINARY},
#line 220 "extensions.gperf"
      {"tiff", BINARY},
#line 43 "extensions.gperf"
      {"coffee", LANG_COFFEESCRIPT},
#line 13 "extensions.gperf"
      {"adb", LANG_ADA},
#line 154 "extensions.gperf"
      {"p8", LANG_LUA},
#line 206 "extensions.gperf"
      {"str", LANG_STRATEGO},
#line 51 "extensions.gperf"
      {"cu", LANG_CUDA},
#line 156 "extensions.gperf"
      {"perl", LANG_PERL},
#line 144 "extensions.gperf"
      {"mustache", LANG_HTML},
#line 118 "extensions.gperf"
      {"kdebuild-1", LANG_EBUILD},
#line 192 "extensions.gperf"
      {"ru", LANG_RUBY},
#line 202 "extensions.gperf"
      {"sps", LANG_SCHEME},
#line 238 "extensions.gperf"
      {"xaml", LANG_XAML},
#line 65 "extensions.gperf"
      {"el", LANG_EMACSLISP},
#line 214 "extensions.gperf"
      {"tap", LANG_PYTHON},
#line 157 "extensions.gperf"
      {"pdf", BINARY},
#line 225 "extensions.gperf"
      {"vala", LANG_VALA},
#line 31 "extensions.gperf"
      {"bi", DISAMBIGUATE("basic")},
#line 246 "extensions.gperf"
      {"z80", LANG_ASSEMBLER},
#line 222 "extensions.gperf"
      {"uc", LANG_UNREALSCRIPT},
#line 125 "extensions.gperf"
      {"lgt", LANG_LOGTALK},
#line 48 "extensions.gperf"
      {"csproj", LANG_XML},
#line 70 "extensions.gperf"
      {"f03", DISAMBIGUATE("fortran")},
#line 233 "extensions.gperf"
      {"vhdl", LANG_VHDL},
#line 111 "extensions.gperf"
      {"j", LANG_OBJECTIVE_J},
#line 237 "extensions.gperf"
      {"wlt", LANG_MATHEMATICA},
#line 52 "extensions.gperf"
      {"cxx", LANG_CPP},
#line 33 "extensions.gperf"
      {"bmx", LANG_BLITZMAX},
#line 232 "extensions.gperf"
      {"vhd", LANG_VHDL},
#line 226 "extensions.gperf"
      {"vapi", LANG_VALA},
#line 127 "extensions.gperf"
      {"m", DISAMBIGUATE("m")},
#line 134 "extensions.gperf"
      {"ml4", LANG_OCAML},
#line 198 "extensions.gperf"
      {"sci", LANG_SCILAB},
#line 182 "extensions.gperf"
      {"rbw", LANG_RUBY},
#line 123 "extensions.gperf"
      {"lsp", LANG_LISP},
#line 17 "extensions.gperf"
      {"as8", LANG_ASSEMBLER},
#line 20 "extensions.gperf"
      {"aspx", DISAMBIGUATE("aspx")},
#line 137 "extensions.gperf"
      {"mo", LANG_MODELICA},
#line 147 "extensions.gperf"
      {"nse", LANG_LUA},
#line 97 "extensions.gperf"
      {"h++", LANG_CPP},
#line 71 "extensions.gperf"
      {"f08", DISAMBIGUATE("fortran")},
#line 56 "extensions.gperf"
      {"di", LANG_DMD},
#line 124 "extensions.gperf"
      {"ltx", LANG_TEX},
#line 90 "extensions.gperf"
      {"go", LANG_GOLANG},
#line 164 "extensions.gperf"
      {"pl", DISAMBIGUATE("pl")},
#line 122 "extensions.gperf"
      {"lisp", LANG_LISP},
#line 61 "extensions.gperf"
      {"ebuild", LANG_EBUILD},
#line 200 "extensions.gperf"
      {"sh", LANG_SHELL},
#line 58 "extensions.gperf"
      {"dtx", LANG_TEX_DTX},
#line 68 "extensions.gperf"
      {"exlib", LANG_EXHERES},
#line 101 "extensions.gperf"
      {"hrl", LANG_ERLANG},
#line 163 "extensions.gperf"
      {"pike", LANG_PIKE},
#line 236 "extensions.gperf"
      {"wl", LANG_MATHEMATICA},
#line 143 "extensions.gperf"
      {"mt", LANG_MATHEMATICA},
#line 82 "extensions.gperf"
      {"frm", LANG_VISUALBASIC},
#line 166 "extensions.gperf"
      {"pmc", LANG_C},
#line 139 "extensions.gperf"
      {"mov", BINARY},
#line 113 "extensions.gperf"
      {"java", LANG_JAVA},
#line 131 "extensions.gperf"
      {"mf", LANG_METAFONT},
#line 133 "extensions.gperf"
      {"ml", LANG_OCAML},
#line 229 "extensions.gperf"
      {"vba", LANG_VISUALBASIC},
#line 242 "extensions.gperf"
      {"xml", LANG_XML},
#line 221 "extensions.gperf"
      {"tpl", LANG_HTML},
#line 161 "extensions.gperf"
      {"php4", LANG_PHP},
#line 109 "extensions.gperf"
      {"in", DISAMBIGUATE("in")},
#line 77 "extensions.gperf"
      {"frag", LANG_GLSL},
#line 172 "extensions.gperf"
      {"ppt", BINARY},
#line 162 "extensions.gperf"
      {"php5", LANG_PHP},
#line 87 "extensions.gperf"
      {"gemspec", LANG_RUBY},
#line 199 "extensions.gperf"
      {"scm", LANG_SCHEME},
#line 89 "extensions.gperf"
      {"glsl", LANG_GLSL},
#line 92 "extensions.gperf"
      {"grace", LANG_GRACE},
#line 196 "extensions.gperf"
      {"scala", LANG_SCALA},
#line 64 "extensions.gperf"
      {"eh", LANG_EC},
#line 170 "extensions.gperf"
      {"pod", LANG_PERL},
#line 15 "extensions.gperf"
      {"aiff", BINARY},
#line 22 "extensions.gperf"
      {"au", BINARY},
#line 117 "extensions.gperf"
      {"jsp", LANG_JSP},
#line 39 "extensions.gperf"
      {"chai", LANG_CHAISCRIPT},
#line 95 "extensions.gperf"
      {"gz", BINARY},
#line 88 "extensions.gperf"
      {"gif", BINARY},
#line 108 "extensions.gperf"
      {"icns", BINARY},
#line 126 "extensions.gperf"
      {"lua", LANG_LUA},
#line 80 "extensions.gperf"
      {"forth", LANG_FORTH},
#line 138 "extensions.gperf"
      {"mod", DISAMBIGUATE("mod")},
#line 146 "extensions.gperf"
      {"nix", LANG_NIX},
#line 91 "extensions.gperf"
      {"groovy", LANG_GROOVY},
#line 160 "extensions.gperf"
      {"php3", LANG_PHP},
#line 30 "extensions.gperf"
      {"bfpp", LANG_BFPP},
#line 42 "extensions.gperf"
      {"cmake", LANG_CMAKE},
#line 44 "extensions.gperf"
      {"com", LANG_DCL},
#line 96 "extensions.gperf"
      {"h", DISAMBIGUATE("h")},
#line 148 "extensions.gperf"
      {"nsi", LANG_NSIS},
#line 177 "extensions.gperf"
      {"qt", BINARY},
#line 98 "extensions.gperf"
      {"haml", LANG_HAML},
#line 167 "extensions.gperf"
      {"pmod", LANG_PIKE},
#line 40 "extensions.gperf"
      {"clj", LANG_CLOJURE},
#line 19 "extensions.gperf"
      {"asm", LANG_ASSEMBLER},
#line 158 "extensions.gperf"
      {"ph", LANG_PERL},
#line 50 "extensions.gperf"
      {"ctp", LANG_PHP},
#line 241 "extensions.gperf"
      {"xlw", BINARY},
#line 105 "extensions.gperf"
      {"hx", LANG_HAXE},
#line 130 "extensions.gperf"
      {"m4a", BINARY},
#line 208 "extensions.gperf"
      {"svg", BINARY},
#line 151 "extensions.gperf"
      {"obn", LANG_OBERON},
#line 32 "extensions.gperf"
      {"bmp", BINARY},
#line 193 "extensions.gperf"
      {"run", LANG_AMPL},
#line 248 "extensions.gperf"
      {"zpt", LANG_HTML},
#line 165 "extensions.gperf"
      {"pm", LANG_PERL},
#line 234 "extensions.gperf"
      {"vim", LANG_VIM},
#line 159 "extensions.gperf"
      {"php", LANG_PHP},
#line 67 "extensions.gperf"
      {"exheres-0", LANG_EXHERES},
#line 171 "extensions.gperf"
      {"pp", DISAMBIGUATE("pp")},
#line 168 "extensions.gperf"
      {"png", BINARY},
#line 106 "extensions.gperf"
      {"hxx", LANG_CPP},
#line 45 "extensions.gperf"
      {"cpp", LANG_CPP},
#line 136 "extensions.gperf"
      {"mm", LANG_OBJECTIVE_C},
#line 141 "extensions.gperf"
      {"mp3", BINARY},
#line 140 "extensions.gperf"
      {"mp", LANG_METAPOST_WITH_TEX},
#line 12 "extensions.gperf"
      {"ada", LANG_ADA},
#line 23 "extensions.gperf"
      {"aug", LANG_AUGEAS},
#line 24 "extensions.gperf"
      {"avi", BINARY},
#line 135 "extensions.gperf"
      {"mli", LANG_OCAML},
#line 81 "extensions.gperf"
      {"fpp", DISAMBIGUATE("fortran")},
#line 209 "extensions.gperf"
      {"svgz", BINARY},
#line 99 "extensions.gperf"
      {"hh", LANG_CPP},
#line 210 "extensions.gperf"
      {"svn", BINARY},
#line 175 "extensions.gperf"
      {"py", LANG_PYTHON},
#line 145 "extensions.gperf"
      {"mxml", LANG_MXML},
#line 176 "extensions.gperf"
      {"qml", LANG_QML},
#line 59 "extensions.gperf"
      {"dylan", LANG_DYLAN},
#line 152 "extensions.gperf"
      {"ogg", BINARY},
#line 114 "extensions.gperf"
      {"jpeg", BINARY},
#line 207 "extensions.gperf"
      {"sty", LANG_TEX},
#line 247 "extensions.gperf"
      {"zip", BINARY},
#line 104 "extensions.gperf"
      {"html", LANG_HTML},
#line 9 "extensions.gperf"
      {"4th", LANG_FORTH},
#line 149 "extensions.gperf"
      {"nsh", LANG_NSIS},
#line 86 "extensions.gperf"
      {"ftn", DISAMBIGUATE("fortran")},
#line 85 "extensions.gperf"
      {"fth", LANG_FORTH},
#line 218 "extensions.gperf"
      {"tgz", BINARY},
#line 100 "extensions.gperf"
      {"hpp", LANG_CPP},
#line 115 "extensions.gperf"
      {"jpg", BINARY},
#line 103 "extensions.gperf"
      {"htm", LANG_HTML},
#line 142 "extensions.gperf"
      {"mpg", BINARY}
    };

  static short lookup[] =
    {
       -1,   0,  -1,  -1,  -1,  -1,  -1,   1,  -1,  -1,
       -1,   2,   3,  -1,  -1,  -1,  -1,   4,  -1,  -1,
       -1,   5,  -1,   6,  -1,  -1,  -1,   7,  -1,  -1,
       -1,   8,  -1,   9,  -1,  -1,  -1,  10,  11,  -1,
       -1,  12,  13,  14,  -1,  -1,  -1,  15,  -1,  -1,
       -1,  16,  17,  18,  -1,  -1,  -1,  19,  20,  -1,
       -1,  21,  -1,  22,  -1,  -1,  -1,  23,  24,  -1,
       -1,  -1,  25,  26,  -1,  -1,  -1,  -1,  27,  -1,
       -1,  28,  29,  30,  -1,  -1,  -1,  31,  32,  -1,
       -1,  33,  34,  -1,  -1,  35,  36,  -1,  37,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  38,
       -1,  39,  -1,  40,  -1,  41,  -1,  -1,  42,  -1,
       -1,  -1,  -1,  43,  -1,  -1,  -1,  44,  45,  -1,
       -1,  -1,  46,  47,  -1,  -1,  -1,  48,  49,  50,
       -1,  51,  52,  -1,  53,  54,  -1,  -1,  55,  -1,
       -1,  -1,  56,  57,  58,  -1,  -1,  59,  60,  -1,
       -1,  -1,  61,  -1,  -1,  -1,  -1,  -1,  62,  -1,
       63,  -1,  64,  65,  -1,  -1,  -1,  66,  67,  -1,
       -1,  -1,  68,  69,  -1,  -1,  -1,  -1,  70,  -1,
       -1,  71,  72,  73,  -1,  -1,  74,  -1,  75,  -1,
       76,  -1,  -1,  77,  78,  -1,  -1,  79,  80,  -1,
       -1,  -1,  81,  82,  -1,  83,  -1,  -1,  84,  -1,
       -1,  85,  86,  87,  -1,  88,  -1,  89,  90,  -1,
       -1,  91,  92,  93,  -1,  -1,  -1,  94,  95,  96,
       -1,  97,  -1,  98,  -1,  -1,  -1,  99, 100,  -1,
       -1,  -1, 101,  -1, 102,  -1,  -1,  -1, 103,  -1,
      104,  -1, 105, 106, 107,  -1,  -1, 108, 109,  -1,
       -1,  -1,  -1, 110, 111,  -1,  -1, 112, 113,  -1,
       -1,  -1, 114, 115,  -1,  -1, 116,  -1, 117, 118,
       -1, 119, 120, 121,  -1,  -1,  -1, 122, 123, 124,
       -1, 125,  -1, 126,  -1,  -1,  -1,  -1, 127,  -1,
       -1, 128,  -1, 129,  -1,  -1,  -1,  -1, 130, 131,
       -1, 132, 133, 134,  -1,  -1,  -1,  -1, 135,  -1,
       -1,  -1, 136, 137, 138,  -1,  -1, 139,  -1, 140,
       -1, 141, 142, 143,  -1, 144,  -1,  -1, 145, 146,
       -1, 147, 148, 149,  -1,  -1,  -1, 150, 151, 152,
      153,  -1, 154, 155,  -1,  -1,  -1, 156, 157, 158,
      159,  -1, 160, 161, 162, 163,  -1,  -1, 164,  -1,
       -1,  -1, 165, 166,  -1,  -1,  -1,  -1,  -1,  -1,
      167,  -1, 168, 169, 170,  -1,  -1, 171, 172, 173,
      174, 175,  -1, 176,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1, 177,  -1, 178,  -1,  -1, 179,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1, 180, 181, 182,
       -1,  -1, 183,  -1, 184,  -1,  -1,  -1, 185,  -1,
       -1, 186, 187,  -1,  -1,  -1,  -1, 188,  -1, 189,
       -1,  -1, 190, 191,  -1,  -1,  -1,  -1, 192,  -1,
       -1,  -1, 193, 194,  -1,  -1, 195, 196, 197,  -1,
       -1,  -1,  -1, 198,  -1, 199,  -1, 200,  -1,  -1,
       -1, 201,  -1, 202,  -1,  -1, 203,  -1, 204,  -1,
       -1,  -1,  -1, 205, 206,  -1,  -1, 207, 208,  -1,
       -1,  -1,  -1, 209,  -1,  -1,  -1,  -1, 210,  -1,
       -1, 211,  -1,  -1,  -1,  -1,  -1,  -1, 212,  -1,
       -1,  -1, 213, 214, 215,  -1,  -1, 216,  -1,  -1,
       -1,  -1,  -1, 217,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1, 218,  -1,  -1, 219,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1, 220,  -1,  -1,
       -1,  -1,  -1,  -1,  -1, 221,  -1,  -1,  -1,  -1,
       -1,  -1, 222,  -1, 223,  -1,  -1, 224,  -1, 225,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1, 226,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1, 227,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1, 228,  -1,
       -1,  -1,  -1, 229, 230,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1, 231,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1, 232,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1, 233,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1, 234,  -1,
       -1,  -1,  -1, 235,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1, 236, 237,
       -1,  -1,  -1, 238, 239
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
