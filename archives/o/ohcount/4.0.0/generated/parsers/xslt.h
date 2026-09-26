
#line 1 "xslt.rl"
// xslt.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_XSLT_PARSER_H
#define OHCOUNT_XSLT_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *XSLT_LANG = LANG_XSLT;

// the languages entities
const char *xslt_entities[] = {
  "space", "comment", "doctype",
  "tag", "entity", "any"
};

// constants associated with the entities
enum {
  XSLT_SPACE = 0, XSLT_COMMENT, XSLT_DOCTYPE,
  XSLT_TAG, XSLT_ENTITY, XSLT_ANY
};

/*****************************************************************************/


#line 30 "xslt.h"
static const char _xslt_actions[] = {
	0, 1, 0, 1, 1, 1, 5, 1, 
	6, 1, 8, 1, 9, 1, 10, 1, 
	11, 1, 13, 1, 14, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 22, 1, 
	23, 1, 24, 1, 25, 2, 0, 14, 
	2, 3, 2, 2, 4, 2, 2, 6, 
	15, 2, 7, 16, 2, 9, 21, 2, 
	12, 7, 2, 12, 9, 3, 3, 2, 
	1, 3, 4, 2, 0
};

static const char _xslt_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 2, 3, 
	4, 4, 4, 4, 4, 4, 4, 4, 
	5, 6, 7, 8, 8, 8, 8, 8, 
	8, 9, 9, 9, 9, 9
};

static const char _xslt_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 1, 1, 1, 1, 
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 1, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0
};

static const short _xslt_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 0
};

static const char _xslt_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const char _xslt_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 6, 11, 
	14, 19, 22, 24, 25, 36, 47, 58, 
	70, 71, 72, 73, 74, 75, 76, 77, 
	88, 99, 110, 122, 123, 124, 128, 131, 
	132, 145, 147, 152, 157, 158
};

static const short _xslt_trans_keys[] = {
	45, 45, 45, 45, 45, 62, 10, 34, 
	92, 12, 13, 10, 12, 13, 10, 39, 
	92, 12, 13, 10, 12, 13, 45, 91, 
	45, 9, 10, 12, 32, 45, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	45, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 45, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 45, 62, 
	269, 525, 0, 11, 14, 255, 10, 67, 
	68, 65, 84, 65, 91, 9, 10, 12, 
	32, 93, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 93, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 93, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 62, 93, 269, 525, 0, 11, 
	14, 255, 10, 10, 32, 60, 9, 13, 
	32, 9, 13, 33, 9, 10, 12, 32, 
	34, 39, 60, 269, 525, 0, 8, 14, 
	255, 9, 32, 10, 34, 92, 12, 13, 
	10, 39, 92, 12, 13, 33, 10, 0
};

static const char _xslt_single_lengths[] = {
	0, 1, 1, 1, 1, 2, 3, 1, 
	3, 1, 2, 1, 7, 7, 7, 8, 
	1, 1, 1, 1, 1, 1, 1, 7, 
	7, 7, 8, 1, 1, 2, 1, 1, 
	9, 2, 3, 3, 1, 1
};

static const char _xslt_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 1, 1, 
	1, 1, 0, 0, 2, 2, 2, 2, 
	0, 0, 0, 0, 0, 0, 0, 2, 
	2, 2, 2, 0, 0, 1, 1, 0, 
	2, 0, 1, 1, 0, 0
};

static const char _xslt_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 11, 16, 
	19, 24, 27, 30, 32, 42, 52, 62, 
	73, 75, 77, 79, 81, 83, 85, 87, 
	97, 107, 117, 128, 130, 132, 136, 139, 
	141, 153, 156, 161, 166, 168
};

static const char _xslt_indicies[] = {
	1, 0, 2, 0, 3, 2, 4, 2, 
	4, 5, 2, 6, 8, 9, 6, 7, 
	6, 6, 7, 6, 8, 11, 6, 10, 
	6, 6, 10, 12, 13, 6, 14, 6, 
	15, 16, 16, 15, 17, 18, 16, 14, 
	14, 6, 20, 21, 21, 20, 22, 23, 
	21, 19, 19, 6, 15, 16, 16, 15, 
	24, 18, 16, 14, 14, 6, 15, 16, 
	16, 15, 24, 25, 18, 16, 14, 14, 
	6, 16, 6, 26, 6, 27, 6, 28, 
	6, 29, 6, 30, 6, 31, 6, 32, 
	33, 33, 32, 34, 35, 33, 31, 31, 
	6, 37, 38, 38, 37, 39, 40, 38, 
	36, 36, 6, 32, 33, 33, 32, 41, 
	35, 33, 31, 31, 6, 32, 33, 33, 
	32, 42, 41, 35, 33, 31, 31, 6, 
	33, 6, 43, 44, 46, 47, 46, 45, 
	46, 46, 48, 50, 49, 52, 43, 43, 
	52, 53, 54, 55, 56, 57, 51, 51, 
	44, 52, 52, 58, 59, 8, 9, 59, 
	7, 59, 8, 11, 59, 10, 60, 59, 
	43, 61, 0
};

static const char _xslt_trans_targs[] = {
	29, 2, 3, 4, 5, 29, 32, 6, 
	32, 7, 8, 9, 11, 17, 12, 12, 
	13, 14, 16, 12, 12, 13, 14, 16, 
	15, 32, 18, 19, 20, 21, 22, 23, 
	23, 24, 25, 27, 23, 23, 24, 25, 
	27, 26, 32, 32, 0, 29, 30, 31, 
	29, 29, 1, 32, 33, 34, 35, 36, 
	28, 37, 32, 32, 10, 32
};

