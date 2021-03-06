
"""
Semantic Music Typesetting
"""

import tempfile
import json
import os
import xml.etree.ElementTree as ET
import subprocess as sp
import copy as cp
import svgwrite as SW
import svgelements as SE
import svgpathtools as SPT
from math import atan2, hypot


##### Font

_SVGNS = {"ns": "http://www.w3.org/2000/svg"}
# _fontsdict = {}
# installed_fonts = []
def install_font1(path, overwrite=False):
    name, ext = os.path.splitext(os.path.basename(path))
    if os.path.exists(f"./fonts/json/{name}.json") and not overwrite:
        raise FileExistsError(f"{name} is already installed.")
    else:
        D = {}
        D[name] = {}
        if ext == ".svg":
            with open(f"./fonts/json/{name}.json", "w") as file_:
                font = ET.parse(path).getroot().find("ns:defs", _SVGNS).find("ns:font", _SVGNS)
                for glyph in font.findall("ns:glyph", _SVGNS):
                    try:
                        path = SE.Path(glyph.attrib["d"], transform="scale(1 -1)")
                        # .scaled(sx=1, sy=-1)

                        # svgpathtools' scaled() method has a bug which deforms shapes. It offers however good bbox support.
                        # svgelements has unreliable bbox functionality, but transformations seem to be more safe than in pathtools.
                        # Bypass: apply transformations in svgelements and pass the d() to pathtools to get bboxes when needed.
                        min_x, min_y, max_x, max_y = path.bbox()
                        D[name][glyph.get("glyph-name")] = {
                            "d": path.d(), "left": min_x, "right": max_x, 
                            "top": min_y, "bottom": max_y, "width": max_x - min_x,
                            "height": max_y - min_y
                        }
                        # D[name][glyph.get("glyph-name")] = glyph.attrib["d"]
                    except KeyError:
                        pass
                json.dump(D[name], file_, indent=2)
                del path
                del glyph
        else:
            raise NotImplementedError("Non-svg fonts are not supported!")

_loaded_fonts = {}

def _load_fonts():
    for json_file in os.listdir("./fonts/json"):        
        with open(f"./fonts/json/{json_file}") as font:
            _loaded_fonts[os.path.splitext(json_file)[0]] = json.load(font)


# install_font1("./fonts/svg/haydn-11.svg",1)
_load_fonts()

def glyph_names(font):
    return _loaded_fonts[font].keys()

def _get_glyph(name, font): return _loaded_fonts[font][name]
# print(_loaded_fonts)


# ################################
# _fonts = {}
# current_font = "Haydn"
STAFF_HEIGHT_REFERENCE_GLYPH = "clefs.C"


##### Rastral, Dimensions, Margins
_PXLPERMM = 3.7795275591 # Pixel per mm
def mmtopx(mm): return mm * _PXLPERMM

def gould_rastral_height(rastral_number):
    """Behind Bars, pg. 482-3:
    The rastral height is the measurement of one staff-space.
    """
    return {
        "zero": mmtopx(9.2*.25), "one": mmtopx(7.9*.25), "two": mmtopx(7.4*.25),
        "three": mmtopx(7*.25), "four": mmtopx(6.5*.25), "five": mmtopx(6*.25),
        "six": mmtopx(5.5*.25), "seven": mmtopx(4.8*.25), "eight": mmtopx(3.7*.25)
    }[rastral_number]

def chlapik_rastral_height(rastral_number):
    return {
    "zwei": mmtopx(1.88), "drei": mmtopx(1.755), "vier": mmtopx(1.6),
    "fuenf": mmtopx(1.532), "sechs": mmtopx(1.4), "sieben": mmtopx(1.19),
    "acht": mmtopx(1.02)}[rastral_number]


# STAFF_SPACE = chlapik_rastral_height("fuenf")
STAFF_SPACE = gould_rastral_height("zero")
GLOBAL_SCALE = 1.0
# print(_get_glyph("clefs.C", "haydn-11"))
def _scale():
    # return GLOBAL_SCALE * ((4 * STAFF_SPACE) / _getglyph("clefs.C", "Haydn")["height"])
    return GLOBAL_SCALE * ((4 * STAFF_SPACE) / _get_glyph("clefs.C", "haydn-11")["height"])

def toplevel_scale(R): return R * _scale()

_LEFT_MARGIN = mmtopx(36)
_TOP_MARGIN = mmtopx(56)



