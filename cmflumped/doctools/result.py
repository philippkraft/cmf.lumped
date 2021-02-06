import matplotlib
import numpy as np
from scipy.stats import gaussian_kde
import tables
import pandas as pd
import os
# matplotlib.use('Agg')
from matplotlib import pyplot as plt
from textwrap import dedent

from .. import BaseModel

class Result:
    """
    Das Modell
    """
    def calculate_threshold(self, n_min=30):
        """
        Eigentlich muss man *a priori* festlegen, welches Gütemaß akzeptable
        Modellläufe darstellt. Hier wird zuerst eine Nash-Suttcliffe-Effizienz
        von 0.6 als akzeptable Güte angesetzt, sie wird dann aber schrittweise
        reduziert bis mindestens :math:`n_{min}` Modelläufe als akzeptabel gewertet
        werden

        :return: Effektive mindest Effizienz
        """
        # Calculate NSE threshold
        threshold = 0.7
        n = 0
        while np.sum(np.array(self.data.cols.like1[:]) > threshold) < n_min and threshold > -2:
            threshold -= 0.05
        n = np.sum(np.array(self.data.cols.like1[:]) > threshold)
        return threshold, n

    def __init__(self, model: BaseModel, result_file:str = None):
        self.name = str(model)
        self.result_filename = result_file or f'{self.name}.h5'

        self.data_file = tables.open_file(self.result_filename)
        self.data = self.data_file.get_node(f'/{self.name}')
        self.model = model
        # Calculate the behaviaroul model
        self.threshold, self.n = self.calculate_threshold()
        self.obs = self.model.data.Q.to_pandas()

    def prune_results(self, condition='like1>=0.0'):
        """
        Prunes the result table
        :param condition: A Python condition to select behaving runs
        :return:
        """
        new_filename = self.result_filename.replace('.h5','.pruned.h5')
        pruned_data = self.data.read_where(condition)
        with tables.open_file(new_filename, 'w') as o:
            tab = tables.Table(o.root, self.name, self.data.description)
            tab.append(pruned_data)
        self.result_filename = new_filename
        self.data_file = tables.open_file(self.result_filename)
        self.data = self.data_file.get_node(f'/{self.name}')

    def close(self):
        self.data_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        self.close()

    def filename(self, *names):
        ext = '.'.join(names)
        return f'{self.name}.{ext}'

    def write_rst(self, *txt):
        with open(self.filename('result', 'rst'), 'w') as f:
            f.write('\n\n'.join(txt))

    def load_obs(self):
        df = pd.read_csv('daten/glauburg_temp.csv', index_col=[0], parse_dates=True)
        return df.Q

    def dotty_plot(self):
        """
        Wie man in :numref:`figdotty` sehen kann, sind viele der Parameter nicht gut begrenzt

        """
        take = np.array(self.data.cols.like1[:] > self.threshold)
        fig = plt.figure(figsize=(8, 8), dpi=100)
        p_names = [cn[3:] for cn in self.data.colnames if cn[:3] == 'par']
        letters = [chr(ord('a') + i) for i in range(20)]
        for i, pn in enumerate(p_names):
            plt.subplot(((len(p_names)-1) // 3) + 1, 3, i + 1)
            params = self.data.col(f'par{pn}')[take]
            plt.plot(params, self.data.col('like1')[take], 'x')
            plt.title(pn.replace('_', ' '), loc='left', fontsize=10)
            try:
                gk = gaussian_kde(params)
                x = np.linspace(params.min(), params.max(), 1001)
                plt.twinx()
                plt.plot(x, gk(x), 'r:')
                plt.yticks([])
            except (np.linalg.linalg.LinAlgError, ValueError):
                pass
        plt.subplots_adjust(left=0.075, bottom=0.05, right=0.95, top=0.95, wspace=0.2, hspace=0.4)
        fig.savefig(self.filename('dotty', 'png'))
        res = ''
        res += f'.. _fig_{self.name}_dotty:\n'
        res += f'.. figure:: {self.name}.dotty.png\n\n'
        res += f'    Die Dotty-Plots für die akzeptierten {self.n} Modellläufe mit einem NSE>{self.threshold:0.2f} zeigen ...'
        return res

    def timeseries_plot(self):
        """
        Zeitreihe der Modelle mit einem

        """
        import pylab as plt
        nse = np.array(self.data.cols.like1)
        best_run = nse.argmax()
        best = self.data.cols.simulation[best_run]

        take = nse > self.threshold
        data = self.data.cols.simulation[:][take].data

        p5 = np.percentile(data, 5, 0)
        p95 = np.percentile(data, 95, 0)

        fig = plt.figure(figsize=(16, 8), dpi=100)
        time = np.arange(np.datetime64('1991','D'), np.datetime64('2019', 'D'))
        plt.fill_between(time, p5, p95, facecolor='#ffff00', edgecolor='none', label='Modelled uncertainty')
        plt.plot(time, self.obs, 'k-', label='Observed')
        plt.plot(time, best, 'r-', label='Best model')
        ax = plt.gca()
        ax.xaxis_date()
        ax.set_xlim(np.datetime64('2000-01-01'))
        plt.axvline(np.datetime64('2010-01-01'), ls='--', c='k', lw=3, alpha=0.5)
        plt.title('{} NSE>{:0.2f}, n={}'.format(self.name.capitalize(), self.threshold, take.sum()),
                  fontsize=24)
        plt.legend()

        fig.savefig(self.filename('timeseries', 'png'))
        res = ''
        res += f'.. _fig_{self.name}_timeseries:\n'
        res += f'.. figure:: {self.name}.timeseries.png\n\n'
        res += '  Die Zeitreihe zeigt den gemessenen und den modellierten Hydrographen der Fulda am Pegel Grebenau.\n'
        res += '  Gemessene Werte sind in schwarz, der beste Modelllauf in rot eingetragen. In Gelb sieht man die\n'
        res += '  das 5. bis 95. Perzentil der Spannweite der akzeptierten Parameter-Sets\n'
        
        return res

    def like(self, row):
        """Returns the 4 objective functions for a model run"""
        return [self.data.col(f'like{i}')[row] for i in range(1,5)] 

    def summary(self):
        best_run = np.array(self.data.cols.like1[:]).argmax()
        res = f'Ergebnisse\n' + '-' * 10 + '\n\n'
        res += ':Calibration (1980-1985):  NSE={0:3g}, PBIAS={2:3g}\n\n'
        res += ':Validation (1986-1989): NSE={1:3g}, PBIAS={3:3g}\n\n'
        res = res.format(*np.array(self.like(best_run)))
        res += dedent(f'''
        {self.n}/{len(self.data)} akzeptierte Parameter sets mit einer :math:`NSE\\ge{self.threshold:0.2f}`
                
        .. todo:: 
           {self.name.capitalize()}: Ergbenisse beschreiben
        
        In :numref:`fig_{self.name}_dotty` sieht man Punkte und :numref:`fig_{self.name}_timeseries` Linien
        
        ''')
        
        return res
        
    def discussion(self):
        return dedent(f'''
        Diskussion
        ----------
        
        .. todo:: 
           {self.name.capitalize()}: Diskussion beschreiben, Namen für Vergleich austauschen
        
        Die Ergebniss aus :numref:`fig_{self.name}_timeseries` sind immer noch besser als von Philipp (:numref:`fig_philipp_timeseries`). 
        Das liegt daran, ...
        
        ''')





