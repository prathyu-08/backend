import os
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# --------------------------------------------------
# AWS CONFIG
# --------------------------------------------------
AWS_REGION = os.getenv("AWS_REGION")
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# --------------------------------------------------
# AWS CLIENTS (THIS FIXES YOUR ERROR)
# --------------------------------------------------
ses = boto3.client(
    "ses",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# --------------------------------------------------
# SIMPLE EMAIL (NO ATTACHMENT)
# --------------------------------------------------
def send_email(to_email: str, subject: str, body: str):
    ses.send_email(
        Source=SES_SENDER_EMAIL,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}},
        },
    )

# --------------------------------------------------
# DOWNLOAD RESUME FROM S3
# --------------------------------------------------
def get_resume_bytes(s3_key: str) -> bytes:
    response = s3.get_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key
    )
    return response["Body"].read()

# --------------------------------------------------
# RAW EMAIL WITH ATTACHMENT (SES)
# --------------------------------------------------
def send_email_with_attachment(
    to_email: str,
    subject: str,
    body: str,
    file_bytes: bytes,
    filename: str,
):
    msg = MIMEMultipart()
    msg["From"] = SES_SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    # Email body
    msg.attach(MIMEText(body, "plain"))

    # Attachment
    attachment = MIMEApplication(file_bytes)
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=filename,
    )
    msg.attach(attachment)

    ses.send_raw_email(
        Source=SES_SENDER_EMAIL,
        Destinations=[to_email],
        RawMessage={"Data": msg.as_string()},
    )