# ~ Why am I not writing this as a method to FORM?
def _descendants(obj, N, D):
    if isinstance(obj, _Form) and obj.content:
        if N not in D:
            # ~ Shallow copy only the outer content List,
            D[N] = cp.copy(obj.content)
        else:
            D[N].extend(obj.content)
        for C in obj.content:
            _descendants(C, N+1, D)
    return D
    
def descendants(obj, lastgen_first=True):
    D = []
    for _, gen in sorted(_descendants(obj, 0, {}).items(), reverse=lastgen_first):
        D.extend(gen)
    return D


def members(obj): return [obj] + descendants(obj, lastgen_first=False)

def getallin(typeof, obj):
    """Returns an iterable of all types in obj."""
    return filter(lambda O: isinstance(O, typeof), members(obj))


############# Rules
_ruletables = set()

def _pending_ruletables():
    """True if there some ruletables with pending rules."""
    return [rt for rt in _ruletables if rt._pending()]

class RuleTable:
    
    def __init__(self, name=None):
        self.name = name
        self.rules = dict()
        self._order = 0
        self.log = True # Print rules as they are being applied.
        self._hook_registry = []
        self._pred_registry = []
        _ruletables.add(self)
    # def __repr__(self): return f"RuleTable {self.id}"
    def _pending(self):
        """Returns a list of rules of this ruletable: (order, rule-dictionary)
        which are pending for application. If nothing is pending 
        [] is returned."""
        # o=order, rd=rule dict
        return [(o, rd) for (o, rd) in self.rules.items() if not rd["applied"]]
    
    def add(self, hook, pred, desc=None):
        """
        Rule will be added only if at least one of hook or predicate are fresh.
        """
        hhash = hook.__hash__()
        phash = pred.__hash__()
        if hhash not in self._hook_registry or phash not in self._pred_registry:
            self.rules[self._order] = {"desc": desc, "hook": hook, "pred": pred, "applied": False}
            self._order += 1
            self._hook_registry.append(hhash)
            self._pred_registry.append(phash)
            
    def __len__(self): return len(self.rules)


# Common Music Notation, default ruletable for all objects
cmn = RuleTable(name="CMN")
_registry = {}
def getbyid(id_): return _registry[id_]
class _SMTObject:
    def __init__(self, id_=None, domain=None, ruletable=None, toplevel=False):
        self.toplevel = toplevel
        self.ancestors = []
        self.id = id_ or self._assign_id()
        self._svg_list = []
        self.domain = domain
        self.ruletable = ruletable or cmn
        _registry[self.id] = self

    def _pack_svg_list_ip(self): self._notimplemented("_pack_svg_list_ip")
    
    def _notimplemented(self, method_name):
        """Crashs if the derived class hasn't implemented this important method."""
        raise NotImplementedError(f"{self.__class__.__name__} must override {method_name}!")
    
    def _assign_id(self):
        id_ = f"{self.__class__.__name__}{self.__class__._idcounter}"
        self.__class__._idcounter += 1
        return id_

    def addsvg(self, *elements):
        self._svg_list.extend(elements)

    def parent(self): return self.ancestors[-1]
    def root(self): return self.ancestors[0]
    
    def _apply_rules(self):
        """
        Applies rules to self and all it's descendants.
        A rule will look for application-targets exactly once per each 
        rule-application iteration. This means however that a rule might be applied
        to an object more than once, if the object satisfies it's condition.
        """
        depth = -1
        while True:
            pending_rts = _pending_ruletables()
            if pending_rts:
                depth += 1
                for rt in pending_rts:
                    # o_rd=(order, ruledictionary), sort pending rules based on their order.
                    for order, rule in sorted(rt._pending(), key=lambda o_rd: o_rd[0]):
                        if rt.log:
                            print(f"RT: {rt.name}, Depth: {depth}, Order: {order}, Desc: {rule['desc']}")
                        # get in each round the up-to-date list of members (possibly new objects have been added etc....)
                        for m in members(self):
                            if rule["pred"](m):
                                rule["hook"](m)
                                if isinstance(m, HForm): m._lineup() # Das untenstehende scheint sinvoller??!
                                # for a in reversed(m.ancestors):
                                    # if isinstance(a, HForm): a._lineup()
                        # A rule is applied not more than once!
                        rule["applied"] = True
                pending_rts = _pending_ruletables()
            else: break


############ page formats
def page_size(use):
    """Behind Bards, pg. 481, portrait formats (height, width)
    largest (A3) = Largest practical """
    return {
        "largest": (mmtopx(420), mmtopx(297)), 
        "largest_instrumental": (mmtopx(353), mmtopx(250)),
        "smallest_instrumental": (mmtopx(297), mmtopx(210)),
        "printed_sheet_music": (mmtopx(305), mmtopx(229)),
        "printed_choral_music": (mmtopx(254), mmtopx(178))
    }[use]

