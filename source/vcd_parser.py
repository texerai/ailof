# Copyright (c) 2024 texer.ai. All rights reserved.

import json
import os
import re

class VcdParser:
    # A class to parse VCD files and generate JSON about the design structure.

    def __init__(self):
        """Initializes an empty VcdParser instance."""
        self.design_info = {}
        self.hierarchy = {}

    def parse_vcd(self, vcd_file_path, design_files_path):
        # Parses the VCD file and design files to generate a design hierarchy.

        # generate hierarchy
        with open(vcd_file_path, 'r') as vcd_file:
          lines = vcd_file.readlines()

        current_path = []
        skip_level = 0
        
        for line in lines:
          line = line.strip()

          scope_module_match = re.match(r"\$scope module (\S+) \$end", line)
          
          scope_struct_match = re.match(r"\$scope struct (\S+) \$end", line)
          scope_interface_match = re.match(r"\$scope interface (\S+) \$end", line)
          scope_union_match = re.match(r"\$scope union (\S+) \$end", line)

          if scope_module_match:
              if skip_level == 0:
                  module_name = scope_module_match.group(1)
                  current_path.append(module_name)

                  current_module = self.hierarchy
                  for path_part in current_path:
                      current_module = current_module.setdefault(path_part, {})

          elif scope_struct_match or scope_interface_match or scope_union_match:
              skip_level += 1

          elif line == "$upscope $end":
              if skip_level > 0:
                  skip_level -= 1
              elif current_path:
                  current_path.pop()

        # parse all modules and entities
        module_declarations = {}
        entity_to_class = {}
        entity_to_path = {}
        
        module_declaration_pattern = r'module\s+(\w+)(?:\s+import\s+[\w\.\*\:]*;)?\s*(?:#\([\s\S]*?\))?\s*\('
        module_entity_pattern = r'(\w+)\s+#\([\s\S]*?\)\s+(\w+)\s+\('
        
        for root, _, files in os.walk(design_files_path):
          for file in files:
              if file.endswith('.v') or file.endswith('.sv'):
                  filepath = os.path.join(root, file)
                  with open(filepath, 'r') as f:
                      content = f.read()
                      
                      modules = re.findall(module_declaration_pattern, content)
                      
                      for module in modules:
                          module_declarations[module] = filepath
                      
                      entities = re.findall(module_entity_pattern, content)
                      
                      for module_class, module_entity in entities:
                          entity_to_path[module_entity] = filepath
                          entity_to_class[module_entity] = module_class
            
        def process_node(node, current_path = ""):
            for key, value in node.items():
                full_path = f"{current_path}.{key}" if current_path else key
                
                self.design_info[full_path] = {
                    "declaration_path": None,
                    "initialization_path": None
                }
                
                if isinstance(value, dict):
                    process_node(value, full_path)
                    
        process_node(self.hierarchy)
        
        for path, _ in self.design_info.items():
          module_name = path.split('.')[-1]
                  
          if(module_declarations.get(module_name) is not None):
              self.design_info[path]['declaration_path'] = module_declarations.get(module_name)
              continue
          
          if(entity_to_path.get(module_name) is not None):
              self.design_info[path]['initialization_path'] = entity_to_path.get(module_name)
              module_class = entity_to_class.get(module_name)
              if(module_class is not None and module_declarations.get(module_class) is not None):
                  self.design_info[path]['declaration_path'] = module_declarations.get(module_class)
              continue
        
        
        self.design_info = {
          path: data for path, data in self.design_info.items()
          if data['declaration_path'] is not None or data['initialization_path'] is not None
        }
        
        return self.design_info

    def export_json(self, output_path):
        with open(output_path, 'w') as outfile:
          json.dump(self.design_info, outfile, indent=4)
        # Util. Exports the parsed design info as a JSON file.
        pass

if __name__ == "__main__":
    # Example usage
    parser = VcdParser()
    parser.parse_vcd('/Users/sanzhar/vcd_parcer/cva6/cva6.vcd', '/Users/sanzhar/vcd_parcer/cva6/design')
    parser.export_json('result.json')