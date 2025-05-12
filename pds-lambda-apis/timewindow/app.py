"""
Lambda function that decimates a miniSEED seismogram from
one S3 bucket and uploads the result to another S3 bucket.

@author: Shang-Lin Chen

"""

import os
import boto3
import json
import base64
import obspy
from obspy.core.stream import Stream
from obspy.core import UTCDateTime
import logging
import json

logging.basicConfig(level = logging.INFO)

s3_input_bucket = 'scedc-pds'

# Retrieve the logger instance
logger = logging.getLogger()

formats = {
    'SAC': 'sac',
    'MSEED': 'ms',
}

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



def write_outfile(infile, start_time=None, end_time=None, dec_factor=1, fmt='MSEED'):
    """
    Write an output file in the desired format.
    :param infile: Name of the input file
    :param outfile: Name of the output file
    :param dec_factor: Decimation factor
    """
    
    print('Reading', infile)
    st = obspy.read(infile)

    if start_time and end_time:
        st.trim(start_time, end_time)

    #st_new = Stream()
    # Decimate each trace in the stream.
    if dec_factor > 1:
        print('Decimating traces')
        for tr in st:
            tr.decimate(factor=dec_factor, strict_length=False, no_filter=True)
            #st_new.append(tr)
        # Write the resulting stream to disk.

    input_filename, _ = os.path.splitext(infile)

    if fmt in formats:
        outfile = "{}.{}".format(input_filename, formats[fmt])
        print('Writing', outfile)
        st.write(outfile, format=fmt)
    else:
        raise Exception('Unknown format')
    return outfile


def get_time_window(event):
    """ Returns a time window as a pair of obspy.core.UTCDateTime objects,
    given the Lambda input event. The start_time and end_time fields are expected
    to be present as ISO8601:2004 strings.
    """
    start_time = None
    end_time = None

    if 'start_time' in event:
        start_time = UTCDateTime(event['start_time'])
    else:
        raise Exception('No start time set')
    if 'end_time' in event:
        end_time = UTCDateTime(event['end_time'])
    
    return start_time, end_time


def get_input_key(nscl, start_time):
    """ Returns the key of the object in the SCEDC Public Dataset bucket
    that corresponds to a NSCL string and start time.
    """
    net, sta, chan, loc = nscl.split('.')

    # '-' can be used to stand for spaces in the location code.
    # Convert both '-' and actual spaces to '_' because that is used 
    # in the key names.
    loc = loc.replace('-', '_').replace(' ', '_')
    
    if loc == '':
        loc = '__'
    
    key = 'continuous_waveforms/{0}/{0}_{1:03}/{2}{3:_<5}{4:_<3}{5:_<2}_{0}{1:03}.ms'.format(start_time.year, start_time.julday, net, sta, chan, loc)
    return key


def get_temp_filename(key, start_time):
    basename = os.path.basename(key)
    (filename, ext) = os.path.splitext(basename)
    filename += '_{:02}{:02}{:02}{}'.format(start_time.hour, start_time.minute, start_time.second, ext)
    return '/tmp/' + filename


def make_waveform_json(wf_file, start_time, end_time):
    """ Reads a waveform file and returns it as a JSON-compatible dictionary.
    """
    
    st = obspy.read(wf_file).merge()
    st.trim(start_time, end_time)
    wf_dict = {}
    trace = st[0]
    wf_dict['network'] = trace.stats['network']
    wf_dict['station'] = trace.stats['station']
    wf_dict['channel'] = trace.stats['channel']
    wf_dict['delta'] = trace.stats['delta']
    wf_dict['location'] = trace.stats['location']
    wf_dict['starttime'] = trace.stats['starttime'].isoformat()
    wf_dict['endtime'] = trace.stats['endtime'].isoformat()
    wf_dict['sampling_rate'] = trace.stats['sampling_rate']
    data_list =  trace.data.tolist()
    print(data_list[0:10])
    wf_dict['data'] = data_list

    return wf_dict


def process(event):
    """
    Process input parameters and calls decimation function.

    :param event: Input parameters to Lambda
    """

    api_gateway = False

    logger.info(event)
    if 'routeKey' in event:
        api_gateway = True
        event = json.loads(event['body'])

    logger.info(event)
    waveforms = []

    session = boto3.Session()
    s3 = boto3.client('s3', region_name='us-west-2')

    for window in event['Windows']:
        nscl = '.'.join([window['Network'], window['Station'], window['Channel'], window['Location']])
        start_time = UTCDateTime(window['Starttime'])
        end_time = UTCDateTime(window['Endtime'])
    
        if start_time is None or end_time is None:
            raise Exception("Missing start_time or end_time.")

        # TODO: We should be able to handle requests that cross day boundaries.
        if start_time.year != end_time.year or start_time.julday != end_time.julday:
            raise Exception("Time windows must start and end within the same day.")

    
        

        key = get_input_key(nscl, start_time)
        infile = get_temp_filename(key, start_time) 

        print(key, infile)

        download_succeeded = False

        # Download file from S3.
        try:
            s3.download_file(s3_input_bucket, key, infile)
            download_succeeded = True
        except Exception:
            print('Could not download {} from {} to {}'.format(key, s3_input_bucket, infile))
    
        if download_succeeded:
            waveform_dict = make_waveform_json(infile, start_time, end_time)
            os.remove(infile)
            waveforms.append(waveform_dict)

    print("len(waveforms):", len(waveforms))
    
    if api_gateway:    
        return { 
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json'},
            'body': json.dumps(waveforms)
        }
    else:
        return waveforms


def handler(event, context):
    """ Lambda function handler.
    """
    return process(event)
