# Copyright 2020 the .NET Foundation
# Licensed under the MIT License

"""
Main tool driver.
"""

__all__ = ['go']

from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
import math
import os
import sep
import subprocess


def image_size_to_anet_preset(size_deg):
    """
    Get an astrometry.net "preset" size from an image size. Docs say:

    0 => ~6 arcmin
    2 => ~12 arcmin
    4 => ~24 arcmin

    etc.
    """
    return 6 + 2 * math.log2(size_deg)


def go(
    fits_path = None,
    rgb_path = None,
):
    """
    Do the whole thing.
    """

    # Check our FITS image and get some basic quantities. We need
    # to read in the data to sourcefind with SEP.

    with fits.open(fits_path) as hdul:
        hdu = hdul[0]
        wcs = WCS(hdu)
        data = hdu.data
        height, width = data.shape[-2:]

    data = data.byteswap(inplace=True).newbyteorder()

    midx = width // 2
    midy = height // 2
    coords = wcs.pixel_to_world(
        [midx, midx + 1, 0, width, 0, width],
        [midy, midy + 1, 0, height, midy, midy],
    )

    small_scale = coords[0].separation(coords[1])
    #print('small scale:', small_scale)
    large_scale = coords[2].separation(coords[3])
    #print('large scale:', large_scale)
    width = coords[4].separation(coords[5])

    # Use SEP to find sources

    bkg = sep.Background(data)
    print('SEP background level:', bkg.globalback)
    print('SEP background rms:', bkg.globalrms)

    bkg.subfrom(data)
    objects = sep.extract(data, 3, err=bkg.globalrms)
    print('SEP object count:', len(objects))
    print('columns:', objects.dtype.names)
    print('first object:', objects[0])

    coords = wcs.pixel_to_world(objects['x'], objects['y'])
    tbl = Table([coords.ra.deg, coords.dec.deg, objects['flux']], names=('RA', 'DEC', 'FLUX'))

    print('XXX hardcoded object table name')
    objects_fits = 'objects.fits'
    tbl.write(objects_fits, format='fits', overwrite=True)

    # Generate the Astrometry.Net index

    index_fits = 'index.fits'
    print('XXX hardcoded index FITS table name')

    argv = [
        '/a/wwt/aligner/astrometry.net/solver/build-astrometry-index', # XXXX
        '-i', objects_fits,
        '-o', index_fits,
        '-E',  # objects table is much less than all-sky
        '-f',  # our sort column is flux-like, not mag-like
        '-S', 'FLUX',
        '-P', str(image_size_to_anet_preset(large_scale.deg))
    ]
    subprocess.check_call(argv, shell=False)

    # Write out config file

    index_dir = os.getcwd()
    cfg_path = 'aligner.cfg'
    print('XXX hardcoded config file')

    with open(cfg_path, 'wt') as f:
        print('add_path', index_dir, file=f)
        print('inparallel', file=f)
        print('index', index_fits, file=f)

    # Solve our input image

    wcs_file = 'wcs.fits'

    argv = [
        '/a/wwt/aligner/astrometry.net/solver/solve-field', # XXXX
        '--config', cfg_path,
        '--scale-units', 'arcminwidth',
        '--scale-low', str(width.arcmin / 2),
        '--scale-high', str(width.arcmin * 2),
        '-W', wcs_file,
        rgb_path,
    ]
    subprocess.check_call(argv, shell=False)
