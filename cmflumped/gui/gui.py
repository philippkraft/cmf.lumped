from spotpy.gui.mpl import Widget, as_scalar, ValueChanger
import numpy as np
from matplotlib.widgets import Slider, Button
from matplotlib import pylab as plt
from matplotlib.animation import FuncAnimation
import time
from spotpy.parameter import get_parameters_array, create_set
from ..basemodel import BaseModel
import cmf
import logging

from .fluxogram import Fluxogram

logger = logging.getLogger(__name__)
class GUI:

    def __init__(self, setup):
        """
        Creates the GUI

        :param setup: A spotpy setup
        """

        logger.debug('init gui')
        self.fig = plt.figure(type(setup).__name__)
        self.time_ax = plt.axes([0.05, 0.1, 0.9, 0.4])

        self.flux_ax = plt.axes([0.05, 0.55, 0.5, 0.4], facecolor='0.8')
        self.fluxogram = Fluxogram(setup.outlet, self.flux_ax)
        self.fluxogram.init_plot(3)
        self.button_play = Widget([0.85, 0.01, 0.04, 0.03], Button, '\u25B6', on_clicked=self.animate)
        # self.button_stop = Widget([0.8, 0.01, 0.04, 0.03], Button, '\u25A0', on_clicked=self.stop)
        self.button_simulate = Widget([0.9, 0.01, 0.04, 0.03], Button, '\u25B6\u25B6', on_clicked=self.run)
        # self.button_clear = Widget([0.9, 0.01, 0.04, 0.03], Button, '\u2718', on_clicked=self.clear)
        self.setup: BaseModel = setup
        self.parameter_values = {
            p['name']: p['optguess']
            for p in get_parameters_array(self.setup)
        }
        self.sliders = self._make_widgets()
        self.lines = []
        self.running = False
        self.clear()


    def close(self):
        plt.close(self.fig)

    def __enter__(self):
        logger.debug('enter gui context')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def show():
        """
        Calls matplotlib.pylab.show to show the GUI.
        """
        plt.show()

    def _make_widgets(self):
        """
        Creates the sliders
        :return:
        """
        if hasattr(self, 'sliders'):
            for s in self.sliders:
                s.ax.remove()

        sliders = []
        params = get_parameters_array(self.setup)

        def calc_step():
            h = self.flux_ax.get_position().height
            n = len(params)
            step = h / n
            return max(0.005, min(0.05, step))

        step = calc_step()
        for i, value in enumerate(params):
            rect = [0.75, 1.0 - step * (i + 1), 0.2, step - 0.005]
            s = Widget(rect, Slider, params['name'][i], params['minbound'][i], params['maxbound'][i],
                       valinit=params['optguess'][i], on_changed=ValueChanger(params['name'][i], self.parameter_values))
            sliders.append(s)
        plt.draw()
        return sliders

    def get_parameter_set(self):
        return create_set(self.setup, **self.parameter_values)

    def clear(self, _=None):
        """
        Clears the graph and plots the evalution
        """
        obs = self.setup.evaluation()
        day = np.timedelta64(1, 'D')
        begin = np.datetime64(self.setup.begin)
        time_dim = begin + day * np.arange(len(obs))

        self.time_ax.clear()

        self.lines = list(
            self.time_ax.plot(time_dim, obs, 'k:', label='Observation', zorder=2)
        )
        self.time_ax.legend()

    def run(self, _=None):
        """
        Runs the model and plots the result
        """
        logger.info('silent run')
        self.running = False
        self.time_ax.set_title('Calculating...')
        plt.draw()
        time.sleep(0.001)

        parset = create_set(self.setup, **self.parameter_values)
        logger.debug('start simulation')
        sim = np.array(self.setup.simulation(parset))
        logger.debug('simulation done')
        objf = as_scalar(self.setup.objectivefunction(sim, self.setup.evaluation()))
        day = np.timedelta64(1, 'D')
        begin = np.datetime64(self.setup.begin)
        time_dim = begin + day * np.arange(len(sim))
        self.lines.extend(self.time_ax.plot(time_dim, sim, '-'))
        self.time_ax.legend()
        self.time_ax.set_title(type(self.setup).__name__)
        self.time_ax.figure.canvas.draw_idle()
        logger.debug('plot result')

    def stop(self, _=None):
        logger.info('pressed stop')
        self.running = False

    def animate(self, _=None):
        logger.info('animation')
        self.running = False
        def cmf_time_to_ms(t):
            return (t - cmf.Time(1, 1, 1970)).AsMilliseconds()
        outflow = [self.setup.output(self.setup.begin)]
        timeline_ms = [cmf_time_to_ms(cmf.AsCMFtime(self.setup.begin))]

        def update(t):
            outflow.append(self.setup.output(t))
            timeline_ms.append(cmf_time_to_ms(t))
            flux_artists = self.fluxogram.update(t)
            time_dim = np.array(timeline_ms, dtype='datetime64[ms]')
            self.lines[-1].set_data(time_dim, outflow)
            return self.lines + flux_artists

        def init():
            act_line, = self.time_ax.plot([], [], '-', label='actual run')
            self.lines.append(act_line)
            self.time_ax.legend()

            flux_artists = self.fluxogram.init_plot(0)
            return self.lines + flux_artists

        def stoppable(it):
            t = self.setup.begin
            try:
                while self.running:
                    t = next(iter(it))
                    yield t
            except StopIteration:
                pass
            finally:
                time_dim = np.array(timeline_ms, dtype='datetime64[ms]')
                self.lines[-1].set_data(time_dim, outflow)
                self.fluxogram.init_plot(0)
                self.fluxogram.update(t)
                for l in self.lines:
                    self.time_ax.figure.draw(l)
                self.time_ax.figure.canvas.draw_idle()
                self.flux_ax.figure.canvas.draw_idle()


        self.running = True
        parset = self.get_parameter_set()
        iterator = stoppable(self.setup.iterate(parset))
        logger.debug('create animation')
        self.animator = FuncAnimation(
            self.fig, update,
            iterator,
            init_func=init, repeat=False,
            interval=1, blit=True
        )




