
#line 1 "jam.rl"
// jam.rl written by Scott Lawrence. bytbox@gmail.com

/************************* Required for every parser *************************/
#ifndef OHCOUNT_JAM_PARSER_H
#define OHCOUNT_JAM_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *JAM_LANG = LANG_JAM;

// the languages entities
const char *jam_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  JAM_SPACE = 0, JAM_COMMENT, JAM_STRING, JAM_ANY
};

/*****************************************************************************/


#line 28 "jam.h"
static const char _jam_actions[] = {
	0, 1, 2, 1, 7, 1, 8, 1, 
	10, 1, 11, 1, 12, 1, 13, 1, 
	18, 1, 19, 1, 20, 1, 21, 1, 
	22, 1, 23, 1, 24, 1, 25, 2, 
	1, 15, 2, 3, 9, 2, 5, 4, 
	2, 6, 4, 2, 8, 16, 2, 9, 
	17, 3, 5, 4, 2, 3, 6, 4, 
	2, 4, 5, 4, 1, 15, 4, 6, 
	4, 1, 15, 4, 14, 0, 2, 9
	
};

static const char _jam_cond_offsets[] = {
	0, 0, 1, 2, 2, 2, 3, 4, 
	4, 4, 4, 4, 4, 4, 5, 5, 
	6, 6, 7
};

static const char _jam_cond_lengths[] = {
	0, 1, 1, 0, 0, 1, 1, 0, 
	0, 0, 0, 0, 0, 1, 0, 1, 
	0, 1, 0
};

static const short _jam_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 0
};

static const char _jam_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0
};

static const char _jam_key_offsets[] = {
	0, 0, 12, 24, 27, 28, 40, 52, 
	55, 56, 57, 61, 64, 67, 80, 82, 
	94, 97, 109
};

static const short _jam_trans_keys[] = {
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	10, 12, 13, 10, 9, 10, 12, 32, 
	39, 92, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 39, 92, 269, 525, 
	0, 11, 14, 255, 10, 12, 13, 10, 
	10, 32, 35, 9, 13, 32, 9, 13, 
	10, 12, 13, 9, 10, 12, 32, 34, 
	35, 39, 269, 525, 0, 8, 14, 255, 
	9, 32, 9, 10, 12, 32, 34, 92, 
	269, 525, 0, 11, 14, 255, 10, 12, 
	13, 9, 10, 12, 32, 39, 92, 269, 
	525, 0, 11, 14, 255, 10, 0
};

static const char _jam_single_lengths[] = {
	0, 8, 8, 1, 1, 8, 8, 1, 
	1, 1, 2, 1, 1, 9, 2, 8, 
	1, 8, 1
};

static const char _jam_range_lengths[] = {
	0, 2, 2, 1, 0, 2, 2, 1, 
	0, 0, 1, 1, 1, 2, 0, 2, 
	1, 2, 0
};

static const char _jam_index_offsets[] = {
	0, 0, 11, 22, 25, 27, 38, 49, 
	52, 54, 56, 60, 63, 66, 78, 81, 
	92, 95, 106
};

static const char _jam_indicies[] = {
	2, 3, 3, 2, 4, 5, 6, 3, 
	1, 1, 0, 8, 9, 9, 8, 10, 
	11, 12, 9, 7, 7, 0, 0, 0, 
	1, 3, 0, 14, 15, 15, 14, 4, 
	16, 17, 15, 13, 13, 0, 19, 20, 
	20, 19, 21, 22, 23, 20, 18, 18, 
	0, 0, 0, 13, 15, 0, 24, 25, 
	27, 28, 27, 26, 27, 27, 29, 30, 
	30, 28, 32, 24, 24, 32, 33, 34, 
	35, 36, 37, 31, 31, 25, 32, 32, 
	38, 2, 3, 3, 2, 4, 5, 6, 
	3, 1, 1, 39, 40, 40, 41, 14, 
	15, 15, 14, 4, 16, 17, 15, 13, 
	13, 39, 24, 42, 0
};

static const char _jam_trans_targs[] = {
	13, 1, 1, 2, 13, 3, 4, 1, 
	1, 2, 13, 3, 4, 5, 5, 6, 
	7, 8, 5, 5, 6, 13, 7, 8, 
	13, 0, 10, 11, 12, 10, 10, 13, 
	14, 15, 16, 17, 9, 18, 13, 13, 
	13, 16, 13
};

static const char _jam_trans_actions[] = {
	23, 1, 0, 0, 31, 0, 0, 53, 
	40, 40, 62, 40, 40, 1, 0, 0, 
	0, 0, 49, 37, 37, 57, 37, 37, 
	43, 0, 25, 7, 9, 27, 29, 46, 
	3, 67, 34, 67, 5, 5, 15, 21, 
	17, 0, 19
};

static const char _jam_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 11, 0, 0, 11, 0, 0, 
	0, 0, 0
};

static const char _jam_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 13, 0, 0, 13, 0, 0, 
	0, 0, 0
};

static const char _jam_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 0, 0, 30, 31, 0, 39, 40, 
	41, 40, 43
};

