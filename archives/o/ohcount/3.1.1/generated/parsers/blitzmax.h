
#line 1 "blitzmax.rl"
// blitzmax.rl written by Bruce A Henderson (http://brucey.net)

/************************* Required for every parser *************************/
#ifndef OHCOUNT_BLITZMAX_PARSER_H
#define OHCOUNT_BLITZMAX_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *BLITZMAX_LANG = LANG_BLITZMAX;

// the languages entities
const char *blitzmax_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  BLITZMAX_SPACE = 0, BLITZMAX_COMMENT, BLITZMAX_STRING, BLITZMAX_ANY
};

/*****************************************************************************/


#line 28 "blitzmax.h"
static const char _blitzmax_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 21, 1, 
	22, 1, 23, 2, 1, 6, 2, 3, 
	2, 2, 5, 14, 2, 6, 15, 2, 
	11, 6, 3, 3, 2, 1, 3, 11, 
	0, 6
};

static const char _blitzmax_cond_offsets[] = {
	0, 0, 0, 0, 0, 1, 2, 3, 
	4, 5, 6, 7, 8, 8, 8, 8, 
	8, 8, 9, 9, 9, 9, 9
};

static const char _blitzmax_cond_lengths[] = {
	0, 0, 0, 0, 1, 1, 1, 1, 
	1, 1, 1, 1, 0, 0, 0, 0, 
	0, 1, 0, 0, 0, 0, 0
};

static const short _blitzmax_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 0
};

static const char _blitzmax_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const char _blitzmax_key_offsets[] = {
	0, 0, 5, 8, 10, 22, 34, 48, 
	62, 76, 90, 102, 118, 119, 120, 124, 
	127, 130, 144, 146, 151, 154, 156
};

static const short _blitzmax_trans_keys[] = {
	10, 34, 92, 12, 13, 10, 12, 13, 
	77, 109, 9, 10, 12, 32, 69, 101, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 69, 101, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 69, 78, 
	101, 110, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 68, 69, 100, 101, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 69, 82, 101, 114, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	69, 82, 101, 114, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 69, 101, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 69, 77, 78, 101, 109, 110, 
	269, 525, 0, 11, 14, 255, 10, 10, 
	32, 39, 9, 13, 32, 9, 13, 10, 
	12, 13, 9, 10, 12, 32, 34, 39, 
	82, 114, 269, 525, 0, 8, 14, 255, 
	9, 32, 10, 34, 92, 12, 13, 10, 
	12, 13, 69, 101, 10, 0
};

static const char _blitzmax_single_lengths[] = {
	0, 3, 1, 2, 8, 8, 10, 10, 
	10, 10, 8, 12, 1, 1, 2, 1, 
	1, 10, 2, 3, 1, 2, 1
};

static const char _blitzmax_range_lengths[] = {
	0, 1, 1, 0, 2, 2, 2, 2, 
	2, 2, 2, 2, 0, 0, 1, 1, 
	1, 2, 0, 1, 1, 0, 0
};

static const char _blitzmax_index_offsets[] = {
	0, 0, 5, 8, 11, 22, 33, 46, 
	59, 72, 85, 96, 111, 113, 115, 119, 
	122, 125, 138, 141, 146, 149, 152
};

static const char _blitzmax_indicies[] = {
	0, 2, 3, 0, 1, 0, 0, 1, 
	4, 4, 0, 5, 6, 6, 5, 7, 
	7, 8, 6, 4, 4, 0, 10, 11, 
	11, 10, 12, 12, 13, 11, 9, 9, 
	0, 5, 6, 6, 5, 7, 14, 7, 
	14, 8, 6, 4, 4, 0, 5, 6, 
	6, 5, 15, 7, 15, 7, 8, 6, 
	4, 4, 0, 5, 6, 6, 16, 7, 
	17, 7, 17, 8, 6, 4, 4, 0, 
	5, 6, 6, 5, 7, 17, 7, 17, 
	8, 6, 4, 4, 0, 5, 6, 6, 
	5, 18, 18, 8, 6, 4, 4, 0, 
	5, 6, 6, 5, 7, 19, 14, 7, 
	19, 14, 8, 6, 4, 4, 0, 6, 
	0, 20, 21, 23, 24, 23, 22, 23, 
	23, 25, 26, 26, 24, 28, 20, 20, 
	28, 29, 30, 31, 31, 32, 33, 27, 
	27, 21, 28, 28, 34, 35, 2, 3, 
	35, 1, 36, 36, 37, 38, 38, 35, 
	20, 39, 0
};

static const char _blitzmax_trans_targs[] = {
	17, 1, 17, 2, 4, 4, 5, 6, 
	12, 4, 4, 5, 6, 12, 7, 8, 
	9, 10, 11, 17, 17, 0, 14, 15, 
	16, 14, 14, 17, 18, 19, 20, 21, 
	13, 22, 17, 17, 17, 20, 3, 17
};

static const char _blitzmax_trans_actions[] = {
	27, 0, 17, 0, 1, 0, 0, 1, 
	0, 50, 38, 38, 50, 38, 1, 1, 
	0, 1, 1, 15, 41, 0, 29, 7, 
	9, 31, 33, 44, 3, 54, 35, 47, 
	5, 5, 19, 25, 21, 0, 0, 23
};

static const char _blitzmax_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 11, 0, 
	0, 11, 0, 0, 0, 0, 0
};

static const char _blitzmax_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 13, 0, 0, 0, 0, 0
};

