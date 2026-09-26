
#line 1 "livecode.rl"
// livecode.rl written by Monte Goulding. monte<att>goulding<dott>ws.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_LIVECODE_PARSER_H
#define OHCOUNT_LIVECODE_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *LIVECODE_LANG = LANG_LIVECODE;

// the languages entities
const char *livecode_entities[] = {
  "space", "comment", "string", "any",
};

// constants associated with the entities
enum {
  LIVECODE_SPACE = 0, LIVECODE_COMMENT, LIVECODE_STRING, LIVECODE_ANY
};

/*****************************************************************************/


#line 28 "livecode.h"
static const char _livecode_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	6, 1, 7, 1, 8, 1, 9, 1, 
	10, 1, 12, 1, 13, 1, 16, 1, 
	17, 1, 18, 1, 19, 1, 20, 1, 
	22, 1, 23, 1, 24, 1, 25, 1, 
	26, 2, 1, 6, 2, 3, 2, 2, 
	5, 14, 2, 6, 15, 2, 8, 21, 
	2, 11, 6, 2, 11, 8, 3, 3, 
	2, 1, 3, 11, 0, 6
};

static const char _livecode_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 2, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	4, 4, 4, 4, 4, 4
};

static const char _livecode_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 1, 1, 
	0, 0, 0, 0, 0, 0, 0, 1, 
	0, 0, 0, 0, 0, 0
};

static const short _livecode_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _livecode_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _livecode_key_offsets[] = {
	0, 0, 1, 3, 8, 11, 22, 33, 
	45, 46, 47, 53, 56, 59, 60, 62, 
	76, 78, 83, 86, 87, 89
};

static const short _livecode_trans_keys[] = {
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	35, 45, 47, 9, 13, 32, 9, 13, 
	10, 12, 13, 45, 42, 47, 9, 10, 
	12, 32, 34, 35, 45, 47, 269, 525, 
	0, 8, 14, 255, 9, 32, 10, 34, 
	92, 12, 13, 10, 12, 13, 45, 42, 
	47, 10, 0
};

static const char _livecode_single_lengths[] = {
	0, 1, 2, 3, 1, 7, 7, 8, 
	1, 1, 4, 1, 1, 1, 2, 10, 
	2, 3, 1, 1, 2, 1
};

static const char _livecode_range_lengths[] = {
	0, 0, 0, 1, 1, 2, 2, 2, 
	0, 0, 1, 1, 1, 0, 0, 2, 
	0, 1, 1, 0, 0, 0
};

static const char _livecode_index_offsets[] = {
	0, 0, 2, 5, 10, 13, 23, 33, 
	44, 46, 48, 54, 57, 60, 62, 65, 
	78, 81, 86, 89, 91, 94
};

static const char _livecode_indicies[] = {
	2, 1, 2, 3, 1, 4, 6, 7, 
	4, 5, 4, 4, 5, 9, 10, 10, 
	9, 11, 12, 10, 8, 8, 4, 14, 
	15, 15, 14, 16, 17, 15, 13, 13, 
	4, 9, 10, 10, 9, 11, 18, 12, 
	10, 8, 8, 4, 10, 4, 19, 20, 
	22, 23, 24, 25, 22, 21, 22, 22, 
	26, 27, 27, 23, 23, 28, 1, 23, 
	28, 30, 19, 19, 30, 31, 32, 33, 
	34, 35, 36, 29, 29, 20, 30, 30, 
	37, 38, 6, 7, 38, 5, 39, 39, 
	40, 41, 38, 8, 41, 38, 19, 42, 
	0
};

static const char _livecode_trans_targs[] = {
	10, 1, 2, 10, 15, 3, 15, 4, 
	5, 5, 6, 7, 8, 5, 5, 6, 
	7, 8, 15, 15, 0, 10, 11, 12, 
	13, 14, 10, 10, 10, 15, 16, 17, 
	18, 19, 20, 9, 21, 15, 15, 15, 
	18, 18, 15
};

static const char _livecode_trans_actions[] = {
	39, 11, 11, 53, 29, 0, 19, 0, 
	1, 0, 0, 1, 0, 62, 44, 44, 
	62, 44, 17, 47, 0, 31, 9, 11, 
	11, 59, 33, 35, 37, 50, 3, 66, 
	41, 7, 56, 5, 5, 21, 27, 23, 
	0, 1, 25
};

static const char _livecode_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 13, 0, 0, 0, 0, 13, 
	0, 0, 0, 0, 0, 0
};

static const char _livecode_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 15, 0, 0, 0, 0, 15, 
	0, 0, 0, 0, 0, 0
};

static const char _livecode_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 0, 0, 27, 28, 29, 29, 0, 
	38, 39, 40, 39, 39, 43
};

static const int livecode_start = 10;
static const int livecode_first_final = 10;
static const int livecode_error = 0;

