/* ANSI-C code produced by gperf version 3.1 */
/* Command-line: gperf -L ANSI-C -E -D -K key -H ohcount_hash_parser -N ohcount_hash_parser_from_language -t parsers.gperf  */
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

#line 1 "parsers.gperf"

#include "../parsers/actionscript.h"
#include "../parsers/ada.h"
#include "../parsers/ampl.h"
#include "../parsers/assembler.h"
#include "../parsers/augeas.h"
#include "../parsers/autoconf.h"
#include "../parsers/automake.h"
#include "../parsers/awk.h"
#include "../parsers/bat.h"
#include "../parsers/blitzmax.h"
#include "../parsers/boo.h"
#include "../parsers/brainfuck.h"
#include "../parsers/bfpp.h"
#include "../parsers/c.h"
#include "../parsers/chaiscript.h"
#include "../parsers/classic_basic.h"
#include "../parsers/clearsilver.h"
#include "../parsers/clearsilverhtml.h"
#include "../parsers/coffeescript.h"
#include "../parsers/cmake.h"
#include "../parsers/coq.h"
#include "../parsers/crystal.h"
#include "../parsers/cs_aspx.h"
#include "../parsers/css.h"
#include "../parsers/d.h"
#include "../parsers/dcl.h"
#include "../parsers/dylan.h"
#include "../parsers/ebuild.h"
#include "../parsers/eiffel.h"
#include "../parsers/erlang.h"
#include "../parsers/exheres.h"
#include "../parsers/factor.h"
#include "../parsers/forth.h"
#include "../parsers/fortranfixed.h"
#include "../parsers/fortranfree.h"
#include "../parsers/fsharp.h"
#include "../parsers/glsl.h"
#include "../parsers/golang.h"
#include "../parsers/grace.h"
#include "../parsers/groovy.h"
#include "../parsers/haml.h"
#include "../parsers/haskell.h"
#include "../parsers/haxe.h"
#include "../parsers/html.h"
#include "../parsers/idl_pvwave.h"
#include "../parsers/jam.h"
#include "../parsers/java.h"
#include "../parsers/javascript.h"
#include "../parsers/jsp.h"
#include "../parsers/kotlin.h"
#include "../parsers/lisp.h"
#include "../parsers/limbo.h"
#include "../parsers/livecode.h"
#include "../parsers/logtalk.h"
#include "../parsers/lua.h"
#include "../parsers/makefile.h"
#include "../parsers/mathematica.h"
#include "../parsers/matlab.h"
#include "../parsers/metafont.h"
#include "../parsers/metapost.h"
#include "../parsers/metapost_with_tex.h"
#include "../parsers/modelica.h"
#include "../parsers/modula2.h"
#include "../parsers/modula3.h"
#include "../parsers/mxml.h"
#include "../parsers/nix.h"
#include "../parsers/nsis.h"
#include "../parsers/oberon.h"
#include "../parsers/objective_c.h"
#include "../parsers/objective_j.h"
#include "../parsers/ocaml.h"
#include "../parsers/octave.h"
#include "../parsers/pascal.h"
#include "../parsers/perl.h"
#include "../parsers/phphtml.h"
#include "../parsers/pike.h"
#include "../parsers/postscript.h"
#include "../parsers/prolog.h"
#include "../parsers/puppet.h"
#include "../parsers/python.h"
#include "../parsers/r.h"
#include "../parsers/rebol.h"
#include "../parsers/rexx.h"
#include "../parsers/ruby.h"
#include "../parsers/rust.h"
#include "../parsers/rhtml.h"
#include "../parsers/scala.h"
#include "../parsers/scilab.h"
#include "../parsers/shell.h"
#include "../parsers/smalltalk.h"
#include "../parsers/stratego.h"
#include "../parsers/structured_basic.h"
#include "../parsers/sql.h"
#include "../parsers/tcl.h"
#include "../parsers/tex.h"
#include "../parsers/tex_dtx.h"
#include "../parsers/unrealscript.h"
#include "../parsers/vb_aspx.h"
#include "../parsers/vhdl.h"
#include "../parsers/vim.h"
#include "../parsers/visual_basic.h"
#include "../parsers/xaml.h"
#include "../parsers/xml.h"
#include "../parsers/xslt.h"
#include "../parsers/xmlschema.h"
#line 108 "parsers.gperf"
struct ParserMap { const char *key; void (*parser)(char *, int, int, void(*) (const char *, const char *, int, int, void *), void *); };
/* maximum key range = 283, duplicates = 1 */

