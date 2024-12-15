# VCD Parser Module

## Overview
The **VCD Parser** module is designed to parse VCD (Value Change Dump) files and generate a structured representation of the design hierarchy, module declarations, and entity initializations. The module outputs a JSON file containing detailed information about the design structure for further analysis or processing.

## Features
- Parses VCD files to generate a design hierarchy.
- Extracts and organizes module declarations, entity initializations, and parent module relationships.
- Outputs a JSON representation of the design with detailed paths for module declarations and initializations.

## Installation

## Usage
To use the VCD Parser module, ensure you have the following dependencies installed:

- Python 3.6+
- Standard Python libraries (`json`, `os`, `re`)

Here is an example of how to use the module in your Python script:

```python
from vcd_parser import VcdParser

# Initialize the parser
parser = VcdParser()

# Parse the VCD file and extract design information
parser.parse_vcd(
    '/path/to/vcd/hello_world.cv32a60x.vcd',
    '/path/to/design/files/cva6'
)

# Export the parsed data to a JSON file
parser.export_json('result.json')
```

## Output Structure
The JSON output contains hierarchical design information, including module declarations and initialization paths. Below is an example of the output structure:

```json
{
    "TOP.ariane_testharness": {
        "declaration_path": "/path/to/design/corev_apu/tb/ariane_testharness.sv",
        "initialization_path": null
    },
    "TOP.ariane_testharness.i_ariane": {
        "declaration_path": "/path/to/design/corev_apu/src/ariane.sv",
        "initialization_path": "/path/to/design/corev_apu/fpga/src/ariane_xilinx.sv"
    }
}
```
