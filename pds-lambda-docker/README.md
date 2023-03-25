# Creating a Lambda Function and API to Process Open Data Set Files

This tutorial will show you how to use Docker to create a Lambda function that uses ObsPy to decimate a data file
from the the SCEDC Open Data Set and stores the resulting file an S3 bucket in your account. 

You will be using a Cloud9 environment to create and upload a Docker image to ECR that contains processing code and ObsPy. You will then create a Lambda function using the Docker image 

The code for the Lambda function is in [`app.py`](app.py). You can modify it to do different types of processing.

## Setting up S3 and Cloud9

1. Log in to the AWS console.

2. Navigate to the S3 service.

3. Click on "Create bucket."

4. Create a bucket with the name `lambda-output-` followed by the last four digits of your account number. All S3 buckets must have a unique name. The rest of the settings don't need to be changed.

5. Navigate to the Cloud9 service. Make sure Oregon (us-west-2) is the region selected in the upper right corner.

6. Click "Create Environment."

7. Choose a name for your environment. Choose `t3.small` for the instance type should be sufficient. `t2.micro` does not work in the US-West-2 region.

8. Click "Create."

9. On the next screen, wait for the environment to finish being created.

10. Click "Open" to open the Cloud9 IDE. In the IDE, the terminal is at the bottom of the workspace. The file explorer is on the right.

## Creating a Docker Image

1. In Cloud9, click the button in left sidebar above the "aws" logo. Click "Clone Repository."
Paste https://github.com/SCEDC/tutorials.git into the "Repository URL" field and hit Enter.

2. Click on the folder icon in the sidebar to navigate the filesystem.  You can open files in the IDE by double clicking them. The files for this tutorial are in `tutorials/pds-lambda-docker`.

3. In the terminal, navigate to tutorials/pds-lambda-docker.

    `cd tutorials/pds-lambda-docker`

4. Choose a name for your Docker image, like decimation-lambda, or my_docker_image, and run the command below to build the image using the provided Dockerfile.
  
    `docker build -t decimation-lambda .`

    This Dockerfile builds a Docker image based on AWS's lambda/python:3.8 base image that has ObsPy installed. ObsPy and its dependencies are listed in `requirements.txt`. The Dockerfile also tells Docker to make a copy of `app.py` in the image and to run the function `app.handler` as the entrypoint for the Lambda function. 
 
## Uploading the Image to ECR
  
