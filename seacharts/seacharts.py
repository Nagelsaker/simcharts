from typing import Sequence, Union

from seacharts.features import Ocean, Surface, Details
from seacharts.files import Parser


class ENC:
    """Class for parsing Navigational Electronic Chart data sets

    This class reads data sets issued by the Norwegian Mapping Authority
    (Kartverket) and extracts features from a user-specified region in
    Cartesian coordinates (easting/northing). Supports Shapely Points and
    Polygons ignoring all inner holes.

    :param origin: tuple(easting, northing) coordinates
    :param window_size: tuple(width, height) of the window size
    :param region: str or Sequence[str] of Norwegian regions
    :param depths: Sequence of integer depth bins for features
    :param new_data: bool indicating if new data should be parsed
    """
    _layers = (Ocean, Surface, Details)
    _features = tuple(f for x in _layers for f in x.features)

    default_origin = (38100, 6948700)
    default_window_size = (20000, 16000)
    default_region = 'Møre og Romsdal'

    def __init__(self,
                 origin: tuple = default_origin,
                 window_size: tuple = default_window_size,
                 region: Union[str, Sequence] = default_region,
                 depths: Sequence = None,
                 new_data: bool = False):

        if isinstance(origin, tuple) and len(origin) == 2:
            self.origin = origin
        else:
            raise TypeError(
                "ENC: Origin should be a tuple of size two"
            )
        if isinstance(window_size, tuple) and len(window_size) == 2:
            self.window_size = window_size
        else:
            raise TypeError(
                "ENC: Window size should be a tuple of size two"
            )
        tr_corner = (i + j for i, j in zip(self.origin, self.window_size))
        bounding_box = *self.origin, *tr_corner
        self.parser = Parser(bounding_box, region, depths)
        self.parser.update_charts_data(self._features, new_data)
        self.layers = {x.__name__: x(self.parser.load) for x in self._layers}

    def __getitem__(self, item):
        return self.layers[item.capitalize()]

    def __getattr__(self, item):
        return self.__getitem__(item)

    @property
    def supported_features(self):
        s = "Supported categories and features:\n"
        for category in self._layers:
            s += category.__name__.lower() + ": "
            s += ", ".join(f.__name__.lower() for f in category.features)
            s += "\n"
        return s

    @property
    def supported_projection(self):
        return "EUREF89 UTM sone 33, 2d"
