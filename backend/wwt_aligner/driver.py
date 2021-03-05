# Copyright 2020-2021 the .NET Foundation
# Licensed under the MIT License

"""
Main tool driver.
"""

__all__ = ['go']

from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
import math
import os.path
from PIL import Image as pil_image
from pyavm import AVM
import sep
import subprocess
import sys
from toasty.builder import Builder
from toasty.image import ImageLoader

from . import logger

DEFAULT_SOLVE_TIME_LIMIT = 60 # seconds

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
    fits_paths = None,
    rgb_path = None,
    output_path = None,
    tile_path = None,
    work_dir = '',
    anet_bin_prefix = '',
):
    """
    Do the whole thing.
    """
    index_fits_list = []

    for fits_num, fits_path in enumerate(fits_paths):
        logger.info('Processing reference science image `%s` ...', fits_path)

        # Check our FITS image and get some basic quantities. We need
        # to read in the data to sourcefind with SEP.

        try:
            data = None

            with fits.open(fits_path) as hdul:
                for hdu_num, hdu in enumerate(hdul):
                    logger.debug('  considering HDU #%d; data shape %r', hdu_num, hdu.shape)

                    if hdu.data is None:
                        continue  # reject: no data

                    if hasattr(hdu, 'columns'):
                        continue  # reject: tabular

                    if len(hdu.shape) < 2:
                        continue  # reject: not at least 2D

                    # OK, it looks like this the HDU we want!
                    wcs = WCS(hdu)
                    data = hdu.data
                    height, width = data.shape[-2:]
                    break

            assert data is not None, 'failed to find a usable image HDU'
            data = data.byteswap(inplace=True).newbyteorder()

            midx = width // 2
            midy = height // 2
            coords = wcs.pixel_to_world(
                [midx, midx + 1, 0, width, 0, width],
                [midy, midy + 1, 0, height, midy, midy],
            )

            large_scale = coords[2].separation(coords[3])
            logger.debug('  large scale for this image: %e deg', large_scale.deg)
            width = coords[4].separation(coords[5])
            logger.debug('  characteristic width for this image: %e deg', width.deg)
        except Exception as e:
            logger.warning('  Failed to read image data from this file')
            logger.warning('  Caused by: %s', e)
            continue

        # Use SEP to find sources

        logger.info('  Finding sources ...')

        try:
            bkg = sep.Background(data)
            logger.debug('  SEP background level: %e', bkg.globalback)
            logger.debug('  SEP background rms: %e', bkg.globalrms)

            bkg.subfrom(data)
            objects = sep.extract(data, 3, err=bkg.globalrms)
            logger.debug('  SEP object count: %d', len(objects))

            coords = wcs.pixel_to_world(objects['x'], objects['y'])
            tbl = Table([coords.ra.deg, coords.dec.deg, objects['flux']], names=('RA', 'DEC', 'FLUX'))

            objects_fits = os.path.join(work_dir, f'objects{fits_num}.fits')
            tbl.write(objects_fits, format='fits', overwrite=True)
        except Exception as e:
            logger.warning('  Failed to find sources in this file')
            logger.warning('  Caused by: %s')
            continue

        # Generate the Astrometry.Net index

        index_fits = os.path.join(work_dir, f'index{fits_num}.fits')

        argv = [
            anet_bin_prefix + 'build-astrometry-index',
            '-i', objects_fits,
            '-o', index_fits,
            '-I', str(fits_num),
            '-E',  # objects table is much less than all-sky
            '-f',  # our sort column is flux-like, not mag-like
            '-S', 'FLUX',
            '-P', str(image_size_to_anet_preset(large_scale.deg))
        ]
        logger.debug('  index command: %s', ' '.join(argv))

        index_log = os.path.join(work_dir, f'build-index-{fits_num}.log')
        logger.info('  Generating Astrometry.Net index ...')

        try:
            with open(index_log, 'wb') as log:
                subprocess.check_call(
                    argv,
                    stdout = log,
                    stderr = subprocess.STDOUT,
                    shell = False,
                )
        except Exception as e:
            logger.warning('  Failed to index this file')
            logger.warning('  Caused by: %s', e)
            continue

        # Success!
        index_fits_list.append(index_fits)

    if not index_fits_list:
        raise Exception('cannot align: failed to index any of the input FITS files')

    # Write out config file

    cfg_path = os.path.join(work_dir, 'aligner.cfg')

    with open(cfg_path, 'wt') as f:
        print('add_path', work_dir, file=f)
        print('inparallel', file=f)

        for p in index_fits_list:
            print('index', p, file=f)

    # Solve our input image
    #
    # XXX we can't use the "WCS" file super conveniently because it doesn't
    # contain NAXIS data. It would be nice if we could because it's small and we
    # could avoid rewriting the full image data. XXXX: use IMAGEW, IMAGEH.

    wcs_file = os.path.join(work_dir, 'solved.fits')

    # https://manpages.debian.org/testing/astrometry.net/solve-field.1.en.html
    argv = [
        anet_bin_prefix + 'solve-field',
        '--config', cfg_path,
        '--scale-units', 'arcminwidth',
        '--scale-low', str(width.arcmin / 2),
        '--scale-high', str(width.arcmin * 2),
        '--cpulimit', str(DEFAULT_SOLVE_TIME_LIMIT),  # seconds
        '--dir', work_dir,
        '-N', wcs_file,
        '--no-plots',
        '--no-tweak',
        '--downsample', '2',
        rgb_path,
    ]
    logger.debug('solve command: %s', ' '.join(argv))

    solve_log = os.path.join(work_dir, 'solve-field.log')
    logger.info('Launching Astrometry.Net solver for `%s` ...', rgb_path)

    try:
        with open(solve_log, 'wb') as log:
            subprocess.check_call(
                argv,
                stdout = log,
                stderr = subprocess.STDOUT,
                shell = False,
            )

        assert os.path.exists(wcs_file), 'Astrometry.Net did not emit a solution file'
    except Exception as e:
        logger.error('  Failed to solve this image')
        logger.error('  Proximate Python exception: %s', e)
        logger.error('  Output from solve-field:')

        try:
            with open(solve_log, 'r') as f:
                for line in f:
                    logger.error('    %s', line.rstrip())
        except Exception as sub_e:
            logger.error('     [failed to read the log! error: %s]', sub_e)

        raise

    # Convert solution to AVM, with hardcoded parity
    # inversion

    img = ImageLoader().load_path(rgb_path)

    with fits.open(wcs_file) as hdul:
        header = hdul[0].header
        wcs = WCS(header)

    hdwork = wcs.to_header()
    hdwork['CRPIX2'] = img.height + 1 - hdwork['CRPIX2']
    hdwork['PC1_2'] *= -1
    hdwork['PC2_2'] *= -1
    wcs = WCS(hdwork)
    avm = AVM.from_wcs(wcs, shape=(img.height, img.width))

    # Apply AVM
    #
    # pyavm can't convert image formats, so if we've been asked to emit a tagged
    # imagine in a format different than the image format, we need to do that
    # conversion manually. We're not in a great position to be clever so we
    # assess "format" from filename extensions.

    in_name_pieces = os.path.splitext(os.path.basename(rgb_path))

    if output_path is None:
        output_path = in_name_pieces[0] + '_tagged' + in_name_pieces[1]

    input_ext = in_name_pieces[1].lower()
    output_ext = os.path.splitext(output_path)[1].lower()

    if input_ext != output_ext:
        logger.info('Converting input image to create `%s`', output_path)
        img.save(output_path, format=output_ext.replace('.', ''))

        logger.info('Adding AVM tags to `%s`', output_path)
        avm.embed(output_path, output_path)
    else:
        logger.info('Writing AVM-tagged image to:`%s`', output_path)
        avm.embed(rgb_path, output_path)

    # Tile it for WWT, if requested

    if tile_path is not None:
        from toasty.merge import averaging_merger, cascade_images
        from toasty.pyramid import PyramidIO

        logger.info('Creating base layer of WWT tiling ...')

        pio = PyramidIO(tile_path, default_format=img.default_format)
        builder = Builder(pio)
        builder.make_thumbnail_from_other(img)
        builder.tile_base_as_study(img, cli_progress=True)
        builder.apply_wcs_info(wcs, img.width, img.height)
        builder.set_name(in_name_pieces[0])
        builder.write_index_rel_wtml()

        logger.info('Cascading tiles ...')
        cascade_images(
            pio,
            builder.imgset.tile_levels,
            averaging_merger,
            cli_progress=True
        )
