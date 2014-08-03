Intro
=====

MSR605 is a very well built and popular magnetic card reader/writer.
msrx is a library and a command line utility that allows talking to this
device.

Features
========

 * msrx python module compatible with python 2.7+ and python 3
 * Command line utility with read, write and erase functionality

Installation
============

    $ pip install msrx

Usage
=====

To read a card's data, run the following and swipe a card:

    $ msrx read
    %PA1VSBUTT0 .8W11(BT003423342?|;943300000002342?:|

The output is a pipe ('|') separated track data in ISO-7811 format. In
the above example, only tracks 1 and 2 have data in them.

To erase a card, run the following and swipe a card (**WARNING** this is
non-reversible):

    $ msrx erase -t 1,3

The above erases tracks 1 and 3. To erase all tracks, leave out `-t`.

To write to a card, run the following and swipe a card:

    $ echo '%HAPPY?||;99?' | msrx write

This writes to tracks 1 and 3 because we left track 2 data empty. Note
that restrictions apply as to what set of characters and in what format
may be stored in each track. Consult ISO-7811 parts 2 and 6 for more
information.

To see other options, run msrx with `-h` option.

To use msrx as a library:

    import msrx
    mymsrx = msrx.MSRX('/dev/ttyUSB0')
