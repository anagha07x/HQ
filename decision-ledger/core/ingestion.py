"""Data ingestion module for multiple file formats."""

import pandas as pd
from typing import Optional, Dict, Any, List, Tuple, Union, BinaryIO
import os
import json
from pathlib import Path
from io import BytesIO


class DataIngestion:
    """Universal data loader for CSV, XLSX, and JSON files."""
    
    SUPPORTED_FORMATS = ['.csv', '.xlsx', '.xls', '.json']
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    def __init__(self):
        """Initialize data ingestion."""
        pass
    
    def detect_file_type(self, filename: str) -> str:
        """Detect file type from extension.
        
        Args:
            filename: Filename or path
            
        Returns:
            File type: 'csv', 'xlsx', or 'json'
        """
        ext = Path(filename).suffix.lower()
        
        if ext == '.csv':
            return 'csv'
        elif ext in ['.xlsx', '.xls']:
            return 'xlsx'
        elif ext == '.json':
            return 'json'
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    async def ingest_from_bytes(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Universal file ingestion from bytes - returns standardized metadata + DataFrames.
        
        Args:
            file_bytes: File content as bytes
            filename: Original filename (for type detection)
            
        Returns:
            Dict with:
                - file_type: 'csv' | 'xlsx' | 'json'
                - sheets: List of sheet names (for XLSX) or ['data'] for others
                - dataframes: Dict[sheet_name, DataFrame]
                - metadata: Standardized file metadata
        """
        # Validate file size
        file_size = len(file_bytes)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size / 1024 / 1024:.2f}MB (max 50MB)")
        
        file_type = self.detect_file_type(filename)
        
        # Create BytesIO wrapper (read once pattern)
        bytes_io = BytesIO(file_bytes)
        
        if file_type == 'csv':
            return await self._ingest_csv_from_bytes(bytes_io, file_size)
        elif file_type == 'xlsx':
            return await self._ingest_xlsx_from_bytes(bytes_io, file_size)
        elif file_type == 'json':
            return await self._ingest_json_from_bytes(bytes_io, file_size)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    async def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """Universal file ingestion from path (legacy method for analysis endpoints).
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict with standardized metadata + DataFrames
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file once into memory
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        filename = os.path.basename(file_path)
        return await self.ingest_from_bytes(file_bytes, filename)
    
    async def ingest_csv(self, file_path: str) -> pd.DataFrame:
        """Legacy method - loads CSV as single DataFrame from path.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame
        """
        result = await self.ingest_file(file_path)
        return result['dataframes']['data']
    
    async def _ingest_csv_from_bytes(self, bytes_io: BytesIO, file_size: int) -> Dict[str, Any]:
        """Ingest CSV from BytesIO.
        
        Args:
            bytes_io: BytesIO wrapper
            file_size: Original file size
            
        Returns:
            Standardized result dict
        """
        try:
            # Try with default encoding
            bytes_io.seek(0)
            df = pd.read_csv(bytes_io)
        except UnicodeDecodeError:
            # Fallback to latin-1
            bytes_io.seek(0)
            df = pd.read_csv(bytes_io, encoding='latin-1')
        except Exception as e:
            # Try with different separators
            try:
                bytes_io.seek(0)
                df = pd.read_csv(bytes_io, sep=';')
            except:
                raise ValueError(f"Failed to parse CSV: {str(e)}")
        
        return {
            'file_type': 'csv',
            'sheets': ['data'],
            'dataframes': {'data': df},
            'metadata': {
                'total_sheets': 1,
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'file_size_bytes': file_size
            }
        }
    
    async def _ingest_xlsx_from_bytes(self, bytes_io: BytesIO, file_size: int) -> Dict[str, Any]:
        """Ingest XLSX from BytesIO with all sheets.
        
        Args:
            bytes_io: BytesIO wrapper
            file_size: Original file size
            
        Returns:
            Standardized result dict with all sheets
        """
        try:
            # Load all sheets from BytesIO
            bytes_io.seek(0)
            excel_file = pd.ExcelFile(bytes_io)
            sheet_names = excel_file.sheet_names
            
            dataframes = {}
            total_rows = 0
            total_columns = 0
            
            for sheet_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                dataframes[sheet_name] = df
                total_rows += len(df)
                total_columns = max(total_columns, len(df.columns))
            
            return {
                'file_type': 'xlsx',
                'sheets': sheet_names,
                'dataframes': dataframes,
                'metadata': {
                    'total_sheets': len(sheet_names),
                    'total_rows': total_rows,
                    'total_columns': total_columns,
                    'file_size_bytes': file_size,
                    'sheet_info': [
                        {
                            'name': name,
                            'rows': len(dataframes[name]),
                            'columns': len(dataframes[name].columns)
                        }
                        for name in sheet_names
                    ]
                }
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse XLSX: {str(e)}")
    
    async def _ingest_json_from_bytes(self, bytes_io: BytesIO, file_size: int) -> Dict[str, Any]:
        """Ingest JSON from BytesIO and flatten nested structures.
        
        Args:
            bytes_io: BytesIO wrapper
            file_size: Original file size
            
        Returns:
            Standardized result dict
        """
        try:
            bytes_io.seek(0)
            data = json.load(bytes_io)
            
            # Flatten and convert to DataFrame
            df = self._flatten_json_to_dataframe(data)
            
            return {
                'file_type': 'json',
                'sheets': ['data'],
                'dataframes': {'data': df},
                'metadata': {
                    'total_sheets': 1,
                    'total_rows': len(df),
                    'total_columns': len(df.columns),
                    'file_size_bytes': file_size,
                    'json_structure': self._analyze_json_structure(data)
                }
            }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse JSON: {str(e)}")
    
    def _flatten_json_to_dataframe(self, data: Any) -> pd.DataFrame:
        """Flatten nested JSON into DataFrame.
        
        Args:
            data: JSON data (dict, list, or primitive)
            
        Returns:
            Flattened DataFrame
        """
        if isinstance(data, list):
            # Array of objects
            if data and isinstance(data[0], dict):
                # Normalize with json_normalize
                return pd.json_normalize(data, sep='_')
            else:
                # Simple array
                return pd.DataFrame({'value': data})
        
        elif isinstance(data, dict):
            # Check if it's a simple key-value dict
            if all(not isinstance(v, (dict, list)) for v in data.values()):
                # Simple flat dict - convert to single row
                return pd.DataFrame([data])
            else:
                # Nested dict - try to find the main data array
                for key, value in data.items():
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        # Found array of objects
                        df = pd.json_normalize(value, sep='_')
                        # Add other top-level keys as columns
                        for k, v in data.items():
                            if k != key and not isinstance(v, (dict, list)):
                                df[k] = v
                        return df
                
                # No array found - flatten the dict
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
            nested_count = sum(1 for v in data.values() if isinstance(v, (dict, list)))
            return f"object (keys: {len(data)}, nested: {nested_count})"
        else:
            return "primitive"
    
    def validate_file_extension(self, filename: str) -> bool:
        """Validate file extension.
        
        Args:
            filename: Filename
            
        Returns:
            True if valid
        """
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_FORMATS
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract file metadata.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict containing metadata
        """
        return {
            "filename": os.path.basename(file_path),
            "size_bytes": os.path.getsize(file_path),
            "path": file_path,
            "extension": Path(file_path).suffix.lower()
        }
