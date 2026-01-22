import boto3
import os
import uuid

AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

PROFILE_PICTURES_PREFIX = os.getenv(
    "AWS_S3_PROFILE_PICTURES_PREFIX", "profile-pictures"
)

RESUMES_PREFIX = os.getenv(
    "AWS_S3_RESUMES_PREFIX", "resumes"
)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)


def upload_profile_picture(file) -> str:
    ext = file.filename.split(".")[-1]
    key = f"{PROFILE_PICTURES_PREFIX}/{uuid.uuid4()}.{ext}"

    s3.upload_fileobj(
        file.file,
        AWS_S3_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type},
    )

    return key


def upload_resume(file) -> str:
    ext = file.filename.split(".")[-1]
    key = f"{RESUMES_PREFIX}/{uuid.uuid4()}.{ext}"

    s3.upload_fileobj(
        file.file,
        AWS_S3_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type},
    )

    return key

def delete_file(key: str):
    if not key:
        return

    s3.delete_object(
        Bucket=AWS_S3_BUCKET,
        Key=key
    )