PAGEH, PAGEW = page_size("largest")

def render(*items):
    D = SW.drawing.Drawing(filename="/tmp/smt.svg", size=(PAGEW, PAGEH), debug=True)
    for item in items:
        item._apply_rules()
        # Form's packsvglst will call packsvglst on descendants recursively
        item._pack_svg_list_ip()
        for elem in item._svg_list:
            D.add(elem)
    D.save(pretty=True)


class _Canvas(_SMTObject):
    def __init__(self, canvas_color=None,
    canvas_opacity=None, xscale=1, yscale=1,
    x=None, y=None,
     # x_locked=False, y_locked=False,
    rotate=0, skewx=0, skewy=0,
    width=None, height=None,
     # width_locked=False,
    canvas_visible=True, origin_visible=True, **kwargs):
        super().__init__(**kwargs)
        self.skewx = skewx
        self.skewy = skewy
        # self.rotate=rotate
        # Only the first item in a hform will need _hlineup, for him 
        # this is set by HForm itself.
        self._is_hlineup_head = False
        self.rotate=rotate
        self.canvas_opacity = canvas_opacity or 0.3
        self.canvas_visible = canvas_visible
        self.canvas_color = canvas_color or SW.utils.rgb(20, 20, 20, "%")
        self.origin_visible = origin_visible
        self._xscale = xscale
        self._yscale = yscale
        # Permit zeros for x and y. xy will be locked if supplied as arguments.
        self._x = 0 if x is None else x
        self.x_locked = False if x is None else True
        self._y = 0 if y is None else y
        self.y_locked = False if y is None else True
        # self.y_locked = y_locked
        # self.x_locked = x_locked
        self._width = 0 if width is None else width
        self._width_locked = False if width is None else True
        self._height = 0 if height is None else height
        self.height_locked = False if height is None else True
        
    @property
    def xscale(self): return self._xscale
    @property
    def yscale(self): return self._yscale
    
    # def unlock(what):
        # if what == "y":
            # self.y_locked = False
    
    @property
    def x(self): return self._x
    @property
    def y(self): return self._y
    
    # # Placeholders
    # @property
    # def top(self): raise NotImplementedError
    # @property
    # def bottom(self): raise NotImplementedError
    # @property
    # def height(self): raise NotImplementedError
    # @property
    # def width(self): raise NotImplementedError
    # @property
    # def left(self): raise NotImplementedError
    # @property
    # def right(self): raise NotImplementedError

    # # X Setters; as these set the x, they have any effect only when x is unlocked.
    # @left.setter
    # def left(self, new): self.x += (new - self.left)
    # @right.setter
    # def right(self, new): self.x += (new - self.right)

    # # Make sure from canvas derived subclasses have implemented these computations.
    # def _compute_width(self):
        # raise NotImplementedError(f"_compute_width not overriden by {self.__class__.__name__}")
    # def _compute_height(self):
        # raise NotImplementedError(f"_compute_height not overriden by {self.__class__.__name__}")
    

    
# def _bboxelem(obj): 
    # return SW.shapes.Rect(insert=(obj.left, obj.top),
                                # size=(obj.width, obj.height), 
                                # fill=obj.canvas_color,
                                # fill_opacity=obj.canvas_opacity, 
                                # id_=obj.id + "BBox")

_ORIGIN_CROSS_LEN = 20
_ORIGIN_CIRCLE_R = 4
_ORIGIN_LINE_THICKNESS = 0.06
def _origelems(obj):
    halfln = _ORIGIN_CROSS_LEN / 2
    return [SW.shapes.Circle(center=(obj.x, obj.y), r=_ORIGIN_CIRCLE_R,
                                    id_=obj.id + "OriginCircle",
                                    stroke=SW.utils.rgb(87, 78, 55), fill="none",
                                    stroke_width=_ORIGIN_LINE_THICKNESS),
            SW.shapes.Line(start=(obj.x-halfln, obj.y), end=(obj.x+halfln, obj.y),
                                        id_=obj.id + "OriginHLine",
                                        stroke=SW.utils.rgb(87, 78, 55), 
                                        stroke_width=_ORIGIN_LINE_THICKNESS),
            SW.shapes.Line(start=(obj.x, obj.y-halfln), end=(obj.x, obj.y+halfln),
                                        id_=obj.id + "OriginVLine",
                                        stroke=SW.utils.rgb(87, 78, 55), 
                                        stroke_width=_ORIGIN_LINE_THICKNESS)]