static const char _xslt_trans_actions[] = {
	35, 11, 11, 11, 11, 52, 27, 0, 
	37, 0, 0, 0, 0, 0, 3, 0, 
	0, 3, 0, 61, 40, 40, 61, 40, 
	3, 17, 0, 0, 0, 0, 0, 1, 
	0, 0, 1, 0, 65, 43, 43, 65, 
	43, 1, 19, 46, 0, 29, 9, 58, 
	31, 33, 11, 49, 5, 55, 55, 55, 
	7, 7, 21, 25, 0, 23
};

static const char _xslt_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 13, 0, 0, 
	13, 0, 0, 0, 0, 0
};

static const char _xslt_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 15, 0, 0, 
	15, 0, 0, 0, 0, 0
};

static const char _xslt_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 7, 
	7, 7, 7, 7, 0, 0, 49, 50, 
	0, 59, 60, 60, 60, 62
};

static const int xslt_start = 29;
static const int xslt_first_final = 29;
static const int xslt_error = 0;

static const int xslt_en_xslt_line = 32;
static const int xslt_en_xslt_entity = 29;


#line 95 "xslt.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with XSLT markup.
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
void parse_xslt(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 228 "xslt.h"
	{
	cs = xslt_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 118 "xslt.rl"
  cs = (count) ? xslt_en_xslt_line : xslt_en_xslt_entity;
  
#line 239 "xslt.h"
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
	_acts = _xslt_actions + _xslt_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 261 "xslt.h"
		}
	}

	_widec = (*p);
	_klen = _xslt_cond_lengths[cs];
	_keys = _xslt_cond_keys + (_xslt_cond_offsets[cs]*2);
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
				switch ( _xslt_cond_spaces[_xslt_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _xslt_trans_keys + _xslt_key_offsets[cs];
	_trans = _xslt_index_offsets[cs];

	_klen = _xslt_single_lengths[cs];
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

	_klen = _xslt_range_lengths[cs];
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
	_trans = _xslt_indicies[_trans];
_eof_trans:
	cs = _xslt_trans_targs[_trans];

	if ( _xslt_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _xslt_actions + _xslt_trans_actions[_trans];
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
#line 33 "xslt.rl"
	{
    switch(entity) {
    case XSLT_SPACE:
      ls
      break;
    case XSLT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XSLT_LANG)
      break;
    case NEWLINE:
      std_newline(XSLT_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XSLT_LANG)
    }
  }
	break;
	case 3:
#line 54 "xslt.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 65 "xslt.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 74 "xslt.rl"
	{ entity = XSLT_SPACE; }
	break;
	case 6:
#line 77 "xslt.rl"
	{ entity = NEWLINE;    }
	break;
	case 7:
#line 78 "xslt.rl"
	{ entity = XSLT_ANY;   }
	break;
	case 8:
#line 90 "xslt.rl"
	{ entity = XSLT_SPACE;   }
	break;
	case 9:
#line 91 "xslt.rl"
	{ entity = XSLT_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 75 "xslt.rl"
	{te = p+1;}
	break;
	case 14:
#line 76 "xslt.rl"
	{te = p+1;}
	break;
	case 15:
#line 33 "xslt.rl"
	{te = p+1;{
    switch(entity) {
    case XSLT_SPACE:
      ls
      break;
    case XSLT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XSLT_LANG)
      break;
    case NEWLINE:
      std_newline(XSLT_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XSLT_LANG)
    }
  }}
	break;
	case 16:
#line 33 "xslt.rl"
	{te = p+1;{
    switch(entity) {
    case XSLT_SPACE:
      ls
      break;
    case XSLT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XSLT_LANG)
      break;
    case NEWLINE:
      std_newline(XSLT_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XSLT_LANG)
    }
  }}
	break;
	case 17:
#line 33 "xslt.rl"
	{te = p;p--;{
    switch(entity) {
    case XSLT_SPACE:
      ls
      break;
    case XSLT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XSLT_LANG)
      break;
    case NEWLINE:
      std_newline(XSLT_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XSLT_LANG)
    }
  }}
	break;
	case 18:
#line 33 "xslt.rl"
	{te = p;p--;{
    switch(entity) {
    case XSLT_SPACE:
      ls
      break;
    case XSLT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XSLT_LANG)
      break;
    case NEWLINE:
      std_newline(XSLT_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XSLT_LANG)
    }
  }}
	break;
	case 19:
#line 33 "xslt.rl"
	{te = p;p--;{
    switch(entity) {
    case XSLT_SPACE:
      ls
      break;
    case XSLT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XSLT_LANG)
      break;
    case NEWLINE:
      std_newline(XSLT_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XSLT_LANG)
    }
  }}
	break;
	case 20:
#line 33 "xslt.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case XSLT_SPACE:
      ls
      break;
    case XSLT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XSLT_LANG)
      break;
    case NEWLINE:
      std_newline(XSLT_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XSLT_LANG)
    }
  }}
	break;
	case 21:
#line 83 "xslt.rl"
	{te = p+1;{
    callback(XSLT_LANG, xslt_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 93 "xslt.rl"
	{te = p+1;}
	break;
	case 23:
#line 83 "xslt.rl"
	{te = p;p--;{
    callback(XSLT_LANG, xslt_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 93 "xslt.rl"
	{te = p;p--;}
	break;
	case 25:
#line 93 "xslt.rl"
	{{p = ((te))-1;}}
	break;
#line 585 "xslt.h"
		}
	}

_again:
	_acts = _xslt_actions + _xslt_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 598 "xslt.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _xslt_eof_trans[cs] > 0 ) {
		_trans = _xslt_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 120 "xslt.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(XSLT_LANG) }
}

#endif

/*****************************************************************************/
