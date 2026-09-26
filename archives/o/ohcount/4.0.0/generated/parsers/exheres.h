
#line 1 "exheres.rl"
// exheres.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_EXHERES_PARSER_H
#define OHCOUNT_EXHERES_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *EXHERES_LANG = LANG_EXHERES;

// the languages entities
const char *exheres_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  EXHERES_SPACE = 0, EXHERES_COMMENT, EXHERES_STRING, EXHERES_ANY
};

/*****************************************************************************/


#line 28 "exheres.h"
static const char _exheres_actions[] = {
	0, 1, 2, 1, 3, 1, 5, 1, 
	6, 1, 7, 1, 8, 1, 10, 1, 
	13, 1, 14, 1, 15, 1, 16, 1, 
	17, 1, 18, 1, 19, 1, 20, 2, 
	1, 4, 2, 3, 11, 2, 4, 12, 
	3, 9, 0, 4
};

static const char _exheres_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 1, 1, 1, 1
};

static const char _exheres_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 0, 0, 0, 0, 0
};

static const short _exheres_cond_keys[] = {
	13, 13, 0
};

static const char _exheres_cond_spaces[] = {
	0, 0
};

static const char _exheres_key_offsets[] = {
	0, 0, 5, 8, 13, 16, 17, 21, 
	24, 27, 40, 42, 47, 50, 55
};

static const short _exheres_trans_keys[] = {
	10, 34, 92, 12, 13, 10, 12, 13, 
	10, 39, 92, 12, 13, 10, 12, 13, 
	10, 32, 35, 9, 13, 32, 9, 13, 
	10, 12, 13, 9, 10, 12, 32, 34, 
	35, 39, 269, 525, 0, 8, 14, 255, 
	9, 32, 10, 34, 92, 12, 13, 10, 
	12, 13, 10, 39, 92, 12, 13, 10, 
	0
};

static const char _exheres_single_lengths[] = {
	0, 3, 1, 3, 1, 1, 2, 1, 
	1, 9, 2, 3, 1, 3, 1
};

static const char _exheres_range_lengths[] = {
	0, 1, 1, 1, 1, 0, 1, 1, 
	1, 2, 0, 1, 1, 1, 0
};

static const char _exheres_index_offsets[] = {
	0, 0, 5, 8, 13, 16, 18, 22, 
	25, 28, 40, 43, 48, 51, 56
};

static const char _exheres_indicies[] = {
	0, 2, 3, 0, 1, 0, 0, 1, 
	0, 2, 5, 0, 4, 0, 0, 4, 
	6, 7, 9, 10, 9, 8, 9, 9, 
	11, 12, 12, 10, 14, 6, 6, 14, 
	15, 16, 17, 18, 19, 13, 13, 7, 
	14, 14, 20, 21, 2, 3, 21, 1, 
	22, 22, 23, 21, 2, 5, 21, 4, 
	6, 24, 0
};

static const char _exheres_trans_targs[] = {
	9, 1, 9, 2, 3, 4, 9, 0, 
	6, 7, 8, 6, 6, 9, 10, 11, 
	12, 13, 5, 14, 9, 9, 9, 12, 
	9
};

static const char _exheres_trans_actions[] = {
	23, 0, 13, 0, 0, 0, 34, 0, 
	25, 5, 7, 27, 29, 37, 1, 40, 
	31, 40, 3, 3, 15, 21, 17, 0, 
	19
};

static const char _exheres_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 9, 0, 
	0, 9, 0, 0, 0, 0, 0
};

static const char _exheres_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 11, 0, 
	0, 11, 0, 0, 0, 0, 0
};

static const char _exheres_eof_trans[] = {
	0, 1, 1, 1, 1, 0, 0, 12, 
	13, 0, 21, 22, 23, 22, 25
};

static const int exheres_start = 6;
static const int exheres_first_final = 6;
static const int exheres_error = 0;

static const int exheres_en_exheres_line = 9;
static const int exheres_en_exheres_entity = 6;


