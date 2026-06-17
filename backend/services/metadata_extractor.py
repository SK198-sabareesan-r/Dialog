"""
Automatic Metadata Extraction Service

Extracts metadata from various file types:
- PDF: Author, title, keywords, creation date
- DOCX: Author, title, company, creation date
- Images: EXIF data (camera, location, timestamp)
- Videos: Duration, resolution, codec (basic info)
- Audio: Duration, bitrate, tags
"""

import io
import json
from typing import Dict, Any, Optional
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class MetadataExtractor:
    """Extract metadata from uploaded files"""

    def __init__(self):
        self.supported_extractors = {
            'application/pdf': self._extract_pdf_metadata,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._extract_docx_metadata,
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': self._extract_pptx_metadata,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': self._extract_xlsx_metadata,
            'image/jpeg': self._extract_image_metadata,
            'image/jpg': self._extract_image_metadata,
            'image/png': self._extract_image_metadata,
            # Video — all variants route to the same extractor
            'video/mp4':        self._extract_video_metadata,
            'video/x-msvideo':  self._extract_video_metadata,  # AVI
            'video/quicktime':  self._extract_video_metadata,  # MOV
            'video/x-matroska': self._extract_video_metadata,  # MKV
            'video/webm':       self._extract_video_metadata,
            # Audio
            'audio/mpeg': self._extract_audio_metadata,
            'audio/wav':  self._extract_audio_metadata,
        }

    def extract_metadata(
        self,
        file_content: bytes,
        filename: str,
        content_type: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from file

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'extraction_timestamp': datetime.utcnow().isoformat(),
            'filename': filename,
            'content_type': content_type,
            'file_size': len(file_content)
        }

        # Get file extension
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        metadata['file_extension'] = file_ext

        # Try to extract format-specific metadata
        extractor = self.supported_extractors.get(content_type)

        if extractor:
            try:
                logger.info(f"Extracting metadata for {content_type}: {filename}")
                specific_metadata = extractor(file_content, filename)
                metadata.update(specific_metadata)
                logger.info(f"Successfully extracted metadata: {json.dumps(specific_metadata, indent=2)}")
            except Exception as e:
                logger.warning(f"Failed to extract {content_type} metadata: {str(e)}")
                metadata['extraction_error'] = str(e)
        else:
            logger.info(f"No specific extractor for {content_type}, using basic metadata only")
            metadata['extraction_note'] = 'No specific extractor available'

        return metadata

    def _extract_pdf_metadata(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract metadata from PDF files"""
        try:
            import PyPDF2

            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            info = pdf_reader.metadata

            metadata = {
                'document_type': 'pdf',
                'page_count': len(pdf_reader.pages)
            }

            if info:
                # Extract standard PDF metadata
                if info.get('/Author'):
                    metadata['author'] = str(info.get('/Author'))
                if info.get('/Title'):
                    metadata['title'] = str(info.get('/Title'))
                if info.get('/Subject'):
                    metadata['subject'] = str(info.get('/Subject'))
                if info.get('/Keywords'):
                    metadata['keywords'] = str(info.get('/Keywords'))
                if info.get('/Creator'):
                    metadata['creator'] = str(info.get('/Creator'))
                if info.get('/Producer'):
                    metadata['producer'] = str(info.get('/Producer'))
                if info.get('/CreationDate'):
                    metadata['creation_date'] = str(info.get('/CreationDate'))
                if info.get('/ModDate'):
                    metadata['modification_date'] = str(info.get('/ModDate'))

            return metadata

        except ImportError:
            logger.warning("PyPDF2 not installed, skipping PDF metadata extraction")
            return {'document_type': 'pdf', 'extraction_note': 'PyPDF2 not available'}
        except Exception as e:
            logger.error(f"PDF metadata extraction failed: {str(e)}")
            return {'document_type': 'pdf', 'extraction_error': str(e)}

    def _extract_docx_metadata(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract metadata from DOCX files"""
        try:
            from docx import Document

            doc = Document(io.BytesIO(file_content))
            core_props = doc.core_properties

            metadata = {
                'document_type': 'docx',
                'paragraph_count': len(doc.paragraphs)
            }

            # Extract core properties
            if core_props.author:
                metadata['author'] = core_props.author
            if core_props.title:
                metadata['title'] = core_props.title
            if core_props.subject:
                metadata['subject'] = core_props.subject
            if core_props.keywords:
                metadata['keywords'] = core_props.keywords
            if core_props.comments:
                metadata['comments'] = core_props.comments
            if core_props.category:
                metadata['category'] = core_props.category
            if core_props.created:
                metadata['creation_date'] = core_props.created.isoformat()
            if core_props.modified:
                metadata['modification_date'] = core_props.modified.isoformat()
            if core_props.last_modified_by:
                metadata['last_modified_by'] = core_props.last_modified_by

            # Additional properties
            if hasattr(core_props, 'content_status'):
                metadata['content_status'] = core_props.content_status
            if hasattr(core_props, 'identifier'):
                metadata['identifier'] = core_props.identifier
            if hasattr(core_props, 'language'):
                metadata['language'] = core_props.language
            if hasattr(core_props, 'version'):
                metadata['version'] = str(core_props.version)

            return metadata

        except ImportError:
            logger.warning("python-docx not installed, skipping DOCX metadata extraction")
            return {'document_type': 'docx', 'extraction_note': 'python-docx not available'}
        except Exception as e:
            logger.error(f"DOCX metadata extraction failed: {str(e)}")
            return {'document_type': 'docx', 'extraction_error': str(e)}

    def _extract_pptx_metadata(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract metadata from PPTX files"""
        try:
            from pptx import Presentation

            prs = Presentation(io.BytesIO(file_content))
            core_props = prs.core_properties

            metadata = {
                'document_type': 'pptx',
                'slide_count': len(prs.slides)
            }

            # Extract core properties
            if core_props.author:
                metadata['author'] = core_props.author
            if core_props.title:
                metadata['title'] = core_props.title
            if core_props.subject:
                metadata['subject'] = core_props.subject
            if core_props.keywords:
                metadata['keywords'] = core_props.keywords
            if core_props.comments:
                metadata['comments'] = core_props.comments
            if core_props.category:
                metadata['category'] = core_props.category
            if core_props.created:
                metadata['creation_date'] = core_props.created.isoformat()
            if core_props.modified:
                metadata['modification_date'] = core_props.modified.isoformat()

            return metadata

        except ImportError:
            logger.warning("python-pptx not installed, skipping PPTX metadata extraction")
            return {'document_type': 'pptx', 'extraction_note': 'python-pptx not available'}
        except Exception as e:
            logger.error(f"PPTX metadata extraction failed: {str(e)}")
            return {'document_type': 'pptx', 'extraction_error': str(e)}

    def _extract_xlsx_metadata(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract metadata from Excel files"""
        try:
            import openpyxl

            workbook = openpyxl.load_workbook(io.BytesIO(file_content))
            props = workbook.properties

            metadata = {
                'document_type': 'xlsx',
                'sheet_count': len(workbook.sheetnames),
                'sheet_names': workbook.sheetnames
            }

            # Extract properties
            if props.creator:
                metadata['author'] = props.creator
            if props.title:
                metadata['title'] = props.title
            if props.subject:
                metadata['subject'] = props.subject
            if props.keywords:
                metadata['keywords'] = props.keywords
            if props.description:
                metadata['description'] = props.description
            if props.category:
                metadata['category'] = props.category
            if props.created:
                metadata['creation_date'] = props.created.isoformat()
            if props.modified:
                metadata['modification_date'] = props.modified.isoformat()
            if props.lastModifiedBy:
                metadata['last_modified_by'] = props.lastModifiedBy

            return metadata

        except ImportError:
            logger.warning("openpyxl not installed, skipping Excel metadata extraction")
            return {'document_type': 'xlsx', 'extraction_note': 'openpyxl not available'}
        except Exception as e:
            logger.error(f"Excel metadata extraction failed: {str(e)}")
            return {'document_type': 'xlsx', 'extraction_error': str(e)}

    def _extract_image_metadata(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract metadata from image files (EXIF data)"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            img = Image.open(io.BytesIO(file_content))

            metadata = {
                'document_type': 'image',
                'format': img.format,
                'mode': img.mode,
                'width': img.width,
                'height': img.height,
                'dimensions': f"{img.width}x{img.height}"
            }

            # Extract EXIF data
            exif_data = img._getexif() if hasattr(img, '_getexif') else None

            if exif_data:
                exif_metadata = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    try:
                        # Convert to string to avoid serialization issues
                        exif_metadata[str(tag)] = str(value)
                    except:
                        pass

                # Extract commonly used fields
                if 'DateTime' in exif_metadata:
                    metadata['capture_date'] = exif_metadata['DateTime']
                if 'Make' in exif_metadata:
                    metadata['camera_make'] = exif_metadata['Make']
                if 'Model' in exif_metadata:
                    metadata['camera_model'] = exif_metadata['Model']
                if 'Software' in exif_metadata:
                    metadata['software'] = exif_metadata['Software']
                if 'Artist' in exif_metadata:
                    metadata['artist'] = exif_metadata['Artist']
                if 'Copyright' in exif_metadata:
                    metadata['copyright'] = exif_metadata['Copyright']

                # GPS data
                if 'GPSInfo' in exif_metadata:
                    metadata['has_gps_data'] = 'true'

                metadata['exif_tags_count'] = len(exif_metadata)

            return metadata

        except ImportError:
            logger.warning("Pillow not installed, skipping image metadata extraction")
            return {'document_type': 'image', 'extraction_note': 'Pillow not available'}
        except Exception as e:
            logger.error(f"Image metadata extraction failed: {str(e)}")
            return {'document_type': 'image', 'extraction_error': str(e)}

    def _extract_video_metadata(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract basic video metadata.

        Full transcription is handled asynchronously by Bedrock Data Automation (BDA)
        after the file lands in S3 and the KB incremental sync triggers.
        """
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'unknown'
        metadata = {
            'document_type': 'video',
            'video_format': file_ext,
            'processor': 'bda',
            'processing_note': 'Stored to S3. BDA will extract audio transcript and index into KB.',
        }

        try:
            # Optional: Use moviepy for detailed metadata if ffmpeg is available.
            # Uncomment the lines below if moviepy + ffmpeg are installed:
            # import tempfile, os
            # from moviepy.editor import VideoFileClip
            # with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False) as tmp:
            #     tmp.write(file_content)
            #     tmp_path = tmp.name
            # try:
            #     clip = VideoFileClip(tmp_path)
            #     metadata['duration_seconds'] = round(clip.duration, 2)
            #     metadata['fps'] = clip.fps
            #     metadata['resolution'] = f"{clip.w}x{clip.h}"
            #     clip.close()
            # finally:
            #     os.unlink(tmp_path)
            pass
        except Exception:
            pass

        return metadata

    def _extract_audio_metadata(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract audio metadata (MP3 tags, etc.)"""
        metadata = {
            'document_type': 'audio',
            'extraction_note': 'Audio transcription handled by Bedrock KB BDA'
        }

        try:
            # Optional: Use mutagen for MP3 tags
            # from mutagen.mp3 import MP3
            # audio = MP3(io.BytesIO(file_content))
            # metadata['duration'] = audio.info.length
            # metadata['bitrate'] = audio.info.bitrate
            # if audio.tags:
            #     metadata['title'] = audio.tags.get('TIT2', '')
            #     metadata['artist'] = audio.tags.get('TPE1', '')
            #     metadata['album'] = audio.tags.get('TALB', '')
            pass
        except:
            pass

        return metadata

# Singleton instance
metadata_extractor = MetadataExtractor()