#ifdef __GNUC__
__inline
#else
#ifdef __cplusplus
inline
#endif
#endif
static unsigned int
ohcount_hash_parser (register const char *str, register size_t len)
{
  static unsigned short asso_values[] =
    {
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
        5,   0, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284,  10,  75,   0,
      125,   0,  10,  95,  65,  60, 115,  70,   5,  30,
       15,  25,  55, 115,   5,   0,   0,  90, 110,   0,
       20,  55,  55, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284, 284, 284, 284, 284,
      284, 284, 284, 284, 284, 284
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

struct ParserMap *
ohcount_hash_parser_from_language (register const char *str, register size_t len)
{
  enum
    {
      TOTAL_KEYWORDS = 118,
      MIN_WORD_LENGTH = 1,
      MAX_WORD_LENGTH = 20,
      MIN_HASH_VALUE = 1,
      MAX_HASH_VALUE = 283
    };

  static struct ParserMap wordlist[] =
    {
#line 123 "parsers.gperf"
      {"c", parse_c},
#line 142 "parsers.gperf"
      {"ec", parse_ec},
#line 136 "parsers.gperf"
      {"css", parse_css},
#line 214 "parsers.gperf"
      {"tcl", parse_tcl},
#line 199 "parsers.gperf"
      {"r", parse_r},
#line 212 "parsers.gperf"
      {"structured_basic", parse_structured_basic},
#line 132 "parsers.gperf"
      {"crystal", parse_crystal},
#line 126 "parsers.gperf"
      {"classic_basic", parse_classic_basic},
#line 184 "parsers.gperf"
      {"nsis", parse_nsis},
#line 201 "parsers.gperf"
      {"rebol", parse_rebol},
#line 200 "parsers.gperf"
      {"racket", parse_racket},
#line 215 "parsers.gperf"
      {"tex", parse_tex},
#line 226 "parsers.gperf"
      {"xslt", parse_xslt},
#line 206 "parsers.gperf"
      {"scala", parse_scala},
#line 127 "parsers.gperf"
      {"clearsilver", parse_clearsilver},
#line 134 "parsers.gperf"
      {"cs_aspx", parse_cs_aspx},
#line 202 "parsers.gperf"
      {"rexx", parse_rexx},
#line 128 "parsers.gperf"
      {"clearsilver_template", parse_cshtml},
#line 145 "parsers.gperf"
      {"exheres", parse_exheres},
#line 211 "parsers.gperf"
      {"stratego", parse_stratego},
#line 125 "parsers.gperf"
      {"cmake", parse_cmake},
#line 207 "parsers.gperf"
      {"scheme", parse_scheme},
#line 130 "parsers.gperf"
      {"coffeescript", parse_coffeescript},
#line 224 "parsers.gperf"
      {"xaml", parse_xaml},
#line 188 "parsers.gperf"
      {"ocaml", parse_ocaml},
#line 173 "parsers.gperf"
      {"make", parse_makefile},
#line 110 "parsers.gperf"
      {"actionscript", parse_actionscript},
#line 176 "parsers.gperf"
      {"metafont", parse_metafont},
#line 112 "parsers.gperf"
      {"ampl", parse_ampl},
#line 150 "parsers.gperf"
      {"fortranfree", parse_fortranfree},
#line 113 "parsers.gperf"
      {"assembler", parse_assembler},
#line 147 "parsers.gperf"
      {"factor", parse_factor},
#line 225 "parsers.gperf"
      {"xml", parse_xml},
#line 182 "parsers.gperf"
      {"mxml", parse_mxml},
#line 174 "parsers.gperf"
      {"mathematica", parse_mathematica},
#line 191 "parsers.gperf"
      {"perl", parse_perl},
#line 218 "parsers.gperf"
      {"typescript", parse_typescript},
#line 135 "parsers.gperf"
      {"csharp", parse_csharp},
#line 181 "parsers.gperf"
      {"modula3", parse_modula3},
#line 227 "parsers.gperf"
      {"xmlschema", parse_xmlschema},
#line 143 "parsers.gperf"
      {"eiffel", parse_eiffel},
#line 180 "parsers.gperf"
      {"modula2", parse_modula2},
#line 170 "parsers.gperf"
      {"livecode", parse_livecode},
#line 160 "parsers.gperf"
      {"html", parse_html},
#line 124 "parsers.gperf"
      {"chaiscript", parse_chaiscript},
#line 151 "parsers.gperf"
      {"fsharp", parse_fsharp},
#line 179 "parsers.gperf"
      {"modelica", parse_modelica},
#line 159 "parsers.gperf"
      {"haxe", parse_haxe},
#line 209 "parsers.gperf"
      {"shell", parse_shell},
#line 117 "parsers.gperf"
      {"awk", parse_awk},
#line 158 "parsers.gperf"
      {"haml", parse_haml},
#line 203 "parsers.gperf"
      {"rhtml", parse_rhtml},
#line 190 "parsers.gperf"
      {"pascal", parse_pascal},
#line 157 "parsers.gperf"
      {"haskell", parse_haskell},
#line 118 "parsers.gperf"
      {"bat", parse_bat},
#line 194 "parsers.gperf"
      {"postscript", parse_postscript},
#line 208 "parsers.gperf"
      {"scilab", parse_scilab},
#line 177 "parsers.gperf"
      {"metapost", parse_metapost},
#line 146 "parsers.gperf"
      {"emacslisp", parse_emacslisp},
#line 183 "parsers.gperf"
      {"nix", parse_nix},
#line 205 "parsers.gperf"
      {"rust", parse_rust},
#line 152 "parsers.gperf"
      {"genie", parse_genie},
#line 129 "parsers.gperf"
      {"clojure", parse_clojure},
#line 137 "parsers.gperf"
      {"cuda", parse_cuda},
#line 155 "parsers.gperf"
      {"grace", parse_grace},
#line 172 "parsers.gperf"
      {"lua", parse_lua},
#line 153 "parsers.gperf"
      {"glsl", parse_glsl},
#line 186 "parsers.gperf"
      {"objective_c", parse_objective_c},
#line 133 "parsers.gperf"
      {"cpp", parse_cpp},
#line 210 "parsers.gperf"
      {"smalltalk", parse_smalltalk},
#line 114 "parsers.gperf"
      {"augeas", parse_augeas},
#line 171 "parsers.gperf"
      {"logtalk", parse_logtalk},
#line 115 "parsers.gperf"
      {"autoconf", parse_autoconf},
#line 193 "parsers.gperf"
      {"pike", parse_pike},
#line 168 "parsers.gperf"
      {"limbo", parse_limbo},
#line 144 "parsers.gperf"
      {"erlang", parse_erlang},
#line 178 "parsers.gperf"
      {"metapost_with_tex", parse_mptex},
#line 213 "parsers.gperf"
      {"sql", parse_sql},
#line 167 "parsers.gperf"
      {"lisp", parse_lisp},
#line 169 "parsers.gperf"
      {"lisp", parse_lisp},
#line 217 "parsers.gperf"
      {"unrealscript", parse_unrealscript},
#line 120 "parsers.gperf"
      {"boo", parse_boo},
#line 175 "parsers.gperf"
      {"matlab", parse_matlab},
#line 138 "parsers.gperf"
      {"dcl", parse_dcl},
#line 219 "parsers.gperf"
      {"vala", parse_vala},
#line 164 "parsers.gperf"
      {"javascript", parse_javascript},
#line 116 "parsers.gperf"
      {"automake", parse_automake},
#line 163 "parsers.gperf"
      {"java", parse_java},
#line 189 "parsers.gperf"
      {"octave", parse_octave},
#line 131 "parsers.gperf"
      {"coq", parse_coq},
#line 122 "parsers.gperf"
      {"bfpp", parse_bfpp},
#line 185 "parsers.gperf"
      {"oberon", parse_oberon},
#line 111 "parsers.gperf"
      {"ada", parse_ada},
#line 196 "parsers.gperf"
      {"puppet", parse_puppet},
#line 216 "parsers.gperf"
      {"tex_dtx", parse_tex_dtx},
#line 198 "parsers.gperf"
      {"qml", parse_qml},
#line 204 "parsers.gperf"
      {"ruby", parse_ruby},
#line 197 "parsers.gperf"
      {"python", parse_python},
#line 162 "parsers.gperf"
      {"jam", parse_jam},
#line 119 "parsers.gperf"
      {"blitzmax", parse_blitzmax},
#line 148 "parsers.gperf"
      {"forth", parse_forth},
#line 165 "parsers.gperf"
      {"jsp", parse_jsp},
#line 121 "parsers.gperf"
      {"brainfuck", parse_brainfuck},
#line 166 "parsers.gperf"
      {"kotlin", parse_kotlin},
#line 149 "parsers.gperf"
      {"fortranfixed", parse_fortranfixed},
#line 192 "parsers.gperf"
      {"php", parse_phtml},
#line 221 "parsers.gperf"
      {"vhdl", parse_vhdl},
#line 195 "parsers.gperf"
      {"prolog", parse_prolog},
#line 223 "parsers.gperf"
      {"visualbasic", parse_visual_basic},
#line 222 "parsers.gperf"
      {"vim", parse_vim},
#line 141 "parsers.gperf"
      {"ebuild", parse_ebuild},
#line 220 "parsers.gperf"
      {"vb_aspx", parse_vb_aspx},
#line 140 "parsers.gperf"
      {"dylan", parse_dylan},
#line 187 "parsers.gperf"
      {"objective_j", parse_objective_j},
#line 154 "parsers.gperf"
      {"golang", parse_golang},
#line 161 "parsers.gperf"
      {"idl_pvwave", parse_idl_pvwave},
#line 156 "parsers.gperf"
      {"groovy", parse_groovy},
#line 139 "parsers.gperf"
      {"dmd", parse_d}
    };

  static short lookup[] =
    {
        -1,    0,    1,    2,   -1,   -1,   -1,   -1,
         3,   -1,   -1,    4,   -1,   -1,   -1,   -1,
         5,    6,    7,    8,    9,   10,   -1,   11,
        12,   13,   14,   15,   -1,   16,   17,   -1,
        18,   19,   -1,   20,   21,   22,   -1,   23,
        24,   -1,   -1,   -1,   25,   -1,   -1,   26,
        27,   28,   -1,   29,   -1,   -1,   30,   -1,
        31,   -1,   32,   33,   -1,   34,   -1,   -1,
        35,   36,   37,   38,   -1,   39,   -1,   40,
        41,   42,   43,   44,   45,   -1,   46,   47,
        48,   -1,   -1,   49,   50,   51,   52,   53,
        54,   -1,   55,   56,   -1,   57,   58,   -1,
        -1,   -1,   59,   60,   61,   -1,   62,   -1,
        63,   64,   -1,   -1,   65,   66,   -1,   67,
        -1,   68,   69,   -1,   70,   71,   72,   73,
        74,   75,   76,   77, -244,  -40,   -2,   80,
        81,   -1,   -1,   82,   -1,   83,   84,   85,
        -1,   -1,   86,   87,   -1,   88,   -1,   89,
        90,   -1,   91,   -1,   92,   -1,   -1,   93,
        94,   95,   96,   -1,   97,   -1,   98,   -1,
        -1,   -1,   -1,   99,   -1,   -1,   -1,   -1,
        -1,   -1,  100,   -1,   -1,  101,  102,   -1,
       103,  104,  105,   -1,   -1,   -1,   -1,   -1,
       106,   -1,  107,   -1,   -1,   -1,   -1,  108,
        -1,   -1,   -1,   -1,   -1,   -1,   -1,   -1,
        -1,   -1,   -1,  109,   -1,   -1,   -1,   -1,
        -1,   -1,   -1,  110,  111,   -1,   -1,  112,
        -1,   -1,   -1,   -1,   -1,   -1,   -1,   -1,
        -1,   -1,  113,   -1,   -1,   -1,   -1,   -1,
        -1,   -1,   -1,   -1,  114,   -1,   -1,   -1,
        -1,   -1,   -1,   -1,   -1,   -1,   -1,   -1,
        -1,   -1,  115,   -1,   -1,   -1,   -1,   -1,
        -1,   -1,   -1,   -1,   -1,   -1,   -1,   -1,
        -1,   -1,   -1,   -1,   -1,   -1,   -1,  116,
        -1,   -1,   -1,   -1,   -1,   -1,   -1,   -1,
        -1,   -1,   -1,  117
    };

  if (len <= MAX_WORD_LENGTH && len >= MIN_WORD_LENGTH)
    {
      register unsigned int key = ohcount_hash_parser (str, len);

      if (key <= MAX_HASH_VALUE)
        {
          register int index = lookup[key];

          if (index >= 0)
            {
              register const char *s = wordlist[index].key;

              if (*str == *s && !strcmp (str + 1, s + 1))
                return &wordlist[index];
            }
          else if (index < -TOTAL_KEYWORDS)
            {
              register int offset = - 1 - TOTAL_KEYWORDS - index;
              register struct ParserMap *wordptr = &wordlist[TOTAL_KEYWORDS + lookup[offset]];
              register struct ParserMap *wordendptr = wordptr + -lookup[offset + 1];

              while (wordptr < wordendptr)
                {
                  register const char *s = wordptr->key;

                  if (*str == *s && !strcmp (str + 1, s + 1))
                    return wordptr;
                  wordptr++;
                }
            }
        }
    }
  return 0;
}
