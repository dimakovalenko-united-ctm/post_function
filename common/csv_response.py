#!/usr/bin/env python
import csv
from io import StringIO
from fastapi.responses import Response
from fastapi.encoders import jsonable_encoder

class CSVResponse(Response):
    media_type = "text/csv"
    
    def render(self, content: any) -> bytes:
        # Convert to dict using jsonable_encoder
        dict_content = jsonable_encoder(content)
        
        # Handle list of objects or single object
        if not isinstance(dict_content, list):
            dict_content = [dict_content]
            
        # Create CSV
        output = StringIO()
        if dict_content:
            writer = csv.DictWriter(output, fieldnames=dict_content[0].keys())
            writer.writeheader()
            writer.writerows(dict_content)
            
        return output.getvalue().encode("utf-8")
