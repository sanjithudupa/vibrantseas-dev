import os
import subprocess
import numpy as np
from netCDF4 import Dataset
import sys

if len(sys.argv) < 3:
    print("Usage: python3 new_l2gen.py <raw_data_path> <nc_output_path>")
    sys.exit(1)

raw_data_path = sys.argv[1]
nc_output_path = sys.argv[2]

if not os.path.exists(raw_data_path):
    print(f"Error: {raw_data_path} does not exist")
    sys.exit(1)

if os.path.exists(nc_output_path):
    print(f"Error: {nc_output_path} already exists")
    sys.exit(1)

params = {
    "raw_data_path": raw_data_path,
    "nc_output_path": nc_output_path,
    "tmp_dir": os.path.join(os.path.dirname(nc_output_path), "tmp")
}

if not os.path.exists(params["tmp_dir"]):
    os.makedirs(params["tmp_dir"])

def gdal_translate(input_file, output_file):
    """
    runs gdal_translate from terminal for an input and output file
    """
    command = [
        'gdal_translate',
        '-of', 'NetCDF',  # Specify output format as NetCDF
        input_file,
        output_file
    ]
    subprocess.run(command, check=True)

def l2gen(par_path):
    """
    runs l2gen from terminal with a generated par file
    """
    command = ['l2gen', f'par={par_path}']
    subprocess.run(command, check=True)

def watermask_tif_to_nc():
    """
    converts the usgs provided watermask tif file in raw_data_path folder to a netcdf in tmp folder
    """
    print("EHLLO")
    nc_path = os.path.join(params['tmp_dir'], "WATER_MASK.nc")
    print(params['raw_data_path'])
    for file in os.listdir(params['raw_data_path']):
        print(f"processing {file}")
        if file.startswith("._"):
            os.remove(os.path.join(params['raw_data_path'], file))
        elif file.lower().endswith("mtl.txt"):
            MTL_file_path = os.path.join(params['raw_data_path'], file)
        elif file.lower().endswith("water_mask.tif") and not os.path.exists(nc_path):
            gdal_translate(os.path.join(params['raw_data_path'], file), nc_path)
    return nc_path, MTL_file_path

def add_masks_to_nc(input_nc):
    """
    converts watermask.tif Band1 variable array to land, water, and cloud (unused) masks after tif->netcdf conversion which
    allows the netcdf to be taken as input in the l2gen par file
    """
    # Open the NetCDF file in append mode
    with Dataset(input_nc, 'a') as nc:
        if 'watermask' in nc.variables:
            return 0
        # Read the Band1 variable
        print(f"reading {input_nc}")
        print("nc.variables", nc.variables)
        band1 = nc.variables['Band1'][:]
        # Check if the new variables already exist, if so delete them
        if 'watermask' in nc.variables:
            del nc.variables['watermask']
        if 'landmask' in nc.variables:
            del nc.variables['landmask']
        # Create the watermask variable
        
        # if dimension y not found, create it
        if 'y' not in nc.dimensions:
            nc.createDimension('y', band1.shape[0])
        # if dimension x not found, create it
        if 'x' not in nc.dimensions:
            nc.createDimension('x', band1.shape[1])
        
        watermask = nc.createVariable('watermask', 'b', ('y', 'x'), fill_value=-1)
        watermask.long_name = "watermask"
        watermask.description = "A simple binary water mask"
        watermask.comment = "0 = land, 1 = water"
        watermask.valid_min = 0
        watermask.valid_max = 1
        
        # Create the landmask variable
        landmask = nc.createVariable('landmask', 'b', ('y', 'x'), fill_value=-1)
        landmask.long_name = "landmask"
        landmask.description = "A simple binary land mask"
        landmask.comment = "0 = water, 1 = land"
        landmask.valid_min = 0
        landmask.valid_max = 1
        
        # Create the cloudmask variable
        cloudmask = nc.createVariable('cloudmask', 'b', ('y', 'x'), fill_value=-1)
        cloudmask.long_name = "cloudmask"
        cloudmask.description = "A simple binary cloud mask"
        cloudmask.comment = "0 = not clouds, 1 = clouds"
        cloudmask.valid_min = 0
        cloudmask.valid_max = 1
        
        # Create the shadowmask variable
        shadowmask = nc.createVariable('shadowmask', 'b', ('y', 'x'), fill_value=-1)
        shadowmask.long_name = "shadowmask"
        shadowmask.description = "A simple binary shadow mask"
        shadowmask.comment = "0 = not shadow, 1 = shadow"
        shadowmask.valid_min = 0
        shadowmask.valid_max = 1
        
        # Fill the watermask and landmask variables
        watermask_data = np.where(band1 == 1, 1, 0).astype('b')
        landmask_data = np.where(band1 == 0, 1, 0).astype('b')
        cloudmask_data = np.where(band1 == 2, 1, 0).astype('b')
        shadowmask_data = np.where(band1 == 3, 1, 0).astype('b')
        
        # Assign the data to the variables
        watermask[:] = watermask_data
        landmask[:] = landmask_data
        cloudmask[:] = cloudmask_data
        shadowmask[:] = shadowmask_data

def make_masks():
    """
    makes a l2gen usable mask for a particular date given preseadas and seadas paths
    """
    nc_path, mtl_path = watermask_tif_to_nc()
    add_masks_to_nc(nc_path)
    return nc_path, mtl_path

def run_l2gen(data_path):
    """
    iterates over the folders in the Processing directory inside the batch_processing_path
    for each folder
        makes the l2gen usable mask
        makes the par file
        runs l2gen
    corruption seems to sometimes be an issue for certain dates, but works for 95% of dates
    """
    seadas_products_path = params['nc_output_path']
    mask_path, mtl_path = make_masks()
    
    if os.path.isdir(data_path) and not os.path.isfile(seadas_products_path):
        print(f'running l2gen for {data_path}')

        ifile = mtl_path

        if ifile:
            ofile = params['nc_output_path']
            water = land = mask_path

            # Create the content for the .par file
            content = f"""# PRIMARY INPUT OUTPUT FIELDS
ifile={ifile}
ofile={ofile}
water={water}
land={land}
"""
            # Define the output .par file path
            par_file_path = os.path.join(data_path, "config.par")

            # Write the content to the .par file
            with open(par_file_path, 'w') as par_file:
                par_file.write(content)

            print(f".par file generated at {par_file_path}")

            # Run l2gen with the generated .par file
            l2gen(par_file_path)

print(f"starting l2gen on files at {params['raw_data_path']}, outputting to {params['nc_output_path']}")

run_l2gen(params['raw_data_path'])