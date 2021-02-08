import cmf
import pandas as pd
import datetime as dt

class DataProvider:
    """
    Holds the forcing and calibration data
    """

    def __init__(self, data, Q='Q', P='P', E='ETpot', Tmin=None, Tmax=None):
        """
        Makes a new dataprovider for a lumped cmf model

        :param data: A pandas dataframe with the dates as the index
        :param Q: Name or index of the dataframe's column containing the validation discharge in mm/day
        :param P: Name or index of the dataframe's column containing Precipitation in mm/day
        :param E: Name or index of the dataframe's column containing potential Evaporation (ETpot) in mm/day
        :param Tmin: Name or index of the dataframe's column containing the daily min Temperature (°C)
                    - None means no Temperature is given
        :param Tmax: Name or index of the dataframe's column containing the daily min Temperature (°C)
                    - None means: use Tmin as daily average Temperature
        """
        # Get begin, step and end from the date column
        self.begin: dt.datetime = data.index[0].to_pydatetime()
        self.end: dt.datetime = data.index[-1].to_pydatetime()
        self.step: dt.timedelta = data.index[1].to_pydatetime() - self.begin

        def a2ts(a):
            """Converts an array column to a timeseries"""
            return cmf.timeseries.from_array(self.begin, self.step, a)

        def get_col(c):
            if type(c) is int:
                return data[data.columns[c]]
            else:
                return data[c]

        self.P = a2ts(get_col(P))
        self.Q = a2ts(get_col(Q))
        self.ETpot = a2ts(get_col(E))

        self.Tmin = a2ts(get_col(Tmin)) if Tmin else None
        self.Tmax = a2ts(get_col(Tmax)) if Tmax else None


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
        if self.Tmin:
            meteo.Tmin = self.Tmin
        else:
            meteo.Tmin = cmf.timeseries.from_scalar(10.0)
        if self.Tmax:
            meteo.Tmax = self.Tmax
        else:
            meteo.Tmax = meteo.Tmin

        project.use_nearest_meteo()

        return rainstation, meteo

    def summerize(self):
        for ts_name in 'P ETpot T Q'.split():
            ts = getattr(self, ts_name)
            print(ts_name, cmf.describe(ts).replace('\n', ''))


def load_csv(csv_file: str, date=0, Q='Q', P='P', E='ETpot', Tmin=None, Tmax=None, **kwargs) -> DataProvider:
    """
    Loads driver and calibration
    -----------------------------

    :param csv_file: The csv file with decimal point and commas as list seperator
    :param date: Name or index of the dataframe's column containing dates
    :param Q: Name or index of the dataframe's column containing the validation discharge in mm/day
    :param P: Name or index of the dataframe's column containing Precipitation in mm/day
    :param E: Name or index of the dataframe's column containing potential Evaporation (ETpot) in mm/day
    :param Tmin: Name or index of the dataframe's column containing the daily min Temperature (°C)
                - None means no Temperature is given
    :param Tmax: Name or index of the dataframe's column containing the daily min Temperature (°C)
                - None means: use Tmin as daily average Temperature

    :param kwargs: Keyword arguments to be passed on to pandas.load_csv

    :return: A DataProvider object

    Example csv file:
    -----------------
    .. code-block::

        date,Prec mm,Temp °C,ET mm,Q mm
        2020-01-01,2.46,5.3,0.2,1.3

    Usage with column names:
    >>> data = load_csv('pteq.csv', date='date', P='Prec mm', E='ET mm', Tmin='Temp °C', Q='Q mm')

    Usage with column positions:
    >>> data = load_csv('pteq.csv', date=0, P=1, E=3, Tmin=2, Q=4)
    """
    data = pd.read_csv(csv_file, index_col=[date], parse_dates=True)
    return DataProvider(data, Q, P, E, Tmin, Tmax)

