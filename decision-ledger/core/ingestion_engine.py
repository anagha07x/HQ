"""Bulletproof data ingestion module - handles body lock issues."""

import pandas as pd
import json
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Tuple
from dataclasses import dataclass

from .dataset_registry import DatasetRegistry


@dataclass
class ParsedFile:
    """Container for parsed file data."""
    datasets: Dict[str, pd.DataFrame]
    metadata: Dict[str, Any]
    source_type: str


class DataIngestionEngine:
    """Bulletproof ingestion engine - processes raw bytes only.
    
    This engine NEVER touches UploadFile or request objects.
    All parsing is done from pre-captured bytes.
    """
    
    SUPPORTED_FORMATS = {'.csv', '.xlsx', '.xls', '.json'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    def ingest_from_bytes(
        self, 
        file_bytes: bytes, 
        filename: str, 
        dataset_id: str
    ) -> DatasetRegistry:
        """Ingest file from raw bytes - the ONLY entry point.
        
        This method receives already-captured bytes. It never reads
        from UploadFile, request.body(), or any stream.
        
        Args:
            file_bytes: Raw file bytes (already captured)
            filename: Original filename for extension detection
            dataset_id: Unique identifier for this dataset
            
        Returns:
            DatasetRegistry with parsed data
            
        Raises:
            ValueError: If file format not supported or parsing fails
        """
        # Validate extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {file_ext}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        file_size = len(file_bytes)
        
        # Validate size
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size / 1024 / 1024:.2f}MB "
                f"(max {self.MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )
        
        if file_size == 0:
            raise ValueError("Empty file received")
        
        # Create fresh BytesIO from bytes
        bytes_io = BytesIO(file_bytes)
        
        # Parse based on format
        source_type = self._get_source_type(file_ext)
        
        if source_type == 'csv':
            datasets, metadata = self._parse_csv(bytes_io, filename, file_size)
        elif source_type == 'xlsx':
            datasets, metadata = self._parse_xlsx(bytes_io, filename, file_size)
        elif source_type == 'json':
            datasets, metadata = self._parse_json(bytes_io, filename, file_size)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        return DatasetRegistry(
            dataset_id=dataset_id,
            source_type=source_type,
            datasets=datasets,
            metadata=metadata
        )
    
    def _get_source_type(self, file_ext: str) -> str:
        """Map file extension to source type."""
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
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        """Parse CSV from BytesIO."""
        bytes_io.seek(0)
        
        # Try different encodings and separators
        df = None
        last_error = None
        
        attempts = [
            {'encoding': 'utf-8'},
            {'encoding': 'utf-8', 'sep': ';'},
            {'encoding': 'latin-1'},
            {'encoding': 'latin-1', 'sep': ';'},
            {'encoding': 'cp1252'},
        ]
        
        for params in attempts:
            try:
                bytes_io.seek(0)
                df = pd.read_csv(bytes_io, **params)
                break
            except Exception as e:
                last_error = e
                continue
        
        if df is None:
            raise ValueError(f"Failed to parse CSV: {last_error}")
        
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
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        """Parse XLSX/XLS from BytesIO with multi-sheet support."""
        bytes_io.seek(0)
        
        try:
            # Determine engine based on extension
            file_ext = Path(filename).suffix.lower()
            engine = 'openpyxl' if file_ext == '.xlsx' else 'xlrd'
            
            # Read all sheets
            excel_file = pd.ExcelFile(bytes_io, engine=engine)
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
            raise ValueError(f"Failed to parse Excel file: {str(e)}")
    
    def _parse_json(
        self, 
        bytes_io: BytesIO, 
        filename: str, 
        file_size: int
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        """Parse JSON from BytesIO and flatten to DataFrame."""
        bytes_io.seek(0)
        
        try:
            raw_text = bytes_io.read().decode('utf-8')
            data = json.loads(raw_text)
            
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
        """Flatten nested JSON to DataFrame."""
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                return pd.json_normalize(data, sep='_')
            else:
                return pd.DataFrame({'value': data})
        
        elif isinstance(data, dict):
            if all(not isinstance(v, (dict, list)) for v in data.values()):
                return pd.DataFrame([data])
            
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    df = pd.json_normalize(value, sep='_')
                    for k, v in data.items():
                        if k != key and not isinstance(v, (dict, list)):
                            df[k] = v
                    return df
            
            return pd.json_normalize(data, sep='_')
        
        else:
            return pd.DataFrame({'value': [data]})
    
    def _analyze_json_structure(self, data: Any) -> str:
        """Analyze JSON structure type."""
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
