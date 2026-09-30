
#line 1 "grace.rl"
// grace.rl written by Michael Homer, based on shell.rl
// by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_GRACE_PARSER_H
#define OHCOUNT_GRACE_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *GRACE_LANG = LANG_GRACE;

// the languages entities
const char *grace_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  GRACE_SPACE = 0, GRACE_COMMENT, GRACE_STRING, GRACE_ANY
};

/*****************************************************************************/


#line 29 "grace.h"
static const char _grace_actions[] = {
	0, 1, 2, 1, 3, 1, 6, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	11, 1, 12, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	23, 1, 24, 1, 25, 2, 1, 14, 
	2, 5, 4, 2, 7, 15, 2, 8, 
	16, 3, 5, 4, 2, 4, 5, 4, 
	1, 14, 4, 13, 0, 2, 8
};

static const char _grace_cond_offsets[] = {
	0, 0, 1, 2, 2, 2, 2, 2, 
	2, 2, 3, 3, 4, 4, 4
};

static const char _grace_cond_lengths[] = {
	0, 1, 1, 0, 0, 0, 0, 0, 
	0, 1, 0, 1, 0, 0, 0
};

static const short _grace_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _grace_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _grace_key_offsets[] = {
	0, 0, 13, 26, 27, 28, 32, 35, 
	36, 39, 51, 53, 66, 67, 70
};

static const short _grace_trans_keys[] = {
	9, 10, 12, 32, 34, 269, 525, 0, 
	11, 14, 91, 93, 255, 9, 10, 12, 
	32, 34, 269, 525, 0, 11, 14, 91, 
	93, 255, 10, 10, 32, 47, 9, 13, 
	32, 9, 13, 47, 10, 12, 13, 9, 
	10, 12, 32, 34, 47, 269, 525, 0, 
	8, 14, 255, 9, 32, 9, 10, 12, 
	32, 34, 269, 525, 0, 11, 14, 91, 
	93, 255, 47, 10, 12, 13, 10, 0
};

static const char _grace_single_lengths[] = {
	0, 7, 7, 1, 1, 2, 1, 1, 
	1, 8, 2, 7, 1, 1, 1
};

static const char _grace_range_lengths[] = {
	0, 3, 3, 0, 0, 1, 1, 0, 
	1, 2, 0, 3, 0, 1, 0
};

static const char _grace_index_offsets[] = {
	0, 0, 11, 22, 24, 26, 30, 33, 
	35, 38, 49, 52, 63, 65, 68
};

static const char _grace_indicies[] = {
	2, 3, 3, 2, 4, 5, 3, 1, 
	1, 1, 0, 7, 8, 8, 7, 9, 
	10, 8, 6, 6, 6, 0, 3, 0, 
	11, 12, 14, 15, 14, 13, 14, 14, 
	16, 18, 17, 19, 19, 18, 21, 11, 
	11, 21, 22, 23, 24, 25, 20, 20, 
	12, 21, 21, 26, 2, 3, 3, 2, 
	4, 5, 3, 1, 1, 1, 27, 28, 
	27, 29, 29, 30, 11, 31, 0
};

static const char _grace_trans_targs[] = {
	9, 1, 1, 2, 9, 3, 1, 1, 
	2, 9, 3, 9, 0, 5, 6, 7, 
	5, 5, 8, 5, 9, 10, 11, 12, 
	4, 14, 9, 9, 13, 9, 13, 9
};

static const char _grace_trans_actions[] = {
	27, 1, 0, 0, 37, 0, 49, 40, 
	40, 53, 40, 43, 0, 29, 11, 13, 
	31, 35, 13, 33, 46, 5, 58, 9, 
	7, 7, 19, 25, 3, 21, 0, 23
};

static const char _grace_to_state_actions[] = {
	0, 0, 0, 0, 0, 15, 0, 0, 
	0, 15, 0, 0, 0, 0, 0
};

static const char _grace_from_state_actions[] = {
	0, 0, 0, 0, 0, 17, 0, 0, 
	0, 17, 0, 0, 0, 0, 0
};

static const char _grace_eof_trans[] = {
	0, 1, 1, 1, 0, 0, 17, 18, 
	20, 0, 27, 28, 28, 30, 32
};

static const int grace_start = 5;
static const int grace_first_final = 5;
static const int grace_error = 0;

