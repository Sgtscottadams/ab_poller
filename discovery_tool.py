#!/usr/bin/env python3
"""
Allen-Bradley PLC Tag Discovery Tool
Streamlined version with proper tag parsing
"""

import sys
import os
from datetime import datetime
from pycomm3 import LogixDriver
import json

class ABTagDiscovery:
    def __init__(self, plc_ip, slot=0):
        self.plc_ip = plc_ip
        self.slot = slot
        self.plc = None
        self.tags = {}
        self.plc_info = {}
        
    def connect(self):
        """Establish connection to the PLC"""
        try:
            print(f"Connecting to PLC at {self.plc_ip}, slot {self.slot}...")
            self.plc = LogixDriver(self.plc_ip, slot=self.slot)
            self.plc.open()
            
            self.plc_info = self.plc.get_plc_info()
            print(f"Connected to: {self.plc_info.get('product_name', 'Unknown PLC')}")
            
            revision = self.plc_info.get('revision', 'Unknown')
            if isinstance(revision, dict):
                print(f"Revision: {revision.get('major', '?')}.{revision.get('minor', '?')}")
            else:
                print(f"Revision: {revision}")
            return True
            
        except Exception as e:
            print(f"Connection failed: {str(e)}")
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
    
    def discover_tags(self):
        """Discover all tags from the PLC"""
        try:
            print("Discovering tags...")
            tags_raw = self.plc.get_tag_list()
            
            total_tags = len(tags_raw)
            print(f"Processing {total_tags} tags...")
            
            for idx, tag in enumerate(tags_raw, 1):
                tag_name = tag.get('tag_name', '')
                
                # Skip system tags
                if tag_name.startswith('__'):
                    continue
                
                # Parse tag information
                tag_info = self.parse_tag_info(tag)
                self.tags[tag_name] = tag_info
                
                # Update progress
                if idx % 10 == 0 or idx == total_tags:
                    self.show_progress(idx, total_tags, "Processing tags")
            
            print(f"\nDiscovered {len(self.tags)} user tags")
            return True
            
        except Exception as e:
            print(f"\nTag discovery failed: {str(e)}")
            return False
    
    def parse_tag_info(self, tag):
        """Parse tag information into a clean structure"""
        tag_info = {
            'data_type': str(tag.get('data_type', 'Unknown')),
            'members': {}
        }
        
        # Check if tag has internal structure (UDT/AOI)
        if isinstance(tag, dict):
            # Handle internal_tags structure
            if 'internal_tags' in tag:
                for member_name, member_data in tag.get('internal_tags', {}).items():
                    # Skip internal/system members
                    if not member_name.startswith('__'):
                        tag_info['members'][member_name] = member_data.get('data_type', 'Unknown')
            
            # Also check for direct member structure
            elif 'struct' in tag:
                for member in tag.get('struct', []):
                    if isinstance(member, dict):
                        member_name = member.get('name', '')
                        if member_name and not member_name.startswith('__'):
                            tag_info['members'][member_name] = member.get('data_type', 'Unknown')
        
        return tag_info
    
    def generate_markdown(self, output_file='plc_tags.md'):
        """Generate clean markdown file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            base_name = os.path.splitext(output_file)[0]
            
            # Format revision
            revision = self.plc_info.get('revision', 'N/A')
            if isinstance(revision, dict):
                revision_str = f"{revision.get('major', '?')}.{revision.get('minor', '?')}"
            else:
                revision_str = str(revision)
            
            # Organize tags
            structured_tags = {}
            simple_tags = {}
            
            for tag_name, tag_info in sorted(self.tags.items()):
                if tag_info['members']:
                    structured_tags[tag_name] = tag_info
                else:
                    simple_tags[tag_name] = tag_info
            
            # Write markdown file
            with open(output_file, 'w', encoding='utf-8') as f:
                # Header
                f.write(f"# PLC Tag Report\n\n")
                f.write(f"**Generated:** {timestamp}\n\n")
                
                # PLC Info
                f.write("## PLC Information\n\n")
                f.write(f"- **PLC:** {self.plc_info.get('product_name', 'N/A')} (Rev {revision_str})\n")
                f.write(f"- **IP:** {self.plc_ip} | **Slot:** {self.slot}\n")
                f.write(f"- **Total Tags:** {len(self.tags)}\n")
                f.write(f"- **Structured Tags:** {len(structured_tags)}\n")
                f.write(f"- **Simple Tags:** {len(simple_tags)}\n\n")
                
                # Structured Tags (limit to first 20 for readability)
                if structured_tags:
                    f.write("## Structured Tags\n\n")
                    
                    count = 0
                    for tag_name, tag_info in sorted(structured_tags.items()):
                        if count >= 20:  # Limit for file size
                            f.write(f"\n*... and {len(structured_tags) - 20} more structured tags*\n")
                            break
                        
                        f.write(f"### {tag_name}\n")
                        f.write(f"**Type:** {tag_info['data_type']}\n\n")
                        
                        # Member table
                        if tag_info['members']:
                            f.write("| Member | Type |\n")
                            f.write("|--------|------|\n")
                            
                            # Show first 15 members
                            member_items = sorted(tag_info['members'].items())
                            for member_name, member_type in member_items[:15]:
                                f.write(f"| {member_name} | {member_type} |\n")
                            
                            if len(member_items) > 15:
                                f.write(f"| *... +{len(member_items)-15} more* | - |\n")
                        
                        f.write("\n")
                        count += 1
                
                # Simple Tags (in a single table)
                if simple_tags:
                    f.write("## Simple Tags\n\n")
                    f.write("| Tag Name | Data Type |\n")
                    f.write("|----------|----------|\n")
                    
                    count = 0
                    for tag_name, tag_info in sorted(simple_tags.items()):
                        if count >= 50:  # Limit for file size
                            f.write(f"| *... +{len(simple_tags)-50} more* | - |\n")
                            break
                        f.write(f"| {tag_name} | {tag_info['data_type']} |\n")
                        count += 1
                
                f.write("\n---\n")
                f.write(f"*Full tag details saved in: {base_name}_full.json*\n")
            
            print(f"\nMarkdown report saved to: {output_file}")
            
            # Save full JSON
            self.save_json(f"{base_name}_full.json")
            
            return True
            
        except Exception as e:
            print(f"\nFailed to generate markdown: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_json(self, json_file):
        """Save complete tag data to JSON"""
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
            
            print(f"Full tag data saved to: {json_file}")
            return True
            
        except Exception as e:
            print(f"Failed to save JSON: {str(e)}")
            return False
    
    def disconnect(self):
        """Close PLC connection"""
        if self.plc:
            self.plc.close()
            print("Disconnected from PLC")
    
    def run(self, output_file='plc_tags.md'):
        """Execute complete discovery workflow"""
        success = False
        
        try:
            if not self.connect():
                return False
            
            if not self.discover_tags():
                return False
            
            success = self.generate_markdown(output_file)
            
        finally:
            self.disconnect()
        
        return success


def get_user_input():
    """Get configuration from user"""
    print("=" * 60)
    print("Allen-Bradley PLC Tag Discovery Tool")
    print("Streamlined Version")
    print("=" * 60)
    
    # Get IP
    while True:
        plc_ip = input("\nEnter PLC IP address: ").strip()
        if plc_ip:
            parts = plc_ip.split('.')
            if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                break
            print("Invalid IP address format.")
        else:
            print("IP address is required.")
    
    # Get slot
    slot_input = input("Enter processor slot [0]: ").strip()
    if slot_input:
        try:
            slot = int(slot_input)
        except ValueError:
            print("Invalid slot. Using default (0).")
            slot = 0
    else:
        slot = 0
    
    # Get filename
    output_file = input("Enter output filename [plc_tags.md]: ").strip()
    if not output_file:
        output_file = "plc_tags.md"
    
    if not output_file.endswith('.md'):
        output_file += '.md'
    
    return plc_ip, slot, output_file


def main():
    """Main execution"""
    plc_ip, slot, output_file = get_user_input()
    
    base_name = os.path.splitext(output_file)[0]
    
    print("\n" + "=" * 60)
    print("Configuration:")
    print(f"  PLC IP:      {plc_ip}")
    print(f"  Slot:        {slot}")
    print(f"  Output:      {output_file}")
    print(f"  JSON:        {base_name}_full.json")
    print("=" * 60)
    
    response = input("\nProceed? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled")
        return
    
    print()
    
    discovery = ABTagDiscovery(plc_ip, slot)
    
    if discovery.run(output_file):
        print("\n✓ Success!")
        print(f"  Markdown: {os.path.abspath(output_file)}")
        print(f"  JSON:     {os.path.abspath(base_name + '_full.json')}")
    else:
        print("\n✗ Failed - see errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()