class _Font:
    """Adds font to MChar & Form"""
    def __init__(self, font=None):
        self.font = font or tuple(_loaded_fonts.keys())[0]


class _Observable(_Canvas):
    
    def __init__(self, color=None, opacity=None, visible=True, **kwargs):
        super().__init__(**kwargs)
        self.color = color or SW.utils.rgb(0, 0, 0)
        self.opacity = opacity or 1
        self.visible = visible
    
    @_Canvas.x.setter
    def x(self, new):
        if not self.x_locked:
            self._x = new
            for a in reversed(self.ancestors):
                a._compute_horizontals()
    
    @_Canvas.y.setter
    def y(self, new):
        if not self.y_locked:
            self._y = new
            for a in reversed(self.ancestors):
                a._compute_verticals()
    
    def _bbox(self): self._notimplemented("_bbox")
        # raise NotImplementedError(f"_bbox method not overriden by {self.__class__.__name__}!")  
    
    @property
    def left(self): return self._bbox()[0]
    @property
    def right(self): return self._bbox()[1]
    @property
    def top(self): return self._bbox()[2]
    @property
    def bottom(self): return self._bbox()[3]
    @property
    def width(self): return self.right - self.left
    @property
    def height(self): return self.bottom - self.top
    # X Setters; as these set the x, they have any effect only when x is unlocked.
    @left.setter
    def left(self, new): self.x += (new - self.left)
    @right.setter
    def right(self, new): self.x += (new - self.right)
    # Y setters
    @top.setter
    def top(self, new): self.y += (new - self.top)
    
        
class MChar(_Observable, _Font):
    
    _idcounter = -1
    
    def __init__(self, name, font=None, **kwargs):
        _Observable.__init__(self, **kwargs)
        _Font.__init__(self, font)
        self.name = name
        # self.glyph = _getglyph(self.name, self.font)
        self._glyph = _get_glyph(self.name, self.font)
        # self._se_path = SE.Path(self.glyph, transform)
        # self.bbox = SPT.Path(self.glyph).bbox()
        # self._path = SPT.Path(_get_glyph_d(self.name, self.font))
        self.canvas_color = SW.utils.rgb(100, 0, 0, "%")
        # self._compute_horizontals()
        # self._compute_verticals()
    
    @_Canvas.xscale.setter
    def xscale(self, new):
        self._xscale = new
        for a in reversed(self.ancestors):
            a._compute_horizontals()
    
    @_Canvas.yscale.setter
    def yscale(self, new):
        self._yscale = new
        for a in reversed(self.ancestors):
            a._compute_verticals()
        
    
    # @_Canvas.x.setter
    # def x(self, new):
        # if not self.x_locked:
            # self._x = new
            # for a in reversed(self.ancestors):
                # a._compute_horizontals()
    # @_Canvas.y.setter
    # def y(self, new):
        # if not self.y_locked:
            # self._y = new
            # for a in reversed(self.ancestors):
                # a._compute_verticals()
    
    # @_Canvas.x.setter
    # def x(self, new):
        # if not self.x_locked:
            # dx = new - self.x # save x before re-assignment!
            # self._x = new
            # self._left += dx
            # self._right += dx
            # for A in reversed(self.ancestors): # An ancestor is always a Form!!
                # A._compute_horizontals()
    
    # @_Canvas.y.setter
    # def y(self, newy):
        # if not self.y_locked:
            # dy = newy - self.y
            # self._y = newy
            # self._top += dy
            # self._bottom += dy
            # for A in reversed(self.ancestors): # A are Forms
                # A._compute_verticals()
            
    # @_Canvas.width.setter
    # def width(self, neww):
        # raise Exception("MChar's width is immutable!")

    # def _compute_left(self):
        # return self.x + toplevel_scale(self.glyph["left"])

    # def _compute_right(self):
        # return self.x + toplevel_scale(self.glyph["right"])

    # def _compute_width(self):
        # return toplevel_scale(self.glyph["width"])
    
    # def _compute_top(self):
        # return self.y + toplevel_scale(self.glyph["top"])
    
    # def _compute_bottom(self):
        # return self.y + toplevel_scale(self.glyph["bottom"])
    
    # def _compute_height(self):
        # return toplevel_scale(self.glyph["height"])
    
    # def _pack_svg_list_ip(self):
        # # Add bbox rect
        # if self.canvas_visible:
            # self._svg_list.append(_bboxelem(self))
        # # Add the music character
        # self._svg_list.append(SW.path.Path(d=_getglyph(self.name, self.font)["d"],
        # id_=self.id, fill=self.color, fill_opacity=self.opacity,
        
        # transform="translate({0} {1}) scale(1 -1) scale({2} {3})".format(
        # self.x, self.y, self.xscale * _scale(), self.yscale * _scale())
        
        
        # ))
        # # Add the origin
        # if self.origin_visible:
            # for elem in _origelems(self):
                # self._svg_list.append(elem)
    
    def _pack_svg_list_ip(self):
        if self.canvas_visible:
            self._svg_list.append(SW.path.Path(
                d=SPT.bbox2path(*self._bbox()).d(),
                fill=self.canvas_color,
                fill_opacity=self.canvas_opacity, 
                id_=f"{self.id}-BBox")
                )
        # Music character itself
        self._svg_list.append(SW.path.Path(
            d=self._path().d(), id_=self.id,
            fill=self.color, fill_opacity=self.opacity,
            # transform="translate({0} {1}) scale({2} {3})".format(
                # self.x, self.y, self.xscale * _scale(), self.yscale * _scale())
        ))
        # Add the origin
        if self.origin_visible:
            for elem in _origelems(self):
                self._svg_list.append(elem)
    
    # svgelements
    def _path(self):
        path = SE.Path(self._glyph)
        path *= f"scale({self.xscale * _scale()}, {self.yscale * _scale()})"
        # First rotate at 00,
        path *= f"rotate({self.rotate}deg)"
        # then move.
        path *= f"translate({self.x}, {self.y})"
        return path
        # return SE.Path(self._glyph, transform=f"rotate({self.rotate}) scale({self.xscale*_scale()} {self.yscale*_scale()})")
    
    # svgelements bbox seems to have a bug getting bboxes of transformed (rotated) paths,
    # use svgpathtools bbox instead (xmin, xmax, ymin, ymax).
    def _bbox(self): return SPT.Path(self._path().d()).bbox()
    
    # @property
    # def left(self): return self._bbox()[0]
    # @property
    # def right(self): return self._bbox()[1]
    # @property
    # def top(self): return self._bbox()[2]
    # @property
    # def bottom(self): return self._bbox()[3]
    # @property
    # def width(self): return self.right - self.left
    # @property
    # def height(self): return self.bottom - self.top
    
    # # X Setters; as these set the x, they have any effect only when x is unlocked.
    # @left.setter
    # def left(self, new): self.x += (new - self.left)
    # @right.setter
    # def right(self, new): self.x += (new - self.right)
    
    