static const int jam_start = 10;
static const int jam_first_final = 10;
static const int jam_error = 0;

static const int jam_en_jam_line = 13;
static const int jam_en_jam_entity = 10;


#line 94 "jam.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Jam code.
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
void parse_jam(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  
#line 189 "jam.h"
	{
	cs = jam_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 117 "jam.rl"
  cs = (count) ? jam_en_jam_line : jam_en_jam_entity;
  
#line 200 "jam.h"
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
	_acts = _jam_actions + _jam_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = p;}
	break;
#line 222 "jam.h"
		}
	}

	_widec = (*p);
	_klen = _jam_cond_lengths[cs];
	_keys = _jam_cond_keys + (_jam_cond_offsets[cs]*2);
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
				switch ( _jam_cond_spaces[_jam_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _jam_trans_keys + _jam_key_offsets[cs];
	_trans = _jam_index_offsets[cs];

	_klen = _jam_single_lengths[cs];
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

	_klen = _jam_range_lengths[cs];
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
	_trans = _jam_indicies[_trans];
_eof_trans:
	cs = _jam_trans_targs[_trans];

	if ( _jam_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _jam_actions + _jam_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 30 "common.rl"
	{
  inqueue = 1;
  if (callback_list_head) free_queue(); // free the current queue
  callback_list_head = NULL;
  callback_list_tail = NULL;
  // set backup variables
  last_line_start = line_start;
  last_line_contains_code = line_contains_code;
  last_whole_line_comment = whole_line_comment;
}
	break;
	case 1:
#line 41 "common.rl"
	{
  if (inqueue) {
    Callback *item;
    for (item = callback_list_head; item != NULL; item = item->next)
      callback(item->lang, item->entity, item->s, item->e, item->udata);
    free_queue();
    inqueue = 0;
  }
}
	break;
	case 2:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 3:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 4:
#line 31 "jam.rl"
	{
    switch(entity) {
    case JAM_SPACE:
      ls
      break;
    case JAM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JAM_LANG)
      break;
    case NEWLINE:
      std_newline(JAM_LANG)
    }
  }
	break;
	case 5:
#line 51 "jam.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 61 "jam.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 73 "jam.rl"
	{ entity = JAM_SPACE; }
	break;
	case 8:
#line 76 "jam.rl"
	{ entity = NEWLINE;     }
	break;
	case 9:
#line 77 "jam.rl"
	{ entity = JAM_ANY;   }
	break;
	case 10:
#line 89 "jam.rl"
	{ entity = JAM_SPACE;   }
	break;
	case 11:
#line 90 "jam.rl"
	{ entity = JAM_COMMENT; }
	break;
	case 14:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 15:
#line 75 "jam.rl"
	{te = p+1;}
	break;
	case 16:
#line 31 "jam.rl"
	{te = p+1;{
    switch(entity) {
    case JAM_SPACE:
      ls
      break;
    case JAM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JAM_LANG)
      break;
    case NEWLINE:
      std_newline(JAM_LANG)
    }
  }}
	break;
	case 17:
#line 31 "jam.rl"
	{te = p+1;{
    switch(entity) {
    case JAM_SPACE:
      ls
      break;
    case JAM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JAM_LANG)
      break;
    case NEWLINE:
      std_newline(JAM_LANG)
    }
  }}
	break;
	case 18:
#line 31 "jam.rl"
	{te = p;p--;{
    switch(entity) {
    case JAM_SPACE:
      ls
      break;
    case JAM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JAM_LANG)
      break;
    case NEWLINE:
      std_newline(JAM_LANG)
    }
  }}
	break;
	case 19:
#line 74 "jam.rl"
	{te = p;p--;}
	break;
	case 20:
#line 31 "jam.rl"
	{te = p;p--;{
    switch(entity) {
    case JAM_SPACE:
      ls
      break;
    case JAM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JAM_LANG)
      break;
    case NEWLINE:
      std_newline(JAM_LANG)
    }
  }}
	break;
	case 21:
#line 31 "jam.rl"
	{te = p;p--;{
    switch(entity) {
    case JAM_SPACE:
      ls
      break;
    case JAM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JAM_LANG)
      break;
    case NEWLINE:
      std_newline(JAM_LANG)
    }
  }}
	break;
	case 22:
#line 31 "jam.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case JAM_SPACE:
      ls
      break;
    case JAM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JAM_LANG)
      break;
    case NEWLINE:
      std_newline(JAM_LANG)
    }
  }}
	break;
	case 23:
#line 92 "jam.rl"
	{te = p+1;}
	break;
	case 24:
#line 82 "jam.rl"
	{te = p;p--;{
    callback(JAM_LANG, jam_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 82 "jam.rl"
	{te = p;p--;{
    callback(JAM_LANG, jam_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 542 "jam.h"
		}
	}

_again:
	_acts = _jam_actions + _jam_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 555 "jam.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _jam_eof_trans[cs] > 0 ) {
		_trans = _jam_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 119 "jam.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(JAM_LANG) }
}

#endif

/*****************************************************************************/
