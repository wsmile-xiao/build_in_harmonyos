
#line 1 "puppet.rl"
// puppet.rl written by Ken Barber <ken@bob.sh>
// Based on pascal.rl by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_PUPPET_PARSER_H
#define OHCOUNT_PUPPET_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *PUPPET_LANG = LANG_PUPPET;

// the languages entities
const char *puppet_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  PUPPET_SPACE = 0, PUPPET_COMMENT, PUPPET_STRING, PUPPET_ANY
};

/*****************************************************************************/


#line 29 "puppet.h"
static const char _puppet_actions[] = {
	0, 1, 0, 1, 1, 1, 5, 1, 
	6, 1, 8, 1, 9, 1, 10, 1, 
	11, 1, 13, 1, 14, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 21, 1, 
	23, 1, 24, 1, 25, 1, 26, 1, 
	27, 2, 1, 7, 2, 3, 2, 2, 
	4, 2, 2, 6, 15, 2, 7, 16, 
	2, 9, 22, 2, 12, 7, 2, 12, 
	9, 3, 3, 2, 0, 3, 4, 2, 
	0, 3, 4, 2, 14, 3, 12, 0, 
	7
};

static const char _puppet_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 2, 2, 
	3, 4, 5, 5, 5, 5, 5, 5, 
	5, 6, 6, 6, 7, 7
};

static const char _puppet_cond_lengths[] = {
	0, 0, 0, 1, 1, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 1, 0, 0
};

static const short _puppet_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 0
};

static const char _puppet_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0
};

static const char _puppet_key_offsets[] = {
	0, 0, 1, 3, 15, 27, 30, 31, 
	42, 53, 65, 66, 67, 72, 75, 78, 
	79, 92, 94, 97, 109, 110
};

static const short _puppet_trans_keys[] = {
	42, 42, 47, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 39, 92, 269, 525, 0, 
	11, 14, 255, 10, 12, 13, 10, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 47, 269, 525, 0, 11, 14, 
	255, 10, 10, 32, 35, 47, 9, 13, 
	32, 9, 13, 10, 12, 13, 42, 9, 
	10, 12, 32, 35, 39, 47, 269, 525, 
	0, 8, 14, 255, 9, 32, 10, 12, 
	13, 9, 10, 12, 32, 39, 92, 269, 
	525, 0, 11, 14, 255, 42, 10, 0
};

static const char _puppet_single_lengths[] = {
	0, 1, 2, 8, 8, 1, 1, 7, 
	7, 8, 1, 1, 3, 1, 1, 1, 
	9, 2, 1, 8, 1, 1
};

static const char _puppet_range_lengths[] = {
	0, 0, 0, 2, 2, 1, 0, 2, 
	2, 2, 0, 0, 1, 1, 1, 0, 
	2, 0, 1, 2, 0, 0
};

static const char _puppet_index_offsets[] = {
	0, 0, 2, 5, 16, 27, 30, 32, 
	42, 52, 63, 65, 67, 72, 75, 78, 
	80, 92, 95, 98, 109, 111
};

static const char _puppet_indicies[] = {
	2, 1, 2, 3, 1, 6, 7, 7, 
	6, 8, 9, 10, 7, 5, 5, 4, 
	12, 13, 13, 12, 14, 15, 16, 13, 
	11, 11, 4, 4, 4, 5, 7, 4, 
	18, 19, 19, 18, 20, 21, 19, 17, 
	17, 4, 23, 24, 24, 23, 25, 26, 
	24, 22, 22, 4, 18, 19, 19, 18, 
	20, 27, 21, 19, 17, 17, 4, 19, 
	4, 28, 29, 31, 32, 33, 31, 30, 
	31, 31, 34, 35, 35, 32, 1, 36, 
	38, 28, 28, 38, 39, 40, 41, 42, 
	43, 37, 37, 29, 38, 38, 44, 45, 
	45, 46, 6, 7, 7, 6, 8, 9, 
	10, 7, 5, 5, 47, 48, 47, 28, 
	49, 0
};

static const char _puppet_trans_targs[] = {
	12, 1, 2, 12, 16, 3, 3, 4, 
	16, 5, 6, 3, 3, 4, 16, 5, 
	6, 7, 7, 8, 9, 10, 7, 7, 
	8, 9, 10, 16, 16, 0, 12, 13, 
	14, 15, 12, 12, 12, 16, 17, 18, 
	19, 20, 11, 21, 16, 16, 18, 16, 
	7, 16
};

static const char _puppet_trans_actions[] = {
	39, 11, 11, 56, 29, 1, 0, 0, 
	19, 0, 0, 69, 47, 47, 73, 47, 
	47, 1, 0, 0, 1, 0, 65, 44, 
	44, 65, 44, 17, 50, 0, 31, 9, 
	11, 62, 33, 35, 37, 53, 5, 41, 
	77, 59, 7, 7, 21, 23, 0, 27, 
	3, 25
};

static const char _puppet_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	13, 0, 0, 0, 0, 0
};

static const char _puppet_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 15, 0, 0, 0, 
	15, 0, 0, 0, 0, 0
};

