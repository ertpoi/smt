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
        note.head = Char(name={
            "w": "noteheads.s0",
            "h": "noteheads.s1",
            "q": "noteheads.s2"
        }[note.duration])
    elif isinstance(note.duration, (float, int)):
        note.head = Char(name={
            1: "noteheads.s0",
            .5: "noteheads.s1",
            .25: "noteheads.s2"
        }[note.duration])

def setstem(self):
    s = Stem(length=10,thickness=10, xlocked=False, ylocked=False)
    # print(s, s.x, s.y)
    self.stem = s
    # self.content.append(Stem(x=self.x+.5, y=self.y,length=10,thickness=1,endxr=10,endyr=10))
    # print(self.stem.left)
    

def notehead_vertical_pos(note):
    if isinstance(note.pitch, list):
        p = note.pitch[0]
        okt = note.pitch[1]
        note.headsymbol.y = ((note.fixbottom - {"c":-STAFF_SPACE, "d":-(.5 * STAFF_SPACE)}[p]) + ((4 - okt) * 7/8 * note.FIXHEIGHT))

# def draw_staff(self):
    # for i in range(-2, 3):
        # y_= i *space + self.y
        # l=_VLineSegment(x=self.left, y=y_, length=self.width, thickness=1)
        # l.angle = 0
        # self._svglist.append(l.svg)
        
        
def make_accidental_char(accobj):
    accobj.char=Char(name="accidentals.sharp")
    accobj.append(accobj.char)

def make_clef_char(clefobj):
    clefobj.symbol = Char(name={"treble":"clefs.G", "g": "clefs.G",
    "bass":"clefs.F", "alto":"clefs.C"}[clefobj.pitch])
    clefobj.append(clefobj.symbol)


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
    return {Note: 10, Clef:10, Accidental: 1}[type(obj)]

def f(h):
    # print([(a.x, a.left, a.width) for a in h.content])
    clkchunks=clock_chunks(h.content)
    # print(clkchunks)
    clocks = list(map(lambda l:l[0], clkchunks))
    perfwidths = compute_perf_punct(clocks, h.width)
    if allclocks(h):
        for C, w in zip(h.content, perfwidths):
            C.width += w
    else:
        print("-------")
        for c,w in zip(clkchunks, perfwidths):
            clock = c[0]
            nonclocks = c[1:]
            s=sum(map(lambda x:x.width + right_guard(x), nonclocks))
            if s < w:
                # add rest of perfect width - sum of nonclocks
                clock.width += (w - s)
                for a in nonclocks:
                    a.width += right_guard(a)

cmn.add(make_notehead, (Note,), ["treble"])
cmn.add(setstem, (Note,), ["treble"])
cmn.add(make_accidental_char, (Accidental,), ["treble", "bass"])
cmn.add(f, (HForm,), ["horizontal"])


# 680.3149 pxl
gemischt=[
Note(domain="treble", duration=1, pitch=["c",4]),
Accidental(pitch=["c", 4],domain="treble"),
Accidental(domain="bass"), 
# Clef(pitch="g",domain="treble"),
Accidental(domain="treble"),
Note(pitch=["d",4],domain="treble", duration=.5),
# Clef(domain="treble",pitch="bass"),
Accidental(domain="treble",pitch=["d",4])
]


# gemischt=[Note(domain="treble", duration=1) for _ in range(10)]
# for a in notes:
    # print(a.content)
    # for s in a.content:
        # s.x += 10
        # print(s.x)
# print(notes[0].width, notes[0].content[0].width)
# print(list(map(lambda n:n.x, notes[0].content)))
# print(notes[0].width)
h=HForm(ruletable=cmn, content=gemischt, width=mmtopxl(50),x=10,y=200, canvas_opacity=.2, widthlocked=True)
# h2=cp.deepcopy(h)
# print(h2.y)
# h2.y += 30
# h2.x += 30
# print(h2.y)
render(h,)
