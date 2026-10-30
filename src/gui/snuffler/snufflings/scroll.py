# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------

from ..snuffling import Snuffling, Param


class ScrollSnuffling(Snuffling):

    '''
    Scroll through archived data automatically, like a running tape.
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

    def call(self):
        '''
        Start scrolling from the left edge of the current view.
        '''

        viewer = self.get_viewer()
        tmin, _ = viewer.get_time_range()

        # Design: start from where the user is looking instead of from the
        # data's first sample. Positioning the view is then the "seek" control,
        # and Stop followed by Play is pause and resume, with no extra state.
        # tmax_start is the right edge of the first window shown.
        viewer.follow(
            self.window,
            lapse=self.speed,
            tmax_start=tmin + self.window)

    def stop(self):
        self.get_viewer().unfollow()

    def pre_destroy(self):
        # do not leave the viewer's timer running when the snuffling is gone
        try:
            self.stop()
        except Exception:
            pass


def __snufflings__():
    '''
    Returns a list of snufflings to be exported by this module.
    '''

    return [ScrollSnuffling()]
