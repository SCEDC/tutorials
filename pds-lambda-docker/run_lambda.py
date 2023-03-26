"""
run_lambda.py runs the lambda function on one seismogram.
"""

import boto3
import json

# Replace with your own Lambda function.
LAMBDA_FUNCTION = 'decimation-lambda'

session = boto3.Session()
client = session.client('lambda', region_name='us-west-2')

event = {
  "s3_input_bucket": "scedc-pds",
  's3_output_bucket': "lambda-output-3909", # Replace with your own bucket.
  "s3_key": "continuous_waveforms/2016/2016_123/CIWCS2_BHE___2016123.ms", # Replace with other keys.
  "decimation_factor": 4
}

print('Invoking lambda function')
response = client.invoke(
        FunctionName=LAMBDA_FUNCTION,
        InvocationType='Event',
        LogType='Tail',
        Payload=json.dumps(event))
print(response)
