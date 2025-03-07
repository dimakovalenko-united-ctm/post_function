#!/usr/bin/env python
import pkgutil
import inspect
from pydantic import BaseModel
import importlib

__all__ = []

# Dynamically discover and import all Pydantic models
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    # Dynamically import the module
    module = importlib.import_module(f"{__name__}.{module_name}")
    
    # Inspect the module for classes that inherit from Pydantic's BaseModel
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj.__module__ == module.__name__:
            globals()[name] = obj
            __all__.append(name)

# Advantages of This Approach
# Automatic Updates :
# You don't need to manually update the __all__ list when adding new models.
# Scalability :
# The solution scales well as the number of models grows.
# Clean Imports :
# Users of the models folder can import everything directly without worrying about individual files.
# Flexibility :
# You can customize the filtering logic to include only specific types of objects (e.g., Pydantic models).
# 
# Potential Caveats
# Performance :
# Dynamically inspecting and importing modules may introduce a slight overhead during initialization. However, this is negligible for most applications.
# Namespace Pollution :
# If the folder contains unrelated objects, they might accidentally be exported unless proper filtering is applied.
# Readability :
# While automatic exports are convenient, they may make it harder to see which objects are being exported at a glance.
