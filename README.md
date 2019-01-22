# Seoul pedestrian network
## Fixes discontinuities in Seoul pedestrian network dataset

The GIS layers for Seoul's pedestrian network are divided by a grid into many
separate shapefiles. When merged into a single layer, the linestrings do not line
up precisely at the endpoints, preventing us from using network analysis tools
that rely on precisely connected links. This script resolves this by finding the
link pairs that should be connected, and altering their geometry to share a
vertex exactly. Beware: this will permanently alter your links shapefile.

# Usage
This assumes you have already merged all the individual node layers into a single
shapefile, and likewise have merged all the link layers into a single shapefile.

1. Make sure you have QGIS installed, with OSGEO4W shell.
2. Run OSGEO4W shell as administrator.
3. From shell, run `py3-env` to switch to the OSGEO python 3 environment.
4. Run `pip install tqdm` to make that module available in python-qgis.
5. From shell, navigate to this local repository folder.
6. Run the following command, replacing _nodesLayer_ with the path to the merged
nodes layer, and _linksLayer_ with the path to the merged links layer: 
`python-qgis merging_pedestrian_network_qgis_script.py nodesLayer linksLayer`