class _Form(_Canvas, _Font):

    _idcounter = 0

    def __init__(self, font=None, content=None, **kwargs):
        self.content = content or []
        _Canvas.__init__(self, **kwargs)
        _Font.__init__(self, font)
        # These attributes preserve information about the Height of a form object. These info
        # is interesting eg when doing operations which refer to the height of a staff. These values
        # should never change, except with when the parent is shifted, they move along of course!
        # In fix-top & bottom is the values of x-offset and possibly absolute x included (self.y).
        
        # self.fixtop = self.y + toplevel_scale(_getglyph(STAFF_HEIGHT_REFERENCE_GLYPH, self.font)["top"])
        # self.fixbottom = self.y + toplevel_scale(_getglyph(STAFF_HEIGHT_REFERENCE_GLYPH, self.font)["bottom"])
        # self.FIXHEIGHT = toplevel_scale(_getglyph(STAFF_HEIGHT_REFERENCE_GLYPH, self.font)["height"])
        # print(">>>", self.id, toplevel_scale(_get_glyph(STAFF_HEIGHT_REFERENCE_GLYPH, self.font)["top"]))
        self.fixtop = self.y + toplevel_scale(_get_glyph(STAFF_HEIGHT_REFERENCE_GLYPH, self.font)["top"])
        self.fixbottom = self.y + toplevel_scale(_get_glyph(STAFF_HEIGHT_REFERENCE_GLYPH, self.font)["bottom"])
        self.FIXHEIGHT = toplevel_scale(_get_glyph(STAFF_HEIGHT_REFERENCE_GLYPH, self.font)["height"])
        
        
        for D in descendants(self, False):
            D.ancestors.insert(0, self) # Need smteq??
        for c in self.content:
            # These assignments take place only if xy are not locked!
            c.x = self.x
            c.y = self.y
            
            # if not c.x_locked:
                # c.x += self.x
            if not c.y_locked:
                # # c.y += self.y
                # c.y = self.y
                
                # If child is to be relocated vertically, their fix-top & bottom can not be
                # the original values, but must move along with the parent.
                if isinstance(c, _Form):
                    c.fixtop += self.y
                    # c.fixtop = self.y
                    c.fixbottom += self.y
                    # Fixheight never changes!
    
    def delcont(self, test):
        for i, c in enumerate(self.content):
            if test(c): del self.content[i]
    
    def _compute_horizontals(self):
        self._left = self._compute_left()
        self._right = self._compute_right()
        self._width = self._compute_width()

    def _compute_verticals(self):
        self._top = self._compute_top()
        self._bottom = self._compute_bottom()
        self._height = self._compute_height()

    # Children is a sequence. This method modifies only ancestor lists.
    def _establish_parental_relationship(self, children):
        for child in children:
            assert isinstance(child, _SMTObject), "Form can only contain MeObjs!"
            child.ancestors.insert(0, self)
            if isinstance(child, _Form):
                for D in descendants(child, False):
                    D.ancestors.insert(0, self)
            for A in reversed(self.ancestors):
                child.ancestors.insert(0, A)
                if isinstance(child, _Form):
                    for D in descendants(child, False):
                        D.ancestors.insert(0, A)

    @_Canvas.x.setter
    def x(self, new):
        if not self.x_locked:
            dx = new - self.x
            self._x = new
            self._left += dx
            self._right += dx
            for D in descendants(self, False):
                # Descendants' x are shifted by delta-x. 
                D._x += dx
                if isinstance(D, _Form):
                    D._left += dx
                    D._right += dx
            for A in reversed(self.ancestors):
                A._compute_horizontals()

    @_Canvas.y.setter
    def y(self, new):
        if not self.y_locked:
            dy = new - self.y
            self._y = new
            self._top += dy
            self._bottom += dy
            for D in descendants(self, False):
                D._y += dy
                if isinstance(D, _Form):
                    # # D._y += dy
                    D._top += dy
                    D._bottom += dy
            # Shifting Y might have an impact on ancestor's width!
            for A in reversed(self.ancestors):
                A._compute_verticals()
    
    def _compute_left(self):
        """Determines the left-most of either: form's own x coordinate 
        or the left-most site of it's direct children."""
        return min([self.x] + list(map(lambda c: c.left, self.content)))
        # return min(self.x, *[c.left for c in self.content])
        # return self._bbox()[0]

    def _compute_right(self):
        if self._width_locked: # ,then right never changes!
            return self.left + self.width
        else:
            return max([self.x] + list(map(lambda c: c.right, self.content)))
    # def _compute_right(self): return self._bbox()[1]

    def _compute_width(self):
        # # print(self.id)
        # if self._width_locked:
            # return self.width
        # else:
            # return self.right - self.left
        return self.width if self._width_locked else (self.right - self.left)

    def _compute_top(self):
        return min([self.fixtop] + list(map(lambda c: c.top, self.content)))
        # return min(self.fixtop, self._bbox()[2])
    
    def _compute_bottom(self):
        return max([self.fixbottom] + list(map(lambda c: c.bottom, self.content)))
        # return max(self.fixbottom, self._bbox()[3])
    
    def _compute_height(self): 
        return self.height if self.height_locked else self.bottom - self.top
    
    def _pack_svg_list_ip(self):
        # Bbox
        if self.canvas_visible: 
            # self._svg_list.append(_bboxelem(self))
            self._svg_list.append(
                SW.shapes.Rect(insert=(self.left, self.top),
                                size=(self.width, self.height), 
                                fill=self.canvas_color,
                                fill_opacity=self.canvas_opacity, 
                                id_=f"{self.id}-BBox")
            )
        # Add content
        for C in self.content:
            # C.xscale *= self.xscale
            # C.yscale *= self.yscale
            # Recursively pack svg elements of each child:
            C._pack_svg_list_ip() 
            self._svg_list.extend(C._svg_list)
        # Origin
        if self.origin_visible: self._svg_list.extend(_origelems(self))
        
    # def _pack_svg_list_ip(self):
        # # Bbox
        # if self.canvas_visible:
            # self._svg_list.append(SW.path.Path(
                # d=SPT.bbox2path(*self._bbox()).d(),
                # fill=self.canvas_color,
                # fill_opacity=self.canvas_opacity, 
                # id_=f"{self.id}-BBox")
                # )
        # # Add content
        # for C in self.content:
            # C.xscale *= self.xscale
            # C.yscale *= self.yscale
            # C._pack_svg_list_ip() # Recursively gather svg elements
            # self._svg_list.extend(C._svg_list)
        # # Origin
        # # if self.origin_visible: self._svg_list.extend(_origelems(self))
        
    @property
    def left(self): return self._left
    @property
    def right(self): return self._right
    @property
    def top(self): return self._top
    @property
    def bottom(self): return self._bottom
    @property
    def width(self): return self._width
    @property
    def height(self): return self._height
    
    # Setters
    @left.setter
    def left(self, new):
        self.x += (new - self.left)
    
    @right.setter
    def right(self, new): 
        self.x += (new - self.right)
    @top.setter
    def top(self, new): self.y += (new - self.top)
    
    @width.setter
    def width(self, new):
        if not self._width_locked:
            self._right = self.left + new
            self._width = new
            # self.right = self.left + new
            for A in reversed(self.ancestors):
                A._compute_horizontals()
    
    # # SPT bbox output: xmin, xmax, ymin, ymax
    # def _bbox(self):
        # # print(">>",self.id, [[*c._bbox()] for c in self.content])
        # # return SPT.Path(*[SPT.bbox2path(*c._bbox()) for c in self.content]).bbox()
        # if self.content:
            # bboxs = [c._bbox() for c in self.content]
            # minx = min(self.x, *[bb[0] for bb in bboxs])
            # maxx = max(self.x, *[bb[1] for bb in bboxs])
            # miny = min(self.y, *[bb[2] for bb in bboxs])
            # maxy = max(self.y, *[bb[3] for bb in bboxs])
            # return SPT.Path(SPT.bbox2path(minx, maxx, miny, maxy)).bbox()
        # else:
            # return 0, 0, self.fixtop, self.fixbottom


