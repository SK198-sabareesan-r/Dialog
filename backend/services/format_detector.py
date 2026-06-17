import mimetypes
from typing import Dict, Tuple, Optional
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

class FormatDetector:
    """Detect and validate file formats"""

    # Supported formats mapped to processing strategies
    SUPPORTED_FORMATS = {
        # Documents
        'application/pdf': {'category': 'document', 'handler': 'bda', 'extensions': ['.pdf']},
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
            'category': 'document', 'handler': 'bda', 'extensions': ['.docx']
        },
        'application/msword': {'category': 'document', 'handler': 'bda', 'extensions': ['.doc']},
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': {
            'category': 'document', 'handler': 'bda', 'extensions': ['.pptx']
        },
        'application/vnd.ms-powerpoint': {'category': 'document', 'handler': 'bda', 'extensions': ['.ppt']},
        'text/plain': {'category': 'document', 'handler': 'bda', 'extensions': ['.txt']},
        'text/html': {'category': 'document', 'handler': 'bda', 'extensions': ['.html', '.htm']},

        # Images
        'image/jpeg': {'category': 'image', 'handler': 'textract', 'extensions': ['.jpg', '.jpeg']},
        'image/png': {'category': 'image', 'handler': 'textract', 'extensions': ['.png']},
        'image/tiff': {'category': 'image', 'handler': 'textract', 'extensions': ['.tiff', '.tif']},
        'image/bmp': {'category': 'image', 'handler': 'textract', 'extensions': ['.bmp']},

        # Videos
        'video/mp4': {'category': 'video', 'handler': 'transcribe', 'extensions': ['.mp4']},
        'video/x-msvideo': {'category': 'video', 'handler': 'transcribe', 'extensions': ['.avi']},
        'video/quicktime': {'category': 'video', 'handler': 'transcribe', 'extensions': ['.mov']},
        'video/x-matroska': {'category': 'video', 'handler': 'transcribe', 'extensions': ['.mkv']},

        # Audio
        'audio/mpeg': {'category': 'audio', 'handler': 'transcribe', 'extensions': ['.mp3']},
        'audio/wav': {'category': 'audio', 'handler': 'transcribe', 'extensions': ['.wav']},
        'audio/x-m4a': {'category': 'audio', 'handler': 'transcribe', 'extensions': ['.m4a']},

        # Spreadsheets
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
            'category': 'spreadsheet', 'handler': 'excel_parser', 'extensions': ['.xlsx']
        },
        'application/vnd.ms-excel': {'category': 'spreadsheet', 'handler': 'excel_parser', 'extensions': ['.xls']},
        'text/csv': {'category': 'spreadsheet', 'handler': 'excel_parser', 'extensions': ['.csv']},
    }

    def __init__(self):
        mimetypes.init()

    def detect_format(self, filename: str, content_type: Optional[str] = None) -> Dict[str, str]:
        """
        Detect file format from filename and content type

        Args:
            filename: Name of the file
            content_type: MIME type (optional)

        Returns:
            Dict with format information including handler strategy

        Raises:
            ValueError: If format is not supported
        """
        file_ext = Path(filename).suffix.lower()

        # Try content_type first
        if content_type and content_type in self.SUPPORTED_FORMATS:
            format_info = self.SUPPORTED_FORMATS[content_type]
            logger.info(f"Detected format from content_type: {content_type}")
            return {
                'mime_type': content_type,
                'extension': file_ext,
                'category': format_info['category'],
                'handler': format_info['handler']
            }

        # Fall back to extension-based detection
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type and guessed_type in self.SUPPORTED_FORMATS:
            format_info = self.SUPPORTED_FORMATS[guessed_type]
            logger.info(f"Detected format from extension: {guessed_type}")
            return {
                'mime_type': guessed_type,
                'extension': file_ext,
                'category': format_info['category'],
                'handler': format_info['handler']
            }

        # Check extension directly
        for mime_type, format_info in self.SUPPORTED_FORMATS.items():
            if file_ext in format_info['extensions']:
                logger.info(f"Detected format from extension mapping: {mime_type}")
                return {
                    'mime_type': mime_type,
                    'extension': file_ext,
                    'category': format_info['category'],
                    'handler': format_info['handler']
                }

        raise ValueError(
            f"Unsupported file format: {filename} (content_type: {content_type}). "
            f"Supported formats: {', '.join(self.get_supported_extensions())}"
        )

    def validate_format(self, filename: str, content_type: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate if file format is supported

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            format_info = self.detect_format(filename, content_type)
            return True, f"Valid format: {format_info['category']} ({format_info['mime_type']})"
        except ValueError as e:
            return False, str(e)

    def get_supported_extensions(self) -> list:
        """Get list of all supported file extensions"""
        extensions = set()
        for format_info in self.SUPPORTED_FORMATS.values():
            extensions.update(format_info['extensions'])
        return sorted(list(extensions))

    def get_handler_for_file(self, filename: str, content_type: Optional[str] = None) -> str:
        """Get the appropriate handler for a file"""
        format_info = self.detect_format(filename, content_type)
        return format_info['handler']

format_detector = FormatDetector()
