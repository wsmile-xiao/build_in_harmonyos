
#line 1 "haskell.rl"
// haskell.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_HASKELL_PARSER_H
#define OHCOUNT_HASKELL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *HASKELL_LANG = LANG_HASKELL;

// the languages entities
const char *haskell_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  HASKELL_SPACE = 0, HASKELL_COMMENT, HASKELL_STRING, HASKELL_ANY
};

/*****************************************************************************/


#line 28 "haskell.h"
static const char _haskell_actions[] = {
	0, 1, 0, 1, 1, 1, 9, 1, 
	10, 1, 13, 1, 14, 1, 15, 1, 
	16, 1, 19, 1, 22, 1, 23, 1, 
	24, 1, 25, 1, 26, 1, 28, 1, 
	29, 1, 30, 1, 31, 1, 32, 2, 
	1, 18, 2, 4, 1, 2, 4, 14, 
	2, 5, 1, 2, 5, 14, 2, 6, 
	1, 2, 7, 2, 2, 8, 2, 2, 
	10, 20, 2, 11, 21, 2, 12, 14, 
	2, 14, 27, 2, 17, 11, 2, 17, 
	14, 3, 7, 2, 1, 3, 8, 2, 
	0, 3, 8, 2, 19, 3, 17, 0, 
	11, 3, 17, 3, 11, 3, 17, 3, 
	14
};

static const char _haskell_cond_offsets[] = {
	0, 0, 0, 1, 2, 3, 5, 5, 
	6, 6, 6, 6, 6, 6, 6, 8, 
	10, 12, 12, 14, 17, 17, 17, 17, 
	17, 17, 17, 18, 18, 18, 18, 18, 
	18, 18
};

static const char _haskell_cond_lengths[] = {
	0, 0, 1, 1, 1, 2, 0, 1, 
	0, 0, 0, 0, 0, 0, 2, 2, 
	2, 0, 2, 3, 0, 0, 0, 0, 
	0, 0, 1, 0, 0, 0, 0, 0, 
	0, 0
};

static const short _haskell_cond_keys[] = {
	45, 45, 45, 45, 45, 45, 45, 45, 
	125, 125, 13, 13, 13, 13, 45, 45, 
	13, 13, 45, 45, 13, 13, 45, 45, 
	13, 13, 45, 45, 13, 13, 45, 45, 
	125, 125, 13, 13, 0
};

static const char _haskell_cond_spaces[] = {
	2, 2, 2, 2, 2, 0, 0, 1, 
	0, 1, 0, 1, 0, 1, 0, 1, 
	1, 0, 0
};

static const char _haskell_key_offsets[] = {
	0, 0, 1, 8, 15, 23, 34, 38, 
	46, 50, 51, 56, 57, 60, 61, 76, 
	91, 106, 107, 123, 142, 143, 148, 151, 
	152, 155, 156, 170, 172, 176, 181, 182, 
	185, 186
};

static const short _haskell_trans_keys[] = {
	62, 123, 1325, 1581, 0, 44, 46, 255, 
	123, 1325, 1581, 0, 44, 46, 255, 123, 
	125, 1325, 1581, 0, 44, 46, 255, 123, 
	1325, 1405, 1581, 1661, 0, 44, 46, 124, 
	126, 255, 9, 32, 34, 92, 10, 12, 
	269, 525, 0, 11, 14, 255, 9, 32, 
	34, 92, 10, 9, 10, 32, 34, 92, 
	39, 10, 12, 13, 62, 9, 10, 12, 
	32, 123, 269, 525, 813, 1069, 0, 11, 
	14, 44, 46, 255, 9, 10, 12, 32, 
	123, 269, 525, 813, 1069, 0, 11, 14, 
	44, 46, 255, 9, 10, 12, 32, 123, 
	269, 525, 813, 1069, 0, 11, 14, 44, 
	46, 255, 10, 9, 10, 12, 32, 123, 
	125, 269, 525, 813, 1069, 0, 11, 14, 
	44, 46, 255, 9, 10, 12, 32, 123, 
	269, 525, 813, 893, 1069, 1149, 0, 11, 
	14, 44, 46, 124, 126, 255, 10, 32, 
	45, 123, 9, 13, 32, 9, 13, 45, 
	10, 12, 13, 45, 9, 10, 12, 32, 
	34, 39, 45, 123, 269, 525, 0, 8, 
	14, 255, 9, 32, 9, 32, 34, 92, 
	10, 39, 92, 12, 13, 45, 10, 12, 
	13, 45, 10, 0
};

static const char _haskell_single_lengths[] = {
	0, 1, 3, 3, 4, 5, 4, 4, 
	4, 1, 5, 1, 1, 1, 9, 9, 
	9, 1, 10, 11, 1, 3, 1, 1, 
	1, 1, 10, 2, 4, 3, 1, 1, 
	1, 1
};