class SForm(_Form):
        
    def __init__(self, **kwargs):
        _Form.__init__(self, **kwargs)
        self.canvas_color = SW.utils.rgb(0, 100, 0, "%")
        self.domain = kwargs.get("domain", "stacked")
        # Content may contain children with absolute x, so compute horizontals with respect to them.
        # See whats happening in _Form init with children without absx!
        self._compute_horizontals()
        self._compute_verticals()
    
    # Sinnvoll nur in rule-application-time?!!!!!!!!!!!!!!!
    def append(self, *children):
        """Appends new children to Form's content list."""
        self._establish_parental_relationship(children)
        for c in children:
            c.x = self.x
            c.y = self.y
        self.content.extend(children)
        # # Having set the content before would have caused assign_x to trigger computing horizontals for the Form,
        # # which would have been to early!????
        self._compute_horizontals()
        self._compute_verticals()
        for A in reversed(self.ancestors):
            if isinstance(A, _Form) and not isinstance(A, SForm):
                A._lineup()
            A._compute_horizontals()
            A._compute_verticals()


class HForm(_Form):

    def __init__(self, **kwargs):
        _Form.__init__(self, **kwargs)
        # self.abswidth = abswidth
        self.canvas_color = SW.utils.rgb(0, 0, 100, "%")
        self.domain = kwargs.get("domain", "horizontal")
        # Lineup content created at init-time,
        self._lineup()
        # then compute surfaces.
        self._compute_horizontals()
        self._compute_verticals()
            
    def _lineup(self):
        for a, b in zip(self.content[:-1], self.content[1:]):            
            b.left = a.right

