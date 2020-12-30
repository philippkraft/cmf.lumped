import networkx as nx
import cmf
import numpy as np
import matplotlib.axes
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class Network:

    def __init__(self, outlet: cmf.flux_node):
        self.nodes = {}
        self.graph = nx.Graph()
        self.add_node(outlet)
        self.__replace_abstract_nodes_with_concrete_storages(outlet.project)

    def __replace_abstract_nodes_with_concrete_storages(self, project: cmf.project):
        """
        self.nodes contains only abstract cmf.flux_nodes.
        This method replaces the nodes with its concrete storages
        """
        storages = {s.node_id: s for s in project.get_storages()}
        self.nodes.update(storages)

    def __node_pos(self, node: cmf.flux_node):
        """
        Gets the position of the node in a 2D view
        Uses displacement keywords to make the view nicer
        :param node: A CMF flux node
        :return: A [x, z] array
        """
        displacement_dict = dict(
            Snow=(+1, 0),
            Canopy=(-1, +1),
            Evaporation=(-1, -18),
            Transpiration=(-2, -18),
            Rainfall=(0, -17.5)
        )
        pos = np.array(node.position)[[0, -1]]
        for s in displacement_dict:
            if str(node).startswith('{' + s):
                pos += np.array(displacement_dict[s])
        return pos

    def add_node(self, node: cmf.flux_node):
        """
        Adds a cmf node and all of its connected nodes into a networkx graph
        :param node: A cmf flux node
        :param G: A networkx.Graph object. If None, a new Graph is created
        :param nodes_done: A set of handled nodes, if None, a new one is created
        :return: The graph
        """
        self.graph.add_node(
            node.node_id,
            position=self.__node_pos(node),
            name=node.Name.replace(' of cell #0', '')
        )

        self.nodes[node.node_id] = node

        for c in node.connections:
            target = c.get_target(node)
            self.graph.add_edge(
                c.left_node().node_id, c.right_node().node_id,
                label=c.short_string().split('#')[0])
            if target.node_id not in self.nodes:
                self.add_node(target)

    def get_volume(self, node_id):
        """
        Returns the stored volume of a node
        :param node_id: A flux node id.
        :return: the stored water volume in m³
        """
        node = self.nodes[node_id]
        if hasattr(node, 'volume'):
            return max(node.volume, 0.0)
        else:
            return 0.0

    def get_volumes(self):
        """
        Returns a list of volumes for each node of the graph
        :return:
        """
        return [self.get_volume(n) for n in self.graph.nodes]

    def get_connection(self, left_id, right_id)->cmf.flux_connection:
        return self.nodes[left_id].connection_to(self.nodes[right_id])

    def get_flux(self, t, left_id, right_id):
        c = self.get_connection(left_id, right_id)
        return np.abs(c.q(c.left_node(), t))

    def get_fluxes(self, t):
        """
        Returns a list a fluxes for each edge in the graph
        :param t: current time to query the fluxes
        :return:
        """
        return [
            self.get_flux(t, *e)
            for e in self.graph.edges
        ]


class Fluxogram:

    def __init__(self, outlet: cmf.flux_node, axis=None, *, with_edge_labels=False):
        self.network = Network(outlet)
        if axis is None:
            axis = plt.gca()
        self.axis: matplotlib.axes.Axes() = axis
        self.axis.set_axis_off()
        self.with_edge_labels = with_edge_labels
        self.node_labels = {}
        self.node_markers = []
        self.edge_lines = []
        self.edge_labels = []
        self.title = None


    def get_artists(self):
        result = [self.node_markers, self.title]
        result.append(self.edge_lines)
        result.extend(self.node_labels.values())
        result.extend(self.edge_labels)
        return result


    def init_plot(self, linewidth=3):

        G = self.network.graph
        pos = G.nodes.data('position')

        self.axis.clear()
        self.axis.set_axis_off()
        self.node_markers = nx.draw_networkx_nodes(
            G, pos, ax=self.axis, node_size=100,
            node_shape='s', node_color='#8888FF',
        )
        self.node_labels = nx.draw_networkx_labels(
            G, pos, ax=self.axis,
            labels=dict(G.nodes.data('name')),
            font_size=9,
            bbox=dict(facecolor='white', alpha=0.5, edgecolor='none')
        )

        self.edge_lines = nx.draw_networkx_edges(
            G, pos, ax=self.axis, width=linewidth, edge_color='#4444FF',
        )

        labels = {(l, r): v for l, r, v in G.edges.data('label')}
        if self.with_edge_labels:
            self.edge_labels = nx.draw_networkx_edge_labels(
                G, pos, ax=self.axis,
                edge_labels=labels, font_size=7
            )
        else:
            self.edge_labels = []

        self.title = self.axis.text(
            x=1.0, y=1.0, s='...',
            horizontalalignment='right',
            verticalalignment='top',
            transform=self.axis.transAxes
        )
        self.axis.set_xlim(*[x * 1.1 for x in self.axis.get_xlim()])
        plt.axis('off')
        return self.get_artists()

    def update(self, t):
        volume = self.network.get_volumes()  # volume of the nodes in mm/day
        flux = self.network.get_fluxes(t)  # fluxes over edges in mm/day
        self.node_markers.set_sizes(10 * np.sqrt(volume))
        self.edge_lines.set_linewidths(flux)
        if t:
            self.title.set_text(str(t))
        return self.get_artists()

    def get_animator(self, integration):
        """
        Returns a matplotlib.animation.FuncAnimator object that uses
        the integration iteratable to advance your model to animate the HillPlot

        Usage example:

        >>>p=cmf.project()
        >>>solver = cmf.CVodeIntegrator(p, 1e-9)
        >>>fg = Fluxogram(outlet)
        >>>animator = fg.get_animator(solver.run(datetime(2012, 1, 1), datetime(2012, 2, 1), timedelta(hours=1)))

        :param integration: An iterable that advances the model and yields the current time
        :return: A matplotlib.animation.FuncAnimator
        """

        fa = FuncAnimation(self.axis.figure, func=self.update,
                           init_func=self.init_plot,
                           frames=integration, blit=False,
                           interval=1, repeat=False)
        return fa
