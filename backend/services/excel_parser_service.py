import json
import io
from typing import Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)

class ExcelParserService:
    """Service for parsing Excel/CSV files"""

    def __init__(self):
        try:
            import openpyxl
            import pandas as pd
            self.openpyxl = openpyxl
            self.pd = pd
            self.available = True
        except ImportError:
            logger.warning("openpyxl or pandas not installed. Excel parsing will be limited.")
            self.available = False

    def parse_excel(
        self,
        file_content: bytes,
        filename: str,
        max_rows_per_sheet: int = 10000
    ) -> Dict[str, Any]:
        """
        Parse Excel file and extract text content

        Args:
            file_content: File bytes
            filename: Original filename
            max_rows_per_sheet: Maximum rows to process per sheet

        Returns:
            Extracted data and metadata
        """
        if not self.available:
            raise RuntimeError("Excel parsing dependencies not installed (openpyxl, pandas)")

        try:
            file_extension = filename.lower().split('.')[-1]

            if file_extension in ['xlsx', 'xlsm']:
                return self._parse_xlsx(file_content, max_rows_per_sheet)
            elif file_extension == 'xls':
                return self._parse_xls(file_content, max_rows_per_sheet)
            elif file_extension == 'csv':
                return self._parse_csv(file_content, max_rows_per_sheet)
            else:
                raise ValueError(f"Unsupported Excel format: {file_extension}")

        except Exception as e:
            logger.error(f"Failed to parse Excel file: {str(e)}")
            raise

    def _parse_xlsx(self, file_content: bytes, max_rows: int) -> Dict[str, Any]:
        """Parse .xlsx files using openpyxl"""
        workbook = self.openpyxl.load_workbook(io.BytesIO(file_content), read_only=True)

        sheets_data = []
        full_text = []

        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            rows_data = []
            row_count = 0

            for row in sheet.iter_rows(values_only=True):
                if row_count >= max_rows:
                    logger.warning(f"Sheet '{sheet_name}' exceeded max rows ({max_rows}), truncating")
                    break

                # Convert row to strings and filter None values
                row_strings = [str(cell) if cell is not None else '' for cell in row]
                rows_data.append(row_strings)

                # Add to full text for indexing
                row_text = ' | '.join(row_strings)
                if row_text.strip():
                    full_text.append(row_text)

                row_count += 1

            sheets_data.append({
                'sheet_name': sheet_name,
                'row_count': row_count,
                'column_count': len(rows_data[0]) if rows_data else 0,
                'data_preview': rows_data[:10]  # First 10 rows for preview
            })

        workbook.close()

        return {
            'text': '\n'.join(full_text),
            'sheets': sheets_data,
            'sheet_count': len(sheets_data),
            'format': 'xlsx',
            'service': 'excel_parser'
        }

    def _parse_xls(self, file_content: bytes, max_rows: int) -> Dict[str, Any]:
        """Parse .xls files using pandas"""
        try:
            # Read all sheets
            excel_file = self.pd.read_excel(io.BytesIO(file_content), sheet_name=None, nrows=max_rows)

            sheets_data = []
            full_text = []

            for sheet_name, df in excel_file.items():
                # Convert DataFrame to text
                sheet_text = df.to_string(index=False, header=True)
                full_text.append(f"Sheet: {sheet_name}\n{sheet_text}")

                sheets_data.append({
                    'sheet_name': sheet_name,
                    'row_count': len(df),
                    'column_count': len(df.columns),
                    'columns': df.columns.tolist(),
                    'data_preview': df.head(10).to_dict('records')
                })

            return {
                'text': '\n\n'.join(full_text),
                'sheets': sheets_data,
                'sheet_count': len(sheets_data),
                'format': 'xls',
                'service': 'excel_parser'
            }

        except Exception as e:
            logger.error(f"Failed to parse .xls file: {str(e)}")
            raise

    def _parse_csv(self, file_content: bytes, max_rows: int) -> Dict[str, Any]:
        """Parse CSV files using pandas"""
        try:
            df = self.pd.read_csv(io.BytesIO(file_content), nrows=max_rows)

            # Convert to text
            csv_text = df.to_string(index=False, header=True)

            return {
                'text': csv_text,
                'sheets': [{
                    'sheet_name': 'CSV',
                    'row_count': len(df),
                    'column_count': len(df.columns),
                    'columns': df.columns.tolist(),
                    'data_preview': df.head(10).to_dict('records')
                }],
                'sheet_count': 1,
                'format': 'csv',
                'service': 'excel_parser'
            }

        except Exception as e:
            logger.error(f"Failed to parse CSV file: {str(e)}")
            raise

    def extract_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured metadata from parsed Excel data

        Args:
            parsed_data: Output from parse_excel

        Returns:
            Metadata dictionary
        """
        metadata = {
            'format': parsed_data.get('format'),
            'sheet_count': parsed_data.get('sheet_count', 0),
            'total_rows': sum(sheet.get('row_count', 0) for sheet in parsed_data.get('sheets', [])),
            'total_columns': sum(sheet.get('column_count', 0) for sheet in parsed_data.get('sheets', [])),
            'sheet_names': [sheet.get('sheet_name') for sheet in parsed_data.get('sheets', [])],
            'service': 'excel_parser'
        }

        return metadata

excel_parser_service = ExcelParserService()
