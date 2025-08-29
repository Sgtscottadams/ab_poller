#!/usr/bin/env python3
"""
Allen-Bradley PLC Tag Discovery Tool
Final, robust version built from direct analysis of PLC debug data.
"""

import sys
import os
import logging
from datetime import datetime
from pycomm3 import LogixDriver
import json

# --- Setup logging to a file ---
log_file = 'discovery_tool.log'
# Clear previous log file if it exists
if os.path.exists(log_file):
    os.remove(log_file)
    
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# --------------------------------

class ABTagDiscovery:
    def __init__(self, plc_ip, slot=0):
        self.plc_ip = plc_ip
        self.slot = slot
        self.plc = None
        self.tags = {}
        self.plc_info = {}
        
    def connect(self):
        """
        Establish a stable connection to the PLC without pre-loading tags.
        """
        try:
            print(f"Connecting to PLC at {self.plc_ip}, slot {self.slot}...")
            logging.info(f"Attempting connection to {self.plc_ip} on slot {self.slot}")
            self.plc = LogixDriver(self.plc_ip, slot=self.slot, timeout=5, init_tags=False)
            self.plc.open()
            
            self.plc_info = self.plc.get_plc_info()
            print(f"Connected to: {self.plc_info.get('product_name', 'Unknown PLC')}")
            logging.info(f"Successfully connected to {self.plc_info.get('product_name')}")
            
            revision = self.plc_info.get('revision', 'Unknown')
            if isinstance(revision, dict):
                print(f"Revision: {revision.get('major', '?')}.{revision.get('minor', '?')}")
            else:
                print(f"Revision: {revision}")
            return True
            
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            logging.error(f"Connection failed: {e}", exc_info=True)
            return False
    
    def show_progress(self, current, total, message="Processing"):
        """Display a progress bar"""
        if total == 0:
            return
        bar_length = 40
        progress = current / total
        filled = int(bar_length * progress)
        bar = '█' * filled + '░' * (bar_length - filled)
        percent = progress * 100
        sys.stdout.write(f'\r{message}: [{bar}] {percent:.1f}% ({current}/{total})')
        sys.stdout.flush()
        if current == total:
            print()

    def _parse_structure_def(self, tag_def):
        """
        Recursively parses a full tag definition dictionary based on the known structure
        from the diagnostic data.
        """
        # A simple helper to get a consistent string name for a data type
        def get_type_name(data_type_value):
            if isinstance(data_type_value, dict):
                return data_type_value.get('name', 'STRUCT')
            return str(data_type_value)

        # THE DEFINITIVE FIX: Based on the debug log, the members are located in
        # the 'internal_tags' dictionary within the 'data_type' dictionary.
        members_source = None
        if 'data_type' in tag_def and isinstance(tag_def['data_type'], dict):
            members_source = tag_def['data_type'].get('internal_tags')

        # If we couldn't find members in the expected place, it's a simple type.
        if not members_source:
            logging.debug(f"Parsing as simple type. Definition: {tag_def}")
            return get_type_name(tag_def.get('data_type', 'Unknown'))
        
        # Build the parsed structure
        structure = {
            '_data_type_': get_type_name(tag_def.get('data_type', 'UDT')),
            'members': {}
        }
        logging.debug(f"Parsing structure '{structure['_data_type_']}'.")

        for member_name, member_data in members_source.items():
            if not member_name.startswith('__'):
                # Recursively parse each member of the structure
                structure['members'][member_name] = self._parse_structure_def(member_data)
        
        return structure

    def discover_tags(self):
        """
        Discovers tags by getting a list of names, then retrieving the full definition
        for each tag individually for maximum stability.
        """
        try:
            print("Discovering tags...")
            logging.info("Starting tag discovery.")
            initial_tag_list = []
            failed_scopes = []

            # Get a lightweight list of controller-scoped tag names.
            print("--> Getting controller-scoped tag list...")
            try:
                controller_tags = self.plc.get_tag_list()
                if controller_tags:
                    initial_tag_list.extend(controller_tags)
                    print(f"    Found {len(controller_tags)} controller tags.")
                    logging.info(f"Found {len(controller_tags)} controller-scoped tags.")
            except Exception as e:
                print(f"    WARNING: Could not retrieve controller-scoped tags. Error: {e}")
                logging.warning("Failed to retrieve controller-scoped tags.", exc_info=True)
                failed_scopes.append("Controller Scope")

            # Get a lightweight list of program-scoped tag names.
            print("--> Getting program-scoped tag list...")
            program_names = []
            try:
                programs_tag = self.plc.read('PROGRAM')
                if programs_tag and programs_tag.value:
                    program_names = programs_tag.value
            except Exception as e:
                 print(f"    WARNING: Could not retrieve program list. Error: {e}")
                 logging.warning("Failed to retrieve program list.", exc_info=True)

            if program_names:
                print(f"    Found {len(program_names)} programs.")
                logging.info(f"Found programs: {program_names}")
                for prog_name in program_names:
                    try:
                        program_tags = self.plc.get_tag_list(program=prog_name)
                        if program_tags:
                            for tag in program_tags:
                                tag['tag_name'] = f"Program:{prog_name}.{tag['tag_name']}"
                            initial_tag_list.extend(program_tags)
                            print(f"    + {len(program_tags)} tags from '{prog_name}'.")
                            logging.info(f"Found {len(program_tags)} tags in program '{prog_name}'.")
                    except Exception as e:
                        print(f"    WARNING: Could not retrieve tags for program '{prog_name}'. Error: {e}")
                        logging.warning(f"Failed to retrieve tags for program '{prog_name}'.", exc_info=True)
                        failed_scopes.append(f"Program:{prog_name}")
            else:
                print("    No programs found.")
                logging.info("No programs found in PLC.")
            
            if not initial_tag_list:
                print("\nERROR: Failed to retrieve any tags from the PLC.")
                logging.error("No tags could be retrieved from the PLC.")
                return False

            # Process the list, getting the full definition for each tag one by one.
            total_tags = len(initial_tag_list)
            print(f"\nProcessing {total_tags} tags (retrieving full definitions)...")
            
            for idx, tag_summary in enumerate(initial_tag_list):
                tag_name = tag_summary.get('tag_name')
                if not tag_name or tag_name.startswith('__') or tag_name.startswith('System:'):
                    continue
                
                try:
                    full_tag_def = self.plc.get_tag_info(tag_name)
                    logging.debug(f"Full definition for '{tag_name}': {json.dumps(full_tag_def, indent=2, default=str)}")
                    self.tags[tag_name] = self._parse_structure_def(full_tag_def)
                except Exception as e:
                    print(f"\n--> WARNING: Could not get full definition for tag '{tag_name}'. Using summary info. Error: {e}")
                    logging.warning(f"Could not get full definition for tag '{tag_name}'.", exc_info=True)
                    self.tags[tag_name] = tag_summary.get('data_type', 'UNKNOWN')

                self.show_progress(idx + 1, total_tags, "Processing definitions")
            
            print(f"\nSuccessfully processed {len(self.tags)} user tags.")
            logging.info(f"Finished processing. Found {len(self.tags)} user tags.")
            return True
            
        except Exception as e:
            print(f"\nAn unexpected error occurred during tag discovery: {str(e)}")
            logging.error("An unexpected error occurred during tag discovery.", exc_info=True)
            import traceback
            traceback.print_exc()
            return False
    
    def generate_report(self, output_file='plc_tags.md'):
        """
        Generate a clean markdown report with a flat table of full, expanded tag paths.
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            base_name = os.path.splitext(output_file)[0]
            
            revision = self.plc_info.get('revision', 'N/A')
            revision_str = f"{revision['major']}.{revision['minor']}" if isinstance(revision, dict) else str(revision)

            flat_tag_list = []
            def flatten_recursive(tag_name_prefix, tag_info):
                if isinstance(tag_info, dict) and 'members' in tag_info:
                    if not tag_info['members']:
                        data_type = tag_info.get('_data_type_', 'STRUCT')
                        flat_tag_list.append({'path': tag_name_prefix, 'type': data_type})
                    else:
                        for member_name, member_info in sorted(tag_info['members'].items()):
                            flatten_recursive(f"{tag_name_prefix}.{member_name}", member_info)
                else:
                    flat_tag_list.append({'path': tag_name_prefix, 'type': tag_info})

            for tag_name, tag_info in sorted(self.tags.items()):
                flatten_recursive(tag_name, tag_info)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# PLC Tag Report\n\n")
                f.write(f"**Generated:** {timestamp}\n\n")
                
                f.write("## PLC Information\n\n")
                f.write(f"- **PLC:** {self.plc_info.get('product_name', 'N/A')} (Rev {revision_str})\n")
                f.write(f"- **IP:** {self.plc_ip} | **Slot:** {self.slot}\n")
                f.write(f"- **Total User Tags (Top Level):** {len(self.tags)}\n")
                f.write(f"- **Total Pollable Tag Paths:** {len(flat_tag_list)}\n\n")
                
                f.write("## Tag List\n\n")
                f.write("This table contains the full tag paths required for SCADA/HMI configuration.\n\n")
                f.write("| Full Tag Path | Data Type |\n")
                f.write("|---------------|-----------|\n")
                
                for tag in flat_tag_list:
                    path_str = tag['path'].replace('|', '\\|')
                    type_str = str(tag['type']).replace('|', '\\|')
                    f.write(f"| `{path_str}` | `{type_str}` |\n")

                f.write("\n---\n")
                f.write(f"*Full, nested tag hierarchy saved in: `{base_name}_full.json`*\n")
            
            print(f"\nMarkdown report saved to: {output_file}")
            
            self.save_json(f"{base_name}_full.json")
            return True
            
        except Exception as e:
            print(f"\nFailed to generate report: {str(e)}")
            logging.error("Failed to generate report.", exc_info=True)
            import traceback
            traceback.print_exc()
            return False
    
    def save_json(self, json_file):
        """Save complete tag data to a nested JSON file."""
        try:
            output_data = {
                'scan_info': {
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'plc_ip': self.plc_ip,
                    'slot': self.slot,
                    'plc_product': self.plc_info.get('product_name', 'Unknown')
                },
                'tags': self.tags
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, default=str)
            
            print(f"Full nested tag data saved to: {json_file}")
            return True
            
        except Exception as e:
            print(f"Failed to save JSON: {str(e)}")
            logging.error(f"Failed to save JSON file '{json_file}'.", exc_info=True)
            return False
    
    def disconnect(self):
        """Close PLC connection"""
        if self.plc and self.plc.connected:
            self.plc.close()
            print("Disconnected from PLC")
            logging.info("Disconnected from PLC.")
    
    def run(self, output_file='plc_tags.md'):
        """Execute complete discovery workflow"""
        success = False
        try:
            if not self.connect():
                return False
            if not self.discover_tags():
                return False
            success = self.generate_report(output_file)
        finally:
            self.disconnect()
        return success

def get_user_input():
    """Get configuration from user, with streamlined flow."""
    print("-" * 60)
    
    while True:
        plc_ip = input("Enter PLC IP address: ").strip()
        if plc_ip:
            parts = plc_ip.split('.')
            if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                break
            print("Invalid IP address format. Please try again.")
        else:
            print("IP address is required.")
    
    while True:
        slot_input = input("Enter processor slot [default: 0]: ").strip()
        if not slot_input:
            slot = 0
            break
        try:
            slot = int(slot_input)
            break
        except ValueError:
            print("Invalid slot. Please enter a number.")
            
    return plc_ip, slot

def main():
    """Main execution loop with improved user experience."""
    print("=" * 60)
    print("Allen-Bradley PLC Tag Discovery Tool")
    print(f"(Debug log will be written to: {os.path.abspath(log_file)})")
    print("=" * 60)

    while True:
        plc_ip, slot = get_user_input()
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
        output_file = f"{timestamp_str}_plc_tags.md"
        base_name = os.path.splitext(output_file)[0]
        
        print("\n" + "=" * 60)
        print("Configuration:")
        print(f"  PLC IP:      {plc_ip}")
        print(f"  Slot:        {slot}")
        print(f"  Output File: {output_file}")
        print(f"  JSON File:   {base_name}_full.json")
        print("=" * 60)
        
        response = input("\nProceed with this configuration? [Y/n]: ").strip().lower()
        
        if response == 'n':
            while True:
                restart_choice = input("Would you like to (r)estart configuration or (e)xit? ").strip().lower()
                if restart_choice in ['r', 'e']:
                    break
                print("Invalid choice. Please enter 'r' or 'e'.")
            
            if restart_choice == 'e':
                print("Exiting.")
                return
            else:
                print("\nRestarting configuration...\n")
                continue
        
        print()
        discovery = ABTagDiscovery(plc_ip, slot)
        
        if discovery.run(output_file):
            print("\n✓ Success!")
            print(f"  Markdown Report: {os.path.abspath(output_file)}")
            print(f"  JSON Data File:  {os.path.abspath(base_name + '_full.json')}")
        else:
            print("\n✗ Failed - see errors above")
        
        run_again = input("\nScan another PLC? (y/n): ").strip().lower()
        if run_again != 'y':
            print("Exiting.")
            break
        print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