#line 76 "exheres.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with exheres code.
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
void parse_exheres(char *buffer, int length, int count,
                   void (*callback) (const char *lang, const char *entity,
                                     int s, int e, void *udata),
                   void *userdata
  ) {
  init

  
#line 159 "exheres.h"
	{
	cs = exheres_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 99 "exheres.rl"
  cs = (count) ? exheres_en_exheres_line : exheres_en_exheres_entity;
  
#line 170 "exheres.h"
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
	_acts = _exheres_actions + _exheres_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 192 "exheres.h"
		}
	}

	_widec = (*p);
	_klen = _exheres_cond_lengths[cs];
	_keys = _exheres_cond_keys + (_exheres_cond_offsets[cs]*2);
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
				switch ( _exheres_cond_spaces[_exheres_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _exheres_trans_keys + _exheres_key_offsets[cs];
	_trans = _exheres_index_offsets[cs];

	_klen = _exheres_single_lengths[cs];
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

	_klen = _exheres_range_lengths[cs];
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
	_trans = _exheres_indicies[_trans];
_eof_trans:
	cs = _exheres_trans_targs[_trans];

	if ( _exheres_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _exheres_actions + _exheres_trans_actions[_trans];
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
#line 54 "exheres.rl"
	{ entity = EXHERES_SPACE; }
	break;
	case 3:
#line 57 "exheres.rl"
	{ entity = NEWLINE;       }
	break;
	case 4:
#line 58 "exheres.rl"
	{ entity = EXHERES_ANY;   }
	break;
	case 5:
#line 71 "exheres.rl"
	{ entity = EXHERES_SPACE;   }
	break;
	case 6:
#line 72 "exheres.rl"
	{ entity = EXHERES_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 56 "exheres.rl"
	{te = p+1;}
	break;
	case 11:
#line 31 "exheres.rl"
	{te = p+1;{
    switch(entity) {
    case EXHERES_SPACE:
      ls
      break;
    case EXHERES_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EXHERES_LANG)
      break;
    case NEWLINE:
      std_newline(EXHERES_LANG)
    }
  }}
	break;
	case 12:
#line 31 "exheres.rl"
	{te = p+1;{
    switch(entity) {
    case EXHERES_SPACE:
      ls
      break;
    case EXHERES_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EXHERES_LANG)
      break;
    case NEWLINE:
      std_newline(EXHERES_LANG)
    }
  }}
	break;
	case 13:
#line 31 "exheres.rl"
	{te = p;p--;{
    switch(entity) {
    case EXHERES_SPACE:
      ls
      break;
    case EXHERES_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EXHERES_LANG)
      break;
    case NEWLINE:
      std_newline(EXHERES_LANG)
    }
  }}
	break;
	case 14:
#line 55 "exheres.rl"
	{te = p;p--;}
	break;
	case 15:
#line 31 "exheres.rl"
	{te = p;p--;{
    switch(entity) {
    case EXHERES_SPACE:
      ls
      break;
    case EXHERES_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EXHERES_LANG)
      break;
    case NEWLINE:
      std_newline(EXHERES_LANG)
    }
  }}
	break;
	case 16:
#line 31 "exheres.rl"
	{te = p;p--;{
    switch(entity) {
    case EXHERES_SPACE:
      ls
      break;
    case EXHERES_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EXHERES_LANG)
      break;
    case NEWLINE:
      std_newline(EXHERES_LANG)
    }
  }}
	break;
	case 17:
#line 31 "exheres.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case EXHERES_SPACE:
      ls
      break;
    case EXHERES_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EXHERES_LANG)
      break;
    case NEWLINE:
      std_newline(EXHERES_LANG)
    }
  }}
	break;
	case 18:
#line 74 "exheres.rl"
	{te = p+1;}
	break;
	case 19:
#line 63 "exheres.rl"
	{te = p;p--;{
    callback(EXHERES_LANG, exheres_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 20:
#line 63 "exheres.rl"
	{te = p;p--;{
    callback(EXHERES_LANG, exheres_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
#line 463 "exheres.h"
		}
	}

_again:
	_acts = _exheres_actions + _exheres_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 476 "exheres.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _exheres_eof_trans[cs] > 0 ) {
		_trans = _exheres_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 101 "exheres.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(EXHERES_LANG) }
}

#endif

/*****************************************************************************/