static const char _blitzmax_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 1, 1, 0, 0, 26, 
	27, 0, 35, 36, 37, 36, 40
};

static const int blitzmax_start = 14;
static const int blitzmax_first_final = 14;
static const int blitzmax_error = 0;

static const int blitzmax_en_blitzmax_line = 17;
static const int blitzmax_en_blitzmax_entity = 14;


#line 94 "blitzmax.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with BlitzMax code.
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
void parse_blitzmax(char *buffer, int length, int count,
                    void (*callback) (const char *lang, const char *entity,
                                      int s, int e, void *udata),
                    void *userdata
  ) {
  init

  
#line 199 "blitzmax.h"
	{
	cs = blitzmax_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 117 "blitzmax.rl"
  cs = (count) ? blitzmax_en_blitzmax_line : blitzmax_en_blitzmax_entity;
  
#line 210 "blitzmax.h"
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
	_acts = _blitzmax_actions + _blitzmax_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 232 "blitzmax.h"
		}
	}

	_widec = (*p);
	_klen = _blitzmax_cond_lengths[cs];
	_keys = _blitzmax_cond_keys + (_blitzmax_cond_offsets[cs]*2);
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
				switch ( _blitzmax_cond_spaces[_blitzmax_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _blitzmax_trans_keys + _blitzmax_key_offsets[cs];
	_trans = _blitzmax_index_offsets[cs];

	_klen = _blitzmax_single_lengths[cs];
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

	_klen = _blitzmax_range_lengths[cs];
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
	_trans = _blitzmax_indicies[_trans];
_eof_trans:
	cs = _blitzmax_trans_targs[_trans];

	if ( _blitzmax_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _blitzmax_actions + _blitzmax_trans_actions[_trans];
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
#line 31 "blitzmax.rl"
	{
    switch(entity) {
    case BLITZMAX_SPACE:
      ls
      break;
    case BLITZMAX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BLITZMAX_LANG)
      break;
    case NEWLINE:
      std_newline(BLITZMAX_LANG)
    }
  }
	break;
	case 3:
#line 50 "blitzmax.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 62 "blitzmax.rl"
	{ entity = BLITZMAX_SPACE; }
	break;
	case 5:
#line 65 "blitzmax.rl"
	{ entity = NEWLINE;      }
	break;
	case 6:
#line 66 "blitzmax.rl"
	{ entity = BLITZMAX_ANY;   }
	break;
	case 7:
#line 89 "blitzmax.rl"
	{ entity = BLITZMAX_SPACE;   }
	break;
	case 8:
#line 90 "blitzmax.rl"
	{ entity = BLITZMAX_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 63 "blitzmax.rl"
	{te = p+1;}
	break;
	case 13:
#line 64 "blitzmax.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "blitzmax.rl"
	{te = p+1;{
    switch(entity) {
    case BLITZMAX_SPACE:
      ls
      break;
    case BLITZMAX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BLITZMAX_LANG)
      break;
    case NEWLINE:
      std_newline(BLITZMAX_LANG)
    }
  }}
	break;
	case 15:
#line 31 "blitzmax.rl"
	{te = p+1;{
    switch(entity) {
    case BLITZMAX_SPACE:
      ls
      break;
    case BLITZMAX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BLITZMAX_LANG)
      break;
    case NEWLINE:
      std_newline(BLITZMAX_LANG)
    }
  }}
	break;
	case 16:
#line 31 "blitzmax.rl"
	{te = p;p--;{
    switch(entity) {
    case BLITZMAX_SPACE:
      ls
      break;
    case BLITZMAX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BLITZMAX_LANG)
      break;
    case NEWLINE:
      std_newline(BLITZMAX_LANG)
    }
  }}
	break;
	case 17:
#line 63 "blitzmax.rl"
	{te = p;p--;}
	break;
	case 18:
#line 31 "blitzmax.rl"
	{te = p;p--;{
    switch(entity) {
    case BLITZMAX_SPACE:
      ls
      break;
    case BLITZMAX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BLITZMAX_LANG)
      break;
    case NEWLINE:
      std_newline(BLITZMAX_LANG)
    }
  }}
	break;
	case 19:
#line 31 "blitzmax.rl"
	{te = p;p--;{
    switch(entity) {
    case BLITZMAX_SPACE:
      ls
      break;
    case BLITZMAX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BLITZMAX_LANG)
      break;
    case NEWLINE:
      std_newline(BLITZMAX_LANG)
    }
  }}
	break;
	case 20:
#line 31 "blitzmax.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case BLITZMAX_SPACE:
      ls
      break;
    case BLITZMAX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BLITZMAX_LANG)
      break;
    case NEWLINE:
      std_newline(BLITZMAX_LANG)
    }
  }}
	break;
	case 21:
#line 92 "blitzmax.rl"
	{te = p+1;}
	break;
	case 22:
#line 71 "blitzmax.rl"
	{te = p;p--;{
    callback(BLITZMAX_LANG, blitzmax_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 23:
#line 71 "blitzmax.rl"
	{te = p;p--;{
    callback(BLITZMAX_LANG, blitzmax_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
#line 529 "blitzmax.h"
		}
	}

_again:
	_acts = _blitzmax_actions + _blitzmax_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 542 "blitzmax.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _blitzmax_eof_trans[cs] > 0 ) {
		_trans = _blitzmax_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 119 "blitzmax.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(BLITZMAX_LANG) }
}

#endif

/*****************************************************************************/
