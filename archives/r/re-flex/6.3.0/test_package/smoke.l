/* End-to-end smoke input for the packaged reflex generator:
 * reflex -> generated scanner -> compile against packaged libreflex.a
 * -> run -> assert NUM:/WORD: tokenization output (see test_package
 * conanfile.py step 3). */
%{
#include <stdio.h>
%}
%option fast flex noyywrap
%%
[0-9]+   printf("NUM:%s\n", yytext);
[a-z]+   printf("WORD:%s\n", yytext);
.|\n     ;
%%
int main()
{
  return yyFlexLexer().yylex();
}
