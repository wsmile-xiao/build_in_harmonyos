
#line 1 "ampl.rl"
// ampl.rl written by Victor Zverovich. victor.zverovich@gmail.com

/************************* Required for every parser *************************/
#ifndef OHCOUNT_AMPL_PARSER_H
#define OHCOUNT_AMPL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *AMPL_LANG = LANG_AMPL;

// the languages entities
const char *ampl_entities[] = {
  "space", "comment", "any"
};

// constants associated with the entities
enum {
  AMPL_SPACE = 0, AMPL_COMMENT, AMPL_ANY
};

/*****************************************************************************/


#line 28 "ampl.h"
static const char _ampl_actions[] = {
	0, 1, 0, 1, 3, 1, 4, 1, 
	6, 1, 7, 1, 8, 1, 9, 1, 
	11, 1, 14, 1, 15, 1, 16, 1, 
	17, 1, 18, 1, 20, 1, 21, 1, 
	22, 1, 23, 1, 24, 2, 0, 5, 
	2, 2, 1, 2, 4, 12, 2, 5, 
	13, 2, 7, 19, 2, 10, 5, 2, 
	10, 7, 3, 2, 1, 0
};

static const char _ampl_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 3, 3, 
	3, 3, 3, 3, 3, 4, 4, 4, 
	4
};

static const char _ampl_cond_lengths[] = {
	0, 0, 0, 1, 1, 1, 0, 0, 
	0, 0, 0, 0, 1, 0, 0, 0, 
	0
};

static const short _ampl_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _ampl_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _ampl_key_offsets[] = {
	0, 0, 1, 3, 14, 25, 37, 38, 
	39, 44, 47, 50, 51, 63, 65, 68, 
	69
};

static const short _ampl_trans_keys[] = {
	42, 42, 47, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	35, 47, 9, 13, 32, 9, 13, 10, 
	12, 13, 42, 9, 10, 12, 32, 35, 
	47, 269, 525, 0, 8, 14, 255, 9, 
	32, 10, 12, 13, 42, 10, 0
};

static const char _ampl_single_lengths[] = {
	0, 1, 2, 7, 7, 8, 1, 1, 
	3, 1, 1, 1, 8, 2, 1, 1, 
	1
};

static const char _ampl_range_lengths[] = {
	0, 0, 0, 2, 2, 2, 0, 0, 
	1, 1, 1, 0, 2, 0, 1, 0, 
	0
};

static const char _ampl_index_offsets[] = {
	0, 0, 2, 5, 15, 25, 36, 38, 
	40, 45, 48, 51, 53, 64, 67, 70, 
	72
};

static const char _ampl_indicies[] = {
	2, 1, 2, 3, 1, 6, 7, 7, 
	6, 8, 9, 7, 5, 5, 4, 11, 
	12, 12, 11, 13, 14, 12, 10, 10, 
	4, 6, 7, 7, 6, 8, 15, 9, 
	7, 5, 5, 4, 7, 4, 16, 17, 
	19, 20, 21, 19, 18, 19, 19, 22, 
	23, 23, 20, 1, 24, 26, 16, 16, 
	26, 27, 28, 29, 30, 25, 25, 17, 
	26, 26, 31, 32, 32, 33, 5, 34, 
	16, 35, 0
};

static const char _ampl_trans_targs[] = {
	8, 1, 2, 8, 12, 3, 3, 4, 
	5, 6, 3, 3, 4, 5, 6, 12, 
	12, 0, 8, 9, 10, 11, 8, 8, 
	8, 12, 13, 14, 15, 7, 16, 12, 
	12, 14, 12, 12
};

static const char _ampl_trans_actions[] = {
	35, 9, 9, 49, 25, 1, 0, 0, 
	1, 0, 58, 40, 40, 58, 40, 15, 
	43, 0, 27, 7, 9, 55, 29, 31, 
	33, 46, 3, 37, 52, 5, 5, 17, 
	19, 0, 23, 21
};

static const char _ampl_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	11, 0, 0, 0, 11, 0, 0, 0, 
	0
};

static const char _ampl_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 0, 13, 0, 0, 0, 
	0
};

static const char _ampl_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 0, 
	0, 23, 24, 25, 0, 32, 33, 35, 
	36
};

static const int ampl_start = 8;
static const int ampl_first_final = 8;
static const int ampl_error = 0;

static const int ampl_en_ampl_line = 12;
static const int ampl_en_ampl_entity = 8;