class VForm(_Form):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._lineup()
        self._compute_horizontals()
        self._compute_verticals()
    def _lineup(self):
        for a, b in zip(self.content[:-1], self.content[1:]):
            b.top = a.bottom
    def append(self, *children):
        """Appends new children to Form's content list."""
        self._establish_parental_relationship(children)
        for c in children:
            c.x = self.x
            c.y = self.y
        self.content.extend(children)
        # # Having set the content before would have caused assign_x to trigger computing horizontals for the Form,
        # # which would have been to early!????
        self._lineup()
        self._compute_horizontals()
        self._compute_verticals()
        for A in reversed(self.ancestors):
            if isinstance(A, _Form) and not isinstance(A, SForm): # V & H
                A._lineup()
            A._compute_horizontals()
            A._compute_verticals()
        
# https://github.com/meerk40t/svgelements/issues/102
class _LineSeg(_Observable):
    """Angle in degrees"""
    _idcounter = -1
    def __init__(self, length=None, direction=None, thickness=None, angle=None, endxr=None, endyr=None,
    # start=None, end=None,
    **kwargs):
        super().__init__(**kwargs)
        self.length = length or 0
        # self.color = color or SW.utils.rgb(0, 0, 0)
        # self.opacity = opacity
        self._angle = angle or 0
        self._thickness = thickness or 0
        self.direction = direction or 1
        self.endxr = endxr or 0
        self.endyr = endyr or 0
        # self.start = start
        # self.end = end
        # self._x2 = 
        # self._y2=y2
        # self._compute_horizontals()
        # self._compute_verticals()


    # Override canvas packsvglist
    def _pack_svg_list_ip(self):
        # bbox
        self._svg_list.append(SW.path.Path(
                d=SPT.bbox2path(*self._bbox()).d(),
                fill=SW.utils.rgb(100,100,0,"%"),
                fill_opacity=self.canvas_opacity, 
                id_=f"{self.id}-BBox")
                )
        self._svg_list.append(SW.path.Path(
            d=self._rect().d(),
            fill=self.color, fill_opacity=self.opacity
        ))
        # Add the origin
        if self.origin_visible:
            for elem in _origelems(self):
                self._svg_list.append(elem)
        
        
    # @property
    # def length(self): return self._length
    
    # @_Canvas.x.setter
    # def x(self, new):
        # if not self.x_locked:
            # # dx = new - self.x
            # self._x = new
            # # self._left += dx
            # # self._right += dx
            # for A in reversed(self.ancestors): # An ancestor is always a Form!!
                # A._compute_horizontals()
    
    # @_Canvas.y.setter
    # def y(self, new): 
        # if not self.y_locked:
            # # dy = new - self.y
            # self._y = new
            # # self._top += dy
            # # self._bottom += dy
            # for A in reversed(self.ancestors): # An ancestor is always a Form!!
                # A._compute_verticals()
    
    @property
    def thickness(self): return self._thickness
    # xmin, xmax, ymin, ymax
    def _bbox(self): 
        return SPT.Path(self._rect().d()).bbox()








