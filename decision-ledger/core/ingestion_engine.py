"""Clean data ingestion module - reads file exactly once."""

import pandas as pd
import json
from io import BytesIO
from pathlib import Path
from typing import Dict, Any
from fastapi import UploadFile

from .dataset_registry import DatasetRegistry


class DataIngestionEngine:
    """Clean ingestion engine that reads files exactly once."""
    
    SUPPORTED_FORMATS = {'.csv', '.xlsx', '.xls', '.json'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    async def ingest_upload(self, file: UploadFile, dataset_id: str) -> DatasetRegistry:
        """Ingest file from FastAPI UploadFile.
        
        This method reads the file EXACTLY ONCE and converts to BytesIO immediately.
        
        Args:
            file: FastAPI UploadFile object
            dataset_id: Unique identifier for this dataset
            
        Returns:
            DatasetRegistry object with parsed data
            
        Raises:
            ValueError: If file format not supported or file too large
        """
        # Validate extension before reading
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {file_ext}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        # READ FILE EXACTLY ONCE
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        # Validate size
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size / 1024 / 1024:.2f}MB "
                f"(max {self.MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )
        
        # Convert to BytesIO immediately - no additional reads
        bytes_io = BytesIO(file_bytes)
        
        # Parse based on format
        source_type = self._get_source_type(file_ext)
        
        if source_type == 'csv':
            datasets, metadata = self._parse_csv(bytes_io, file.filename, file_size)
        elif source_type == 'xlsx':
            datasets, metadata = self._parse_xlsx(bytes_io, file.filename, file_size)
        elif source_type == 'json':
            datasets, metadata = self._parse_json(bytes_io, file.filename, file_size)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        return DatasetRegistry(
            dataset_id=dataset_id,
            source_type=source_type,
            datasets=datasets,
            metadata=metadata
        )
    
    def _get_source_type(self, file_ext: str) -> str:
        """Map file extension to source type.
        
        Args:
            file_ext: File extension (e.g., '.csv')
            
        Returns:
            Source type: 'csv', 'xlsx', or 'json'
        """
        if file_ext == '.csv':
            return 'csv'
        elif file_ext in {'.xlsx', '.xls'}:
            return 'xlsx'
        elif file_ext == '.json':
            return 'json'
        else:
            raise ValueError(f"Unsupported extension: {file_ext}")
    
    def _parse_csv(
        self, 
        bytes_io: BytesIO, 
        filename: str, 
        file_size: int
    ) -> tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        """Parse CSV from BytesIO.
        
        Args:
            bytes_io: BytesIO containing file data
            filename: Original filename
            file_size: File size in bytes
            
        Returns:
            Tuple of (datasets dict, metadata dict)
        """
        try:
            bytes_io.seek(0)
            df = pd.read_csv(bytes_io)
        except UnicodeDecodeError:
            bytes_io.seek(0)
            df = pd.read_csv(bytes_io, encoding='latin-1')
        except Exception as e:
            # Try semicolon separator
            try:
                bytes_io.seek(0)
                df = pd.read_csv(bytes_io, sep=';')
            except:
                raise ValueError(f"Failed to parse CSV: {str(e)}")
        
        datasets = {'data': df}
        metadata = {
            'filename': filename,
            'file_size_bytes': file_size,
            'total_sheets': 1,
            'sheet_names': ['data'],
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': df.columns.tolist()
        }
        
        return datasets, metadata
    
    def _parse_xlsx(
        self, 
        bytes_io: BytesIO, 
        filename: str, 
        file_size: int
    ) -> tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        """Parse XLSX/XLS from BytesIO with multi-sheet support.
        
        Args:
            bytes_io: BytesIO containing file data
            filename: Original filename
            file_size: File size in bytes
            
        Returns:
            Tuple of (datasets dict, metadata dict)
        """
        try:
            bytes_io.seek(0)
            excel_file = pd.ExcelFile(bytes_io)
            sheet_names = excel_file.sheet_names
            
            datasets = {}
            total_rows = 0
            total_columns = 0
            sheet_info = []
            
            for sheet_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                datasets[sheet_name] = df
                total_rows += len(df)
                total_columns = max(total_columns, len(df.columns))
                
                sheet_info.append({
                    'name': sheet_name,
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': df.columns.tolist()
                })
            
            metadata = {
                'filename': filename,
                'file_size_bytes': file_size,
                'total_sheets': len(sheet_names),
                'sheet_names': sheet_names,
                'total_rows': total_rows,
                'total_columns': total_columns,
                'sheet_info': sheet_info
            }
            
            return datasets, metadata
            
        except Exception as e:
            raise ValueError(f"Failed to parse XLSX: {str(e)}")
    
    def _parse_json(
        self, 
        bytes_io: BytesIO, 
        filename: str, 
        file_size: int
    ) -> tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        """Parse JSON from BytesIO and flatten to DataFrame.
        
        Args:
            bytes_io: BytesIO containing file data
            filename: Original filename
            file_size: File size in bytes
            
        Returns:
            Tuple of (datasets dict, metadata dict)
        """
        try:
            bytes_io.seek(0)
            data = json.load(bytes_io)
            
            # Flatten JSON to DataFrame
            df = self._flatten_json(data)
            
            datasets = {'data': df}
            metadata = {
                'filename': filename,
                'file_size_bytes': file_size,
                'total_sheets': 1,
                'sheet_names': ['data'],
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'columns': df.columns.tolist(),
                'json_structure': self._analyze_json_structure(data)
            }
            
            return datasets, metadata
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse JSON: {str(e)}")
    
    def _flatten_json(self, data: Any) -> pd.DataFrame:
        """Flatten nested JSON to DataFrame.
        
        Args:
            data: JSON data (dict, list, or primitive)
            
        Returns:
            Flattened DataFrame
        """
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                # Array of objects - use json_normalize
                return pd.json_normalize(data, sep='_')
            else:
                # Simple array
                return pd.DataFrame({'value': data})
        
        elif isinstance(data, dict):
            # Check if simple key-value dict
            if all(not isinstance(v, (dict, list)) for v in data.values()):
                return pd.DataFrame([data])
            
            # Look for array of objects in nested dict
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    df = pd.json_normalize(value, sep='_')
                    # Add other top-level keys as columns
                    for k, v in data.items():
                        if k != key and not isinstance(v, (dict, list)):
                            df[k] = v
                    return df
            
            # Flatten nested dict
            return pd.json_normalize(data, sep='_')
        
        else:
            # Primitive value
            return pd.DataFrame({'value': [data]})
    
    def _analyze_json_structure(self, data: Any) -> str:
        """Analyze JSON structure type.
        
        Args:
            data: JSON data
            
        Returns:
            Structure description
        """
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                return f"array_of_objects (length: {len(data)})"
            else:
                return f"array_of_primitives (length: {len(data)})"
        elif isinstance(data, dict):
            nested = sum(1 for v in data.values() if isinstance(v, (dict, list)))
            return f"object (keys: {len(data)}, nested: {nested})"
        else:
            return "primitive"
