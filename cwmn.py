from random import randint, choice
from score import *
""".smt File
[unknownName knownExpression] is an assignment.
[knownName knownExpression] ?
[myNote [note
            [domain treble]
            [color [rgb 100 10 20]]
            [absx 100] [absy 100]]]
[sform [content myNote]]
[render sform]
; Here we bind Python code
[py def double(x): return x * 2]
[double 4]
[page1 [page [title [bold Douxe [size [cm 10] Notation]] pour Piano]]]
Syntax known Names:
[SIZE Type:Number Type:String] Returns a new String with the size Number.  
[BOLD Type:String] Returns a new String in bold.

[RGB Type:Number Type:Number Type:Number] Returns an RGB Object for use as the value for the COLOR attribute.
[COLOR red] Designates the attribute color to be the string value red.
[LOOP variable Type:Sequence|[RANGE Type:Integer Type:Integer]]

sehr high-level!!
[seq [content [note] [note] [rest] [chord] [timesig 3 4] [clef treble]] [yoffset -10] [domain bass]]

Hier deklarieren wir zwei Notenamen:
[c4a [note [spn 60]]]
[c4b [note [spn 60]]]


Und hier verwenden wir die Namen
[line [note [spn f # 5] [ 1/4]]
    [rest [duration .25]]
     [chord (yoff -15) 
        [note [spn f # 5]]
         [note [spn f#5]]
          c4a c4b]]
Immer die letzte  Form wird gerendert! (und überigens alles was 
nicht in eckigen Klammern steht ist Comment! Wenn ich mitten im Kommentieren [print [+ 3 4]]
dann wird es geprinted! Also aufpassen mit eckigen Klammern!)
:-)
[print hello beautiful world of music typesetting!]
"""


def make_notehead(note):
    # setter for head? to append automatically
    if isinstance(note.duration, str):
        note.head_char = Char(name={
            "w": "noteheads.s0",
            "h": "noteheads.s1",
            "q": "noteheads.s2"
        }[note.duration])
    elif isinstance(note.duration, (float, int)):
        note.head_char = Char(name={
            1: "noteheads.s0",
            .5: "noteheads.s1",
            .25: "noteheads.s2"
        }[note.duration])
    # note.head.y += randint(-100, 100)
    note.append(note.head_char)

def make_accidental_char(accobj):
    accobj.append(Char(name="accidentals.sharp"))

def make_clef_char(clefobj):
    clefobj.char = Char(name={"treble":"clefs.G",
    "bass":"clefs.F", "alto":"clefs.C"}[clefobj.pitch])
    clefobj.append(clefobj.char)


def decide_unit_dur(dur_counts):
    # return list(sorted(dur_counts.items()))[1][1]
    return list(sorted(dur_counts, key=lambda l:l[0]))[0][1]

punct_units = {1:7, .5: 5, .25: 3.5, 1/8: 2.5, 1/16: 2}

def ufactor(udur, dur2):
    return punct_units[dur2] / punct_units[udur]
    
def compute_perf_punct(clocks, w):
    # notes=list(filter(lambda x:isinstance(x, Note), clocks))
    durs=list(map(lambda x:x.duration, clocks))
    dur_counts = []
    for d in set(durs):
        # dur_counts[durs.count(d)] =d
        # dur_counts[d] =durs.count(d)
        dur_counts.append((durs.count(d), d))
    udur=decide_unit_dur(dur_counts)
    uw=w / sum([x[0] * ufactor(udur, x[1]) for x in dur_counts])
    perfwidths = []
    for x in clocks:
        space = ((uw * ufactor(udur, x.duration)) - x.width)
        perfwidths.append(space)
        # x.width += ((uw * ufactor(udur, x.duration)) - x.width)
    return perfwidths

def right_guard(obj):
    return {Note: 2, Clef:10, Accidental: 1}[type(obj)]

def f(h):
    clkchunks=clock_chunks(h.content)
    # print(clkchunks)
    clocks = list(map(lambda l:l[0], clkchunks))
    perfwidths = compute_perf_punct(clocks, h.width)
    if allclocks(h):
        for C, w in zip(h.content, perfwidths):
            C.width += w
    else:
        for c,w in zip(clkchunks, perfwidths):
            clock = c[0]
            nonclocks = c[1:]
            s=sum(map(lambda x:x.width + right_guard(x), nonclocks))
            if s < w:
                # add rest of perfect width - sum of nonclocks
                clock.width += (w - s)
                for a in nonclocks:
                    a.width += right_guard(a)
            
r((Note,), ["treble"], make_notehead)
r((Accidental,), ["treble", "bass"], make_accidental_char)
r((Clef,),["treble"], make_clef_char)
r((HForm,), ["horizontal"], f)



print(mmtopxl(100))
# 680.3149 pxl
gemischt=[Note(domain="treble", duration=1), Accidental(domain="treble"),Accidental(domain="bass"), Clef("alto",domain="treble"),Accidental(domain="treble"),
            Note(domain="treble", duration=.5),Clef("bass",domain="treble"), Accidental(domain="treble")]
# gemischt=[Note(domain="treble", duration=1) for _ in range(10)]
# for a in notes:
    # print(a.content)
    # for s in a.content:
        # s.x += 10
        # print(s.x)
# print(notes[0].width, notes[0].content[0].width)
# print(list(map(lambda n:n.x, notes[0].content)))
# print(notes[0].width)
h=HForm(abswidth=mmtopxl(100),content=gemischt, absx=200,absy=200, canvas_opacity=.2)
# print(list(map(lambda n:n._fixtop, notes)))
h.render()
# print(h.content[0].content)
# print(mmtopxl(100),sum(list(map(lambda x:x.width, notes))))
# a=E.SForm(xoff=20, content=[Char("clefs.F", xoff=50)])
# b=HForm(absy=100, content=[a])
# b.render()
