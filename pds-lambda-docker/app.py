"""
Lambda function that decimates a miniSEED seismogram from
one S3 bucket and uploads the result to another S3 bucket.

author: Shang-Lin Chen

"""

import os
import boto3
import json
import obspy
from obspy.core.stream import Stream
import logging

logging.basicConfig(level = logging.INFO)

# Retrieve the logger instance
logger = logging.getLogger()

# If this Lambda function is called through API Gateway,
# api_gateway will be changed to True in the process() function.
api_gateway = False

def decimate(infile, outfile, dec_factor):
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
    # Decimate each trace in the stream.
    print('Decimating traces')
    for tr in st:
        tr.decimate(factor=dec_factor, strict_length=False, no_filter=True)
        #st_new.append(tr)
    # Write the resulting stream to disk.
    st.write(outfile, format='MSEED')


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

    key = event['s3_key']
    print('Processing {}'.format(key))
    bkt_out_name = event['s3_output_bucket']
    bkt_in_name = event['s3_input_bucket']
    dec_factor = event['decimation_factor']
    print('input bucket:{} output bucket:{} decimation:{}'.format(bkt_in_name, bkt_out_name, dec_factor))
    (wf_dir, year, year_day, filename) = key.split('/')
    (fn, ext) = os.path.splitext(filename)

    session = boto3.Session()
    s3 = boto3.client('s3', region_name='us-west-2')

    infile = '/tmp/{}'.format(filename)
    outfile = '/tmp/{}_decimated.ms'.format(fn)
    # Download file from S3.
    s3.download_file(bkt_in_name, key, infile)

    if not os.path.isfile(infile):
        raise Exception('Could not download {} from {} to {}'.format(key, bkt_in_name, infile))

    logger.info('Calling decimate on {}'.format(infile))
    decimate(infile, outfile, dec_factor)

    if not os.path.isfile(outfile):
        raise Exception('Could not write output file {}'.format(outfile))

    logger.info('Uploading {} to {}'.format(outfile, bkt_out_name))
    output_key = 'decimated/{}/{}/{}.ms'.format(year, year_day, fn)
    s3.upload_file(outfile, bkt_out_name, 'decimated/{}/{}/{}.ms'.format(year, year_day, fn))
    os.remove(outfile)
    os.remove(infile)

    return { 'output_key': 's3://{}/{}'.format(bkt_out_name, output_key) }
    

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

