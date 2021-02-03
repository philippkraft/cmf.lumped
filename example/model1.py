"""
CMF-Model for Nidder / Glauberg
===============================

by Philipp Kraft

last modification: 2021-01-21 09:27

This text is from the doc-string of the Model's module
"""

import os
import cmf
from cmflumped.basemodel import BaseParameters, u, BaseModel
from cmflumped.dataprovider import load_csv


# The concept class is only used for documentation purposes.
class Concept:
    """
    Concept for {name}
    ==================

    Using the concept of a simple overflowing bucket,
    the model does not generate any baseflow.

    It is based on ...

    bla...

    The implementation idea is shown in :numref:`fig_{name}_concept`

    .. _fig_{name}_concept:
    .. figure:: {name}.concept.png

    """
    ...


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
    Sfc = u(0.0, 1.0, default=0.5, doc='Fraction of capacity at field capacity in mm/mm. field capicty = Sfc * Smax')
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

    A simple single storage model with infiltration and saturation excess
    but no baseflow
    """
    verbose = True
    calibration_start = 2000
    validation_start = 2010
    parameters = Parameters()

    def __init__(self):
        path = os.path.dirname(__file__)
        # date,Q,ETpot,P,air_temp_proxy,soil_temperature_5cm
        data = load_csv(os.path.join(path, 'glauburg_temp.csv'),
                        date=0, P=2, E=1, Tmin=3, Q=0)
        
        # Call BaseModel.__init__, which does the following
        #   self.project = cmf.project
        #   self.cell = self.project.NewCell(0, 0, 0, 1000)
        #   self.create_nodes()
        
        super().__init__(data)

    def create_nodes(self):
        """
        Create the nodes (storages, distribution nodes and boundaries) of your model.

        Called from model initialization (self.__init__)
        """
        # Create a subsurface storage
        self.soil = self.cell.add_layer(1)
        self.soil.Name = 'Soil'
        # Make an outlet
        self.outlet = self.project.NewOutlet('outlet', 2, 0, -1)

    def create_result_structure(self):
        """
        Creates the container to store the results in.

        Called, when the run time loop starts
        """
        outflow = cmf.timeseries(self.data.begin, cmf.day)
        outflow.add(self.outlet(self.data.begin))
        return outflow

    def fill_result_structure(self, result, t):
        """
        Fills the result structure with data.

        Called in each timestep.
        """
        q = self.output(t)
        result.add(q)
        if self.verbose:
            print(f'{t!s:>12s} Q={q:10.5g}mm/day')

    def set_soil_capacity(self, p: Parameters)->float:
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

        capacity = self.set_soil_capacity(p)

        cmf.timeseriesETpot(self.soil, self.cell.transpiration, self.data.ETpot)

        # Parameterize infiltration capacity
        self.soil.soil.Ksat = p.infiltration_capacity / 1000

        # Parameterize water stress function
        self.cell.set_uptakestress(cmf.VolumeStress(
            p.ETV1 * capacity, 0)
        )

    def initial_values(self, p: Parameters = None):
        """
        Is called before a simulation starts and should reset
        every storage of the model and needs to be defined for each model
        :param p: The parameters object. May or may not be used in the function
        :return: None
        """

        self.soil.volume = self.soil.get_capacity() * 0.5

    def output(self, t):
        """
        Defines what the ouput of the model is

        :param t: Time step of the model
        :return: A value representing the model output
        """
        return self.outlet.waterbalance(t)


if __name__ == '__main__':
    from cmflumped import commands as cmd
    # m = Model1()
    # Starts the graphic user interface for manual calibration.
    # In Spyder: Make sure to run this in an external terminal (Ctrl + F6)
    cmd.doc(__file__, in_browser=True)
    

