
#line 1 "eiffel.rl"
/************************* Required for every parser *************************/
#ifndef OHCOUNT_EIFFEL_PARSER_H
#define OHCOUNT_EIFFEL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *EIFFEL_LANG = LANG_EIFFEL;

// the languages entities
const char *eiffel_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  EIFFEL_SPACE = 0, EIFFEL_COMMENT, EIFFEL_STRING, EIFFEL_ANY
};

/*****************************************************************************/


#line 26 "eiffel.h"
static const char _eiffel_actions[] = {
	0, 1, 1, 1, 2, 1, 3, 1, 
	4, 1, 5, 1, 6, 1, 7, 1, 
	8, 1, 10, 1, 13, 1, 14, 1, 
	15, 1, 16, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 2, 3, 11, 
	2, 4, 12, 3, 9, 0, 4
};

static const char _eiffel_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 1, 1, 1
};

static const char _eiffel_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	0, 0, 0, 0, 0
};

static const short _eiffel_cond_keys[] = {
	13, 13, 0
};

static const char _eiffel_cond_spaces[] = {
	0, 0
};

static const char _eiffel_key_offsets[] = {
	0, 0, 4, 5, 9, 12, 13, 16, 
	28, 30, 34, 35, 38
};

static const short _eiffel_trans_keys[] = {
	10, 34, 12, 13, 10, 32, 45, 9, 
	13, 32, 9, 13, 45, 10, 12, 13, 
	9, 10, 12, 32, 34, 45, 269, 525, 
	0, 8, 14, 255, 9, 32, 10, 34, 
	12, 13, 45, 10, 12, 13, 10, 0
};

static const char _eiffel_single_lengths[] = {
	0, 2, 1, 2, 1, 1, 1, 8, 
	2, 2, 1, 1, 1
};

static const char _eiffel_range_lengths[] = {
	0, 1, 0, 1, 1, 0, 1, 2, 
	0, 1, 0, 1, 0
};

static const char _eiffel_index_offsets[] = {
	0, 0, 4, 6, 10, 13, 15, 18, 
	29, 32, 36, 38, 41
};

static const char _eiffel_trans_targs[] = {
	7, 7, 7, 1, 7, 0, 4, 5, 
	4, 3, 4, 4, 3, 6, 3, 3, 
	3, 6, 8, 7, 7, 8, 9, 10, 
	2, 12, 7, 7, 0, 8, 8, 7, 
	7, 7, 7, 1, 11, 7, 7, 7, 
	11, 7, 7, 7, 3, 3, 3, 7, 
	7, 7, 7, 7, 0
};

static const char _eiffel_trans_actions[] = {
	27, 17, 27, 0, 37, 0, 9, 11, 
	9, 29, 9, 9, 31, 11, 35, 33, 
	33, 11, 3, 37, 37, 3, 43, 7, 
	5, 5, 40, 40, 0, 3, 3, 19, 
	25, 17, 25, 0, 1, 25, 21, 21, 
	0, 37, 23, 27, 31, 35, 33, 19, 
	25, 25, 21, 23, 0
};

static const char _eiffel_to_state_actions[] = {
	0, 0, 0, 13, 0, 0, 0, 13, 
	0, 0, 0, 0, 0
};

static const char _eiffel_from_state_actions[] = {
	0, 0, 0, 15, 0, 0, 0, 15, 
	0, 0, 0, 0, 0
};

static const char _eiffel_eof_trans[] = {
	0, 44, 0, 0, 45, 46, 47, 0, 
	48, 50, 50, 51, 52
};

static const int eiffel_start = 3;
static const int eiffel_first_final = 3;
static const int eiffel_error = 0;

static const int eiffel_en_eiffel_line = 7;
static const int eiffel_en_eiffel_entity = 3;


