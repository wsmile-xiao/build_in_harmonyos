
#line 1 "css.rl"
// css.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_CSS_PARSER_H
#define OHCOUNT_CSS_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *CSS_LANG = LANG_CSS;

// the languages entities
const char *css_entities[] = {
  "space", "comment", "string", "at_rule", "selector",
  "value", "unit", "color", "url", "any"
};

// constants associated with the entities
enum {
  CSS_SPACE = 0, CSS_COMMENT, CSS_STRING, CSS_AT_RULE, CSS_SELECTOR,
  CSS_VALUE, CSS_UNIT, CSS_COLOR, CSS_URL, CSS_ANY
};

/*****************************************************************************/


#line 30 "css.h"
static const char _css_actions[] = {
	0, 1, 0, 1, 1, 1, 6, 1, 
	7, 1, 9, 1, 10, 1, 11, 1, 
	12, 1, 14, 1, 15, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 23, 1, 
	24, 1, 25, 1, 26, 2, 3, 2, 
	2, 4, 2, 2, 5, 2, 2, 7, 
	16, 2, 8, 17, 2, 10, 22, 2, 
	13, 8, 2, 13, 10, 3, 3, 2, 
	1, 3, 4, 2, 0, 3, 4, 2, 
	15, 3, 5, 2, 0, 3, 5, 2, 
	15, 3, 13, 0, 8
};

static const char _css_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 2, 2, 
	3, 4, 4, 4, 5, 6, 7, 7, 
	7, 7, 7, 7, 8, 8, 9, 10, 
	10
};

static const char _css_cond_lengths[] = {
	0, 0, 0, 1, 1, 0, 0, 1, 
	1, 0, 0, 1, 1, 1, 0, 0, 
	0, 0, 0, 1, 0, 1, 1, 0, 
	0
};

static const short _css_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 0
};

static const char _css_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const char _css_key_offsets[] = {
	0, 0, 1, 3, 15, 27, 30, 31, 
	43, 55, 58, 59, 70, 81, 93, 94, 
	95, 99, 102, 103, 116, 118, 130, 142, 
	143
};

static const short _css_trans_keys[] = {
	42, 42, 47, 9, 10, 12, 32, 34, 
	92, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 34, 92, 269, 525, 0, 
	11, 14, 255, 10, 12, 13, 10, 9, 
	10, 12, 32, 39, 92, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	12, 13, 10, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	47, 9, 13, 32, 9, 13, 42, 9, 
	10, 12, 32, 34, 39, 47, 269, 525, 
	0, 8, 14, 255, 9, 32, 9, 10, 
	12, 32, 34, 92, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 39, 92, 
	269, 525, 0, 11, 14, 255, 42, 10, 
	0
};

static const char _css_single_lengths[] = {
	0, 1, 2, 8, 8, 1, 1, 8, 
	8, 1, 1, 7, 7, 8, 1, 1, 
	2, 1, 1, 9, 2, 8, 8, 1, 
	1
};

static const char _css_range_lengths[] = {
	0, 0, 0, 2, 2, 1, 0, 2, 
	2, 1, 0, 2, 2, 2, 0, 0, 
	1, 1, 0, 2, 0, 2, 2, 0, 
	0
};

static const char _css_index_offsets[] = {
	0, 0, 2, 5, 16, 27, 30, 32, 
	43, 54, 57, 59, 69, 79, 90, 92, 
	94, 98, 101, 103, 115, 118, 129, 140, 
	142
};

static const char _css_indicies[] = {
	2, 1, 2, 3, 1, 6, 7, 7, 
	6, 8, 9, 10, 7, 5, 5, 4, 
	12, 13, 13, 12, 14, 15, 16, 13, 
	11, 11, 4, 4, 4, 5, 7, 4, 
	18, 19, 19, 18, 8, 20, 21, 19, 
	17, 17, 4, 23, 24, 24, 23, 25, 
	26, 27, 24, 22, 22, 4, 4, 4, 
	17, 19, 4, 29, 30, 30, 29, 31, 
	32, 30, 28, 28, 4, 34, 35, 35, 
	34, 36, 37, 35, 33, 33, 4, 29, 
	30, 30, 29, 31, 38, 32, 30, 28, 
	28, 4, 30, 4, 39, 40, 42, 43, 
	42, 41, 42, 42, 44, 1, 45, 47, 
	39, 39, 47, 48, 49, 50, 51, 52, 
	46, 46, 40, 47, 47, 53, 6, 7, 
	7, 6, 8, 9, 10, 7, 5, 5, 
	54, 18, 19, 19, 18, 8, 20, 21, 
	19, 17, 17, 54, 28, 54, 39, 55, 
	0
};

static const char _css_trans_targs[] = {
	16, 1, 2, 16, 19, 3, 3, 4, 
	19, 5, 6, 3, 3, 4, 19, 5, 
	6, 7, 7, 8, 9, 10, 7, 7, 
	8, 19, 9, 10, 11, 11, 12, 13, 
	14, 11, 11, 12, 13, 14, 19, 19, 
	0, 16, 17, 18, 16, 16, 19, 20, 
	21, 22, 23, 15, 24, 19, 19, 19
};

