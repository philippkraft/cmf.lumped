
import os
import cmf
from cmflumped.basemodel import BaseParameters, u, BaseModel
from cmflumped.dataprovider import load_csv


class Parameters(BaseParameters):
    """
    A helper class to define the parameters of the model

    Create class owned fields as parameters
    """
    infiltration_capacity = u(
        0, 50, 10,
        doc='Infiltration capacity over a day in mm/day')
    infiltration_w0 = u(
        0.5, 0.99, default=0.75,
        doc=':math:`W_0` saturation index'
    )
    soil_capacity = u(
        10, 500, default=100,
        doc='Capacity of rooted zone in :math:`mm`'
    )
    ETV1 = u(
        0.1, 0.9, default=0.5,
        doc='Fraction of soil capacity where ET starts to be limited'
    )
    retention_time = u(
        1, 150, default=10,
        doc='Retention time in the catchment water storage'
    )


class Model1(BaseModel):
    """
    CMF-Model for Nidder / Glauberg

    by Philipp Kraft

    last modification: 2021-01-13
    """
    verbose = True
    calibration_start = 2000
    validation_start = 2010
    parameters = Parameters()

    def __init__(self):
        path = os.path.dirname(__file__)
        data = load_csv(os.path.join(path, 'glauburg_temp.csv'),
                        date=0, P=2, E=1, Tmin=3, Q=1)
        super().__init__(data)

    def create_nodes(self):
        """
        Create the nodes (storages, distribution nodes and boundaries) of your model.
        """
        # Create two subsurface storages
        self.soil, = self.add_layers(1)
        self.soil.Name = 'Soil'
        # Make an outlet
        self.outlet = self.project.NewOutlet('outlet', 2, 0, -1)

    def create_result_structure(self):
        outflow = cmf.timeseries(self.data.begin, cmf.day)
        outflow.add(self.outlet(self.data.begin))
        return outflow

    def fill_result_structure(self, result, t):
        q = self.output(t)
        result.add(q)
        if self.verbose:
            print(f'{t!s:>12s} Q={q:10.5g}mm/day')


    def set_soil_capacity(self, p: Parameters):
        """
        Sets the upper soil capacity
        """
        # Parameterize soil water capacity
        self.soil.soil.porosity = p.soil_capacity / (1000 * self.soil.thickness)
        # Set initial value
        self.soil.volume = 0.5 * p.soil_capacity
        # Just a shortcut for the next connections
        return self.soil.get_capacity()

    def create_connections(self, p: Parameters):
        """
        Creates the connections and parameterizes the storages of the model

        """
        # Infiltration
        cmf.SimpleInfiltration(self.soil, self.cell.surfacewater, W0=p.infiltration_w0)
        # Route infiltration / saturation excess to outlet
        cmf.waterbalance_connection(self.cell.surfacewater, self.outlet)

        C = self.set_soil_capacity(p)

        cmf.timeseriesETpot(self.soil, self.cell.transpiration, self.data.ETpot)
        # Parameterize water stress function

        self.soil.soil.Ksat = p.infiltration_capacity / 1000

        self.cell.set_uptakestress(cmf.VolumeStress(
            p.ETV1 * C, 0.1 * C)
        )

    def initial_values(self, p: Parameters = None):
        self.soil.volume = self.soil.get_capacity() * 0.5

    def output(self, t):
        """
        Defines what the ouput of the model is
        :param t: Time step of the model
        :return: A value representing the model output
        """
        return self.outlet.waterbalance(t)


if __name__ == '__main__':
    m = Model1()
    print(cmf.describe(m.project))
    from cmflumped.gui import GUI
    GUI(m).show()
