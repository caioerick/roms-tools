import pytest
import tempfile
import os
from roms_tools import Grid, TidalForcing
import xarray as xr
from roms_tools.setup.download import download_test_data
import textwrap


@pytest.fixture
def grid_that_lies_within_bounds_of_regional_tpxo_data():
    grid = Grid(
        nx=3, ny=3, size_x=1500, size_y=1500, center_lon=235, center_lat=25, rot=-20
    )
    return grid


@pytest.fixture
def grid_that_is_out_of_bounds_of_regional_tpxo_data():
    grid = Grid(
        nx=3, ny=3, size_x=1800, size_y=1500, center_lon=235, center_lat=25, rot=-20
    )
    return grid


@pytest.fixture
def grid_that_straddles_dateline():
    """
    Fixture for creating a domain that straddles the dateline.
    """
    grid = Grid(
        nx=5,
        ny=5,
        size_x=1800,
        size_y=2400,
        center_lon=-10,
        center_lat=30,
        rot=20,
    )

    return grid


@pytest.fixture
def grid_that_straddles_180_degree_meridian():
    """
    Fixture for creating a domain that straddles 180 degree meridian.
    """

    grid = Grid(
        nx=5,
        ny=5,
        size_x=1800,
        size_y=2400,
        center_lon=180,
        center_lat=30,
        rot=20,
    )

    return grid


@pytest.mark.parametrize(
    "grid_fixture",
    [
        "grid_that_lies_within_bounds_of_regional_tpxo_data",
        "grid_that_is_out_of_bounds_of_regional_tpxo_data",
        "grid_that_straddles_dateline",
        "grid_that_straddles_180_degree_meridian",
    ],
)
def test_successful_initialization_with_global_data(grid_fixture, request):

    fname = download_test_data("TPXO_global_test_data.nc")

    grid = request.getfixturevalue(grid_fixture)

    tidal_forcing = TidalForcing(
        grid=grid, source={"name": "TPXO", "path": fname}, ntides=2
    )

    assert isinstance(tidal_forcing.ds, xr.Dataset)
    assert "omega" in tidal_forcing.ds
    assert "ssh_Re" in tidal_forcing.ds
    assert "ssh_Im" in tidal_forcing.ds
    assert "pot_Re" in tidal_forcing.ds
    assert "pot_Im" in tidal_forcing.ds
    assert "u_Re" in tidal_forcing.ds
    assert "u_Im" in tidal_forcing.ds
    assert "v_Re" in tidal_forcing.ds
    assert "v_Im" in tidal_forcing.ds

    assert tidal_forcing.source == {"name": "TPXO", "path": fname}
    assert tidal_forcing.ntides == 2


def test_successful_initialization_with_regional_data(
    grid_that_lies_within_bounds_of_regional_tpxo_data,
):

    fname = download_test_data("TPXO_regional_test_data.nc")

    tidal_forcing = TidalForcing(
        grid=grid_that_lies_within_bounds_of_regional_tpxo_data,
        source={"name": "TPXO", "path": fname},
        ntides=10,
    )

    assert isinstance(tidal_forcing.ds, xr.Dataset)
    assert "omega" in tidal_forcing.ds
    assert "ssh_Re" in tidal_forcing.ds
    assert "ssh_Im" in tidal_forcing.ds
    assert "pot_Re" in tidal_forcing.ds
    assert "pot_Im" in tidal_forcing.ds
    assert "u_Re" in tidal_forcing.ds
    assert "u_Im" in tidal_forcing.ds
    assert "v_Re" in tidal_forcing.ds
    assert "v_Im" in tidal_forcing.ds

    assert tidal_forcing.source == {"name": "TPXO", "path": fname}
    assert tidal_forcing.ntides == 10


def test_unsuccessful_initialization_with_regional_data_due_to_nans(
    grid_that_is_out_of_bounds_of_regional_tpxo_data,
):

    fname = download_test_data("TPXO_regional_test_data.nc")

    with pytest.raises(ValueError, match="NaN values found"):
        TidalForcing(
            grid=grid_that_is_out_of_bounds_of_regional_tpxo_data,
            source={"name": "TPXO", "path": fname},
            ntides=10,
        )


@pytest.mark.parametrize(
    "grid_fixture",
    ["grid_that_straddles_dateline", "grid_that_straddles_180_degree_meridian"],
)
def test_unsuccessful_initialization_with_regional_data_due_to_no_overlap(
    grid_fixture, request
):

    fname = download_test_data("TPXO_regional_test_data.nc")

    grid = request.getfixturevalue(grid_fixture)

    with pytest.raises(
        ValueError, match="Selected longitude range does not intersect with dataset"
    ):
        TidalForcing(grid=grid, source={"name": "TPXO", "path": fname}, ntides=10)


def test_insufficient_number_of_consituents(grid_that_straddles_dateline):

    fname = download_test_data("TPXO_global_test_data.nc")

    with pytest.raises(ValueError, match="The dataset contains fewer"):
        TidalForcing(
            grid=grid_that_straddles_dateline,
            source={"name": "TPXO", "path": fname},
            ntides=10,
        )


def test_tidal_forcing_plot_save(tidal_forcing, tmp_path):
    """
    Test plot and save methods in the same test since we dask arrays are already computed.
    """
    tidal_forcing.ds.load()

    tidal_forcing.plot(varname="ssh_Re", ntides=0)

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        filepath = tmpfile.name

    tidal_forcing.save(filepath)

    try:
        assert os.path.exists(filepath)
    finally:
        os.remove(filepath)


def test_roundtrip_yaml(tidal_forcing):
    """Test that creating a TidalForcing object, saving its parameters to yaml file, and re-opening yaml file creates the same object."""

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        filepath = tmpfile.name

    try:
        tidal_forcing.to_yaml(filepath)

        tidal_forcing_from_file = TidalForcing.from_yaml(filepath)

        assert tidal_forcing == tidal_forcing_from_file

    finally:
        os.remove(filepath)


def test_from_yaml_missing_tidal_forcing():
    yaml_content = textwrap.dedent(
        """\
    ---
    roms_tools_version: 0.0.0
    ---
    Grid:
      nx: 100
      ny: 100
      size_x: 1800
      size_y: 2400
      center_lon: -10
      center_lat: 61
      rot: -20
      topography_source: ETOPO5
      smooth_factor: 8
      hmin: 5.0
      rmax: 0.2
    """
    )

    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        yaml_filepath = tmp_file.name
        tmp_file.write(yaml_content.encode())

    try:
        with pytest.raises(
            ValueError, match="No TidalForcing configuration found in the YAML file."
        ):
            TidalForcing.from_yaml(yaml_filepath)
    finally:
        os.remove(yaml_filepath)