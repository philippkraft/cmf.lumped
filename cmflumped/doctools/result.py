
import numpy as np
from scipy.stats import gaussian_kde
import tables
import pandas as pd

import yaml
import os

from matplotlib import pyplot as plt
from textwrap import dedent

from .. import BaseModel
from ..doctools import DocClass


def result_filename(setup, path='.'):
    return os.path.join(path, str(setup) + '.result.yml')


class BaseResult(DocClass):
    """
    A base class for documentary result classes. See usage in example/model2.py
    """
    @classmethod
    def describe(cls, setup=None, **kwargs) -> str:
        with open(result_filename(setup)) as f:
            data = yaml.safe_load(f)
            return super().describe(setup, **data)

    threshold = None
    def calculate_threshold(self, n_min=30):
        """
        Calculates a rejection criteria for given data.
        Use this is only for explorative studies, for a real GLUE approach,
        you may not change an a priori defined rejection criterium.

        :param n_min: Minimum number of behavioural runs
        """
        # Calculate NSE threshold
        threshold = 0.7
        n = 0
        while np.sum(np.array(self.data.cols.like1[:]) > threshold) < n_min and threshold > -2:
            threshold -= 0.05
        n = np.sum(np.array(self.data.cols.like1[:]) > threshold)
        return threshold, n

    def __init__(self, model: BaseModel, result_file: str = None, outputdir = '.'):
        self.name = model.name
        if not hasattr(self, 'result_filename'):
            self.result_filename = result_file or f'{self.name}.h5'

        self.data_file = tables.open_file(self.result_filename)
        self.data = self.data_file.get_node(f'/{model}')
        self.model = model
        # Calculate the behavioural model
        self.threshold, self.n = self.calculate_threshold()
        self.obs = self.model.data.Q.to_pandas()
        self.outputdir = outputdir

    def save(self, verbose):
        self.dotty_plot()
        self.timeseries_plot()
        data = self.result_summary()
        if verbose:
            print(data)
        with open(self.filename('result', 'yml'), 'w') as f:
            yaml.safe_dump(data, f)

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
        self.data = self.data_file.get_node(f'/{self.model}')

    def close(self):
        self.data_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        self.close()

    def filename(self, *names):
        ext = '.'.join(names)
        return f'{self.outputdir}/{self.name}.{ext}'

    def load_obs(self):
        df = pd.read_csv('daten/glauburg_temp.csv', index_col=[0], parse_dates=True)
        return df.Q

    def dotty_plot(self):
        """
        Plots the distribution of parameters in the behavioural runs
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
        return self.filename('dotty', 'png')

    def timeseries_plot(self):
        """
        Plots the result timeseries with the p5 to p95 uncertainty interval
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
        time = np.arange(np.datetime64('1991', 'D'), np.datetime64('2019', 'D'))
        plt.fill_between(time, p5, p95, facecolor='#ffff00', edgecolor='none', label='Modelled uncertainty')
        plt.plot(time, self.obs, 'k-', label='Observed')
        plt.plot(time, best, 'r-', label='Best model')
        ax = plt.gca()
        ax.xaxis_date()
        ax.set_xlim(np.datetime64(f'{self.model.validation_start}-01-01'))
        plt.axvline(np.datetime64(f'{self.model.validation_start}-01-01'), ls='--', c='k', lw=3, alpha=0.5)
        plt.title('{} NSE>{:0.2f}, n={}'.format(self.name.capitalize(), self.threshold, take.sum()),
                  fontsize=24)
        plt.legend()

        fig.savefig(self.filename('timeseries', 'png'))
        return self.filename('timeseries', 'png')

    def like(self, row):
        """Returns the 4 objective functions for a model run"""
        return [self.data.col(colname)[row] for colname in self.data.colnames if colname.startswith('like')]

    def best_run_id(self):
        """Returns the row number of the best run"""
        return np.array(self.data.cols.like1[:]).argmax()

    def result_summary(self) -> dict:
        best_run_id = self.best_run_id()
        like = self.like(best_run_id)
        return dict(
            n=int(self.n),
            threshold=float(self.threshold),
            best_run_id=int(best_run_id),
            NSE_c=float(like[0]),
            NSE_v=float(like[1]),
            PBIAS_c=float(like[2]),
            PBIAS_v=float(like[3]),
        )