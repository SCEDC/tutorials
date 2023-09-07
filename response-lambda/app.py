"""
Lambda function that decimates a miniSEED seismogram from
one S3 bucket and uploads the result to another S3 bucket.

author: Shang-Lin Chen

"""

import os
import boto3
import json
import obspy
import numpy
from obspy.core.inventory.inventory import read_inventory
from obspy.core.stream import Stream
import logging

logging.basicConfig(level = logging.INFO)

# Retrieve the logger instance
logger = logging.getLogger()

# If this Lambda function is called through API Gateway,
# api_gateway will be changed to True in the process() function.
api_gateway = False

pds_bucket = 'scedc-pds'

def remove_response(infile, outfile, staxml_file, pre_filt=[], water_level=None, fmt='MSEED'):
    """
    Runs ObsPy's decimate function on the traces
    in an input seismogram.

    :param infile: Name of the input file
    :param outfile: Name of the output file
    :param dec_factor: Decimation factor
    """
    
    print('Reading', infile)
    st = obspy.read(infile)
    #st_new = Stream()
    # Create inventory from StationXML.
    inv = read_inventory(staxml_file)

    print('Removing response')
    #for tr in st:
    #    tr.remove_response()
        #st_new.append(tr)
    # Write the resulting stream to disk.
    st.remove_response(inventory=inv, pre_filt=pre_filt, water_level=water_level)
    # Convert data to int32 so that it can be compressed in STEIM2.
    for trace in st:
        trace.data = trace.data.astype(numpy.int32)
    st.write(outfile, format='MSEED', encoding='STEIM2')


def get_s3_key(net, sta, chan, loc, year, day):
    """ Returns the Public Data Set filename and the full key given an NSCL, year, and day.
    """
    filler = '_'
    filename = f'{net}{sta:{filler}<{5}}{chan}{loc:{filler}<{2}}_{year}{day.zfill(3)}.ms'
    #filename = f"{net}{sta.rjust(5, '_')}{chan}{loc.rjust(2, '_')}_{year}{day.zfill(3)}.ms"
    return (filename, f'continuous_waveforms/{year}/{year}_{day.zfill(3)}/{filename}')


def get_s3_staxml_key(net, sta):
    """ Returns the Public Set filename and full key of a station's
    StationXML file.
    """
    
    filename = f'{net}_{sta}.xml'
    return filename, f'FDSNstationXML/{net}/{filename}'


def process(event):
    """
    Process input parameters and calls decimation function.

    :param event: Input parameters to Lambda
    """

    global api_gateway

    logger.info(event)
    if 'routeKey' in event:
        api_gateway = True
        event = json.loads(event['body'])

    #key = event['s3_key']
    year, day = event['day'].split(',')
    nscl = event['nscl']

    print(year, day, nscl)

    net, sta, chan, loc = nscl.split('.')

    (filename, s3_key) = get_s3_key(net, sta, chan, loc, year, day)

    print('Processing {}'.format(s3_key))
    
    output_bucket = os.environ['S3_OUTPUT_BUCKET']
    #bkt_in_name = event['s3_input_bucket']
    
    #print('input bucket:{} output bucket:{} decimation:{}'.format(bkt_in_name, bkt_out_name, dec_factor))
    #(wf_dir, year, year_day, filename) = s3_key.split('/')
    (fn, ext) = os.path.splitext(filename)

    session = boto3.Session()
    s3 = boto3.client('s3', region_name='us-west-2')

    infile = '/tmp/{}'.format(filename)
    outfile = '/tmp/{}_noresp.ms'.format(fn)
    
    # Download waveform file from the Public Data Set.
    s3.download_file(pds_bucket, s3_key, infile)
    if not os.path.isfile(infile):
        raise Exception('Could not download {} from {} to {}'.format(s3_key, pds_bucket, infile))

    # Download StationXML from the Public Data Set.
    staxml_fn, staxml_key = get_s3_staxml_key(net, sta)
    staxml_infile = f'/tmp/{staxml_fn}'
    s3.download_file(pds_bucket, staxml_key, f'/tmp/{staxml_fn}')
    if not os.path.isfile(staxml_infile):
        raise Exception('Could not download StationXML')
    
    remove_response(infile, outfile, staxml_infile)

    if not os.path.isfile(outfile):
        raise Exception('Could not write output file {}'.format(outfile))

    logger.info('Uploading {} to {}'.format(outfile, output_bucket))
    output_key = f'noresp/{year}/{year}_{day.zfill(3)}/{fn}.ms'
    s3.upload_file(outfile, output_bucket, output_key)
    
    # Remove all temporary files.
    os.remove(outfile)
    os.remove(infile)
    os.remove(staxml_infile)

    return { 'output_key': 's3://{}/{}'.format(output_bucket, output_key) }
    

def handler(event, context):
    """ Lambda function handler.
    """
    
    response =  process(event)
    print(response)

    if api_gateway:
        return {
            'statusCode': 200,
            'body': json.dumps(response),
        }
    else:
        return response

