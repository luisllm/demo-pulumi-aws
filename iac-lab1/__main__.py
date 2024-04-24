"""A Python Pulumi program"""

import pulumi
import pulumi_aws as aws
import os 
import mimetypes

# Pulumi config variables so that they are not hardcoded in the code
# pulumi config set iac-lab1:siteDir <value>
config = pulumi.Config()
site_dir = config.require("siteDir")


# S3 bucket to be created
bucket = aws.s3.Bucket("my-bucket-llm",
  website={
    "index_document": "index.html"
  }
)

# Upload every file in 'site_dir' to the S3 bucket
for file in os.listdir(site_dir):
  # Folder and file of the index.html
  filepath = os.path.join(site_dir, file)

  # Get ytype of the index.htlm file
  mimetype, _ = mimetypes.guess_type(filepath) 

  # S3 object to upload
  obj = aws.s3.BucketObject(file, 
    bucket=bucket.bucket,
    source=pulumi.FileAsset(filepath),
    #acl="public-read",
    content_type=mimetype
  )

# Export the s3 bucket as a Pulumi output
pulumi.export('bucket_name', bucket.bucket)
pulumi.export('bucket_endpoint', pulumi.Output.concat("http://", bucket.website_endpoint))
