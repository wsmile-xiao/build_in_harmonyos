/* ANSI-C code produced by gperf version 3.1 */
/* Command-line: gperf -L ANSI-C -E -D -K key -H ohcount_hash_language -N ohcount_hash_language_from_name -t languages.gperf  */
/* Computed positions: -k'1-2,5,$' */

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

#line 1 "languages.gperf"

#include "../languages.h"
#line 4 "languages.gperf"
struct LanguageMap;
/* maximum key range = 316, duplicates = 0 */

#ifdef __GNUC__
__inline
#else
#ifdef __cplusplus
inline
#endif
#endif
static unsigned int
ohcount_hash_language (register const char *str, register size_t len)
{
  static unsigned short asso_values[] =
    {
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
       20,   5, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317,  10,  40,   0,
      120,   0,  60, 100,  70, 125,   7, 125,   5,  30,
       20,  40,  55,   0,   5,   0,  55,  85,  95,  35,
       20,  45,   0, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317, 317, 317, 317, 317,
      317, 317, 317, 317, 317, 317
    };
  register unsigned int hval = len;

  switch (hval)
    {
      default:
        hval += asso_values[(unsigned char)str[4]];
      /*FALLTHROUGH*/
      case 4:
      case 3:
      case 2:
        hval += asso_values[(unsigned char)str[1]];
      /*FALLTHROUGH*/
      case 1:
        hval += asso_values[(unsigned char)str[0]];
        break;
    }
  return hval + asso_values[(unsigned char)str[len - 1]];
}

