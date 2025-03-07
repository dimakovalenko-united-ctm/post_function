#!/usr/bin/env python
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from common.models.date_time_iso8601 import ApprovedDateTime as DateTime
from common.logging_utils import debug, exception
from common.models.http_response_model import HttpResponses, SuccessResponse, ErrorResponse, HttpResponseMetaData

from common.csv_response import CSVResponse

class FormatPandasToFormat:    

    @staticmethod
    def convert_format(data, format_type):
        """
        Convert a list of dictionaries to XML, CSV, or JSON format based on the specified format_type.
        
        Args:
            data (list): List of dictionaries containing the data
            format_type (str): The output format - 'xml', 'csv', or 'json'
            
        Returns:
            str: The formatted data as a string
        """
        import json
        import csv
        import io
        from xml.dom.minidom import getDOMImplementation
        
        if format_type.lower() == 'json':
            # Convert to JSON with indentation for readability
            return JSONResponse(jsonable_encoder(data))
        
        elif format_type.lower() == 'csv':
            # Use StringIO to create a CSV string
            output = io.StringIO()
            if data and len(data) > 0:
                # Get field names from the first dictionary
                fieldnames = data[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue()
        
        elif format_type.lower() == 'xml':
            #TODO: Finish implemet
            # Create XML document
            # Create the root structure first
            impl = getDOMImplementation()
            doc = impl.createDocument(None, "data", None)
            root = doc.documentElement

            metadata_elem = doc.createElement("metadata")
            root.appendChild(metadata_elem)

            # Add metadata fields
            for key, value in data['metadata'].items():
                if isinstance(value, dict):
                    # Handle nested dictionaries like 'query'
                    nested_elem = doc.createElement(key)
                    metadata_elem.appendChild(nested_elem)
                    
                    for sub_key, sub_value in value.items():
                        sub_elem = doc.createElement(sub_key)
                        nested_elem.appendChild(sub_elem)
                        
                        sub_text = doc.createTextNode(str(sub_value))
                        sub_elem.appendChild(sub_text)
                else:
                    # Handle simple metadata fields
                    meta_field = doc.createElement(key)
                    metadata_elem.appendChild(meta_field)
                    
                    meta_text = doc.createTextNode(str(value))
                    meta_field.appendChild(meta_text)

            # Create data section
            data_section = doc.createElement("data")
            root.appendChild(data_section)

            # Process actual data items
            for item in data['data']:
                # Create item element
                item_elem = doc.createElement("item")
                data_section.appendChild(item_elem)
                
                # Add all fields to the item element
                for key, value in item.items():
                    # Create element for this field
                    field_elem = doc.createElement(key)
                    item_elem.appendChild(field_elem)
                    
                    # Add text content
                    text_content = doc.createTextNode(str(value))
                    field_elem.appendChild(text_content)
            
            # Return formatted XML
            return doc.toprettyxml()
        
        else:
            raise ValueError(f"Unsupported format type: {format_type}. Supported formats are 'xml', 'csv', and 'json'.")

    # Example usage:
    # data = [{'id': 'aee97161-1d8e-4007-a71a-36ee0e0e76fe', ...}, {...}]
    # xml_output = convert_format(data, 'xml')
    # csv_output = convert_format(data, 'csv')
    # json_output = convert_format(data, 'json')

    @staticmethod
    def build_response(input_data: BaseModel, params: HttpResponses, start_timestamp: DateTime):                
        if params.output_format == 'csv':            
            #TODO: Implement CSV Building
            #If CSV, just return the data, no need to do other steps

            # import ipdb; ipdb.set_trace()
            CSVResponse.render(content=input_data)
            return_data = FormatPandasToFormat.convert_format(input_data, params.output_format)
            debug(f"Formatted Return: {return_data}")
        
            return return_data

        try:            
            return_data = FormatPandasToFormat.convert_format(input_data, params.output_format)
            
            debug(f"Formatted Return: {return_data}")
            return return_data
        except Exception as e:
            exception(f"Error converting data to: {e}")
            raise e


