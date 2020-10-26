# SeaCharts
Python-based application for reading Electronic Navigational Charts (ENC)

[![platform](https://img.shields.io/badge/platform-windows-lightgrey)]()
[![python version](https://img.shields.io/badge/python-3.7-blue)]()
[![license](https://img.shields.io/badge/license-MIT-green)]()


## Features

- Read and process depth data 
[FileGDB](https://gdal.org/drivers/vector/filegdb.html) files into points and
polygon coordinate lists.


## Code style
This module follows the [PEP8](https://www.python.org/dev/peps/pep-0008/) 
convention for Python code.


## Prerequisites

First, ensure that [Python 3.7](https://www.python.org/downloads/) 
(or another compatible version) and the required
[C++ build tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019) 
are installed.

Next, install the required Python packages (in a virtual environment):
```
pip install wheel
pip install pipwin
pipwin install numpy
pipwin install pandas
pipwin install shapely
pipwin install gdal
pipwin install fiona
```


## Usage
This module supports reading and processing the `FGDB` files for sea depth data 
found [here](https://kartkatalog.geonorge.no/metadata/2751aacf-5472-4850-a208-3532a51c529a).

### Downloading regional datasets
Follow the above link to download the `Depth data` (`Sjøkart - Dybdedata`) 
dataset from the [Norwegian Mapping Authority](https://kartkatalog.geonorge.no/?organization=Norwegian%20Mapping%20Authority), 
by adding it to the Download queue and navigating to the separate 
[download page](https://kartkatalog.geonorge.no/nedlasting). 
Choose one or more county areas (e.g. `Møre og Romsdal`), and 
select the `EUREF89 UTM sone 33, 2d` (`UTM zone 33N`) projection and `FGDB 10.0` 
format. Finally, select your appropriate user group and purpose, and click 
`Download` to obtain the ZIP file(s).

### Processing ENC data into shapefiles
Place the downloaded ZIP file(s) in the path `data/external/`, where the 
top-level folder `data` is located in the same directory as the executing 
script.

Import the module, initialize an instance of `seacharts.ENC` with appropriate 
settings, and set its `new_data` keyword argument to `True` in order 
to unpack and parse desired ENC features from the downloaded ZIP file(s) into 
shapefiles:

```python
from seacharts import ENC

origin = (38100, 6948700)     # easting/northing (UTM zone 33N)
window_size = (20000, 16000)  # w, h (east, north) distance in meters
region = 'Møre og Romsdal'    # name for a Norwegian county region

enc = ENC(origin, window_size, region, new_data=True)

```
Note that `region` may be one or several Norwegian county names
(or the whole country if the `Hele landet` data set is available), 
corresponding to each downloaded ZIP file. Furthermore, a user-defined list of 
sea `depths` bins may be passed to `ENC` as an additional keyword argument.

### Accessing features
After the data is parsed into shapefiles and read into memory as shown above, 
the [Shapely](https://pypi.org/project/Shapely/) -based features may be 
accessed through the following ENC attributes:
```python
from seacharts import ENC

origin = (38100, 6948700)     # easting/northing (UTM zone 33N)
window_size = (20000, 16000)  # w, h (east, north) distance in meters
region = 'Møre og Romsdal'    # name for a Norwegian county region

enc = ENC(origin, window_size, region)
print(enc.supported_features)

feature1 = enc.ocean.seabed[-1]
feature2 = enc.surface.land[-1]

for feature in (feature1, feature2):
    print("Feature name:                    ", feature.name)
    print("Feature shape:                   ", feature.shape)
    print("Feature category:                ", feature.category)
    print("Area of the feature polygon:     ", int(feature.area))
    print("Number of feature polygon points:", len(feature.coordinates))
    print("Minimum sea depth inside feature:", int(feature.depth))
    print()

```
Note that the `new_data` argument may be omitted or set to `False` if the 
desired regional feature data has already been unpacked and processed into 
shapefiles in a previous call. Additionally, the `origin` and `window_size` 
arguments here may be different from the one used to extract the external 
ENC data, allowing for loading of more specific (smaller) areas of interest 
into memory during runtime.


## Contributors

- Simon Blindheim ([simon.blindheim@ntnu.no](mailto:simon.blindheim@ntnu.no))


## License

This project uses the [MIT](https://choosealicense.com/licenses/mit/) license.