static const int livecode_en_livecode_line = 15;
static const int livecode_en_livecode_entity = 10;


#line 85 "livecode.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with LiveCode code.
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
void parse_livecode(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 185 "livecode.h"
	{
	cs = livecode_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 108 "livecode.rl"
  cs = (count) ? livecode_en_livecode_line : livecode_en_livecode_entity;
  
#line 196 "livecode.h"
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
	_acts = _livecode_actions + _livecode_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 218 "livecode.h"
		}
	}

	_widec = (*p);
	_klen = _livecode_cond_lengths[cs];
	_keys = _livecode_cond_keys + (_livecode_cond_offsets[cs]*2);
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
				switch ( _livecode_cond_spaces[_livecode_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _livecode_trans_keys + _livecode_key_offsets[cs];
	_trans = _livecode_index_offsets[cs];

	_klen = _livecode_single_lengths[cs];
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

	_klen = _livecode_range_lengths[cs];
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
	_trans = _livecode_indicies[_trans];
_eof_trans:
	cs = _livecode_trans_targs[_trans];

	if ( _livecode_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _livecode_actions + _livecode_trans_actions[_trans];
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
#line 31 "livecode.rl"
	{
    switch(entity) {
    case LIVECODE_SPACE:
      ls
      break;
    case LIVECODE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIVECODE_LANG)
      break;
    case NEWLINE:
      std_newline(LIVECODE_LANG)
    }
  }
	break;
	case 3:
#line 50 "livecode.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 62 "livecode.rl"
	{ entity = LIVECODE_SPACE; }
	break;
	case 5:
#line 65 "livecode.rl"
	{ entity = NEWLINE;   }
	break;
	case 6:
#line 66 "livecode.rl"
	{ entity = LIVECODE_ANY;   }
	break;
	case 7:
#line 80 "livecode.rl"
	{ entity = LIVECODE_SPACE;   }
	break;
	case 8:
#line 81 "livecode.rl"
	{ entity = LIVECODE_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 63 "livecode.rl"
	{te = p+1;}
	break;
	case 13:
#line 64 "livecode.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "livecode.rl"
	{te = p+1;{
    switch(entity) {
    case LIVECODE_SPACE:
      ls
      break;
    case LIVECODE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIVECODE_LANG)
      break;
    case NEWLINE:
      std_newline(LIVECODE_LANG)
    }
  }}
	break;
	case 15:
#line 31 "livecode.rl"
	{te = p+1;{
    switch(entity) {
    case LIVECODE_SPACE:
      ls
      break;
    case LIVECODE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIVECODE_LANG)
      break;
    case NEWLINE:
      std_newline(LIVECODE_LANG)
    }
  }}
	break;
	case 16:
#line 31 "livecode.rl"
	{te = p;p--;{
    switch(entity) {
    case LIVECODE_SPACE:
      ls
      break;
    case LIVECODE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIVECODE_LANG)
      break;
    case NEWLINE:
      std_newline(LIVECODE_LANG)
    }
  }}
	break;
	case 17:
#line 63 "livecode.rl"
	{te = p;p--;}
	break;
	case 18:
#line 31 "livecode.rl"
	{te = p;p--;{
    switch(entity) {
    case LIVECODE_SPACE:
      ls
      break;
    case LIVECODE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIVECODE_LANG)
      break;
    case NEWLINE:
      std_newline(LIVECODE_LANG)
    }
  }}
	break;
	case 19:
#line 31 "livecode.rl"
	{te = p;p--;{
    switch(entity) {
    case LIVECODE_SPACE:
      ls
      break;
    case LIVECODE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIVECODE_LANG)
      break;
    case NEWLINE:
      std_newline(LIVECODE_LANG)
    }
  }}
	break;
	case 20:
#line 31 "livecode.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case LIVECODE_SPACE:
      ls
      break;
    case LIVECODE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIVECODE_LANG)
      break;
    case NEWLINE:
      std_newline(LIVECODE_LANG)
    }
  }}
	break;
	case 21:
#line 71 "livecode.rl"
	{te = p+1;{
    callback(LIVECODE_LANG, livecode_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 83 "livecode.rl"
	{te = p+1;}
	break;
	case 23:
#line 71 "livecode.rl"
	{te = p;p--;{
    callback(LIVECODE_LANG, livecode_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 71 "livecode.rl"
	{te = p;p--;{
    callback(LIVECODE_LANG, livecode_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 83 "livecode.rl"
	{te = p;p--;}
	break;
	case 26:
#line 83 "livecode.rl"
	{{p = ((te))-1;}}
	break;
#line 527 "livecode.h"
		}
	}

_again:
	_acts = _livecode_actions + _livecode_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 540 "livecode.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _livecode_eof_trans[cs] > 0 ) {
		_trans = _livecode_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 110 "livecode.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(LIVECODE_LANG) }
}

#endif

/*****************************************************************************/
