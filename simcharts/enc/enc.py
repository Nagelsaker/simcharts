from typing import Any, List, Tuple, Union
import rclpy
from rclpy.node import Node
import datetime
import matplotlib
import simcharts.display as dis
import simcharts.environment as env
from simcharts.utils.helper import *
from simcharts.nodes import LocalTrafficSubscriber
from simcharts_interfaces.msg import Point, Polygon
from simcharts_interfaces.srv import GetStaticObstacles


class ENC(Node):
    """Electronic Navigational Charts

    Reads and extracts features from a user-specified region of spatial data
    given in Cartesian coordinates. Based on Matplotlib, Shapely and Cartopy.
    An independent visualization window may be spawned and displayed using the
    multiprocessing option. Geometric shapes may be accessed through the
    attributes 'land', 'shore', and 'seabed'.

    :param config_file: string containing path to configuration file
    :param multiprocessing: bool for independent visualization display
    :param kwargs: Includes the following optional parameters:
        :param size: tuple(width, height) of bounding box size
        :param origin: tuple(easting, northing) box origin of coordinates
        :param center: tuple(easting, northing) box center of coordinates
        :param buffer: int of dilation or erosion distance for geometries
        :param tolerance: int of maximum tolerance distance for geometries
        :param layers: list(str...) of feature layers to load or show
        :param depths: list(int...) of depth bins for feature layers
        :param files: list(str...) of file names for zipped FGDB files
        :param new_data: bool indicating if new files should be parsed
        :param border: bool for showing a border around the environment plot
        :param verbose: bool for status printing during geometry processing
    """

    def __init__(self, config, executor=None, cli_args=None, multiprocessing=False, **kwargs):
        super().__init__('simcharts__node', cli_args=cli_args)
        matplotlib.use("TkAgg")
        
        self.local_traffic = {}

        self.executor = executor
        self._cfg = config
        self.sim_callback_time = self._cfg.settings['enc']['sim_callback_time']
        
        self._environment = env.Environment(self._cfg.settings)
        self.land = self._environment.topography.land
        self.shore = self._environment.topography.shore
        self.seabed = self._environment.hydrography.bathymetry
        self._display = dis.Display(self._cfg.settings, self._environment, self)


        self.local_traffic_subscriber = LocalTrafficSubscriber()
        self.srv_callback_group = rclpy.callback_groups.ReentrantCallbackGroup()
        self.static_obstacles_srv = self.create_service(GetStaticObstacles, 'simcharts__get_static_obstacles', self._get_static_obstacles_callback, callback_group=self.srv_callback_group)

    @property
    def size(self) -> Tuple[int, int]:
        """
        :return: tuple of bounding box size
        """
        return self._environment.scope.extent.size

    @property
    def center(self) -> Tuple[int, int]:
        """
        :return: tuple of ENC center coordinates
        """
        return self._environment.scope.extent.center

    @property
    def origin(self) -> Tuple[int, int]:
        """
        :return: tuple of ENC origin (lower left) coordinates.
        """
        return self._environment.scope.extent.origin

    @property
    def supported_crs(self) -> str:
        """Return the supported coordinate reference system."""
        return self._environment.supported_crs

    @property
    def supported_layers(self) -> str:
        """Return the supported feature layers."""
        return self._environment.supported_layers

    def updateLocalTraffic(self):
        rclpy.spin_once(self.local_traffic_subscriber, executor=self.executor, timeout_sec=0.01)
        new_traffic = self.local_traffic_subscriber.get_local_traffic()
        if new_traffic != {}:
            self.local_traffic = new_traffic

    def timerCallbackGetLocalTraffic(self):
        self.get_logger().info('Timer expired, getting local traffic')
        self.sendRequestGetLocalTraffic()

    def start_sim(self, executor, duration: float = 0.0) -> None:
        """
        Show a Matplotlib display window of a maritime environment.
        :param duration: optional int for window pause duration
        :return: None
        """
        self.executor = executor
        self.executor.add_node(self)
        self.get_logger().debug("Simulation started")
        t_start = datetime.datetime.now().timestamp()
        t_i = datetime.datetime.now().timestamp()
        t_i_plus_1 = datetime.datetime.now().timestamp() + 5000
        self.updateLocalTraffic()
        self._display.refresh_vessels(self.local_traffic, self.size, self.origin)
        self._display.update_static_plot()
        self._display.update_vessels_plot()
        while True:
            rclpy.spin_once(self, executor=self.executor, timeout_sec=0.01)
            self._display.update_vessels_plot()
            delta_t = t_i_plus_1 - t_i
            if delta_t >= self.sim_callback_time:
                # rclpy.spin_once(self, executor=self.executor, timeout_sec=0.01)
                self.updateLocalTraffic()
                if len(self.local_traffic) > 0:
                    self._display.refresh_vessels(self.local_traffic, self.size, self.origin)
                    self.local_traffic = {}
                t_i = datetime.datetime.now().timestamp()
            t_i_plus_1 = datetime.datetime.now().timestamp()

    def fullscreen_mode(self, arg: bool = True) -> None:
        """
        Enable or disable fullscreen mode view of environment figure.
        :param arg: boolean switching fullscreen mode on or off
        :return: None
        """
        self._display.toggle_fullscreen(arg)

    def colorbar(self, arg: bool = True) -> None:
        """
        Enable or disable the colorbar legend of environment figure.
        :param arg: boolean switching the colorbar on or off.
        """
        self._display.toggle_colorbar(arg)

    def dark_mode(self, arg: bool = True) -> None:
        """
        Enable or disable dark mode view of environment figure.
        :param arg: boolean switching dark mode on or off
        :return: None
        """
        self._display.toggle_dark_mode(arg)

    def add_vessels(self, *args: Tuple[int, int, int, int, str]) -> None:
        """
        Add colored vessel features to the displayed environment plot.
        :param args: tuples with id, easting, northing, heading, color
        :return: None
        """
        self._display.refresh_vessels_from_file(list(args))

    def clear_vessels(self) -> None:
        """
        Remove all vessel features from the environment plot.
        :return: None
        """
        self._display.refresh_vessels_from_file([])

    def add_ownship(
        self,
        easting: int,
        northing: int,
        heading: float,
        hull_scale: float = 1.0,
        lon_scale: float = 10.0,
        lat_scale: float = 10.0,
    ) -> None:
        """
        Add the body of a controllable vessel to the environment.
        :param easting: int denoting the ownship X coordinate
        :param northing: int denoting the ownship Y coordinate
        :param heading: float denoting the ownship heading in degrees
        :param hull_scale: optional float scaling the ownship body size
        :param lon_scale: optional float scaling the longitudinal horizon
        :param lat_scale: optional float scaling the lateral horizon
        :return: None
        """
        self._environment.create_ownship(easting, northing, heading, hull_scale, lon_scale, lat_scale)
        self._display.update_plot()

    def remove_ownship(self) -> None:
        """
        Remove the controllable vessel from the environment.
        :return: None
        """
        self._environment.ownship = None

    def add_hazards(self, depth: int, buffer: int = 0) -> None:
        """
        Add hazardous areas to the environment, filtered by given depth.
        :param depth: int denoting the filter depth
        :param buffer: optional int denoting the buffer distance
        :return: None
        """
        self._environment.filter_hazardous_areas(depth, buffer)

    def draw_arrow(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        color: str,
        width: float = None,
        head_size: float = None,
        thickness: float = None,
        edge_style: Union[str, tuple] = None,
    ) -> None:
        """
        Add a straight arrow overlay to the environment plot.
        :param start: tuple of start point coordinate pair
        :param end: tuple of end point coordinate pair
        :param color: str of line color
        :param width: float denoting the line buffer width
        :param thickness: float denoting the Matplotlib linewidth
        :param edge_style: str or tuple denoting the Matplotlib linestyle
        :param head_size: float of head size (length) in meters
        :return: None
        """
        self._display.features.add_arrow(start, end, color, width, head_size, thickness, edge_style)

    def draw_circle(
        self,
        center: Tuple[float, float],
        radius: float,
        color: str,
        fill: bool = True,
        thickness: float = None,
        edge_style: Union[str, tuple] = None,
    ) -> None:
        """
        Add a circle or disk overlay to the environment plot.
        :param center: tuple of circle center coordinates
        :param radius: float of circle radius
        :param color: str of circle color
        :param fill: bool which toggles the interior disk color
        :param thickness: float denoting the Matplotlib linewidth
        :param edge_style: str or tuple denoting the Matplotlib linestyle
        :return: None
        """
        self._display.features.add_circle(center, radius, color, fill, thickness, edge_style)

    def draw_line(
        self,
        points: List[Tuple[float, float]],
        color: str,
        width: float = None,
        thickness: float = None,
        edge_style: Union[str, tuple] = None,
    ) -> None:
        """
        Add a straight line overlay to the environment plot.
        :param points: list of tuples of coordinate pairs
        :param color: str of line color
        :param width: float denoting the line buffer width
        :param thickness: float denoting the Matplotlib linewidth
        :param edge_style: str or tuple denoting the Matplotlib linestyle
        :return: None
        """
        self._display.features.add_line(points, color, width, thickness, edge_style)

    def draw_polygon(
        self,
        geometry: Union[Any, List[Tuple[float, float]]],
        color: str,
        interiors: List[List[Tuple[float, float]]] = None,
        fill: bool = True,
        thickness: float = None,
        edge_style: Union[str, tuple] = None,
    ) -> None:
        """
        Add an arbitrary polygon shape overlay to the environment plot.
        :param geometry: Shapely geometry or list of exterior coordinates
        :param interiors: list of lists of interior polygon coordinates
        :param color: str of rectangle color
        :param fill: bool which toggles the interior shape color
        :param thickness: float denoting the Matplotlib linewidth
        :param edge_style: str or tuple denoting the Matplotlib linestyle
        :return: None
        """
        self._display.features.add_polygon(geometry, color, interiors, fill, thickness, edge_style)

    def draw_rectangle(
        self,
        center: Tuple[float, float],
        size: Tuple[float, float],
        color: str,
        rotation: float = 0.0,
        fill: bool = True,
        thickness: float = None,
        edge_style: Union[str, tuple] = None,
    ) -> None:
        """
        Add a rectangle or box overlay to the environment plot.
        :param center: tuple of rectangle center coordinates
        :param size: tuple of rectangle (width, height)
        :param color: str of rectangle color
        :param rotation: float denoting the rectangle rotation in degrees
        :param fill: bool which toggles the interior rectangle color
        :param thickness: float denoting the Matplotlib linewidth
        :param edge_style: str or tuple denoting the Matplotlib linestyle
        :return: None
        """
        self._display.features.add_rectangle(center, size, color, rotation, fill, thickness, edge_style)

    def get_display_handle(self):
        """Returns figure and axes handles to the seacharts display."""
        return self._display.figure, self._display.axes

    def refresh_display(self) -> None:
        """
        Manually redraw the environment display window.
        :return: None
        """
        self._display.draw_plot()

    def close_display(self) -> None:
        """
        Close the environment display window and clear all vessels.
        :return: None
        """
        self._display.terminate()
        self.clear_vessels()

    def save_image(
        self,
        name: str = None,
        scale: float = 1.0,
        extension: str = "png",
    ) -> None:
        """
        Save the environment plot as a .png image.
        :param name: optional str of file name
        :param scale: optional float scaling the image resolution
        :param extension: optional str of file extension name
        :return: None
        """
        self._display.save_figure(name, scale, extension)

    def _get_static_obstacles_callback(self, request, response) -> None:
        """
        Callback function for the static obstacles subscriber.
        :param msg: ObstacleArray message
        :return: None
        """
        self.get_logger().debug("Sending Static Obstacles...")
        raw_obstacles = self.land.geometry.__geo_interface__['coordinates']
        obstacles = []
        for _pol in raw_obstacles:
            pol = _pol[0]
            polygon = Polygon()
            points = []
            for p in pol:
                point = Point()
                point.x = p[0]
                point.y = p[1]
                points.append(point)
            polygon.polygon = points
            obstacles.append(polygon)
        self.get_logger().debug(f"\n\nCLOCK: {self.get_clock().now().to_msg().sec}.{self.get_clock().now().to_msg().nanosec}\n\n")
        response.timestamp = getTimeStamp(self.get_clock())
        response.static_obstacles = obstacles
        self.get_logger().debug("Sent Static Obstacles...")
        return response