This tutorial creates an API from an AWS Lambda function that downloads a data file from the SCEDC Open Data Set,
decimates it, and stores the resulting file in an S3 bucket in your account. 

It is recommended that you run this in an AWS Cloud9 environment. You can run it locally if you have the awscli
and Docker. 

1. Log in to the AWS console.

2. Navigate to the S3 service.

3. Click on "Create bucket."

4. Create a bucket with the name `lambda-output-` followed by the last four digits of your account number. All S3 buckets must have a unique name. The rest of the settings don't need to be changed.

5. Navigate to the Cloud9 service. Make sure Oregon (us-west-2) is the region selected in the upper right corner.

6. Click "Create Environment."

7. Choose a name for your environment. Choose `t3.small` for the instance type should be sufficient. `t2.micro` does not work in the US-West-2 region.

8. Click "Create."

9. On the next screen, wait for the environment to finish being created.