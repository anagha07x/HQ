"""Data ingestion module for multiple file formats."""

import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
import os
import json
from pathlib import Path


class DataIngestion:
    """Universal data loader for CSV, XLSX, and JSON files."""
    
    SUPPORTED_FORMATS = ['.csv', '.xlsx', '.xls', '.json']
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    def __init__(self):
        """Initialize data ingestion."""
        pass
    
    def detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            File type: 'csv', 'xlsx', or 'json'
        """
        ext = Path(file_path).suffix.lower()
        
        if ext == '.csv':
            return 'csv'
        elif ext in ['.xlsx', '.xls']:
            return 'xlsx'
        elif ext == '.json':
            return 'json'
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    async def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """Universal file ingestion - returns standardized metadata + DataFrames.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict with:
                - file_type: 'csv' | 'xlsx' | 'json'
                - sheets: List of sheet names (for XLSX) or ['data'] for others
                - dataframes: Dict[sheet_name, DataFrame]
                - metadata: Standardized file metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Validate file size
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size / 1024 / 1024:.2f}MB (max 50MB)")
        
        file_type = self.detect_file_type(file_path)
        
        if file_type == 'csv':
            return await self._ingest_csv(file_path)
        elif file_type == 'xlsx':
            return await self._ingest_xlsx(file_path)
        elif file_type == 'json':
            return await self._ingest_json(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    async def ingest_csv(self, file_path: str) -> pd.DataFrame:
        """Legacy method - loads CSV as single DataFrame.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame
        """
        result = await self._ingest_csv(file_path)
        return result['dataframes']['data']
    
    async def _ingest_csv(self, file_path: str) -> Dict[str, Any]:
        """Ingest CSV file.
        
        Args:
            file_path: Path to CSV
            
        Returns:
            Standardized result dict
        """
        try:
            # Try with default encoding
            df = pd.read_csv(file_path)
        except UnicodeDecodeError:
            # Fallback to latin-1
            df = pd.read_csv(file_path, encoding='latin-1')
        except Exception as e:
            # Try with different separators
            try:
                df = pd.read_csv(file_path, sep=';')
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
                'file_size_bytes': os.path.getsize(file_path)
            }
        }
    
    async def _ingest_xlsx(self, file_path: str) -> Dict[str, Any]:
        """Ingest XLSX file with all sheets.
        
        Args:
            file_path: Path to XLSX
            
        Returns:
            Standardized result dict with all sheets
        """
        try:
            # Load all sheets
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            dataframes = {}
            total_rows = 0
            total_columns = 0
            
            for sheet_name in sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
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
                    'file_size_bytes': os.path.getsize(file_path),
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
    
    async def _ingest_json(self, file_path: str) -> Dict[str, Any]:
        """Ingest JSON file and flatten nested structures.
        
        Args:
            file_path: Path to JSON
            
        Returns:
            Standardized result dict
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
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
                    'file_size_bytes': os.path.getsize(file_path),
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
    
    def validate_file(self, file_path: str) -> bool:
        """Validate file format and size.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if valid
        """
        if not os.path.exists(file_path):
            return False
        
        # Check extension
        ext = Path(file_path).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            return False
        
        # Check file size
        file_size = os.path.getsize(file_path)
        return file_size <= self.MAX_FILE_SIZE
    
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