#line 72 "eiffel.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Eiffel code.
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
void parse_eiffel(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 149 "eiffel.h"
	{
	cs = eiffel_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 95 "eiffel.rl"
  cs = (count) ? eiffel_en_eiffel_line : eiffel_en_eiffel_entity;
  
#line 160 "eiffel.h"
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
	_acts = _eiffel_actions + _eiffel_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 182 "eiffel.h"
		}
	}

	_widec = (*p);
	_klen = _eiffel_cond_lengths[cs];
	_keys = _eiffel_cond_keys + (_eiffel_cond_offsets[cs]*2);
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
				switch ( _eiffel_cond_spaces[_eiffel_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _eiffel_trans_keys + _eiffel_key_offsets[cs];
	_trans = _eiffel_index_offsets[cs];

	_klen = _eiffel_single_lengths[cs];
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

	_klen = _eiffel_range_lengths[cs];
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
_eof_trans:
	cs = _eiffel_trans_targs[_trans];

	if ( _eiffel_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _eiffel_actions + _eiffel_trans_actions[_trans];
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
#line 50 "eiffel.rl"
	{ entity = EIFFEL_SPACE; }
	break;
	case 3:
#line 53 "eiffel.rl"
	{ entity = NEWLINE;   }
	break;
	case 4:
#line 54 "eiffel.rl"
	{ entity = EIFFEL_ANY;   }
	break;
	case 5:
#line 67 "eiffel.rl"
	{ entity = EIFFEL_SPACE;   }
	break;
	case 6:
#line 68 "eiffel.rl"
	{ entity = EIFFEL_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 52 "eiffel.rl"
	{te = p+1;}
	break;
	case 11:
#line 29 "eiffel.rl"
	{te = p+1;{
    switch(entity) {
    case EIFFEL_SPACE:
      ls
      break;
    case EIFFEL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EIFFEL_LANG)
      break;
    case NEWLINE:
      std_newline(EIFFEL_LANG)
    }
  }}
	break;
	case 12:
#line 29 "eiffel.rl"
	{te = p+1;{
    switch(entity) {
    case EIFFEL_SPACE:
      ls
      break;
    case EIFFEL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EIFFEL_LANG)
      break;
    case NEWLINE:
      std_newline(EIFFEL_LANG)
    }
  }}
	break;
	case 13:
#line 29 "eiffel.rl"
	{te = p;p--;{
    switch(entity) {
    case EIFFEL_SPACE:
      ls
      break;
    case EIFFEL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EIFFEL_LANG)
      break;
    case NEWLINE:
      std_newline(EIFFEL_LANG)
    }
  }}
	break;
	case 14:
#line 51 "eiffel.rl"
	{te = p;p--;}
	break;
	case 15:
#line 29 "eiffel.rl"
	{te = p;p--;{
    switch(entity) {
    case EIFFEL_SPACE:
      ls
      break;
    case EIFFEL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EIFFEL_LANG)
      break;
    case NEWLINE:
      std_newline(EIFFEL_LANG)
    }
  }}
	break;
	case 16:
#line 29 "eiffel.rl"
	{te = p;p--;{
    switch(entity) {
    case EIFFEL_SPACE:
      ls
      break;
    case EIFFEL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EIFFEL_LANG)
      break;
    case NEWLINE:
      std_newline(EIFFEL_LANG)
    }
  }}
	break;
	case 17:
#line 29 "eiffel.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case EIFFEL_SPACE:
      ls
      break;
    case EIFFEL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(EIFFEL_LANG)
      break;
    case NEWLINE:
      std_newline(EIFFEL_LANG)
    }
  }}
	break;
	case 18:
#line 70 "eiffel.rl"
	{te = p+1;}
	break;
	case 19:
#line 59 "eiffel.rl"
	{te = p;p--;{
    callback(EIFFEL_LANG, eiffel_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 20:
#line 59 "eiffel.rl"
	{te = p;p--;{
    callback(EIFFEL_LANG, eiffel_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 21:
#line 70 "eiffel.rl"
	{te = p;p--;}
	break;
#line 456 "eiffel.h"
		}
	}

_again:
	_acts = _eiffel_actions + _eiffel_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 469 "eiffel.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _eiffel_eof_trans[cs] > 0 ) {
		_trans = _eiffel_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 97 "eiffel.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(EIFFEL_LANG) }
}

#endif

/*****************************************************************************/
