import os
import boto3

def upload_files_to_s3(static_folder_path, bucket_name):
    s3 = boto3.client('s3')
    # Walk through the folder
    for subdir, dirs, files in os.walk(static_folder_path):
        for file in files:
            full_path = os.path.join(subdir, file)
            with open(full_path, 'rb') as data:
                # The S3 Key will be the same as the file path relative to the static folder
                s3_key = os.path.relpath(full_path, start=static_folder_path)
                try:
                    s3.upload_fileobj(
                        data,
                        bucket_name,
                        s3_key,
                        ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/jpeg'}  # Modify ContentType as needed
                    )
                    print(f'Successfully uploaded {s3_key} to {bucket_name}')
                except Exception as e:
                    print(f'Failed to upload {s3_key} to {bucket_name}. Error: {e}')

# Set your static folder path and bucket name
static_folder_path = 'static/images/posts'  # Updated to point to the images folder
bucket_name = 'netwrkproto'  # Assuming this is your bucket name

# Call the function to upload all files
upload_files_to_s3(static_folder_path, bucket_name)
