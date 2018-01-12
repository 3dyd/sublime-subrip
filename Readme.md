# SubRip plugin for Sublime Text 3

SubRip (`*.srt`) format extensions:
- syntax highlighter
- few commands
- auto cue

## Commands

Commands are prefixed with `SubRip:` in Command Palette.

### Shift

Shift timestamps of selected or all cues.

Timestamp format is the same as the one used in SubRip. All timestamp parts are optional.

Examples:

Rule | Time Interval
------------ | -------------
`01:02:03,004` | Canonical notation. 1 hour 2 min 3 sec 4 msec
`3` | 3 seconds
`,4` | 4 msec
`3,4` | 3004 msec
`3,004` | 3004 msec
`3,400` | 3400 msec
`2:` | 2 minutes
`2::` | 2 hours

### Recount

Renumber all cue counters in the file.

### Remove Cue

Remove cue(s) under cursor(s) or in selection(s). Performs recount after removal.

## Auto Cue

Inserts cue snippet when you press `Enter` on empty line. Snippet has correct counter and timestamps of previous cue. You can walk through timestamps parts using `Tab` key.

It can be disabled by setting `auto_cue` parameter to `false`. Parameter can be edited using menu `Preferences -> Package Settings -> SubRip -> Settings — User`.