static const char _haskell_range_lengths[] = {
	0, 0, 2, 2, 2, 3, 0, 2, 
	0, 0, 0, 0, 1, 0, 3, 3, 
	3, 0, 3, 4, 0, 1, 1, 0, 
	1, 0, 2, 0, 0, 1, 0, 1, 
	0, 0
};

static const char _haskell_index_offsets[] = {
	0, 0, 2, 8, 14, 21, 30, 35, 
	42, 47, 49, 55, 57, 60, 62, 75, 
	88, 101, 103, 117, 133, 135, 140, 143, 
	145, 148, 150, 163, 166, 171, 176, 178, 
	181, 183
};

static const char _haskell_indicies[] = {
	0, 1, 3, 4, 5, 2, 2, 0, 
	3, 6, 7, 2, 2, 0, 3, 8, 
	4, 5, 2, 2, 0, 3, 4, 8, 
	5, 9, 2, 2, 2, 0, 12, 12, 
	13, 14, 11, 15, 15, 16, 17, 11, 
	11, 10, 19, 19, 20, 21, 18, 15, 
	10, 19, 22, 19, 20, 21, 18, 13, 
	10, 10, 10, 23, 10, 24, 26, 27, 
	27, 26, 28, 29, 27, 30, 31, 25, 
	25, 25, 10, 33, 34, 34, 33, 35, 
	36, 34, 37, 38, 32, 32, 32, 10, 
	26, 27, 27, 26, 28, 29, 27, 39, 
	40, 25, 25, 25, 10, 27, 10, 26, 
	27, 27, 26, 28, 41, 29, 27, 30, 
	31, 25, 25, 25, 10, 26, 27, 27, 
	26, 28, 29, 27, 30, 41, 31, 42, 
	25, 25, 25, 25, 10, 43, 44, 46, 
	47, 48, 46, 45, 46, 46, 49, 51, 
	50, 52, 52, 53, 2, 50, 55, 43, 
	43, 55, 56, 57, 58, 59, 60, 61, 
	54, 54, 44, 55, 55, 62, 12, 12, 
	13, 14, 11, 63, 63, 64, 63, 23, 
	65, 63, 66, 66, 67, 25, 63, 43, 
	68, 0
};

static const char _haskell_trans_targs[] = {
	21, 24, 2, 3, 4, 5, 4, 5, 
	2, 21, 26, 6, 6, 26, 7, 8, 
	9, 10, 6, 6, 26, 7, 8, 11, 
	31, 14, 14, 15, 16, 17, 18, 19, 
	14, 14, 15, 16, 17, 18, 19, 18, 
	19, 14, 26, 26, 0, 21, 22, 23, 
	25, 21, 21, 1, 21, 24, 26, 27, 
	28, 29, 30, 32, 20, 33, 26, 26, 
	12, 13, 26, 31, 26
};

static const char _haskell_trans_actions[] = {
	37, 69, 11, 11, 11, 11, 45, 45, 
	51, 72, 27, 1, 0, 17, 0, 0, 
	0, 0, 85, 60, 89, 60, 85, 0, 
	54, 3, 0, 0, 3, 0, 3, 3, 
	81, 57, 57, 81, 57, 81, 81, 42, 
	42, 48, 39, 63, 0, 29, 9, 78, 
	101, 31, 35, 11, 33, 11, 66, 5, 
	93, 93, 75, 97, 7, 7, 19, 25, 
	0, 0, 21, 0, 23
};

static const char _haskell_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 13, 0, 0, 
	0, 0, 13, 0, 0, 0, 0, 0, 
	0, 0
};

static const char _haskell_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 15, 0, 0, 
	0, 0, 15, 0, 0, 0, 0, 0, 
	0, 0
};

static const char _haskell_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 11, 11, 
	11, 11, 11, 11, 11, 11, 11, 11, 
	11, 11, 11, 11, 0, 0, 50, 51, 
	53, 51, 0, 63, 64, 64, 64, 67, 
	64, 69
};

static const int haskell_start = 21;
static const int haskell_first_final = 21;
static const int haskell_error = 0;

static const int haskell_en_haskell_line = 26;
static const int haskell_en_haskell_entity = 21;