static const int grace_en_grace_line = 9;
static const int grace_en_grace_entity = 5;


#line 81 "grace.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Grace code.
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
void parse_grace(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  
#line 165 "grace.h"
	{
	cs = grace_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 104 "grace.rl"
  cs = (count) ? grace_en_grace_line : grace_en_grace_entity;
  
#line 176 "grace.h"
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
	_acts = _grace_actions + _grace_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 198 "grace.h"
		}
	}

	_widec = (*p);
	_klen = _grace_cond_lengths[cs];
	_keys = _grace_cond_keys + (_grace_cond_offsets[cs]*2);
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
				switch ( _grace_cond_spaces[_grace_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _grace_trans_keys + _grace_key_offsets[cs];
	_trans = _grace_index_offsets[cs];

	_klen = _grace_single_lengths[cs];
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

	_klen = _grace_range_lengths[cs];
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
	_trans = _grace_indicies[_trans];
_eof_trans:
	cs = _grace_trans_targs[_trans];

	if ( _grace_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _grace_actions + _grace_trans_actions[_trans];
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
#line 32 "grace.rl"
	{
    switch(entity) {
    case GRACE_SPACE:
      ls
      break;
    case GRACE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GRACE_LANG)
      break;
    case NEWLINE:
      std_newline(GRACE_LANG)
    }
  }
	break;
	case 5:
#line 52 "grace.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 60 "grace.rl"
	{ entity = GRACE_SPACE; }
	break;
	case 7:
#line 63 "grace.rl"
	{ entity = NEWLINE;     }
	break;
	case 8:
#line 64 "grace.rl"
	{ entity = GRACE_ANY;   }
	break;
	case 9:
#line 76 "grace.rl"
	{ entity = GRACE_SPACE;   }
	break;
	case 10:
#line 77 "grace.rl"
	{ entity = GRACE_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 62 "grace.rl"
	{te = p+1;}
	break;
	case 15:
#line 32 "grace.rl"
	{te = p+1;{
    switch(entity) {
    case GRACE_SPACE:
      ls
      break;
    case GRACE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GRACE_LANG)
      break;
    case NEWLINE:
      std_newline(GRACE_LANG)
    }
  }}
	break;
	case 16:
#line 32 "grace.rl"
	{te = p+1;{
    switch(entity) {
    case GRACE_SPACE:
      ls
      break;
    case GRACE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GRACE_LANG)
      break;
    case NEWLINE:
      std_newline(GRACE_LANG)
    }
  }}
	break;
	case 17:
#line 32 "grace.rl"
	{te = p;p--;{
    switch(entity) {
    case GRACE_SPACE:
      ls
      break;
    case GRACE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GRACE_LANG)
      break;
    case NEWLINE:
      std_newline(GRACE_LANG)
    }
  }}
	break;
	case 18:
#line 61 "grace.rl"
	{te = p;p--;}
	break;
	case 19:
#line 32 "grace.rl"
	{te = p;p--;{
    switch(entity) {
    case GRACE_SPACE:
      ls
      break;
    case GRACE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GRACE_LANG)
      break;
    case NEWLINE:
      std_newline(GRACE_LANG)
    }
  }}
	break;
	case 20:
#line 32 "grace.rl"
	{te = p;p--;{
    switch(entity) {
    case GRACE_SPACE:
      ls
      break;
    case GRACE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GRACE_LANG)
      break;
    case NEWLINE:
      std_newline(GRACE_LANG)
    }
  }}
	break;
	case 21:
#line 32 "grace.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case GRACE_SPACE:
      ls
      break;
    case GRACE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GRACE_LANG)
      break;
    case NEWLINE:
      std_newline(GRACE_LANG)
    }
  }}
	break;
	case 22:
#line 79 "grace.rl"
	{te = p+1;}
	break;
	case 23:
#line 69 "grace.rl"
	{te = p;p--;{
    callback(GRACE_LANG, grace_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 69 "grace.rl"
	{te = p;p--;{
    callback(GRACE_LANG, grace_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 79 "grace.rl"
	{te = p;p--;}
	break;
#line 518 "grace.h"
		}
	}

_again:
	_acts = _grace_actions + _grace_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 531 "grace.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _grace_eof_trans[cs] > 0 ) {
		_trans = _grace_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 106 "grace.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(GRACE_LANG) }
}

#endif

/*****************************************************************************/