static const char _puppet_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 0, 0, 35, 36, 37, 
	0, 45, 46, 48, 48, 50
};

static const int puppet_start = 12;
static const int puppet_first_final = 12;
static const int puppet_error = 0;

static const int puppet_en_puppet_line = 16;
static const int puppet_en_puppet_entity = 12;


#line 96 "puppet.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Puppet DSL code.
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
void parse_puppet(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 194 "puppet.h"
	{
	cs = puppet_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 119 "puppet.rl"
  cs = (count) ? puppet_en_puppet_line : puppet_en_puppet_entity;
  
#line 205 "puppet.h"
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
	_acts = _puppet_actions + _puppet_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 227 "puppet.h"
		}
	}

	_widec = (*p);
	_klen = _puppet_cond_lengths[cs];
	_keys = _puppet_cond_keys + (_puppet_cond_offsets[cs]*2);
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
				switch ( _puppet_cond_spaces[_puppet_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _puppet_trans_keys + _puppet_key_offsets[cs];
	_trans = _puppet_index_offsets[cs];

	_klen = _puppet_single_lengths[cs];
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

	_klen = _puppet_range_lengths[cs];
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
	_trans = _puppet_indicies[_trans];
_eof_trans:
	cs = _puppet_trans_targs[_trans];

	if ( _puppet_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _puppet_actions + _puppet_trans_actions[_trans];
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
#line 32 "puppet.rl"
	{
    switch(entity) {
    case PUPPET_SPACE:
      ls
      break;
    case PUPPET_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PUPPET_LANG)
      break;
    case NEWLINE:
      std_newline(PUPPET_LANG)
    }
  }
	break;
	case 3:
#line 51 "puppet.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 61 "puppet.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 71 "puppet.rl"
	{ entity = PUPPET_SPACE; }
	break;
	case 6:
#line 74 "puppet.rl"
	{ entity = NEWLINE;      }
	break;
	case 7:
#line 75 "puppet.rl"
	{ entity = PUPPET_ANY;   }
	break;
	case 8:
#line 91 "puppet.rl"
	{ entity = PUPPET_SPACE;   }
	break;
	case 9:
#line 92 "puppet.rl"
	{ entity = PUPPET_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 72 "puppet.rl"
	{te = p+1;}
	break;
	case 14:
#line 73 "puppet.rl"
	{te = p+1;}
	break;
	case 15:
#line 32 "puppet.rl"
	{te = p+1;{
    switch(entity) {
    case PUPPET_SPACE:
      ls
      break;
    case PUPPET_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PUPPET_LANG)
      break;
    case NEWLINE:
      std_newline(PUPPET_LANG)
    }
  }}
	break;
	case 16:
#line 32 "puppet.rl"
	{te = p+1;{
    switch(entity) {
    case PUPPET_SPACE:
      ls
      break;
    case PUPPET_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PUPPET_LANG)
      break;
    case NEWLINE:
      std_newline(PUPPET_LANG)
    }
  }}
	break;
	case 17:
#line 32 "puppet.rl"
	{te = p;p--;{
    switch(entity) {
    case PUPPET_SPACE:
      ls
      break;
    case PUPPET_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PUPPET_LANG)
      break;
    case NEWLINE:
      std_newline(PUPPET_LANG)
    }
  }}
	break;
	case 18:
#line 72 "puppet.rl"
	{te = p;p--;}
	break;
	case 19:
#line 32 "puppet.rl"
	{te = p;p--;{
    switch(entity) {
    case PUPPET_SPACE:
      ls
      break;
    case PUPPET_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PUPPET_LANG)
      break;
    case NEWLINE:
      std_newline(PUPPET_LANG)
    }
  }}
	break;
	case 20:
#line 32 "puppet.rl"
	{te = p;p--;{
    switch(entity) {
    case PUPPET_SPACE:
      ls
      break;
    case PUPPET_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PUPPET_LANG)
      break;
    case NEWLINE:
      std_newline(PUPPET_LANG)
    }
  }}
	break;
	case 21:
#line 32 "puppet.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case PUPPET_SPACE:
      ls
      break;
    case PUPPET_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PUPPET_LANG)
      break;
    case NEWLINE:
      std_newline(PUPPET_LANG)
    }
  }}
	break;
	case 22:
#line 80 "puppet.rl"
	{te = p+1;{
    callback(PUPPET_LANG, puppet_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 23:
#line 94 "puppet.rl"
	{te = p+1;}
	break;
	case 24:
#line 80 "puppet.rl"
	{te = p;p--;{
    callback(PUPPET_LANG, puppet_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 25:
#line 80 "puppet.rl"
	{te = p;p--;{
    callback(PUPPET_LANG, puppet_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 26:
#line 94 "puppet.rl"
	{te = p;p--;}
	break;
	case 27:
#line 94 "puppet.rl"
	{{p = ((te))-1;}}
	break;
#line 543 "puppet.h"
		}
	}

_again:
	_acts = _puppet_actions + _puppet_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 556 "puppet.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _puppet_eof_trans[cs] > 0 ) {
		_trans = _puppet_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 121 "puppet.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(PUPPET_LANG) }
}

#endif

/*****************************************************************************/
