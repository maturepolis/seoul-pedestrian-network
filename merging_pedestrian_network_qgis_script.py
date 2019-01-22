# coding=utf-8
""" Fixes discontinuities in Seoul pedestrian network dataset

The GIS layers for Seoul's pedestrian network are divided by a grid into many
separate shapefiles. When merged into a single layer, the linestrings do not line
up precisely at the endpoints, preventing us from using network analysis tools
that rely on precisely connected links. This script resolves this by finding the
link pairs that should be connected, and altering their geometry to share a
vertex exactly. Beware: this will permanently alter your links shapefile.
"""

import argparse

from qgis.core import QgsApplication, QgsVectorLayer, QgsRectangle, QgsGeometry
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('nodesLayer', help='path to merged nodes layer')
parser.add_argument('linksLayer', help='path to merged links layer')
args = parser.parse_args()

# supply path to qgis install location
QgsApplication.setPrefixPath(r'C:\Program Files\QGIS 3.4\bin\qgis-bin.exe', True)

# create a reference to the QgsApplication, setting the
# second argument to False disables the GUI
qgs = QgsApplication([], False)

# load providers
qgs.initQgis()

# Write your code here to load some layers, use processing
# algorithms, etc.

# load combined node and link layers
print('loading nodes and links layers')
allNodesLayer = QgsVectorLayer(args.nodesLayer, "AllNodes", "ogr")
allLinksLayer = QgsVectorLayer(args.linksLayer, "AllLinks", "ogr")

# get all mesh_ids, edge node pairs, and point coordinates of edge nodes
allMeshIds = set()
allNodePairs = dict()
allPointsByMeshNode = dict()

print('iterating through all nodes')
allNodesLayer.selectAll()
for nodeFeature in tqdm(allNodesLayer.getFeatures(), total=allNodesLayer.selectedFeatureCount()):
    meshId = nodeFeature['MESH_ID']
    allMeshIds.add(nodeFeature['MESH_ID'])

    adjacentMeshId = nodeFeature['ADJMAP_ID']
    adjacentNode = nodeFeature['ADJND_ID']

    if adjacentMeshId > 0 or adjacentNode > 0:
        currentNode = nodeFeature['NODE_ID']
        allNodePairs[(meshId, currentNode)] = (adjacentMeshId, adjacentNode)
        allPointsByMeshNode[(meshId, currentNode)] = nodeFeature.geometry().asWkt()[7:-1]

print('{} edge nodes found'.format(len(allNodePairs.keys())))

fixedCount = 0
deleteCount = 0
orphanNodes = set()

print('finding broken pairs')
for nodeSource, nodeTarget in allNodePairs.items():
    if nodeTarget not in allNodePairs or allNodePairs[nodeTarget] != nodeSource:
        orphanNodes.add(nodeSource)

print('cleaning up broken pairs')
for orphanNodeId in tqdm(orphanNodes):
    orphanX, orphanY = [float(coord) for coord in allPointsByMeshNode[orphanNodeId].split(' ')]
    tolerance = 0.00001
    nearestNeighborWindow = QgsRectangle(
        orphanX - tolerance,
        orphanY - tolerance,
        orphanX + tolerance,
        orphanY + tolerance)
    allNodesLayer.selectByRect(nearestNeighborWindow)
    if allNodesLayer.selectedFeatureCount() == 2:
        nodeIds = [(feature['MESH_ID'], feature['NODE_ID']) for feature in allNodesLayer.getSelectedFeatures()]
        featureIds = [feature.id() for feature in allNodesLayer.getSelectedFeatures()]
        if orphanNodeId == nodeIds[0]:
            allNodePairs[orphanNodeId] = nodeIds[1]
            fixedCount += 1
            if nodeIds[1] not in allPointsByMeshNode:
                allPointsByMeshNode[nodeIds[1]] = allNodesLayer.getFeature(featureIds[1]).geometry().asWkt()[7:-1]
        elif orphanNodeId == nodeIds[1]:
            allNodePairs[orphanNodeId] = nodeIds[0]
            fixedCount += 1
            if nodeIds[0] not in allPointsByMeshNode:
                allPointsByMeshNode[nodeIds[0]] = allNodesLayer.getFeature(featureIds[0]).geometry().asWkt()[7:-1]
        else:
            del allNodePairs[orphanNodeId]
            deleteCount += 1
            print('node was not in pair!')
    else:
        del allNodePairs[orphanNodeId]
        deleteCount += 1
print('{} pairs fixed'.format(fixedCount))
print('{} pairs deleted'.format(deleteCount))

# try to edit links layer
if allLinksLayer.startEditing():
    print('start editing links layer')

changeCount = 0
# iterate through links
allLinksLayer.selectAll()
for linkFeature in tqdm(allLinksLayer.getFeatures(), total=allLinksLayer.selectedFeatureCount()):
    startNode = (linkFeature['MESH_ID'], linkFeature['S_NODE_ID'])
    if startNode in allNodePairs and allNodePairs[startNode] in allNodePairs:
        xyList = linkFeature.geometry().asWkt()[18:-2].split(', ')
        xyList[0] = allPointsByMeshNode[allNodePairs[startNode]]
        allPointsByMeshNode[startNode] = xyList[0]
        newGeom = QgsGeometry.fromWkt('MultiLineString(({}))'.format(', '.join(xyList)))
        if allLinksLayer.changeGeometry(linkFeature.id(), newGeom):
            changeCount += 1

    endNode = (linkFeature['MESH_ID'], linkFeature['E_NODE_ID'])
    if endNode in allNodePairs and allNodePairs[endNode] in allNodePairs:
        xyList = linkFeature.geometry().asWkt()[18:-2].split(', ')
        xyList[-1] = allPointsByMeshNode[allNodePairs[endNode]]
        allPointsByMeshNode[endNode] = xyList[-1]
        newGeom = QgsGeometry.fromWkt('MultiLineString(({}))'.format(', '.join(xyList)))
        if allLinksLayer.changeGeometry(linkFeature.id(), newGeom):
            changeCount += 1

if allLinksLayer.commitChanges():
    print('committing changes to {} links'.format(changeCount))

# check our impact
mismatchCount = 0
print('checking for mismatched node locations')
for nodeA, nodeB in allNodePairs.items():
    if allPointsByMeshNode[nodeA] != allPointsByMeshNode[nodeB]:
        mismatchCount += 1
        print(nodeA, nodeB)
        print(allPointsByMeshNode[nodeA])
        print(allPointsByMeshNode[nodeB])
print('{} mismatched'.format(mismatchCount))


# When your script is complete, call exitQgis() to remove the
# provider and layer registries from memory

qgs.exitQgis()