#line 112 "haskell.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Haskell code.
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
void parse_haskell(char *buffer, int length, int count,
                   void (*callback) (const char *lang, const char *entity,
                                     int s, int e, void *udata),
                   void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 244 "haskell.h"
	{
	cs = haskell_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 137 "haskell.rl"
  cs = (count) ? haskell_en_haskell_line : haskell_en_haskell_entity;
  
#line 255 "haskell.h"
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
	_acts = _haskell_actions + _haskell_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 16:
#line 1 "NONE"
	{ts = p;}
	break;
#line 277 "haskell.h"
		}
	}

	_widec = (*p);
	_klen = _haskell_cond_lengths[cs];
	_keys = _haskell_cond_keys + (_haskell_cond_offsets[cs]*2);
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
				switch ( _haskell_cond_spaces[_haskell_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
	case 1: {
		_widec = (short)(768 + ((*p) - 0));
		if ( 
#line 64 "haskell.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 102 "haskell.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _haskell_trans_keys + _haskell_key_offsets[cs];
	_trans = _haskell_index_offsets[cs];

	_klen = _haskell_single_lengths[cs];
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

	_klen = _haskell_range_lengths[cs];
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
	_trans = _haskell_indicies[_trans];
_eof_trans:
	cs = _haskell_trans_targs[_trans];

	if ( _haskell_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _haskell_actions + _haskell_trans_actions[_trans];
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
#line 31 "haskell.rl"
	{
    switch(entity) {
    case HASKELL_SPACE:
      ls
      break;
    case HASKELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HASKELL_LANG)
      break;
    case NEWLINE:
      std_newline(HASKELL_LANG)
    }
  }
	break;
	case 3:
#line 47 "haskell.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 48 "haskell.rl"
	{ nest_count++; }
	break;
	case 5:
#line 49 "haskell.rl"
	{ nest_count--; }
	break;
	case 6:
#line 52 "haskell.rl"
	{ p--; }
	break;
	case 7:
#line 55 "haskell.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 70 "haskell.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 81 "haskell.rl"
	{ entity = HASKELL_SPACE; }
	break;
	case 10:
#line 84 "haskell.rl"
	{ entity = NEWLINE;       }
	break;
	case 11:
#line 85 "haskell.rl"
	{ entity = HASKELL_ANY;   }
	break;
	case 12:
#line 95 "haskell.rl"
	{ p--; }
	break;
	case 13:
#line 107 "haskell.rl"
	{ entity = HASKELL_SPACE;   }
	break;
	case 14:
#line 108 "haskell.rl"
	{ entity = HASKELL_COMMENT; }
	break;
	case 17:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 18:
#line 82 "haskell.rl"
	{te = p+1;}
	break;
	case 19:
#line 83 "haskell.rl"
	{te = p+1;}
	break;
	case 20:
#line 31 "haskell.rl"
	{te = p+1;{
    switch(entity) {
    case HASKELL_SPACE:
      ls
      break;
    case HASKELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HASKELL_LANG)
      break;
    case NEWLINE:
      std_newline(HASKELL_LANG)
    }
  }}
	break;
	case 21:
#line 31 "haskell.rl"
	{te = p+1;{
    switch(entity) {
    case HASKELL_SPACE:
      ls
      break;
    case HASKELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HASKELL_LANG)
      break;
    case NEWLINE:
      std_newline(HASKELL_LANG)
    }
  }}
	break;
	case 22:
#line 31 "haskell.rl"
	{te = p;p--;{
    switch(entity) {
    case HASKELL_SPACE:
      ls
      break;
    case HASKELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HASKELL_LANG)
      break;
    case NEWLINE:
      std_newline(HASKELL_LANG)
    }
  }}
	break;
	case 23:
#line 82 "haskell.rl"
	{te = p;p--;}
	break;
	case 24:
#line 31 "haskell.rl"
	{te = p;p--;{
    switch(entity) {
    case HASKELL_SPACE:
      ls
      break;
    case HASKELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HASKELL_LANG)
      break;
    case NEWLINE:
      std_newline(HASKELL_LANG)
    }
  }}
	break;
	case 25:
#line 31 "haskell.rl"
	{te = p;p--;{
    switch(entity) {
    case HASKELL_SPACE:
      ls
      break;
    case HASKELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HASKELL_LANG)
      break;
    case NEWLINE:
      std_newline(HASKELL_LANG)
    }
  }}
	break;
	case 26:
#line 31 "haskell.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case HASKELL_SPACE:
      ls
      break;
    case HASKELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HASKELL_LANG)
      break;
    case NEWLINE:
      std_newline(HASKELL_LANG)
    }
  }}
	break;
	case 27:
#line 90 "haskell.rl"
	{te = p+1;{
    callback(HASKELL_LANG, haskell_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 28:
#line 110 "haskell.rl"
	{te = p+1;}
	break;
	case 29:
#line 90 "haskell.rl"
	{te = p;p--;{
    callback(HASKELL_LANG, haskell_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 30:
#line 90 "haskell.rl"
	{te = p;p--;{
    callback(HASKELL_LANG, haskell_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 31:
#line 110 "haskell.rl"
	{te = p;p--;}
	break;
	case 32:
#line 110 "haskell.rl"
	{{p = ((te))-1;}}
	break;
#line 627 "haskell.h"
		}
	}

_again:
	_acts = _haskell_actions + _haskell_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 15:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 640 "haskell.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _haskell_eof_trans[cs] > 0 ) {
		_trans = _haskell_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 139 "haskell.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(HASKELL_LANG) }
}

#endif

/*****************************************************************************/
