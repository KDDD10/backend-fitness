import cloudinary
import cloudinary.api
import cloudinary.uploader
import environ

env = environ.Env()
environ.Env.read_env()

cloudinary.config(
    cloud_name=env("CLOUDINARY_CLOUD_NAME"),
    api_key=env("CLOUDINARY_API_KEY"),
    api_secret=env("CLOUDINARY_API_SECRET"),
)


def upload_file(file_path, folder="common", resource_type="auto"):
    """
    Upload a file to Cloudinary.

    Args:
        file_path (str): The path to the file to upload.
        folder (str): The Cloudinary folder where the file will be stored.
        resource_type (str): The type of file ('image', 'video', or 'auto').

    Returns:
        str: The URL of the uploaded file.
    """
    try:
        result = cloudinary.uploader.upload(
            file_path, folder=folder, resource_type=resource_type
        )
        print(f"File uploaded successfully: {result['secure_url']}")
        return result["secure_url"]
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise


# Example Usage
if __name__ == "__main__":
    file_path = "path/to/your/file.jpg"  # Replace with the path to your file
    upload_file(file_path)
