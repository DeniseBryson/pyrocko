# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------

import time
import logging

from ..snuffling import Snuffling, Param
from ...qt_compat import qc

logger = logging.getLogger('pyrocko.gui.snuffler.snufflings.scroll')


class Hooks(qc.QObject):

    '''
    Qt glue: polling timer and event filter on the viewer.

    A Snuffling is not a QObject, so it cannot own a timer or be an event
    filter itself. This object only forwards to the snuffling.
    '''

    def __init__(self, snuffling):
        qc.QObject.__init__(self)
        self.snuffling = snuffling
        self.timer = qc.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(snuffling.tick)

    def eventFilter(self, obj, event):
        return self.snuffling.handle_event(event)


class ScrollSnuffling(Snuffling):

    '''
    Scroll through archived data automatically, like a running tape.

    **Run** (or key **t**) starts scrolling from the left edge of the current
    view. **Stop**, **Clear**, a mouse click or **space** stops it. Space
    only stops while scrolling; otherwise it keeps its normal function.

    While scrolling, the scale ranges are fixed to those of the starting view
    (View - Scale - Fix Scale Ranges), so traces do not rescale as they move
    past. They are released again whenever scrolling stops.

    Scrolling also stops when you zoom, drag or jump somewhere else. With
    **Auto-Run** ticked it resumes from the new position once you have left
    the view alone for a while, and it restarts when you change a parameter.
    Without Auto-Run it stays stopped.
    '''

    def setup(self):
        '''
        Customization of the snuffling.
        '''

        self.set_name('Scroll')

        self.add_parameter(Param(
            'Window length [s]', 'window', 60., 1., 86400.))

        self.add_parameter(Param(
            'Speed [x real time]', 'speed', 1., 0.1, 1000.))

        self.add_trigger('Stop', self.stop)
        self.set_live_update(False)

        # None: idle, 'playing', or 'waiting' (stopped by navigation, will
        # resume if Auto-Run is on)
        self.state = None
        self.hooks = None
        self.scale_fixed = False
        self.idle_since = 0.0
        self.last_trange = None

    def init_gui(self, viewer, panel_parent, menu_parent, reloaded=False):
        Snuffling.init_gui(
            self, viewer, panel_parent, menu_parent, reloaded=reloaded)

        self.remove_hooks()
        self.hooks = Hooks(self)
        viewer.installEventFilter(self.hooks)

    def remove_hooks(self):
        if self.hooks is not None:
            self.hooks.timer.stop()
            try:
                self.get_viewer().removeEventFilter(self.hooks)
            except Exception:
                pass
            self.hooks = None

    def call(self):
        '''
        Start scrolling from the left edge of the current view.
        '''

        viewer = self.get_viewer()
        tmin, _ = viewer.get_time_range()

        # Always start where the user is looking right now; Stop then Run is
        # pause and resume. unfollow() first because follow() starts a new
        # timer without stopping the old one, which then keeps running and
        # cannot be stopped anymore.
        viewer.unfollow()
        viewer.follow(
            self.window,
            lapse=self.speed,
            tmax_start=tmin + self.window)

        # Freeze the scale ranges of the view we start from. The viewer
        # reuses the ranges of its last draw while this is on. We only
        # release it again if we are the one who set it (see halt).
        viewer.menuitem_fixscalerange.setChecked(True)
        self.scale_fixed = True

        self.state = 'playing'
        if self.hooks is not None:
            self.hooks.timer.start()

    def halt(self):
        '''
        Stop scrolling and release the scale ranges, so they adapt to the
        new view when the user zooms.
        '''

        viewer = self.get_viewer()
        viewer.unfollow()
        if self.scale_fixed:
            viewer.menuitem_fixscalerange.setChecked(False)
            self.scale_fixed = False
            viewer.update()

    def stop(self):
        self.state = None
        if self.hooks is not None:
            self.hooks.timer.stop()
        try:
            self.halt()
        except Exception:
            pass

    def cleanup(self):
        # The Clear button: we add no traces or markers, so stopping is the
        # only sensible meaning.
        self.stop()

    def pre_destroy(self):
        self.stop()
        self.remove_hooks()

    def tick(self):
        '''
        Poll the viewer: detect navigation, resume after it if wanted.
        '''

        try:
            viewer = self.get_viewer()
            now = time.time()
            if self.state == 'playing':
                # The viewer only pauses following for a while after
                # navigation, but its clock keeps running, so it would jump
                # ahead on resume. Stop right away instead.
                if viewer.interactive_range_change_time:
                    self.halt()
                    if self._live_update:
                        self.state = 'waiting'
                        self.last_trange = viewer.get_time_range()
                        self.idle_since = now
                    else:
                        self.stop()

            elif self.state == 'waiting':
                trange = viewer.get_time_range()
                if trange != self.last_trange:
                    # still navigating
                    self.last_trange = trange
                    self.idle_since = now

                elif now - self.idle_since \
                        >= viewer.interactive_range_change_delay_time:
                    self.call_button_triggered()

        except Exception:
            logger.exception('Scroll snuffling failed, stopping.')
            self.stop()

    def handle_event(self, event):
        '''
        Event filter. Returns True if the event has been consumed.
        '''

        if event.type() == qc.QEvent.MouseButtonPress:
            if self.state:
                self.stop()

        elif event.type() == qc.QEvent.KeyPress:
            if event.key() == qc.Qt.Key_Space and self.state:
                self.stop()
                return True

            # not 's': the scale menu has chords starting with S, and Qt
            # holds back such a key press as a possible shortcut start.
            if event.text() == 't' and not event.isAutoRepeat():
                self.call_button_triggered()
                return True

        return False


def __snufflings__():
    '''
    Returns a list of snufflings to be exported by this module.
    '''

    return [ScrollSnuffling()]
