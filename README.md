sam-basic
=========

This is the interpreter for the SAM-BASIC language, which I created while procrastinating on my college applications. I have never written a line of BASIC code in my life, but this language is built on what I've seen of it:

* Line numbers
* Goto Statement
* ALL CAPS

This said, BASIC looks to have an actual parser, while SAM-BASIC has a mess worse that what the C Shell uses. Everything is done with regular expressions.

Some goals for the future:

* Add arrays
* Remove all uses of `eval` from the source
* Add metadata to events
* Make the `UNDEFINED` event fire when it's supposed to
* Add key-by-key input
* Rewrite in C
* Add functions
* Add `DO` statement that executes a series of statements
* Add interface for C APIs
