import cmf
import pandas as pd


class DataProvider:
    """
    Holds the forcing and calibration data
    """

    def __init__(self, data, **columnmapper):
        """

        :param data: A pandas dataframe with the dates as a
        :param columnmapper:
        """
        cm = {k: v if not isinstance(v, int) else data.columns[v]
              for k, v in columnmapper.items()
              }
        # Get begin, step and end from the date column
        self.begin = data.index[0].to_pydatetime()
        self.end = data.index[-1].to_pydatetime()
        self.step = data.index[1].to_pydatetime() - self.begin

        def a2ts(a):
            """Converts an array column to a timeseries"""
            return cmf.timeseries.from_array(self.begin, self.step, a)

        self.P = a2ts(data[cm['P']])
        self.T = a2ts(data[cm['T']])
        self.Tmin = self.T
        self.Tmax = self.T
        self.Q = a2ts(data[cm['Q']])
        self.ETpot = a2ts(data[cm['E']])

    def add_stations(self, project):
        """
        Creates a rainstation and a meteo station for the cmf project
        :param project: A cmf.project
        :return: rainstation, meteo
        """
        rainstation = project.rainfall_stations.add('Glauburg', self.P, (0, 0, 0))

        project.use_nearest_rainfall()

        # Temperaturdaten
        meteo = project.meteo_stations.add_station('Glauburg', (0, 0, 0))
        meteo.T = self.T
        meteo.Tmin = self.Tmin
        meteo.Tmax = self.Tmax

        project.use_nearest_meteo()

        return rainstation, meteo

    def summerize(self):
        for ts_name in 'P ETpot T Q'.split():
            ts = getattr(self, ts_name)
            print(ts_name, cmf.describe(ts).replace('\n', ''))


def load_csv(csv_file: str, time_column=0, **columnmapper):
    """
    :param csv_file: The csv file with decimal point and commas as list seperator
    :param columnmapper: Maps the column names or positions to the items P, E, T, Q
    :return: A DataProvider object

    Example csv file:

    .. code-block::

        date,Prec mm,Temp °C,ET mm,Q mm
        2020-01-01,2.46,5.3,0.2,1.3

    Usage with column names:
    >>> data = load_csv('pteq.csv', P='Prec mm', E='ET mm', T='Temp °C', Q='Q mm')

    Usage with column positions:
    >>> data = load_csv('pteq.csv', P=1, E=3, T=2, Q=4)
    """
    data = pd.read_csv(csv_file, index_col=[time_column], parse_dates=True)
    return DataProvider(data, **columnmapper)

