import pytest
import unittest.mock as mock

import open_cp.geometry
open_cp.geometry.configure_gdal()

import os
import geopandas as gpd
import numpy as np

import open_cp.gui.predictors.geo_clip as geo_clip
import open_cp.gui.common as common

@pytest.fixture
def geojson_filename():
    return os.path.join("tests", "test_geometry", "test.geojson")

@pytest.fixture
def shp_filename():
    return os.path.join("tests", "test_geometry", "test.shp")

def test_can_find_file(geojson_filename):
    frame = gpd.read_file(geojson_filename)
    geo = frame.unary_union
    assert geo.area == pytest.approx(0.5)
    
    frame = gpd.read_file(os.path.join("tests", "test_geometry", "test.shp"))
    geo = frame.unary_union
    assert geo.area == pytest.approx(0.5)

@pytest.fixture
def model():
    import logging
    logging.basicConfig(level=logging.DEBUG)
    model_mock = mock.MagicMock()
    model_mock.analysis_tools_model = mock.MagicMock()
    model_mock.analysis_tools_model.projected_coords.return_value = (
        [0,1,2], [1,0,-1] )
    model_mock.analysis_tools_model.coordinate_projector = mock.MagicMock()
    model_mock.analysis_tools_model.coordinate_projector.return_value = None
    return model_mock

@pytest.fixture
def comp(model):
    return geo_clip.CropToGeometry(model)

def test_setup_gdal(comp):
    import os
    assert "GDAL_DATA" in os.environ

def test_build_CropToGeometry(comp):
    assert comp.name == "Crop to geometry"
    assert comp.settings_string == "No geometry"

    old = comp.settings_string
    data = comp.to_dict()
    comp.from_dict(data)
    assert comp.settings_string == old

def test_run_no_settings(comp):
    assert comp.run(None) is None

def test_load(comp, geojson_filename):
    comp.load(geojson_filename)
    geo = comp.geometry()
    assert geo.area == 0.5
    coords = np.asarray(geo.exterior.coords)
    np.testing.assert_allclose(coords, [[0,0], [1,0], [1,1], [0,0]])

    assert comp.settings_string.startswith("Geometry file: ")
    assert comp.crs == {"init" : "epsg:4326"}
    assert comp.settings_string.endswith(geojson_filename)
    assert comp.guessed_crs is False

def test_load_shapefile(comp, shp_filename):
    comp.load(shp_filename)
    geo = comp.geometry()
    assert geo.area == 0.5
    coords = np.asarray(geo.exterior.coords)
    np.testing.assert_allclose(coords, [[0,0], [1,1], [1,0], [0,0]])

    assert comp.settings_string.startswith("Geometry file: ")
    assert comp.crs == {"init" : "epsg:4326"}
    assert comp.settings_string.endswith(shp_filename)
    assert comp.guessed_crs is False

def test_load_failure(comp):
    comp.load("bob")

    assert comp.filename is None
    assert comp.error == "Failed to load: <class 'OSError'>/no such file or directory: 'bob'"

def test_dataset_coords(comp):
    xcs, ycs = comp.dataset_coords()
    np.testing.assert_almost_equal(xcs, [0,1,2])
    np.testing.assert_almost_equal(ycs, [1,0,-1])
    
def test_projector(comp, geojson_filename):
    assert comp.chosen_projector() is None
    comp.load(geojson_filename)

    geo = comp.projected_geometry()
    coords = np.asarray(geo.exterior.coords)
    np.testing.assert_allclose(coords, [[0,0], [1,0], [1,1], [0,0]])

def test_epsg_and_projector(comp, geojson_filename, model):
    comp.load(geojson_filename)
    comp.epsg = 2041
    geo = comp.projected_geometry()
    coords = np.asarray(geo.exterior.coords)
    
    def proj(x,y):
        return y,x
    task = mock.MagicMock()
    task.make_tasks.return_value = [proj]
    model.analysis_tools_model.coordinate_projector.return_value = task
    geo = comp.projected_geometry()
    np.testing.assert_allclose(np.asarray(geo.exterior.coords), coords)
    
    comp.epsg = None
    geo = comp.projected_geometry()
    np.testing.assert_allclose(np.asarray(geo.exterior.coords),
        [[0,0], [0,1], [1,1], [0,0]])