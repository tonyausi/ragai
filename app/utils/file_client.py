import os
import logging
from datetime import datetime
from app.config.setting import settings

logger = logging.getLogger(__name__)


# obtain the processed file directory if it does not exist
def get_processed_file_directory(dir_name: str = settings.PROCESSED_FILE_DIR) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.abspath(os.path.join(current_dir, "../.."))
    processed_file_dir = os.path.join(app_dir, dir_name)
    # Create a directory for the current date if it doesn't exist
    current_date = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join(processed_file_dir, current_date)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create directory {output_dir}: {e}")
        raise OSError(f"Failed to create directory: {e}")
    return output_dir
