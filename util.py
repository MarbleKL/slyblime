import asyncio
from bisect import bisect_left
import re
from math import inf

# Needed because we shadow one thing from the default ST stuff
import sublime
from sublime import *
from typing import *

from .sexpdata import loads, dumps

import uuid

def get_if_in(dictionary, *items):
    return tuple(dictionary[item] if item in dictionary else None 
                                  for item in items)

async def show_input_panel(loop, window, prompt, initial_value, on_change=None):
    future = loop.create_future()
    print("OK")
    def on_confirm(value):
        nonlocal future
        async def set_result(future, value):
            future.set_result(value)
        asyncio.run_coroutine_threadsafe(set_result(future, value), loop)
    def on_cancel():
        nonlocal future
        async def set_result(future):
            future.cancel()
        asyncio.run_coroutine_threadsafe(set_result(future), loop)
    window.show_input_panel(prompt, initial_value, on_confirm, on_change, on_cancel)
    await future
    return future.result()

async def show_quick_panel(loop, window, items, flags, selected_index=0, on_highlighted=None):
    future = loop.create_future()
    def on_done(index):
        nonlocal future
        async def set_result(future, index):
            future.set_result(index)
        asyncio.run_coroutine_threadsafe(set_result(future, index), loop)
    window.show_quick_panel(items, on_done, flags, selected_index, on_highlighted)
    await future
    return future.result()


def find_closest_before_point(view, point, regex):
    possibilities = view.find_all(regex)
    if len(possibilities) == 0: 
        return None
    i = bisect_left(
        [possibility.begin() for possibility in possibilities], 
        point) - 1
    if i < 0:
        return None
    return possibilities[i]


# Prefer before is used to determine which value to send in the event of
# two regions equidistant from the point
def find_closest(view, point, regex, prefer_before=True):
    possibilities = view.find_all(regex)
    if len(possibilities) == 0: 
        return None
    i = bisect_left(
        [possibility.begin() for possibility in possibilities], 
        point)
    if i < -1:
        return None
    elif i == 0:
        return possibilities[i]
    elif i >= len(possibilities):
        return possibilities[i-1]

    before_point = possibilities[i-1]
    after_point = possibilities[i]
    distance = point - before_point.end()
    distance1 = after_point.begin() - point

    if distance < distance1:
        return before_point
    elif distance1 < distance:
        return after_point
    elif prefer_before:
        return before_point
    else:
        return after_point

PACKAGE_REGEX = r"(?i)^\((cl:|common-lisp:)?in-package\ +[ \t']*([^\)]+)[ \t]*\)"
IN_PACKAGE_REGEX = re.compile(r"(?i)(cl:|common-lisp:)?in-package\ +[ \t']*")


# Equivalent to Sly Current Package
def current_package(view, point=None, return_region=False):
    settings = view.settings()
    if settings.get("sly-repl") and (package := settings.get("package")):
        if return_region:
            # TODO: Find a way to get the region before the prompt and indicate as package
            return package, Region(settings.get("prompt-region")[0], settings.get("prompt-region")[1])
        return package
    else:
        if not point:
            point = view.sel()[0].begin()
        region = find_closest_before_point(view, point, PACKAGE_REGEX)
        # Remove the IN-PACKAGE symbol.
        if region is None: 
            if return_region: return None, None 
            return None

        info = IN_PACKAGE_REGEX.sub("", view.substr(region)[1:-1])

        if return_region:
            return info, region


def compute_flags(flags):
    computed_flags = 0
    for flag in flags:
        computed_flags = computed_flags | globals()[flag.upper()]
    return computed_flags


def safe_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return None


def load_resource(path):
    return sublime.load_resource(f"Packages/{__name__.split('.')[0]}/{path}")


def add_regions_temporarily(view, regions, duration, *args):
    id = uuid.uuid4().hex
    view.add_regions(id, regions, *args)
    set_timeout_async(lambda: view.erase_regions(id), duration)


def highlight_region (view, region, config, duration=None, *args):
    if not duration:
       duration = config['duration'] * 1000
    add_regions_temporarily(view, [region], duration, *args)


def set_status(view, session):
    if session:
        slynk = session.slynk
        message = [
            "[",
            slynk.connexion_info.lisp_implementation.name,
            "] ",
            slynk.host, 
            ":",
            str(slynk.port)]
    else:
        message = []
    view.set_status("slynk", "".join(message))



def in_lisp_file(view, settings: Callable):
    matches = re.findall(
        settings().get("compilation")["syntax_regex"], 
        view.settings().get("syntax"))
    return len(matches) > 0


SCOPE_REGEX = re.compile(r"(meta.(parens|section))")

def get_scopes(view, point):
    return view.scope_name(point).strip().split(" ")
    
def determine_depth(scopes):
    depth = 0
    for scope in scopes:
        # TODO: replace with customisable regex
        if SCOPE_REGEX.match(scope):
            depth += 1
    return depth

def find_form_region(view, point: int=None, desired_depth=1, max_iterations=100) -> Region: 
    point = point or view.sel()[0].begin()
    region = view.extract_scope(point)
    # It only has the scope of the file, so its outside
    # a toplevel form, we need to find one.
    if len(get_scopes(view, point)) == 1:
        region = find_closest_before_point(view, point, r"\S")
        distance_to_first = point - region.end() 
        region1 = view.find(r"\S", point) # finds closest after point
        if (point - region.end()) >= (region1.begin() - point):
            region = region1
    """
     This algorithm will go through a form, going to the start
     of every scope and checking if it is of form 
     ["source.lisp", "meta.parens.lisp"] or something*
     at which point it'll return the region. Otherwise, it
     keeps on expanding the scope
    
     *deliberately vague in the while statement to allow for different
     syntax scoping (e.g. "source.cl" or "source.scm").
    """
    point: int = region.begin()
    scopes: str = get_scopes(view, point)
    depth: int = determine_depth(scopes)
    if desired_depth == None: # Select the current depth
        desired_depth = depth
    previous_region = Region(-1, -1)
    iterations = 0
    forward = True
    def should_continue():
        return ((depth > desired_depth 
                      or (desired_depth == 1 and len(scopes) > 2)) 
                and iterations < max_iterations)
    while should_continue():
        if previous_region != region:
            point = region.begin() if forward else region.end()
        else:
            point += -1 if forward else +1

        scopes = get_scopes(view, point)
        depth = determine_depth(scopes)
        previous_region = region
        region = view.extract_scope(point)
        iterations += 1
        # We check if we reached the "(" of a top-level form
        # and if we did we go the opposite way until we find
        # a scope where the extract_scope is the top-level form
        if len(scopes) == 3 and "begin" in scopes[2]:
            forward = False
    if depth == desired_depth:
        return region
    elif iterations >= max_iterations:
        raise RuntimeWarning("Search iterations exceeded")
    else:
        print(depth, desired_depth)
        return None


def event_to_point(view, event: Dict[str, int]) -> Tuple[int]:
    return view.window_to_text((event["x"], event["y"]))

def nearest_region_to_point (point: int, regions: Iterable[Region]) -> Optional[Region]:
    if len(regions) == 0:
        return None
    minimal_distance = inf
    for region in regions:
        distance = min(
            abs(region.begin() - point), 
            abs(region.end() - point))
        if distance < minimal_distance:
            result = region
            if result.contains(point):
                break
    return result