class VLineSeg(_LineSeg):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    # def angle(self):
        # """Inverse tangent of the line in radians"""
        # return atan2(self.y2 - self.y, self.x2 - self.x)
    # def _recty(self): return self.y - self.thickness*.5
    # def _rect(self):
        # R = SE.Rect(self.x, self._recty(), hypot(self.x2-self.x, self.y2-self.y), self.thickness)
        # R *= f"rotate({self.angle()}rad {self.x} {self.y})"
        # return R
    
    def _rect(self):
        rect = SE.Rect(
            # Rect(x, y, width, height, rx, ry, matrix, stroke, fill)
            self.x - self.thickness*.5, self.y, 
            self.thickness, self.length,
            self.endxr, self.endyr
            )
        rect *= f"skew({self.skewx}, {self.skewy}, {self.x}, {self.y})"
        rect *= f"rotate({self.rotate}deg, {self.x}, {self.y})"
        return rect
    

    
    # @property
    # def left(self): return self._bbox()[0]
    # @property
    # def right(self): return self._bbox()[1]
    # @property
    # def top(self): return self._bbox()[2]
    # @property
    # def bottom(self): return self._bbox()[3]
    # @property
    # def width(self): 
        # # return self.thickness
        # return self.right-self.left
    # @property
    # def height(self):
        # # return self.length
        # return self.bottom -self.top
    
    # def _compute_width(self): return self.thickness
    # def _compute_left(self): return self.x - self.thickness*.5
    # def _compute_right(self): return self.x + self.thickness*.5
    # def _compute_height(self): return self.length
    # def _compute_bottom(self): return self.y + self.length
    # def _compute_top(self): return self.y
    # @_LineSeg.length.setter
    # def length(self, new):
        # self._length = new
        # self._compute_verticals()
        # for a in reversed(self.ancestors):
            # a._compute_verticals()

class HLineSeg(_LineSeg):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    def _rect(self):
        rect = SE.Rect(
            self.x, self.y - self.thickness*.5,
            self.length, self.thickness,
            self.endxr, self.endyr
            )
        rect *= f"scale({self.direction} 1)"
        rect *= f"skew({self.skewx}, {self.skewy}, {self.x}, {self.y})"
        rect *= f"rotate({self.rotate}deg, {self.x}, {self.y})"
        return rect
    # def _compute_width(self): return self.length
    # def _compute_height(self): return self.thickness
    # def _compute_left(self): return self.x
    # def _compute_right(self): return self.x + self.length
    # def _compute_top(self): return self.y - self.thickness*.5
    # def _compute_bottom(self): return self.y + self.thickness*.5