static const char _css_trans_actions[] = {
	35, 11, 11, 52, 27, 1, 0, 0, 
	19, 0, 0, 73, 43, 43, 77, 43, 
	43, 1, 0, 0, 0, 0, 65, 40, 
	40, 69, 40, 40, 3, 0, 0, 3, 
	0, 61, 37, 37, 61, 37, 17, 46, 
	0, 29, 9, 58, 31, 33, 49, 5, 
	81, 81, 55, 7, 7, 21, 25, 23
};

static const char _css_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 13, 0, 0, 0, 0, 
	0
};

static const char _css_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 15, 0, 0, 0, 0, 
	0
};

static const char _css_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 0, 
	0, 45, 46, 0, 54, 55, 55, 55, 
	56
};

static const int css_start = 16;
static const int css_first_final = 16;
static const int css_error = 0;

static const int css_en_css_line = 19;
static const int css_en_css_entity = 16;


#line 102 "css.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with CSS code.
 *
 * @param *buffer The string to parse.
 * @param length The length of the string to parse.
 * @param count Integer flag specifying whether or not to count lines. If yes,
 *   uses the Ragel machine optimized for counting. Otherwise uses the Ragel
 *   machine optimized for returning entity positions.
 * @param *callback Callback function. If count is set, callback is called for
 *   every line of code, comment, or blank with 'lcode', 'lcomment', and
 *   'lblank' respectively. Otherwise callback is called for each entity found.
 */
void parse_css(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 215 "css.h"
	{
	cs = css_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 125 "css.rl"
  cs = (count) ? css_en_css_line : css_en_css_entity;
  
#line 226 "css.h"
	{
	int _klen;
	unsigned int _trans;
	short _widec;
	const char *_acts;
	unsigned int _nacts;
	const short *_keys;

	if ( p == pe )
		goto _test_eof;
	if ( cs == 0 )
		goto _out;
_resume:
	_acts = _css_actions + _css_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 248 "css.h"
		}
	}

	_widec = (*p);
	_klen = _css_cond_lengths[cs];
	_keys = _css_cond_keys + (_css_cond_offsets[cs]*2);
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				switch ( _css_cond_spaces[_css_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _css_trans_keys + _css_key_offsets[cs];
	_trans = _css_index_offsets[cs];

	_klen = _css_single_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + _klen - 1;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + ((_upper-_lower) >> 1);
			if ( _widec < *_mid )
				_upper = _mid - 1;
			else if ( _widec > *_mid )
				_lower = _mid + 1;
			else {
				_trans += (unsigned int)(_mid - _keys);
				goto _match;
			}
		}
		_keys += _klen;
		_trans += _klen;
	}

	_klen = _css_range_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				_trans += (unsigned int)((_mid - _keys)>>1);
				goto _match;
			}
		}
		_trans += _klen;
	}

_match:
	_trans = _css_indicies[_trans];
_eof_trans:
	cs = _css_trans_targs[_trans];

	if ( _css_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _css_actions + _css_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 1:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 2:
#line 33 "css.rl"
	{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }
	break;
	case 3:
#line 51 "css.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 60 "css.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 70 "css.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 81 "css.rl"
	{ entity = CSS_SPACE; }
	break;
	case 7:
#line 84 "css.rl"
	{ entity = NEWLINE;   }
	break;
	case 8:
#line 85 "css.rl"
	{ entity = CSS_ANY;   }
	break;
	case 9:
#line 97 "css.rl"
	{ entity = CSS_SPACE;   }
	break;
	case 10:
#line 98 "css.rl"
	{ entity = CSS_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 82 "css.rl"
	{te = p+1;}
	break;
	case 15:
#line 83 "css.rl"
	{te = p+1;}
	break;
	case 16:
#line 33 "css.rl"
	{te = p+1;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 17:
#line 33 "css.rl"
	{te = p+1;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 18:
#line 33 "css.rl"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 19:
#line 33 "css.rl"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 20:
#line 33 "css.rl"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 21:
#line 33 "css.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 22:
#line 90 "css.rl"
	{te = p+1;{
    callback(CSS_LANG, css_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 23:
#line 100 "css.rl"
	{te = p+1;}
	break;
	case 24:
#line 90 "css.rl"
	{te = p;p--;{
    callback(CSS_LANG, css_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 100 "css.rl"
	{te = p;p--;}
	break;
	case 26:
#line 100 "css.rl"
	{{p = ((te))-1;}}
	break;
#line 555 "css.h"
		}
	}

_again:
	_acts = _css_actions + _css_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 568 "css.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _css_eof_trans[cs] > 0 ) {
		_trans = _css_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 127 "css.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(CSS_LANG) }
}

#endif

/*****************************************************************************/
