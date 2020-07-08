from sublime import *
import sublime_plugin, threading, asyncio  # import the required modules

from operator import itemgetter

from . import util, sexpdata, debugger

from .slynk import slynk

import logging
import functools
from typing import *

_settings = None

def settings():
    global _settings
    if "_settings()" not in globals():
        _settings = load_settings("sly.sublime-settings")
    return _settings


class Sessions:
    """
    Singleton object to store all the currently active sessions.
    Designed to allow a natural number of windows to be connected to one session.
    """
    def __init__(self, sessions=[], window_assignment: Dict[int, Tuple[Window, SlynkSession]]={}):
        self.sessions = sessions
        self.window_assignment = window_assignment
    def add(self, session):
        self.sessions.append(session)

    def remove(self, session):
        self.sessions.remove(session)
        for window_id, (window, window_session) in self.window_assignment:
            if window_session is session:
                del self.window_assignment[window_id]
                try:
                    window.set_status("slynk", "")
                    window.status_message("Slynk session disconnected and unassigned")
                except e:
                    print(f"Error with status message: {e}")

    def get_by_window_id(self, id: int):
        return self.window_assignment[id][1] if id in self.window_assignment else None

    # This function also performs a lot of UX work the one above doesn't
    # autoset is actually True by default, None means consult user settings.
    def get_by_window(self, window, indicate_failure=True, autoset: bool=None):
        if autoset is None:
            try:
                autoset = settings().get("autoset_slynk_connexion")
            except e:
                autoset = True
        id = window.id()
        if id in self.window_assignment:
            return self.window_assignment[id][1]
        # The session desired is obvious if only one is there
        elif autoset and len(sessions) == 1:
            self.set_by_window(window, sessions[0], False)
            window.status_message("Automatically assigned only slynk connexion to window")
            return sessions[0]
        else:
            if indicate_failure:
                window.status_message(
                    "Slynk not connected" if len(sessions) == 0
                                          else "No slynk connexion assigned to window")
            return None

    def set_by_window(self, window, session, message=True):
        self.window_assignment[window.id()] = (window, session)
        if message:
            window.status_message("Slynk assigned to window")
        print(f"Error {e}")

    def window_ids_for_session(self, session) -> List[int]:
        return [window_id for window_id, (__, window_session) in self.window_assignment.items()
                          if window_session == session]

    def windows_for_session(self, session) -> List[Window]:
        return [window for __, (window, window_session) in self.window_assignment.items()
                       if window_session == session]


class SlynkSession:
    """
    This object stores all the information the plugin will use to connect 
    and deal with (a single) slynk.

    Inspectors, REPLs etc are all stored here
    """
    def __init__(self, host, port, window, loop) -> None:
        super().__init__()
        self.slynk = slynk.SlynkClient(host, port)
        self.window = window
        self.repl_views = []
        self.loop = loop
        self.slynk.bind(__aio_loop__=loop,
                        connect=self.on_connect,
                        disconnect=self.on_disconnect,
                        debug_setup=self.on_debug_setup,
                        debug_activate=self.on_debug_activate,
                        debug_return=self.on_debug_return,
                        read_from_minibuffer=self.on_read_from_minibuffer,
                        y_or_n_p=self.on_y_or_n)
        self.inspectors = {}
        self.nearest_inspector = None

    async def connect(self):
        slynk = self.slynk
        self.window.status_message(f"Attempting to connect to Slynk at {slynk.host}:{slynk.port} [≈ 1 min]")
        await slynk.connect(asyncio.get_event_loop())
        await slynk.prepare(f"{packages_path()}/Slims")
        #await slynk.closed()

    def on_connect(self, *args):
        self.window.status_message("SLYNK connexion established")
        print("SLYNK connexion established")

    def on_disconnect(self, *args):
        self.window.status_message("SLYNK connexion lost")
        print("SLYNK connexion lost")

    async def on_debug_setup(self, debug_data):
        print("run")
        (action, index) = await debugger.show(self, debug_data)
        if action == "restart":
            await self.slynk.debug_invoke_restart(debug_data.level, index, debug_data.thread)
        elif action == "frame":
            await self.slynk.debug_restart_frame(index, debug_data.thread)
        #(action, index)

    def on_debug_activate(self, *args):
        print(f":activate {args}")

    def on_debug_return(self, *args):
        print(f":return {args}")

    async def on_read_from_minibuffer(self, prompt, initial_value, future):
        initial_value = initial_value if initial_value else ""
        output = await util.show_input_panel(self.loop, self.window, prompt, initial_value)
        future.set_result(output)

    async def on_y_or_n(self, prompt, future):
        value = yes_no_cancel_dialog(prompt)
        if value == DIALOG_CANCEL:
            future.cancel()
        else:
            future.set_result(True if value == DIALOG_YES else False)


class ConnectSlynkCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):  # implement run method
        global loop
        if not loop.is_running():
            threading.Thread(target=loop.run_forever).start()
        asyncio.run_coroutine_threadsafe(
            self.async_run(**kwargs),
            loop)

    async def async_run(self, host=None, port=None, prompt_connexion=None):
        print("hi")
        defaults = settings().get("default_connexion_parameters")
        host = defaults["hostname"] if host is None else host
        port = defaults["port"] if port is None else port

        if prompt_connexion in ["both", "host", "hostname"] or host is None:
            host = await util.show_input_panel(
                loop, self.window, "Enter hostname", host)
        if prompt_connexion in ["both", "port"] or port is None:
            port = await util.show_input_panel(
                loop, self.window, "Enter port", str(port))

        session = SlynkSession(host, port, self.window, loop)
        await session.connect()
        sessions.add(session)
        sessions.set_by_window(self.window, session)


class DisconnectSlynkCommand(sublime_plugin.WindowCommand):
    def run(self):  # implement run method
        global loop
        session = sessions.get_by_window(self.window)
        if session is None: return
        session.slynk.disconnect()
        sessions.remove(session)


if "ready" not in globals():
    ready = True
    print("Preparing stuff for SLY")
    sessions = Sessions()
    loop = asyncio.new_event_loop()
    if settings().get("debug"):
        loop.set_debug(True)
        logging.basicConfig(level=logging.DEBUG)
else:
    sessions_1 = Sessions(sessions.sessions, sessions.window_assignment)
    sessions = sessions_1