#line 81 "ampl.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with AMPL code.
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
void parse_ampl(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 176 "ampl.h"
	{
	cs = ampl_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 104 "ampl.rl"
  cs = (count) ? ampl_en_ampl_line : ampl_en_ampl_entity;
  
#line 187 "ampl.h"
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
	_acts = _ampl_actions + _ampl_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = p;}
	break;
#line 209 "ampl.h"
		}
	}

	_widec = (*p);
	_klen = _ampl_cond_lengths[cs];
	_keys = _ampl_cond_keys + (_ampl_cond_offsets[cs]*2);
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
				switch ( _ampl_cond_spaces[_ampl_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _ampl_trans_keys + _ampl_key_offsets[cs];
	_trans = _ampl_index_offsets[cs];

	_klen = _ampl_single_lengths[cs];
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

	_klen = _ampl_range_lengths[cs];
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
	_trans = _ampl_indicies[_trans];
_eof_trans:
	cs = _ampl_trans_targs[_trans];

	if ( _ampl_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _ampl_actions + _ampl_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 1:
#line 31 "ampl.rl"
	{
    switch(entity) {
    case AMPL_SPACE:
      ls
      break;
    case AMPL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AMPL_LANG)
      break;
    case NEWLINE:
      std_newline(AMPL_LANG)
    }
  }
	break;
	case 2:
#line 50 "ampl.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 3:
#line 59 "ampl.rl"
	{ entity = AMPL_SPACE; }
	break;
	case 4:
#line 61 "ampl.rl"
	{ entity = NEWLINE;    }
	break;
	case 5:
#line 62 "ampl.rl"
	{ entity = AMPL_ANY;   }
	break;
	case 6:
#line 77 "ampl.rl"
	{ entity = AMPL_SPACE;   }
	break;
	case 7:
#line 78 "ampl.rl"
	{ entity = AMPL_COMMENT; }
	break;
	case 10:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 11:
#line 60 "ampl.rl"
	{te = p+1;}
	break;
	case 12:
#line 31 "ampl.rl"
	{te = p+1;{
    switch(entity) {
    case AMPL_SPACE:
      ls
      break;
    case AMPL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AMPL_LANG)
      break;
    case NEWLINE:
      std_newline(AMPL_LANG)
    }
  }}
	break;
	case 13:
#line 31 "ampl.rl"
	{te = p+1;{
    switch(entity) {
    case AMPL_SPACE:
      ls
      break;
    case AMPL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AMPL_LANG)
      break;
    case NEWLINE:
      std_newline(AMPL_LANG)
    }
  }}
	break;
	case 14:
#line 31 "ampl.rl"
	{te = p;p--;{
    switch(entity) {
    case AMPL_SPACE:
      ls
      break;
    case AMPL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AMPL_LANG)
      break;
    case NEWLINE:
      std_newline(AMPL_LANG)
    }
  }}
	break;
	case 15:
#line 60 "ampl.rl"
	{te = p;p--;}
	break;
	case 16:
#line 31 "ampl.rl"
	{te = p;p--;{
    switch(entity) {
    case AMPL_SPACE:
      ls
      break;
    case AMPL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AMPL_LANG)
      break;
    case NEWLINE:
      std_newline(AMPL_LANG)
    }
  }}
	break;
	case 17:
#line 31 "ampl.rl"
	{te = p;p--;{
    switch(entity) {
    case AMPL_SPACE:
      ls
      break;
    case AMPL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AMPL_LANG)
      break;
    case NEWLINE:
      std_newline(AMPL_LANG)
    }
  }}
	break;
	case 18:
#line 31 "ampl.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case AMPL_SPACE:
      ls
      break;
    case AMPL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AMPL_LANG)
      break;
    case NEWLINE:
      std_newline(AMPL_LANG)
    }
  }}
	break;
	case 19:
#line 67 "ampl.rl"
	{te = p+1;{
    callback(AMPL_LANG, ampl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 20:
#line 79 "ampl.rl"
	{te = p+1;}
	break;
	case 21:
#line 67 "ampl.rl"
	{te = p;p--;{
    callback(AMPL_LANG, ampl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 67 "ampl.rl"
	{te = p;p--;{
    callback(AMPL_LANG, ampl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 23:
#line 79 "ampl.rl"
	{te = p;p--;}
	break;
	case 24:
#line 79 "ampl.rl"
	{{p = ((te))-1;}}
	break;
#line 507 "ampl.h"
		}
	}

_again:
	_acts = _ampl_actions + _ampl_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 520 "ampl.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _ampl_eof_trans[cs] > 0 ) {
		_trans = _ampl_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 106 "ampl.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(AMPL_LANG) }
}

#endif

/*****************************************************************************/