struct LanguageMap *
ohcount_hash_language_from_name (register const char *str, register size_t len)
{
  enum
    {
      TOTAL_KEYWORDS = 118,
      MIN_WORD_LENGTH = 1,
      MAX_WORD_LENGTH = 20,
      MIN_HASH_VALUE = 1,
      MAX_HASH_VALUE = 316
    };

  static struct LanguageMap wordlist[] =
    {
#line 20 "languages.gperf"
      {"c", LANG_C, "C", 0},
#line 40 "languages.gperf"
      {"ec", LANG_EC, "eC", 0},
#line 33 "languages.gperf"
      {"css", LANG_CSS, "CSS", 1},
#line 110 "languages.gperf"
      {"sql", LANG_SQL, "SQL", 0},
#line 96 "languages.gperf"
      {"r", LANG_R, "R", 0},
#line 22 "languages.gperf"
      {"classic_basic", LANG_CLASSIC_BASIC, "Classic Basic", 0},
#line 98 "languages.gperf"
      {"rebol", LANG_REBOL, "REBOL", 0},
#line 81 "languages.gperf"
      {"nsis", LANG_NSIS, "NSIS", 0},
#line 103 "languages.gperf"
      {"scala", LANG_SCALA, "Scala", 0},
#line 23 "languages.gperf"
      {"clearsilver", LANG_CLEARSILVER, "ClearSilver", 0},
#line 31 "languages.gperf"
      {"cs_aspx", LANG_CS_ASPX, "", 0},
#line 99 "languages.gperf"
      {"rexx", LANG_REXX, "rexx", 0},
#line 24 "languages.gperf"
      {"clearsilver_template", LANG_CLEARSILVER_TEMPLATE, "ClearSilver", 0},
#line 61 "languages.gperf"
      {"java", LANG_JAVA, "Java", 0},
#line 44 "languages.gperf"
      {"exheres", LANG_EXHERES, "Exheres", 0},
#line 26 "languages.gperf"
      {"cmake", LANG_CMAKE, "Cmake script", 2},
#line 104 "languages.gperf"
      {"scheme", LANG_SCHEME, "Scheme", 0},
#line 95 "languages.gperf"
      {"qml", LANG_QML, "QML", 1},
#line 120 "languages.gperf"
      {"xaml", LANG_XAML, "XAML", 1},
#line 28 "languages.gperf"
      {"coq", LANG_COQ, "Coq", 0},
#line 70 "languages.gperf"
      {"make", LANG_MAKE, "Make", 2},
#line 8 "languages.gperf"
      {"ampl", LANG_AMPL, "AMPL", 0},
#line 60 "languages.gperf"
      {"jam", LANG_JAM, "Jam", 2},
#line 9 "languages.gperf"
      {"assembler", LANG_ASSEMBLER, "Assembler", 0},
#line 85 "languages.gperf"
      {"ocaml", LANG_OCAML, "Objective Caml", 0},
#line 105 "languages.gperf"
      {"scilab", LANG_SCILAB, "Scilab", 0},
#line 121 "languages.gperf"
      {"xml", LANG_XML, "XML", 1},
#line 79 "languages.gperf"
      {"mxml", LANG_MXML, "MXML", 1},
#line 71 "languages.gperf"
      {"mathematica", LANG_MATHEMATICA, "Mathematica", 0},
#line 111 "languages.gperf"
      {"tcl", LANG_TCL, "TCL", 0},
#line 88 "languages.gperf"
      {"perl", LANG_PERL, "Perl", 0},
#line 63 "languages.gperf"
      {"jsp", LANG_JSP, "", 0},
#line 32 "languages.gperf"
      {"csharp", LANG_CSHARP, "C#", 0},
#line 123 "languages.gperf"
      {"xmlschema", LANG_XMLSCHEMA, "XML Schema", 1},
#line 109 "languages.gperf"
      {"structured_basic", LANG_STRUCTURED_BASIC, "Structured Basic", 0},
#line 30 "languages.gperf"
      {"crystal", LANG_CRYSTAL, "Crystal", 0},
#line 16 "languages.gperf"
      {"blitzmax", LANG_BLITZMAX, "BlitzMax", 0},
#line 97 "languages.gperf"
      {"racket", LANG_RACKET, "Racket", 0},
#line 112 "languages.gperf"
      {"tex", LANG_TEX, "TeX/LaTeX", 1},
#line 122 "languages.gperf"
      {"xslt", LANG_XSLT, "XSL Transformation", 0},
#line 62 "languages.gperf"
      {"javascript", LANG_JAVASCRIPT, "JavaScript", 0},
#line 57 "languages.gperf"
      {"haxe", LANG_HAXE, "HaXe", 0},
#line 106 "languages.gperf"
      {"shell", LANG_SHELL, "shell script", 0},
#line 87 "languages.gperf"
      {"pascal", LANG_PASCAL, "Pascal", 0},
#line 78 "languages.gperf"
      {"modula3", LANG_MODULA3, "Modula-3", 0},
#line 55 "languages.gperf"
      {"haml", LANG_HAML, "Haml", 1},
#line 100 "languages.gperf"
      {"rhtml", LANG_RHTML, "", 0},
#line 83 "languages.gperf"
      {"objective_c", LANG_OBJECTIVE_C, "Objective-C", 0},
#line 56 "languages.gperf"
      {"haskell", LANG_HASKELL, "Haskell", 0},
#line 76 "languages.gperf"
      {"modelica", LANG_MODELICA, "Modelica", 0},
#line 42 "languages.gperf"
      {"emacslisp", LANG_EMACSLISP, "Emacs lisp", 0},
#line 72 "languages.gperf"
      {"matlab", LANG_MATLAB, "Matlab", 0},
#line 25 "languages.gperf"
      {"clojure", LANG_CLOJURE, "Clojure", 0},
#line 84 "languages.gperf"
      {"objective_j", LANG_OBJECTIVE_J, "Objective-J", 0},
#line 34 "languages.gperf"
      {"cuda", LANG_CUDA, "CUDA", 0},
#line 77 "languages.gperf"
      {"modula2", LANG_MODULA2, "Modula-2", 0},
#line 69 "languages.gperf"
      {"lua", LANG_LUA, "Lua", 0},
#line 50 "languages.gperf"
      {"genie", LANG_GENIE, "Genie", 0},
#line 27 "languages.gperf"
      {"coffescript", LANG_COFFEESCRIPT, "CoffeeScript", 0},
#line 14 "languages.gperf"
      {"bat", LANG_BAT, "DOS batch script", 0},
#line 53 "languages.gperf"
      {"grace", LANG_GRACE, "Grace", 0},
#line 10 "languages.gperf"
      {"augeas", LANG_AUGEAS, "Augeas", 0},
#line 29 "languages.gperf"
      {"cpp", LANG_CPP, "C++", 0},
#line 51 "languages.gperf"
      {"glsl", LANG_GLSL, "OpenGL Shading Language", 0},
#line 48 "languages.gperf"
      {"fortranfree", LANG_FORTRANFREE, "Fortan (Free-format)", 0},
#line 6 "languages.gperf"
      {"actionscript", LANG_ACTIONSCRIPT, "ActionScript", 0},
#line 115 "languages.gperf"
      {"vala", LANG_VALA, "Vala", 0},
#line 45 "languages.gperf"
      {"factor", LANG_FACTOR, "Factor", 0},
#line 75 "languages.gperf"
      {"metapost_with_tex", LANG_METAPOST_WITH_TEX, "", 0},
#line 17 "languages.gperf"
      {"boo", LANG_BOO, "Boo", 0},
#line 15 "languages.gperf"
      {"bash", LANG_SHELL, "shell script", 0},
#line 49 "languages.gperf"
      {"fsharp", LANG_FSHARP, "F#", 0},
#line 35 "languages.gperf"
      {"dcl", LANG_DCL, "DCL", 0},
#line 43 "languages.gperf"
      {"erlang", LANG_ERLANG, "Erlang", 0},
#line 12 "languages.gperf"
      {"automake", LANG_AUTOMAKE, "Automake", 2},
#line 58 "languages.gperf"
      {"html", LANG_HTML, "HTML", 1},
#line 21 "languages.gperf"
      {"chaiscript", LANG_CHAISCRIPT, "ChaiScript", 0},
#line 41 "languages.gperf"
      {"eiffel", LANG_EIFFEL, "Eiffel", 0},
#line 67 "languages.gperf"
      {"livecode", LANG_LIVECODE, "LiveCode", 0},
#line 101 "languages.gperf"
      {"ruby", LANG_RUBY, "Ruby", 0},
#line 86 "languages.gperf"
      {"octave", LANG_OCTAVE, "", 0},
#line 7 "languages.gperf"
      {"ada", LANG_ADA, "Ada", 0},
#line 82 "languages.gperf"
      {"oberon", LANG_OBERON, "Oberon", 0},
#line 74 "languages.gperf"
      {"metapost", LANG_METAPOST, "MetaPost", 1},
#line 102 "languages.gperf"
      {"rust", LANG_RUST, "Rust", 0},
#line 73 "languages.gperf"
      {"metafont", LANG_METAFONT, "MetaFont", 1},
#line 108 "languages.gperf"
      {"stratego", LANG_STRATEGO, "Stratego", 0},
#line 19 "languages.gperf"
      {"bfpp", LANG_BFPP, "Brainfuck++", 0},
#line 91 "languages.gperf"
      {"postscript", LANG_POSTSCRIPT, "PostScript", 1},
#line 116 "languages.gperf"
      {"vb_aspx", LANG_VB_ASPX, "", 0},
#line 11 "languages.gperf"
      {"autoconf", LANG_AUTOCONF, "Autoconf", 2},
#line 114 "languages.gperf"
      {"typescript", LANG_TYPESCRIPT, "TypeScript", 0},
#line 94 "languages.gperf"
      {"python", LANG_PYTHON, "Python", 0},
#line 80 "languages.gperf"
      {"nix", LANG_NIX, "Nix", 0},
#line 107 "languages.gperf"
      {"smalltalk", LANG_SMALLTALK, "Smalltalk", 0},
#line 39 "languages.gperf"
      {"ebuild", LANG_EBUILD, "Ebuild", 0},
#line 13 "languages.gperf"
      {"awk", LANG_AWK, "AWK", 0},
#line 117 "languages.gperf"
      {"vhdl", LANG_VHDL, "VHDL", 0},
#line 113 "languages.gperf"
      {"unrealscript", LANG_UNREALSCRIPT, "UnrealScript", 0},
#line 89 "languages.gperf"
      {"php", LANG_PHP, "PHP", 0},
#line 90 "languages.gperf"
      {"pike", LANG_PIKE, "Pike", 0},
#line 68 "languages.gperf"
      {"logtalk", LANG_LOGTALK, "Logtalk", 0},
#line 66 "languages.gperf"
      {"lisp", LANG_LISP, "Lisp", 0},
#line 37 "languages.gperf"
      {"dtx", LANG_TEX_DTX, "DTX for TeX/LaTeX", 1},
#line 18 "languages.gperf"
      {"brainfuck", LANG_BRAINFUCK, "Brainfuck", 0},
#line 93 "languages.gperf"
      {"puppet", LANG_PUPPET, "Puppet", 0},
#line 92 "languages.gperf"
      {"prolog", LANG_PROLOG, "Prolog", 0},
#line 38 "languages.gperf"
      {"dylan", LANG_DYLAN, "Dylan", 0},
#line 65 "languages.gperf"
      {"limbo", LANG_LIMBO, "Limbo", 0},
#line 47 "languages.gperf"
      {"fortranfixed", LANG_FORTRANFIXED, "Fortan (Fixed-format)", 0},
#line 119 "languages.gperf"
      {"visualbasic", LANG_VISUALBASIC, "Visual Basic", 0},
#line 46 "languages.gperf"
      {"forth", LANG_FORTH, "Forth", 0},
#line 54 "languages.gperf"
      {"groovy", LANG_GROOVY, "Groovy", 0},
#line 118 "languages.gperf"
      {"vim", LANG_VIM, "Vim script", 0},
#line 52 "languages.gperf"
      {"golang", LANG_GOLANG, "Golang", 0},
#line 36 "languages.gperf"
      {"dmd", LANG_DMD, "D", 0},
#line 59 "languages.gperf"
      {"idl_pvwave", LANG_IDL_PVWAVE, "IDL/PV-WAVE/GDL", 0},
#line 64 "languages.gperf"
      {"kotlin", LANG_KOTLIN, "Kotlin", 0}
    };

  static signed char lookup[] =
    {
       -1,   0,   1,   2,  -1,  -1,  -1,  -1,   3,  -1,
       -1,   4,  -1,  -1,  -1,  -1,  -1,  -1,   5,  -1,
        6,  -1,  -1,  -1,   7,   8,   9,  10,  -1,  11,
       12,  13,  14,  -1,  -1,  15,  16,  -1,  17,  18,
       -1,  -1,  -1,  19,  20,  -1,  -1,  -1,  -1,  21,
       22,  -1,  -1,  -1,  23,  24,  25,  -1,  26,  27,
       -1,  28,  -1,  29,  30,  31,  32,  -1,  -1,  33,
       -1,  34,  35,  36,  -1,  -1,  37,  -1,  38,  39,
       -1,  -1,  40,  -1,  41,  42,  43,  44,  -1,  45,
       46,  47,  48,  49,  50,  -1,  51,  52,  53,  54,
       -1,  -1,  55,  56,  -1,  57,  58,  -1,  59,  -1,
       60,  61,  -1,  62,  63,  -1,  64,  65,  -1,  66,
       -1,  67,  68,  69,  70,  -1,  71,  -1,  72,  -1,
       -1,  73,  -1,  74,  75,  76,  77,  -1,  78,  79,
       -1,  80,  -1,  81,  -1,  -1,  82,  -1,  83,  84,
       -1,  -1,  -1,  85,  -1,  -1,  -1,  -1,  86,  87,
       88,  -1,  89,  90,  -1,  91,  92,  -1,  93,  94,
       -1,  95,  -1,  96,  97,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  98,  99, 100,  -1,  -1, 101,  -1, 102,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1, 103, 104,
       -1, 105,  -1,  -1,  -1,  -1, 106,  -1,  -1,  -1,
      107,  -1,  -1,  -1,  -1, 108,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1, 109,  -1,  -1,
       -1, 110,  -1,  -1,  -1, 111,  -1,  -1,  -1,  -1,
       -1, 112,  -1, 113,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1, 114,  -1,  -1,  -1,
       -1,  -1,  -1, 115,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
       -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
      116,  -1,  -1,  -1,  -1,  -1, 117
    };

  if (len <= MAX_WORD_LENGTH && len >= MIN_WORD_LENGTH)
    {
      register unsigned int key = ohcount_hash_language (str, len);

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
